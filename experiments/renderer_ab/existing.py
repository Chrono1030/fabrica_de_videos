"""Pillow/FFmpeg control; reuses production font loader without changing it."""

import json
import subprocess
import sys
from pathlib import Path

from visual import EXP, pillow_frame


def main():
    fixture = json.loads((EXP / "fixture.json").read_text())
    settings = json.loads((EXP / "config.json").read_text())["settings"]
    output = Path(sys.argv[1])
    cmd = [
        "ffmpeg",
        "-v",
        "error",
        "-f",
        "rawvideo",
        "-pixel_format",
        "rgb24",
        "-video_size",
        "1080x1920",
        "-framerate",
        "24",
        "-i",
        "pipe:0",
        "-an",
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
        "-movflags",
        "+faststart",
        str(output),
    ]
    with subprocess.Popen(cmd, stdin=subprocess.PIPE) as p:
        for frame in range(480):
            p.stdin.write(pillow_frame(fixture, settings, frame / 24).tobytes())
        p.stdin.close()
        if p.wait() != 0:
            raise RuntimeError("FFmpeg failed")
    print("PROVENANCE existing Pillow frames -> FFmpeg libx264")


if __name__ == "__main__":
    main()
