"""Measured audio timeline and engine-independent visual retiming."""

import hashlib
import math
import re
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from .normalization import normalize
from .subtitle_style import cues
from .visual_storyboard import StrictModel, VisualStoryboard


def text_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def plan_narration(board, currency=None):
    requests = []
    for scene in board.scenes:
        phrases = []
        for sentence in re.split(r"(?<=[.!?])\s+(?=[¿¡A-ZÁÉÍÓÚÑ])", scene.narrative):
            if len(cues(sentence)) <= 1:
                phrases.extend(cues(sentence))
                continue
            current = ""
            for clause in re.split(r"(?<=[,;:])\s+", sentence):
                combined = (current + " " + clause).strip()
                if current and len(cues(combined)) > 1:
                    phrases.extend(cues(current))
                    current = clause
                else:
                    current = combined
            phrases.extend(cues(current))
        if not phrases:
            raise ValueError("Empty narrative segment")
        for index, subtitle in enumerate(phrases, 1):
            editorial = " ".join(subtitle.split())
            spoken = normalize(
                editorial, currency or board.source_metadata.get("currency")
            )
            requests.append(
                dict(
                    segment_id=f"{scene.narrative_segment_id}--p{index:03}",
                    scene_id=scene.id,
                    parent_segment_id=scene.narrative_segment_id,
                    editorial_text=editorial,
                    spoken_text=spoken,
                    subtitle_text=subtitle,
                    spoken_text_sha256=text_hash(spoken),
                )
            )
    return requests


class NarrationSegment(StrictModel):
    segment_id: str
    scene_id: str
    parent_segment_id: str
    editorial_text: str
    spoken_text: str
    subtitle_text: str
    wav: Path
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    raw_wav: Path
    raw_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    samples: int = Field(gt=0)
    sample_rate: int = Field(gt=0)
    channels: int = Field(ge=1, le=2)
    duration: float = Field(gt=0)
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    pause_after: float = Field(ge=0)
    provider: dict
    synchronization: Literal["MEASURED_PHRASE_AUDIO"] = "MEASURED_PHRASE_AUDIO"

    @model_validator(mode="after")
    def measured(self):
        if (
            abs(self.duration - self.samples / self.sample_rate) > 1e-8
            or abs(self.end - self.start - self.duration) > 1e-8
        ):
            raise ValueError(
                "Timeline must use the measured PCM duration without truncation"
            )
        return self


class NarrationTimeline(StrictModel):
    schema_version: Literal[1] = 1
    job_id: str
    sample_rate: int
    channels: int
    duration: float = Field(gt=0)
    total_samples: int = Field(gt=0)
    wav: Path
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    segments: list[NarrationSegment] = Field(min_length=1)
    scene_spans: list[dict]
    alignment: Literal["measured_phrase_segments_not_word_alignment"] = (
        "measured_phrase_segments_not_word_alignment"
    )
    phonetic_alignment: Literal[False] = False
    audio_is_mock: bool
    authorization_mode: Literal["test", "commercial"]

    @model_validator(mode="after")
    def contiguous(self):
        if len({s.segment_id for s in self.segments}) != len(self.segments):
            raise ValueError("Duplicate narration segment")
        cursor = 0.0
        for segment in self.segments:
            if (
                abs(segment.start - cursor) > 1e-7
                or segment.sample_rate != self.sample_rate
                or segment.channels != self.channels
            ):
                raise ValueError(
                    "Narration overlap, unregistered gap or format mismatch"
                )
            cursor = segment.end + segment.pause_after
        if (
            abs(cursor - self.duration) > 1e-7
            or abs(self.duration - self.total_samples / self.sample_rate) > 1e-8
        ):
            raise ValueError(
                "Narration total differs from measured segments and pauses"
            )
        scene_cursor = 0.0
        seen = set()
        for span in self.scene_spans:
            sid = span["scene_id"]
            group = [s for s in self.segments if s.scene_id == sid]
            if (
                sid in seen
                or not group
                or abs(span["start"] - scene_cursor) > 1e-7
                or abs(group[0].start - span["start"]) > 1e-7
                or abs(group[-1].end + group[-1].pause_after - span["end"]) > 1e-7
            ):
                raise ValueError(
                    "Scene spans must exactly cover their measured narration"
                )
            seen.add(sid)
            scene_cursor = span["end"]
        if (
            seen != {s.scene_id for s in self.segments}
            or abs(scene_cursor - self.duration) > 1e-7
        ):
            raise ValueError("Scene spans do not cover the narration timeline")
        return self


def calculate_timing(board, records, config):
    expected = [
        (r["segment_id"], r["scene_id"]) for r in plan_narration(board, config.currency)
    ]
    if [(r["segment_id"], r["scene_id"]) for r in records] != expected:
        raise ValueError("Measured segments differ from the narration plan")
    if config.sample_rate % board.fps:
        raise ValueError("Sample rate must support an exact video frame grid")
    per_frame = config.sample_rate // board.fps
    cursor, segments, spans = 0, [], []
    for si, scene in enumerate(board.scenes):
        group = [r for r in records if r["scene_id"] == scene.id]
        if not group:
            raise ValueError("Every visual scene needs authorized audio")
        scene_start = cursor
        for j, record in enumerate(group):
            info = record["normalized"]
            if (info["sample_rate"], info["channels"]) != (
                config.sample_rate,
                config.channels,
            ):
                raise ValueError("Normalize PCM format before calculating timing")
            start = cursor
            cursor += info["samples"]
            pause = (
                round(config.phrase_pause * config.sample_rate)
                if j < len(group) - 1
                else 0
            )
            if j == len(group) - 1:
                if si < len(board.scenes) - 1:
                    pause += round(config.scene_pause * config.sample_rate)
                pause += (-(cursor + pause)) % per_frame
            segments.append(
                dict(
                    **{
                        k: record[k]
                        for k in [
                            "segment_id",
                            "scene_id",
                            "parent_segment_id",
                            "editorial_text",
                            "spoken_text",
                            "subtitle_text",
                        ]
                    },
                    wav=record["wav"],
                    sha256=info["sha256"],
                    raw_wav=record["raw_wav"],
                    raw_sha256=record["raw"]["sha256"],
                    samples=info["samples"],
                    sample_rate=info["sample_rate"],
                    channels=info["channels"],
                    duration=info["duration"],
                    start=start / config.sample_rate,
                    end=cursor / config.sample_rate,
                    pause_after=pause / config.sample_rate,
                    provider=record["provider"],
                )
            )
            cursor += pause
        spans.append(
            dict(
                scene_id=scene.id,
                parent_segment_id=scene.narrative_segment_id,
                start=scene_start / config.sample_rate,
                end=cursor / config.sample_rate,
            )
        )
    if cursor / config.sample_rate > config.max_seconds:
        from .audio_providers import NarrationBlocked

        raise NarrationBlocked(
            "Measured narration exceeds the configured Short limit; revise script or pauses, never truncate",
            "BLOCKED_NARRATION_DURATION",
        )
    return segments, spans, cursor


def retime_storyboard(board, timeline):
    data = board.model_dump(mode="json")
    spans = {s["scene_id"]: s for s in timeline.scene_spans}
    for scene in data["scenes"]:
        span = spans[scene["id"]]
        old_start, old_end = scene["start"], scene["end"]
        scale = (span["end"] - span["start"]) / (old_end - old_start)
        scene["start"], scene["end"] = span["start"], span["end"]
        for event in scene["events"]:
            event["at"] *= scale
            event["duration"] *= scale
        for anchor in scene["anchors"]:
            anchor["start"] = span["start"] + (anchor["start"] - old_start) * scale
            anchor["end"] = span["start"] + (anchor["end"] - old_start) * scale
        for element in scene["elements"]:
            if element.get("narration_anchor") is None:
                element["narration_anchor"] = scene["narrative_segment_id"]
        existing = {a["id"] for a in scene["anchors"]}
        for segment in timeline.segments:
            if segment.scene_id == scene["id"] and segment.segment_id not in existing:
                scene["anchors"].append(
                    dict(
                        id=segment.segment_id,
                        start=segment.start,
                        end=segment.end,
                        text=segment.editorial_text,
                    )
                )
    data["duration"] = timeline.duration
    data["audio"] = "external"
    data["source_metadata"]["narrative_mode"] = "burned_subtitles"
    data["source_metadata"]["narration_alignment"] = timeline.alignment
    if timeline.audio_is_mock:
        data["source_metadata"]["audio_notice"] = "AUDIO MOCK"
    result = VisualStoryboard.model_validate(data)
    if not math.isclose(result.duration, timeline.duration, abs_tol=1e-8):
        raise ValueError("Visual and audio timeline disagree")
    return result
