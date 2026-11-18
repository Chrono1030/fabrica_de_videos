"""Audio stages of the main visual job; native engines render only the timed visuals."""

import json
import resource
import shutil
import time
import uuid
from pathlib import Path

from .narration_audio import NarrationStages, prepare_narration, signature
from .narration_subtitles import write_subtitles
from .narration_timeline import NarrationTimeline, plan_narration
from .renderers import select_renderer
from .renderers.runtime import command, sha
from .visual_storyboard import VisualStoryboard


def narrated_stages(*, board, job, job_id, config, narration_config, state, save):
    job = Path(job).resolve()
    stages = NarrationStages(job, state, save)
    # A packaged video and all its dependencies are immutable on recovery.
    binding = job / "metadata.json"
    if not binding.exists():
        binding = job / "publication-binding.json"
    if binding.exists():
        if (
            not (job / "final.mp4").is_file()
            or sha(job / "final.mp4") != json.loads(binding.read_text())["asset_hash"]
        ):
            raise ValueError("Packaged audiovisual asset changed; create a new job")
        for entry in stages.cache.values():
            if any(
                not (job / p).is_file() or sha(job / p) != digest
                for p, digest in entry["outputs"].items()
            ):
                raise ValueError(
                    "Packaged narration artifacts changed; create a new job"
                )
    if binding.exists():
        existing = VisualStoryboard.model_validate_json(
            (job / "storyboard.json").read_text()
        )
        visual = existing.model_copy(update={"audio": "none"})
        if signature(select_renderer(config).inputs(visual)) != state.get(
            "render_inputs"
        ):
            raise ValueError("Packaged renderer inputs changed; create a new job")
        planned = plan_narration(board, narration_config.currency)
        if stages.cache.get("NARRATION_PLAN", {}).get("input") != stages.token(
            "NARRATION_PLAN", planned
        ):
            raise ValueError("Packaged narration text changed; create a new job")
    adjusted, timeline = prepare_narration(
        board, job, job_id, narration_config, config, stages, save
    )
    caption_files = [
        job / x for x in ("subtitles.srt", "subtitles.ass", "subtitle_validation.json")
    ]
    stages.run(
        "SUBTITLES",
        caption_files,
        dict(
            timeline=timeline.model_dump(mode="json"),
            size=narration_config.subtitle_size,
            margin=narration_config.subtitle_margin,
            safe_area=adjusted.safe_area.model_dump(),
            canvas=[adjusted.width, adjusted.height],
        ),
        lambda: write_subtitles(timeline, adjusted, narration_config, job, save),
    )
    renderer = select_renderer(config)
    silent_board = adjusted.model_copy(update={"audio": "none"})
    visual_inputs = renderer.inputs(silent_board)
    silent, metrics, thumb = [
        job / p for p in ("video_silent.mp4", "render.json", "thumbnail.png")
    ]

    def render():
        directory = job / "render" / ("attempt-" + uuid.uuid4().hex)
        product = renderer.render(renderer.prepare(silent_board, directory))
        pending = job / (".silent-" + uuid.uuid4().hex + ".mp4")
        shutil.copyfile(product.video, pending)
        if sha(pending) != product.metrics["sha256"]:
            raise ValueError("Silent render promotion hash mismatch")
        pending.replace(silent)
        shutil.copyfile(product.thumbnail, thumb)
        save(
            metrics,
            product.metrics
            | {
                "quality": product.quality,
                "attempt_directory": str(directory),
                "asset_role": "silent_visual",
            },
        )

    stages.run("VIDEO_RENDERED", [silent, metrics, thumb], visual_inputs, render)
    final, qa, manifest = [job / p for p in ("final.mp4", "qa.json", "manifest.json")]
    compose_inputs = dict(
        silent=sha(silent),
        audio=timeline.sha256,
        captions=sha(job / "subtitles.ass"),
        font=sha(config.font_path),
        channels=timeline.channels,
        recipe="h264-aac-ass-v1",
    )

    def compose():
        directory = job / "composition" / uuid.uuid4().hex
        directory.mkdir(parents=True)
        shutil.copyfile(job / "subtitles.ass", directory / "subtitles.ass")
        (directory / "fonts").mkdir()
        shutil.copyfile(config.font_path, directory / "fonts" / "brand.ttf")
        temporary = directory / "composed.mp4"
        started = time.perf_counter()
        before = resource.getrusage(resource.RUSAGE_CHILDREN)
        command(
            [
                "ffmpeg",
                "-v",
                "error",
                "-i",
                silent,
                "-i",
                job / "narration.wav",
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-vf",
                "ass=subtitles.ass:fontsdir=fonts",
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "18",
                "-threads",
                "2",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-ar",
                "48000",
                "-ac",
                timeline.channels,
                "-movflags",
                "+faststart",
                temporary,
            ],
            config=config,
            directory=directory,
            timeout=config.timeout_seconds,
        )
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        quality = renderer.inspect(
            temporary, adjusted, directory / "qa", expect_audio=True
        )
        if (quality["audio_sample_rate"], quality["audio_channels"]) != (
            48000,
            timeline.channels,
        ):
            raise ValueError("Unexpected final audio format")
        if abs(quality["audio_duration"] - timeline.duration) > 0.05:
            raise ValueError("Final narration duration differs from measured WAV")
        quality.update(
            audio_sha256=timeline.sha256,
            subtitle_validation=json.loads(
                (job / "subtitle_validation.json").read_text()
            ),
            synchronization=timeline.alignment,
            composition_wall_seconds=time.perf_counter() - started,
            composition_cpu_seconds=(
                after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime
            ),
            children_max_rss_kib=after.ru_maxrss,
            max_rss_scope="process lifetime child high-water mark; not isolated composition RAM",
            publish_ready=False,
        )
        pending = job / (".final-" + uuid.uuid4().hex + ".mp4")
        shutil.copyfile(temporary, pending)
        pending.replace(final)
        save(qa, quality)

    stages.run("SUBTITLED", [final, qa], compose_inputs, compose)
    assets = [
        job / p
        for p in (
            "narration.wav",
            "narration_timeline.json",
            "visual_storyboard.json",
            "video_silent.mp4",
            "subtitles.srt",
            "subtitles.ass",
            "final.mp4",
            "qa.json",
        )
    ]
    stages.run(
        "TECHNICAL_QA_READY",
        [manifest],
        {p.name: sha(p) for p in assets},
        lambda: save(
            manifest,
            dict(
                status="TECHNICAL_QA_READY",
                publish_ready=False,
                audio_is_mock=timeline.audio_is_mock,
                commercial_export_authorized=narration_config.authorization_mode
                == "commercial",
                requires_review=["content", "voice", "rights", "pronunciation"],
                artifacts={
                    p.name: dict(path=str(p), sha256=sha(p), bytes=p.stat().st_size)
                    for p in assets
                },
            ),
        ),
    )
    state["stages"]["RENDER"] = {p.name: sha(p) for p in (final, metrics, thumb)}
    state.update(
        renderer=config.renderer,
        render_metrics=json.loads(metrics.read_text()),
        quality=json.loads(qa.read_text()),
        duration=timeline.duration,
        scene_durations=[s.end - s.start for s in adjusted.scenes],
        audio_simulated=timeline.audio_is_mock,
        audio_present=True,
        storyboard=str(job / "storyboard.json"),
        narrative_anchors=str(job / "narration_timeline.json"),
        thumbnail=str(thumb),
        render_inputs=signature(visual_inputs),
        final_inputs=signature(compose_inputs),
        publish_enabled=False,
        editorial_status="REQUIRES_REVIEW",
    )


def inspect_narrated_job(job, config):
    job = Path(job).resolve()
    manifest = json.loads((job / "manifest.json").read_text())
    for name, entry in manifest["artifacts"].items():
        if sha(job / name) != entry["sha256"]:
            raise ValueError("Audiovisual artifact hash mismatch: " + name)
    timeline = NarrationTimeline.model_validate_json(
        (job / "narration_timeline.json").read_text()
    )
    if sha(job / "narration.wav") != timeline.sha256:
        raise ValueError("Narration hash mismatch")
    board = VisualStoryboard.model_validate_json((job / "storyboard.json").read_text())
    return select_renderer(config).inspect(
        job / "final.mp4",
        board,
        job / "validation" / uuid.uuid4().hex,
        expect_audio=True,
    )
