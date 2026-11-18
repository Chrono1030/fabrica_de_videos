"""Persisted narration stages inside the existing job, with dependency-based caching."""

import hashlib
import json
import time
import uuid
from pathlib import Path

from .audio_providers import (
    ExternalAudio,
    NarrationBlocked,
    create_audio_provider,
    inspect_wav,
)
from .narration_timeline import (
    NarrationTimeline,
    calculate_timing,
    plan_narration,
    retime_storyboard,
)
from .renderers.runtime import command, sha
from .tts import MockTTS


def signature(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


class NarrationStages:
    """The caller owns produce()'s job lock. Inputs, not list order, invalidate stages."""

    def __init__(self, job, state, save):
        self.job, self.state, self.save = Path(job).resolve(), state, save
        self.cache = state.setdefault("narration_cache", {})

    def run(self, name, outputs, inputs, action):
        token = signature(inputs)
        previous = self.cache.get(name)
        if (
            previous
            and previous["input"] == token
            and all(
                p.is_file()
                and sha(p) == previous["outputs"].get(str(p.relative_to(self.job)))
                for p in outputs
            )
        ):
            self.state["stages"][name] = {p.name: sha(p) for p in outputs}
            return False
        self.state["events"].append(dict(status=name + "_STARTED", at=time.time()))
        self.save(self.job / "result.json", self.state)
        try:
            action()
            if not all(p.is_file() for p in outputs):
                raise ValueError(
                    "Narration stage did not produce all required artifacts"
                )
        except Exception as exc:
            self.state["events"].append(
                dict(
                    status=name + "_FAILED",
                    error_type=type(exc).__name__,
                    at=time.time(),
                )
            )
            self.save(self.job / "result.json", self.state)
            raise
        self.cache[name] = dict(
            input=token, outputs={str(p.relative_to(self.job)): sha(p) for p in outputs}
        )
        self.state["stages"][name] = {p.name: sha(p) for p in outputs}
        self.state["status"] = name
        self.state["events"].append(dict(status=name, at=time.time()))
        self.save(self.job / "result.json", self.state)
        return True


def prepare_narration(board, job, job_id, config, renderer_config, stages, save):
    job = Path(job).resolve()
    audio = job / "audio"
    audio.mkdir(exist_ok=True)
    requests = plan_narration(board, config.currency)
    if set(config.mock_durations) - {r["segment_id"] for r in requests}:
        raise ValueError("Unknown segment in MOCK duration overrides")
    request_path = job / "narration_request.json"
    stages.run(
        "NARRATION_PLAN",
        [request_path],
        requests,
        lambda: save(
            request_path,
            {
                "segments": requests,
                "caption_alignment": "one measured WAV per phrase, not word alignment",
            },
        ),
    )
    try:
        bundle = create_audio_provider(config)
    except NarrationBlocked as exc:
        save(
            job / "manifest.json",
            dict(
                status=exc.code,
                publish_ready=False,
                provider=config.provider,
                reason=str(exc),
            ),
        )
        raise
    records = []
    try:
        for index, request in enumerate(requests):
            provenance = bundle.provenance
            chosen_seconds = config.mock_durations.get(
                request["segment_id"], config.mock_seconds
            )
            if isinstance(bundle.provider, ExternalAudio):
                clip, path, _ = bundle.provider.authorize(
                    request["segment_id"], request["spoken_text_sha256"]
                )
                provenance = provenance | {
                    "clip": clip.model_dump(mode="json"),
                    "actual_source_sha256": sha(path),
                }
            inputs = dict(
                request=request,
                spoken_text=request["spoken_text"],
                provider=provenance,
                mock_seconds=chosen_seconds if config.provider == "mock" else None,
                piper_scale=config.piper_length_scale,
                sample_rate=config.sample_rate,
                channels=config.channels,
            )
            directory = audio / f"s{index:04}-{signature(inputs)[:16]}"
            directory.mkdir(exist_ok=True)
            raw, normalized, receipt = (
                directory / "raw.wav",
                directory / "normalized.wav",
                directory / "segment.json",
            )

            def action(
                req=request,
                raw=raw,
                target=normalized,
                record=receipt,
                seconds=chosen_seconds,
                provenance=provenance,
            ):
                temporary = raw.with_name(f"raw-{uuid.uuid4().hex}.partial.wav")
                started = time.perf_counter()
                try:
                    if config.provider == "external":
                        bundle.provider.synthesize_segment(req, temporary)
                    elif config.provider == "mock":
                        MockTTS(seconds).synthesize(req["spoken_text"], temporary)
                    else:
                        bundle.provider.synthesize(req["spoken_text"], temporary)
                    measured = inspect_wav(temporary)
                    temporary.replace(raw)
                finally:
                    temporary.unlink(missing_ok=True)
                synthesis_seconds = time.perf_counter() - started
                normalized_tmp = target.with_name(
                    f"normalized-{uuid.uuid4().hex}.partial.wav"
                )
                try:
                    command(
                        [
                            "ffmpeg",
                            "-v",
                            "error",
                            "-i",
                            raw,
                            "-map",
                            "0:a:0",
                            "-ar",
                            config.sample_rate,
                            "-ac",
                            config.channels,
                            "-c:a",
                            "pcm_s16le",
                            normalized_tmp,
                        ],
                        config=renderer_config,
                        directory=directory,
                        timeout=config.timeout_seconds,
                    )
                    info = inspect_wav(normalized_tmp)
                    if abs(info["duration"] - measured["duration"]) > max(
                        2 / measured["sample_rate"], 2 / info["sample_rate"]
                    ):
                        raise ValueError(
                            "Format normalization unexpectedly changed narration duration"
                        )
                    normalized_tmp.replace(target)
                finally:
                    normalized_tmp.unlink(missing_ok=True)
                save(
                    record,
                    dict(
                        **req,
                        raw_wav=str(raw),
                        wav=str(target),
                        raw=measured,
                        normalized=info,
                        provider=provenance,
                        synthesis_wall_seconds=synthesis_seconds,
                        estimated_api_cost_usd=0,
                    ),
                )

            stages.run(
                f"AUDIO_SEGMENT_{index:04}", [raw, normalized, receipt], inputs, action
            )
            records.append(json.loads(receipt.read_text()))
    finally:
        if hasattr(bundle.provider, "close"):
            bundle.provider.close()
    index_path = job / "audio_segments.json"
    stages.run(
        "AUDIO_READY",
        [index_path],
        records,
        lambda: save(
            index_path,
            {
                "segments": records,
                "provider": bundle.provenance,
                "audio_is_mock": config.provider == "mock",
            },
        ),
    )
    timeline_path = job / "narration_timeline.json"
    wav_path = job / "narration.wav"
    visual_path = job / "visual_storyboard.json"
    board_path = job / "storyboard.json"
    timing_inputs = dict(
        records=records,
        base_storyboard=board.model_dump(mode="json"),
        phrase_pause=config.phrase_pause,
        scene_pause=config.scene_pause,
        max_seconds=config.max_seconds,
        sample_rate=config.sample_rate,
        channels=config.channels,
        authorization_mode=config.authorization_mode,
    )

    def timeline_action():
        segments, spans, total = calculate_timing(board, records, config)
        listing = []
        for record, segment in zip(records, segments):
            listing.append(
                "file '"
                + str(Path(record["wav"]).relative_to(audio)).replace("\\", "/")
                + "'"
            )
            count = round(segment["pause_after"] * config.sample_rate)
            if count:
                pause = (
                    audio / f"pause-{config.sample_rate}-{config.channels}-{count}.wav"
                )
                if not pause.exists():
                    command(
                        [
                            "ffmpeg",
                            "-v",
                            "error",
                            "-f",
                            "lavfi",
                            "-i",
                            f"anullsrc=r={config.sample_rate}:cl={'mono' if config.channels == 1 else 'stereo'}",
                            "-t",
                            f"{count / config.sample_rate:.12f}",
                            "-c:a",
                            "pcm_s16le",
                            pause,
                        ],
                        config=renderer_config,
                        directory=audio,
                    )
                if inspect_wav(pause)["samples"] != count:
                    raise ValueError("Pause samples differ from the planned gap")
                listing.append(f"file '{pause.name}'")
        concat = audio / "narration.ffconcat"
        concat.write_text("\n".join(listing) + "\n")
        temporary = audio / f"narration-{uuid.uuid4().hex}.partial.wav"
        try:
            command(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-f",
                    "concat",
                    "-safe",
                    "1",
                    "-i",
                    concat,
                    "-c:a",
                    "pcm_s16le",
                    temporary,
                ],
                config=renderer_config,
                directory=audio,
                timeout=config.timeout_seconds,
            )
            actual = inspect_wav(temporary)
            if actual["samples"] != total:
                raise ValueError(
                    "Assembled narration differs from measured audio and pauses"
                )
            temporary.replace(wav_path)
        finally:
            temporary.unlink(missing_ok=True)
        timeline = NarrationTimeline(
            job_id=job_id,
            sample_rate=config.sample_rate,
            channels=config.channels,
            duration=total / config.sample_rate,
            total_samples=total,
            wav=wav_path,
            sha256=sha(wav_path),
            segments=segments,
            scene_spans=spans,
            audio_is_mock=config.provider == "mock",
            authorization_mode=config.authorization_mode,
        )
        adjusted = retime_storyboard(board, timeline)
        save(timeline_path, timeline.model_dump(mode="json"))
        save(visual_path, adjusted.model_dump(mode="json"))
        save(board_path, adjusted.model_dump(mode="json"))

    stages.run(
        "TIMELINE_READY",
        [timeline_path, wav_path, visual_path, board_path],
        timing_inputs,
        timeline_action,
    )
    timeline = NarrationTimeline.model_validate_json(timeline_path.read_text())
    if sha(wav_path) != timeline.sha256:
        raise ValueError("Narration hash mismatch")
    adjusted = type(board).model_validate_json(visual_path.read_text())
    return adjusted, timeline
