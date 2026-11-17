"""Independent native adapters, reusing the first benchmark's process measurement."""

import hashlib
import html
import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Protocol

from experiments.renderer_ab.measure import measured
from fabrica.visual_storyboard import VisualStoryboard

ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "experiments/renderer_advanced"
OUT = ROOT / "out/renderer_advanced"
ENG = ROOT / "experiments/renderer_ab/engines"
NODE = ENG / "node-v22.16.0-linux-x64/bin/node"
CHROME = ENG / "chrome157/chrome-headless-shell-linux64/chrome-headless-shell"


def sha(path):
    with Path(path).open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def environment():
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


def execute(args, cwd=ROOT, timeout=600):
    result = subprocess.run(
        list(map(str, args)),
        cwd=cwd,
        env=environment(),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    result.check_returncode()
    return result.stdout + result.stderr


def load_config():
    data = json.loads((EXP / "config.json").read_text())
    if data["execution"] != "sequential" or data["repetitions"] != 2:
        raise ValueError("Experiment requires sequential execution and two repetitions")
    if set(data["renderers"]) != {"givemotion", "hyperframes"}:
        raise ValueError("Only the two approved renderers may be enabled")
    return data


class Renderer(Protocol):
    name: str

    def validate(self, storyboard: VisualStoryboard) -> None: ...
    def render(self, project: Path, directory: Path) -> dict: ...
    def inspect(self, directory: Path, storyboard: VisualStoryboard) -> dict: ...
    def collect_metrics(self, directory: Path) -> dict: ...
    def build(self, storyboard: VisualStoryboard, project: Path) -> None: ...


class NativeAdapter:
    name: str
    entry: str

    def cli(self):
        return [NODE, ENG / self.name / "node_modules" / self.name / self.entry]

    def validate(self, storyboard):
        installed = json.loads(
            (ENG / self.name / "node_modules" / self.name / "package.json").read_text()
        )
        if (installed["name"], installed["version"]) != (
            self.name,
            load_config()["renderers"][self.name],
        ):
            raise ValueError("Installed renderer differs from pinned version")
        if (
            storyboard.width,
            storyboard.height,
            storyboard.fps,
            storyboard.duration,
        ) != (1080, 1920, 24, 55):
            raise ValueError(
                "Advanced experiment requires 1080x1920, 24 fps, 55 seconds"
            )
        if len(storyboard.scenes) != 7:
            raise ValueError("Seven scenes required")

    def prepare(self, project):
        project.mkdir(parents=True, exist_ok=True)
        shutil.copy(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", project / "brand.ttf"
        )

    def render(self, project, directory):
        command = self.command(project, directory / "final.mp4")
        start = time.perf_counter()
        code, peak = measured(
            [
                "/usr/bin/time",
                "-f",
                "%e %U %S %M",
                "-o",
                directory / "resources.txt",
                *command,
            ],
            project,
            environment(),
            directory / "render.log",
            timeout=1800,
        )
        if code:
            raise RuntimeError(
                f"Native renderer exited {code}; see {directory}/render.log"
            )
        return {
            "command": list(map(str, command)),
            "render_wall_seconds": time.perf_counter() - start,
            "peak_process_tree_rss_mb": peak,
            "memory_method": "Simultaneous process tree RSS, sampled every 50ms; shared pages counted per process",
        }

    def collect_metrics(self, directory):
        values = (directory / "resources.txt").read_text().splitlines()[-1].split()
        video = directory / "final.mp4"
        return dict(
            cpu_seconds=float(values[1]) + float(values[2]),
            peak_individual_rss_mb=float(values[3]) / 1024,
            out_bytes=video.stat().st_size,
            sha256=sha(video),
        )

    def inspect(self, directory, storyboard):
        video = directory / "final.mp4"
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
        (directory / "ffprobe.json").write_text(probe)
        info = json.loads(probe)
        assert len(info["streams"]) == 1, "Only a silent video track is permitted"
        stream = info["streams"][0]
        assert (
            stream["width"],
            stream["height"],
            stream["codec_name"],
            stream["r_frame_rate"],
        ) == (storyboard.width, storyboard.height, "h264", f"{storyboard.fps}/1")
        count = int(storyboard.duration * storyboard.fps)
        assert int(stream["nb_frames"]) == count
        assert abs(float(info["format"]["duration"]) - storyboard.duration) < 0.001
        log = execute(
            ["ffmpeg", "-v", "error", "-xerror", "-i", video, "-f", "null", "-"]
        )
        (directory / "decode.log").write_text(log)
        hashes = execute(["ffmpeg", "-v", "error", "-i", video, "-f", "framemd5", "-"])
        (directory / "frames.md5").write_text(hashes)
        rows = "\n".join(s for s in hashes.splitlines() if not s.startswith("#"))
        for t in load_config()["captures"]:
            execute(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-ss",
                    t,
                    "-i",
                    video,
                    "-frames:v",
                    "1",
                    directory / f"frame-{t:g}.png",
                ]
            )
        # FFmpeg produces QA sheets; no Python raster renderer participates.
        captures = load_config()["captures"]
        select = "+".join(f"eq(n,{round(t * storyboard.fps)})" for t in captures)
        execute(
            [
                "ffmpeg",
                "-v",
                "error",
                "-i",
                video,
                "-vf",
                f"select='{select}',scale=270:480,drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='%{{pts\\:hms}}':x=8:y=450:fontsize=20:fontcolor=white:box=1:boxcolor=black@0.7,tile=4x4",
                "-frames:v",
                "1",
                directory / "contact-sheet.jpg",
            ]
        )
        return dict(
            technical_pass=True,
            decoded_frames=count,
            duration=storyboard.duration,
            framehash=hashlib.sha256(rows.encode()).hexdigest(),
        )

    def diagnostics(self, project, directory):
        command = self.cli() + ["check", project, "--json"]
        if self.name == "givemotion":
            command += ["--workers", "1"]
        result = subprocess.run(
            list(map(str, command)),
            cwd=project,
            env=environment(),
            capture_output=True,
            text=True,
            timeout=600,
        )
        (directory / "check.log").write_text(result.stdout + result.stderr)
        return {"command": list(map(str, command)), "exit_code": result.returncode}


class GivemotionAdapter(NativeAdapter):
    name = "givemotion"
    entry = "src/cli.js"

    def build(self, storyboard, project):
        self.prepare(project)
        page = (
            (EXP / "templates/givemotion.html")
            .read_text()
            .replace(
                "__STORYBOARD__", storyboard.model_dump_json().replace("<", "\\u003c")
            )
        )
        (project / "index.html").write_text(page)

    def command(self, project, video):
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
            "1030",
            "--quality",
            "standard",
            "--json",
        ]


class HyperframesAdapter(NativeAdapter):
    name = "hyperframes"
    entry = "bin/hyperframes.mjs"

    def build(self, storyboard, project):
        self.prepare(project)
        shutil.copy(
            ENG / "hyperframes/node_modules/gsap/dist/gsap.min.js",
            project / "gsap.min.js",
        )
        template = (EXP / "templates/hyperframes.html").read_text()
        comps = project / "compositions"
        comps.mkdir(exist_ok=True)
        # Relative font references can resolve against either main page or composition.
        shutil.copy(project / "brand.ttf", comps / "brand.ttf")
        headings = [
            "¿Cuánto te queda?",
            "El recorrido de cada peso",
            "Los gastos fijos",
            "El margen que te queda",
            "Trasladar, sin ganar más",
            "Compará el ahorro",
            "Tu presupuesto, visible",
        ]
        mounts = []
        for i, scene in enumerate(storyboard.scenes):
            identity = f"sequence{i}"
            duration = scene.end - scene.start
            replacements = {
                "__ID__": identity,
                "__DURATION__": str(duration),
                "__NUMBER__": f"{i + 1:02}",
                "__HEADING__": html.escape(headings[i]),
                "__SEGMENT__": scene.narrative_segment_id,
                "__NARRATIVE__": html.escape(scene.narrative),
                "__SCENE__": scene.model_dump_json().replace("<", "\\u003c"),
                "__INDEX__": str(i),
            }
            page = template
            for key, value in replacements.items():
                page = page.replace(key, value)
            (comps / f"s{i}.html").write_text(page)
            mounts.append(
                f'<div id="mount-{identity}" data-composition-id="{identity}" data-composition-src="compositions/s{i}.html" data-start="{scene.start}" data-duration="{duration}" data-track-index="{i}" style="position:absolute;inset:0"></div>'
            )
        (project / "index.html").write_text(
            '<!doctype html><html lang="es" data-width="1080" data-height="1920" data-fps="24"><head><meta charset="utf-8"><script src="gsap.min.js"></script><style>html,body{margin:0;background:#112037;width:1080px;height:1920px;overflow:hidden}</style></head><body><main data-composition-id="main" data-start="0" data-duration="55" data-width="1080" data-height="1920" data-fps="24">'
            + "".join(mounts)
            + "</main><script>window.__timelines=window.__timelines||{};const tl=gsap.timeline({paused:true});tl.to({},{duration:55});window.__timelines.main=tl;</script></body></html>"
        )

    def command(self, project, video):
        return self.cli() + [
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


def select_adapter(name) -> Renderer:
    config = load_config()
    if name not in config["renderers"]:
        raise ValueError(f"Renderer {name!r} is disabled or unknown")
    return {"givemotion": GivemotionAdapter, "hyperframes": HyperframesAdapter}[name]()
