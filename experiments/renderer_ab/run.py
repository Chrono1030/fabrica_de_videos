"""Isolated, sequential renderer experiment. No production entry points invoked."""

import argparse
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

from measure import measured
from PIL import Image, ImageDraw
from visual import EXP, ROOT, build_html

ENG = EXP / "engines"
NODE = ENG / "node-v22.16.0-linux-x64/bin/node"
CHROME = ENG / "chrome157/chrome-headless-shell-linux64/chrome-headless-shell"
OUT = ROOT / "out/renderer_ab"


def sha(path):
    return hashlib.file_digest(Path(path).open("rb"), "sha256").hexdigest()


def env():
    # Allowlist: application secrets and .env are never inherited by JS/Chrome.
    return {
        "PATH": f"{NODE.parent}:/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "LD_LIBRARY_PATH": str(ENG / "browser-libs/root/usr/lib/x86_64-linux-gnu"),
        "XDG_CACHE_HOME": str(OUT / "cache"),
        "GIVEMOTION_CACHE": str(OUT / "cache/givemotion"),
        "HYPERFRAMES_BROWSER_PATH": str(CHROME),
        "GIVEMOTION_CHROME": str(CHROME),
        "HYPERFRAMES_NO_TELEMETRY": "1",
        "HYPERFRAMES_NO_UPDATE_CHECK": "1",
        "DO_NOT_TRACK": "1",
        "GIVEMOTION_MAX_BROWSERS": "1",
    }


def execute(args, cwd=ROOT, timeout=1800):
    return subprocess.run(
        [str(a) for a in args],
        cwd=cwd,
        env=env(),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def version(args):
    r = execute(args)
    return (r.stdout + r.stderr).strip().split("\n")[0]


def cli(name):
    binpath = (
        ENG
        / name
        / "node_modules"
        / name
        / ("bin/hyperframes.mjs" if name == "hyperframes" else "src/cli.js")
    )
    return [NODE, binpath]


def validate(video, directory, captures):
    probe = execute(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            video,
        ]
    )
    probe.check_returncode()
    data = json.loads(probe.stdout)
    (directory / "ffprobe.json").write_text(probe.stdout)
    v = next(s for s in data["streams"] if s["codec_type"] == "video")
    assert (v["width"], v["height"], v["codec_name"], v["r_frame_rate"]) == (
        1080,
        1920,
        "h264",
        "24/1",
    )
    assert abs(float(data["format"]["duration"]) - 20) < 0.001
    assert int(v["nb_frames"]) == 480
    assert len(data["streams"]) == 1, "No audio permitted"
    decode = execute(
        ["ffmpeg", "-v", "error", "-xerror", "-i", video, "-f", "null", "-"]
    )
    (directory / "decode.log").write_text(decode.stderr)
    decode.check_returncode()
    hashes = execute(
        ["ffmpeg", "-v", "error", "-i", video, "-map", "0:v", "-f", "framemd5", "-"]
    )
    hashes.check_returncode()
    # Ignore headers; compare every decoded frame, not container metadata.
    rows = "\n".join(s for s in hashes.stdout.splitlines() if not s.startswith("#"))
    (directory / "frames.md5").write_text(hashes.stdout)
    thumbs = []
    for t in captures:
        p = directory / f"frame-{t:g}.png"
        r = execute(
            ["ffmpeg", "-v", "error", "-ss", str(t), "-i", video, "-frames:v", "1", p]
        )
        r.check_returncode()
        with Image.open(p) as im:
            thumb = im.resize((270, 480)).convert("RGB")
        thumbs.append((t, thumb))
    sheet = Image.new("RGB", (1080, 1020), "#112037")
    draw = ImageDraw.Draw(sheet)
    for i, (t, im) in enumerate(thumbs):
        x, y = i % 4 * 270, i // 4 * 510
        sheet.paste(im, (x, y))
        draw.text((x + 10, y + 484), f"{t:g} s", fill="#F6EEDB")
    sheet.save(directory / "contact-sheet.jpg")
    return {
        "technical_pass": True,
        "decoded_frames": 480,
        "duration": 20,
        "framehash": hashlib.sha256(rows.encode()).hexdigest(),
    }


def diagnostics(name, project, directory):
    if name == "existing":
        return []
    if name == "hyperframes":
        commands = [
            ["lint", project, "--json"],
            ["check", project, "--json"],
            [
                "snapshot",
                project,
                "--at",
                "0.5,2,4.5,6.5,9.5,12,15,18.5",
                "--output",
                directory / "native-snapshots",
            ],
        ]
    else:
        commands = [
            ["doctor"],
            ["check", project, "--workers", "1", "--json"],
            [
                "snapshot",
                project,
                "--times",
                "0.5,2,4.5,6.5,9.5,12,15,18.5",
                "-o",
                directory / "native-snapshots",
                "--json",
            ],
        ]
    results = []
    for args in commands:
        try:
            r = execute(cli(name) + args, cwd=project, timeout=600)
            (directory / f"{args[0]}.log").write_text(r.stdout + r.stderr)
            results.append(
                {"command": [str(a) for a in args], "exit_code": r.returncode}
            )
        except subprocess.TimeoutExpired as e:
            (directory / f"{args[0]}.log").write_text(str(e))
            results.append({"command": str(args), "error": "timeout"})
    return results


def run(name, repeat, overwrite):
    config = json.loads((EXP / "config.json").read_text())
    candidate = config["renderers"][name]
    if not candidate["enabled"]:
        raise ValueError(f"{name} is disabled")
    for index in range(1, repeat + 1):
        if (OUT / name / f"run-{index}").exists() and not overwrite:
            raise FileExistsError(f"run-{index} exists; explicit --overwrite required")
    if name != "existing":
        installed = json.loads(
            (ENG / name / "node_modules" / name / "package.json").read_text()
        )
        if (
            installed["name"] != name
            or installed["version"] != candidate["candidate_version"]
        ):
            raise ValueError("Installed engine identity/version does not match config")
    fixture = json.loads((EXP / "fixture.json").read_text())
    project = OUT / name / "project"
    if name != "existing":
        build_html(name, fixture, config["settings"], project)
    frozen = {p.name: sha(p) for p in EXP.glob("*.py")}
    frozen_sha = version(["git", "rev-parse", "HEAD"])
    for index in range(1, repeat + 1):
        assert frozen == {p.name: sha(p) for p in EXP.glob("*.py")}, (
            "Sources changed between repetitions"
        )
        assert frozen_sha == version(["git", "rev-parse", "HEAD"]), (
            "Git SHA changed between repetitions"
        )
        directory = OUT / name / f"run-{index}"
        if directory.exists() and not overwrite:
            raise FileExistsError(f"{directory} exists; explicit --overwrite required")
        directory.mkdir(parents=True, exist_ok=True)
        video = directory / "final.mp4"
        if overwrite and video.exists():
            video.unlink()
        manifest = {
            "renderer": name,
            "run": index,
            "git_sha": version(["git", "rev-parse", "HEAD"]),
            "engine_version": (
                f"Pillow {importlib.metadata.version('Pillow')} / FFmpeg 6.1.1"
                if name == "existing"
                else candidate["candidate_version"]
            ),
            "fixture_sha256": sha(EXP / "fixture.json"),
            "config_sha256": sha(EXP / "config.json"),
            "python": sys.version,
            "node": version([NODE, "--version"]),
            "browser": version([CHROME, "--version"]),
            "ffmpeg": version(["ffmpeg", "-version"]),
            "os": platform.platform(),
            "source_sha256": {p.name: sha(p) for p in EXP.glob("*.py")},
            "cache": {
                "render_parts_reuse": False,
                "os_cache_warmed": True,
                "diagnostics_before_render": index == 1,
            },
            "status": "RUNNING",
            "visual_review": "pending human review",
        }
        lock = ENG / name / "package-lock.json"
        if lock.exists():
            manifest["lockfile_sha256"] = sha(lock)
            manifest["composition_sha256"] = {
                str(p.relative_to(project)): sha(p) for p in project.rglob("*.html")
            }
        (directory / "manifest.json").write_text(json.dumps(manifest, indent=2))
        try:
            if index == 1:
                manifest["diagnostics"] = diagnostics(name, project, directory)
            if name == "existing":
                command = [sys.executable, EXP / "existing.py", video]
            elif name == "hyperframes":
                command = cli(name) + [
                    "render",
                    project,
                    "--output",
                    video,
                    "--fps",
                    "24",
                    "--workers",
                    "1",
                    "--quality",
                    "standard",
                    "--page-motion-blur",
                    "off",
                ]
            else:
                command = cli(name) + [
                    "render",
                    project,
                    "-o",
                    video,
                    "--workers",
                    "1",
                    "--no-cache",
                    "--muted",
                    "--seed",
                    "1030",
                    "--quality",
                    "standard",
                    "--json",
                ]
            manifest["command"] = [str(a) for a in command]
            start = time.perf_counter()
            metrics = directory / "resources.txt"
            returncode, tree_peak = measured(
                ["/usr/bin/time", "-f", "%e %U %S %M", "-o", metrics, *command],
                project if name != "existing" else ROOT,
                env(),
                directory / "render.log",
            )
            manifest["render_wall_seconds"] = time.perf_counter() - start
            manifest["peak_process_tree_rss_mb"] = tree_peak
            manifest["tree_memory_method"] = (
                "Sum of simultaneous descendant RSS sampled from /proc every 50ms; shared pages counted per process"
            )
            values = metrics.read_text().splitlines()[-1].split()
            manifest.update(
                cpu_seconds=float(values[1]) + float(values[2]),
                peak_rss_mb=float(values[3]) / 1024,
                memory_method="GNU time ru_maxrss: maximum individual process RSS, not simultaneous process-tree sum",
            )
            if returncode != 0:
                raise RuntimeError(f"Native renderer exit {returncode}; see render.log")
            manifest["provenance"] = {
                "adapter": name,
                "native_command": manifest["command"],
                "engine_package_sha256": sha(
                    ENG / name / "node_modules" / name / "package.json"
                )
                if name != "existing"
                else None,
                "no_cross_engine_assets": True,
            }
            manifest.update(validate(video, directory, config["qa"]["capture_seconds"]))
            manifest.update(
                status="PASS", sha256=sha(video), out_bytes=video.stat().st_size
            )
        except Exception as e:
            manifest.update(status="FAILED", error=str(e))
            (directory / "error.log").write_text(str(e))
        (directory / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
        )
        print(name, index, manifest["status"], flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--renderer",
        default="all",
        choices=[
            "all",
            "existing",
            "hyperframes",
            "givemotion",
            "motion_canvas",
            "remotion",
        ],
    )
    parser.add_argument("--repeat", type=int, default=2)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error("--repeat must be positive")
    names = (
        [
            n
            for n, v in json.loads((EXP / "config.json").read_text())[
                "renderers"
            ].items()
            if v["enabled"]
        ]
        if args.renderer == "all"
        else [args.renderer]
    )
    failed = False
    for name in names:
        run(name, args.repeat, args.overwrite)
        failed |= any(
            json.loads((OUT / name / f"run-{i}/manifest.json").read_text())["status"]
            != "PASS"
            for i in range(1, args.repeat + 1)
        )
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
