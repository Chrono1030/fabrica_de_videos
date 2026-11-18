"""Production native adapters promoted from the measured advanced comparison."""

import hashlib
import json
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from fabrica.visual_storyboard import VisualStoryboard

from .measure import measured
from .runtime import (
    PINS,
    RendererConfig,
    RenderFailure,
    asset,
    atomic_json,
    available,
    command,
    environment,
    fingerprint,
    sha,
)


class AudioTrack(BaseModel):
    """A verified external asset; independent of TTS engines or voice generation."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    path: Path
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    commercial_allowed: Literal[True]
    license: str = Field(min_length=1)
    evidence: list[str] = Field(min_length=1)

    @field_validator("path")
    @classmethod
    def absolute_path(cls, value):
        return value.resolve()

    def verify(self):
        if not self.path.is_file() or sha(self.path) != self.sha256:
            raise ValueError(
                "External audio missing or hash differs from verified manifest"
            )


@dataclass(frozen=True)
class PreparedRender:
    storyboard: VisualStoryboard
    project: Path
    directory: Path
    inputs: dict
    fingerprint: str


@dataclass(frozen=True)
class RenderProduct:
    video: Path
    thumbnail: Path
    metrics: dict
    quality: dict


class Renderer(Protocol):
    def validate(
        self, storyboard: VisualStoryboard, audio: AudioTrack | None = None
    ) -> None: ...
    def prepare(
        self,
        storyboard: VisualStoryboard,
        directory: Path,
        audio: AudioTrack | None = None,
    ) -> PreparedRender: ...
    def render(
        self, prepared: PreparedRender, audio: AudioTrack | None = None
    ) -> RenderProduct: ...
    def inspect(
        self,
        video: Path,
        storyboard: VisualStoryboard,
        directory: Path,
        audio: AudioTrack | None = None,
    ) -> dict: ...


def json_script(value):
    return (
        json.dumps(value, ensure_ascii=False)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


class NativeRenderer:
    name: str
    entry: str

    def __init__(self, config: RendererConfig):
        self.config = config

    def validate(self, storyboard, audio=None):
        # Revalidate frozen models: model_copy/update and nested mutable structures are not trusted.
        storyboard = VisualStoryboard.model_validate(storyboard.model_dump())
        if storyboard.schema_version != 2:
            raise ValueError(
                "Production requires a V2 visual plan; migrate the V1 example with the editorial planner"
            )
        if storyboard.audio == "external" and audio is None:
            raise ValueError("External soundtrack requires its verified asset manifest")
        if audio is not None:
            audio.verify()
            if storyboard.audio != "external":
                raise ValueError("Storyboard must explicitly declare external audio")
        available(self.config)

    def inputs(self, storyboard, audio=None):
        self.validate(storyboard, audio)
        return {
            "runtime": fingerprint(self.config),
            "storyboard_sha256": hashlib.sha256(
                storyboard.model_dump_json().encode()
            ).hexdigest(),
            "audio": audio.model_dump(mode="json") if audio else None,
        }

    def prepare(self, storyboard, directory, audio=None):
        inputs = self.inputs(storyboard, audio)
        directory = Path(directory).resolve()
        directory.mkdir(parents=True, exist_ok=False)
        project = directory / "project"
        project.mkdir()
        shutil.copy(self.config.font_path, project / "brand.ttf")
        for filename in ("components.js", "scene.css"):
            (project / filename).write_bytes(asset("assets/" + filename).read_bytes())
        atomic_json(directory / "storyboard.json", storyboard.model_dump(mode="json"))
        self.build(storyboard, project)
        token = hashlib.sha256(json_script(inputs).encode()).hexdigest()
        atomic_json(directory / "inputs.json", inputs | {"fingerprint": token})
        return PreparedRender(storyboard, project, directory, inputs, token)

    def cli(self):
        p = available(self.config)
        return [p["node"], p["package"] / self.entry]

    def log(self, directory, phase, **details):
        record = {"phase": phase, "renderer": self.name, "at": time.time(), **details}
        with (directory / "events.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")

    def render(self, prepared, audio=None):
        b, d, p = prepared.storyboard, prepared.directory, prepared.project
        current = self.inputs(b, audio)
        if current != prepared.inputs:
            raise ValueError("Render inputs changed after preparation")
        output = d / "native.mp4"
        argv = self.render_command(p, output, b)
        resources = d / "resources.txt"
        self.log(
            d,
            "render_started",
            fingerprint=prepared.fingerprint,
            argv=list(map(str, argv)),
        )
        started = time.perf_counter()
        try:
            code, peak = measured(
                ["/usr/bin/time", "-f", "%e %U %S %M", "-o", resources, *argv],
                p,
                environment(self.config, d),
                d / "render.log",
                timeout=self.config.timeout_seconds,
            )
            elapsed = time.perf_counter() - started
            if code:
                raise RenderFailure(
                    f"{self.name} exited {code}; see {d / 'render.log'}. No fallback was attempted."
                )
            values = resources.read_text().splitlines()[-1].split()
            metrics = {
                "renderer": self.name,
                "engine_version": PINS[self.name],
                "fingerprint": prepared.fingerprint,
                "storyboard_sha256": prepared.inputs["storyboard_sha256"],
                "render_wall_seconds": elapsed,
                "cpu_seconds": float(values[1]) + float(values[2]),
                "peak_process_tree_rss_mib": peak,
                "peak_individual_rss_mib": float(values[3]) / 1024,
                "memory_method": "RSS sum of simultaneous descendants every 50ms, shared pages counted per process; individual GNU time peak separate",
                "argv": list(map(str, argv)),
                "dependencies": prepared.inputs["runtime"],
                "audio": prepared.inputs["audio"],
            }
            if audio:
                audio.verify()
                probe = json.loads(
                    command(
                        [
                            "ffprobe",
                            "-v",
                            "error",
                            "-show_format",
                            "-of",
                            "json",
                            audio.path,
                        ],
                        config=self.config,
                        directory=d,
                    )
                )
                seconds = float(probe["format"]["duration"])
                if seconds > b.duration + 1 / b.fps:
                    raise ValueError(
                        "Audio exceeds planned duration; revise narrative anchors explicitly"
                    )
                mux_started = time.perf_counter()
                command(
                    [
                        "ffmpeg",
                        "-v",
                        "error",
                        "-i",
                        output,
                        "-i",
                        audio.path,
                        "-map",
                        "0:v:0",
                        "-map",
                        "1:a:0",
                        "-c:v",
                        "copy",
                        "-c:a",
                        "aac",
                        "-af",
                        "apad",
                        "-t",
                        b.duration,
                        "-movflags",
                        "+faststart",
                        d / "with-audio.mp4",
                    ],
                    config=self.config,
                    directory=d,
                    timeout=self.config.timeout_seconds,
                )
                metrics["mux_wall_seconds"] = time.perf_counter() - mux_started
                metrics["audio_end_padding_seconds"] = max(0, b.duration - seconds)
                output = d / "with-audio.mp4"
            quality = self.inspect(output, b, d, audio)
            thumb = d / "thumbnail.png"
            command(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-ss",
                    min(0.5, b.duration / 2),
                    "-i",
                    output,
                    "-frames:v",
                    "1",
                    thumb,
                ],
                config=self.config,
                directory=d,
            )
            metrics.update(
                out_bytes=output.stat().st_size,
                thumbnail_sha256=sha(thumb),
                sha256=sha(output),
                frames=quality["frames"],
                duration=quality["duration"],
            )
            pth = available(self.config)
            metrics["versions"] = {
                "node": command(
                    [pth["node"], "--version"], config=self.config, directory=d
                ).strip(),
                "browser": command(
                    [pth["browser"], "--version"], config=self.config, directory=d
                ).strip(),
                "ffmpeg": command(
                    ["ffmpeg", "-version"], config=self.config, directory=d
                ).splitlines()[0],
            }
            if (
                metrics["versions"]["node"] != "v22.16.0"
                or "157.0.8103.78" not in metrics["versions"]["browser"]
            ):
                raise RenderFailure(
                    "Runtime version differs from the pinned deployment"
                )
            if self.inputs(b, audio) != prepared.inputs:
                raise RenderFailure("Inputs changed during native render")
            atomic_json(d / "metrics.json", metrics)
            self.log(
                d,
                "render_validated",
                frames=quality["frames"],
                sha256=metrics["sha256"],
            )
            return RenderProduct(output, thumb, metrics, quality)
        except Exception as exc:
            self.log(
                d,
                "render_failed",
                error_type=type(exc).__name__,
                elapsed=time.perf_counter() - started,
            )
            if isinstance(exc, (subprocess.TimeoutExpired, TimeoutError, OSError)):
                raise RenderFailure(
                    f"{self.name} failed: {type(exc).__name__}; no fallback"
                ) from exc
            raise

    def inspect(self, video, storyboard, directory, audio=None):
        raw = command(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_streams",
                "-show_format",
                "-of",
                "json",
                video,
            ],
            config=self.config,
            directory=directory,
        )
        info = json.loads(raw)
        (directory / "ffprobe.json").write_text(raw)
        streams = info["streams"]
        videos = [s for s in streams if s["codec_type"] == "video"]
        sounds = [s for s in streams if s["codec_type"] == "audio"]
        if (
            len(videos) != 1
            or len(streams) != (2 if audio else 1)
            or bool(sounds) != bool(audio)
        ):
            raise ValueError("Unexpected audio/video streams")
        v = videos[0]
        b = storyboard
        if (v["width"], v["height"], v["codec_name"], v["r_frame_rate"]) != (
            b.width,
            b.height,
            "h264",
            f"{b.fps}/1",
        ):
            raise ValueError("Invalid resolution, codec or FPS")
        expected = round(b.duration * b.fps)
        if int(v.get("nb_frames", 0)) != expected or abs(
            float(info["format"]["duration"]) - b.duration
        ) > max(0.05, 1 / b.fps):
            raise ValueError("Invalid duration or frame count")
        if audio and sounds[0]["codec_name"] != "aac":
            raise ValueError("External soundtrack must be AAC")
        command(
            ["ffmpeg", "-v", "error", "-xerror", "-i", video, "-f", "null", "-"],
            config=self.config,
            directory=directory,
            timeout=self.config.timeout_seconds,
        )
        (directory / "decode.log").write_text("Full decode PASS\n")
        hashes = command(
            [
                "ffmpeg",
                "-v",
                "error",
                "-i",
                video,
                "-map",
                "0:v:0",
                "-f",
                "framemd5",
                "-",
            ],
            config=self.config,
            directory=directory,
            timeout=self.config.timeout_seconds,
        )
        (directory / "frames.md5").write_text(hashes)
        rows = [r for r in hashes.splitlines() if r and not r.startswith("#")]
        if len(rows) != expected:
            raise ValueError("Decoded frame count differs from timeline")
        return dict(
            decoded=True,
            frames=expected,
            duration=float(info["format"]["duration"]),
            width=b.width,
            height=b.height,
            fps=b.fps,
            audio=bool(audio),
            editorial_verified=False,
            framehash=hashlib.sha256("\n".join(rows).encode()).hexdigest(),
        )


class GivemotionRenderer(NativeRenderer):
    name = "givemotion"
    entry = "src/cli.js"

    def build(self, b, project):
        # Native sequences and callbacks reused from the advanced adapter; no prescribed scene count.
        clips = "".join(
            f'<section id="clip{i}" data-start="0" data-duration="{s.end - s.start}"></section>'
            for i, s in enumerate(b.scenes)
        )
        page = f'''<!doctype html><html lang="es" data-width="{b.width}" data-height="{b.height}" data-fps="{b.fps}" data-duration="{b.duration}"><head><meta charset="utf-8"><link rel="stylesheet" href="scene.css"><script src="components.js"></script></head><body style="width:{b.width}px;height:{b.height}px"><main data-sequence>{clips}</main><script>const board={json_script(b.model_dump(mode="json"))};board.scenes.forEach((s,i)=>{{const frame=FactoryVisuals.mount(document.getElementById('clip'+i),s,board,i);gm.onFrame('#clip'+i,t=>frame(t));}});</script></body></html>'''
        (project / "index.html").write_text(page)

    def render_command(self, project, video, b):
        return self.cli() + [
            "render",
            project,
            "-o",
            video,
            "--workers",
            "1",
            "--no-cache",
            "--muted",
            "--seed",
            str(self.config.seed),
            "--quality",
            "standard",
            "--json",
        ]


class HyperFramesRenderer(NativeRenderer):
    name = "hyperframes"
    entry = "bin/hyperframes.mjs"

    def build(self, b, project):
        # Native GSAP timelines and timed subcompositions promoted from the previous adapter.
        p = available(self.config)
        shutil.copy(
            p["package"].parent / "gsap/dist/gsap.min.js", project / "gsap.min.js"
        )
        comps = project / "compositions"
        comps.mkdir()
        shutil.copy(project / "brand.ttf", comps / "brand.ttf")
        mounts = []
        css = (project / "scene.css").read_text()
        for i, scene in enumerate(b.scenes):
            identity = f"scene{i}"
            duration = scene.end - scene.start
            page = f'''<template><div id="{identity}" data-composition-id="{identity}" data-width="{b.width}" data-height="{b.height}" data-duration="{duration}"></div><style>{css}</style><script>(()=>{{const b={json_script(b.model_dump(mode="json"))},s=b.scenes[{i}],frame=FactoryVisuals.mount(document.getElementById('{identity}'),s,b,{i}),clock={{t:0}};const tl=gsap.timeline({{paused:true}});tl.to(clock,{{t:{duration},duration:{duration},ease:'none',onUpdate:()=>frame(clock.t)}},0);frame(0);window.__timelines=window.__timelines||{{}};window.__timelines.{identity}=tl;}})();</script></template>'''
            (comps / f"s{i}.html").write_text(page)
            mounts.append(
                f'<div id="mount{i}" data-composition-id="{identity}" data-composition-src="compositions/s{i}.html" data-start="{scene.start}" data-duration="{duration}" data-track-index="{i}" style="position:absolute;inset:0"></div>'
            )
        (project / "index.html").write_text(
            f'''<!doctype html><html lang="es" data-width="{b.width}" data-height="{b.height}" data-fps="{b.fps}"><head><meta charset="utf-8"><script src="gsap.min.js"></script><script src="components.js"></script></head><body style="margin:0;width:{b.width}px;height:{b.height}px"><main data-composition-id="main" data-start="0" data-duration="{b.duration}" data-width="{b.width}" data-height="{b.height}" data-fps="{b.fps}">{"".join(mounts)}</main><script>window.__timelines=window.__timelines||{{}};const tl=gsap.timeline({{paused:true}});tl.to({{}},{{duration:{b.duration}}});window.__timelines.main=tl;</script></body></html>'''
        )

    def render_command(self, project, video, b):
        return self.cli() + [
            "render",
            project,
            "--output",
            video,
            "--fps",
            str(b.fps),
            "--workers",
            "1",
            "--quality",
            "standard",
            "--page-motion-blur",
            "off",
        ]
