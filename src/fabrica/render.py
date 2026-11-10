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
    from .subtitle_style import cues

    entries, start = [], 0.0
    for scene, seconds in zip(scenes, durations):
        chunks = cues(("[AUDIO SIMULADO] " if mock else "") + scene.narration)
        weights = [len(c.split()) for c in chunks]
        cursor = start
        for chunk, weight in zip(chunks, weights):
            end = cursor + seconds * weight / sum(weights)
            entries.append(
                f"{len(entries) + 1}\n{timestamp(cursor)} --> {timestamp(end)}\n{chunk}\n"
            )
            cursor = end
        start += seconds
    target.write_text("\n".join(entries), encoding="utf-8")


def compose(
    images,
    audios,
    durations,
    srt,
    target,
    width=1080,
    height=1920,
    scenes=None,
    style=None,
):
    if (
        width < 90
        or height < 160
        or width * 16 != height * 9
        or width % 2
        or height % 2
    ):
        raise ValueError("Se requiere resolución vertical 9:16 par")
    from .subtitle_style import SubtitleStyle

    style = style or SubtitleStyle()
    segments = []
    for i, (image, audio, seconds) in enumerate(zip(images, audios, durations)):
        segment = target.parent / f"segment_{i:02}.mp4"
        fade = min(0.15, seconds / 4)
        animation_fps = 24
        source = ["-loop", "1", "-i", str(image)]
        if (
            scenes
            and scenes[i].visual_type in ("big_number", "bar_chart", "line_chart")
            and scenes[i].visual_data
        ):
            try:
                number = float(scenes[i].visual_data[0])
            except ValueError:
                number = None
            if number is not None or scenes[i].visual_type in (
                "bar_chart",
                "line_chart",
            ):
                import math

                if number is not None and not math.isfinite(number):
                    raise ValueError("Número visual inválido")
                from .cards import make_card

                frames = target.parent / f"counter_{i:02}"
                frames.mkdir(exist_ok=True)
                frame_count = max(12, min(72, round(seconds * 12)))
                for step in range(frame_count):
                    scene = scenes[i].model_copy(
                        update={
                            "visual_data": [f"{number * step / (frame_count - 1):g}"]
                        }
                        if number is not None
                        else {}
                    )
                    make_card(
                        scene,
                        i + 1,
                        len(scenes),
                        frames / f"frame_{step:02}.png",
                        progress=step / (frame_count - 1),
                    )
                animation_fps = frame_count / seconds
                source = [
                    "-framerate",
                    str(frame_count / seconds),
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
    # Ruta local fija: los identificadores no se interpolan en el filtro FFmpeg.
    if style.burn:
        local_srt = target.parent / "burn.ass"
        rows = []
        for block in srt.read_text().strip().split("\n\n"):
            lines = block.splitlines()
            if len(lines) < 3:
                continue
            start, end = lines[1].split(" --> ")

            def ass_time(t):
                return t[:8] + "." + t[9:11]

            text = r"\N".join(lines[2:]).replace("{", "").replace("}", "")
            rows.append(
                f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Default,,0,0,0,,{text}"
            )
        local_srt.write_text(
            "[Script Info]\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 2\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV\nStyle: Default,DejaVu Sans,44,&H00DDEEF4,&H00352112,1,2,1,2,110,110,320\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
            + "\n".join(rows)
        )
        command = [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            "segments.txt",
            "-vf",
            f"subtitles=burn.ass:original_size=1080x1920:force_style='{style.ass_style()}'",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-threads",
            "2",
            "-c:a",
            "copy",
            "-movflags",
            "+faststart",
            partial.name,
        ]
        subprocess.run(
            command, cwd=target.parent, check=True, capture_output=True, timeout=600
        )
    else:
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


def quality(video, width, height, expected_duration, srt, burned=True):
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
    if not burned and not any(s["codec_type"] == "subtitle" for s in streams):
        raise ValueError("Faltan subtítulos integrados")
    if burned and any(s["codec_type"] == "subtitle" for s in streams):
        raise ValueError("Pista duplicada con subtítulos quemados")
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
