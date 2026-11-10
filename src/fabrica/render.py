"""Composición acotada en memoria y QA técnico mediante FFmpeg."""

import json
import subprocess
from pathlib import Path


def run(args):
    subprocess.run(args, check=True, capture_output=True, text=True, timeout=600)


def timestamp(seconds):
    ms = round(seconds * 1000)
    return (
        f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"
    )


def subtitles(scenes, durations, target: Path, mock=False):
    entries, start = [], 0.0
    for i, (scene, seconds) in enumerate(zip(scenes, durations), 1):
        label = "[AUDIO SIMULADO] " if mock else ""
        entries.append(
            f"{i}\n{timestamp(start)} --> {timestamp(start + seconds)}\n{label}{scene.narration}\n"
        )
        start += seconds
    target.write_text("\n".join(entries), encoding="utf-8")


def compose(
    images, audios, durations, srt, target, width=1080, height=1920, scenes=None
):
    if (
        width < 90
        or height < 160
        or width * 16 != height * 9
        or width % 2
        or height % 2
    ):
        raise ValueError("Se requiere resolución vertical 9:16 par")
    segments = []
    for i, (image, audio, seconds) in enumerate(zip(images, audios, durations)):
        segment = target.parent / f"segment_{i:02}.mp4"
        fade = min(0.15, seconds / 4)
        animation_fps = 24
        source = ["-loop", "1", "-i", str(image)]
        if scenes and scenes[i].visual_type == "big_number" and scenes[i].visual_data:
            try:
                number = float(scenes[i].visual_data[0])
            except ValueError:
                number = None
            if number is not None:
                import math

                if not math.isfinite(number):
                    raise ValueError("Número visual inválido")
                from .cards import make_card

                frames = target.parent / f"counter_{i:02}"
                frames.mkdir(exist_ok=True)
                for step in range(12):
                    scene = scenes[i].model_copy(
                        update={"visual_data": [f"{number * step / 11:g}"]}
                    )
                    make_card(
                        scene, i + 1, len(scenes), frames / f"frame_{step:02}.png"
                    )
                animation_fps = 12 / seconds
                source = [
                    "-framerate",
                    str(12 / seconds),
                    "-i",
                    str(frames / "frame_%02d.png"),
                ]
        run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                *source,
                "-i",
                str(audio),
                "-vf",
                f"scale={width}:{height},zoompan=z=min(zoom+0.0004\\,1.025):d=1:s={width}x{height}:fps={animation_fps},fps=24,fade=t=in:d={fade},fade=t=out:st={seconds - fade}:d={fade}",
                "-t",
                str(seconds),
                "-r",
                "24",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-threads",
                "2",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                str(segment),
            ]
        )
        segments.append(segment)
    listing = target.parent / "segments.txt"
    listing.write_text("".join(f"file '{p.name}'\n" for p in segments))
    partial = target.with_name("final.partial.mp4")
    run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(listing),
            "-i",
            str(srt),
            "-map",
            "0:v",
            "-map",
            "0:a",
            "-map",
            "1:0",
            "-c",
            "copy",
            "-c:s",
            "mov_text",
            "-movflags",
            "+faststart",
            str(partial),
        ]
    )
    partial.replace(target)


def quality(video, width, height, expected_duration, srt):
    data = json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_streams",
                "-show_format",
                "-of",
                "json",
                str(video),
            ],
            text=True,
            timeout=30,
        )
    )
    streams = data["streams"]
    v = next(s for s in streams if s["codec_type"] == "video")
    if (v["width"], v["height"], v["codec_name"]) != (width, height, "h264"):
        raise ValueError("Video inválido")
    if not any(
        s["codec_type"] == "audio" and s["codec_name"] == "aac" for s in streams
    ):
        raise ValueError("Falta AAC")
    if not any(s["codec_type"] == "subtitle" for s in streams):
        raise ValueError("Faltan subtítulos integrados")
    if not srt.is_file() or "-->" not in srt.read_text():
        raise ValueError("Falta SRT")
    if abs(float(data["format"]["duration"]) - expected_duration) >= 0.5:
        raise ValueError("Duración fuera de tolerancia")
    run(["ffmpeg", "-v", "error", "-xerror", "-i", str(video), "-f", "null", "-"])
    return {
        "duration": float(data["format"]["duration"]),
        "width": width,
        "height": height,
        "decoded": True,
        "editorial_verified": False,
    }
