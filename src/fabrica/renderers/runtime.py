"""Pinned, optional local Node runtimes. Never downloads or inherits application secrets."""

import hashlib
import json
import os
import shutil
import subprocess
import uuid
from importlib.resources import files
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

PINS = {"givemotion": "0.1.6", "hyperframes": "0.9.59"}
NODE_DIR = "node-v22.16.0-linux-x64"
CHROME_REL = "chrome157/chrome-headless-shell-linux64/chrome-headless-shell"


class RendererUnavailable(ValueError):
    pass


class RenderFailure(RuntimeError):
    pass


class RendererConfig(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, allow_inf_nan=False, validate_default=True
    )
    renderer: Literal["givemotion", "hyperframes", "legacy"] = "givemotion"
    runtime_root: Path = Path(".renderers")
    font_path: Path = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    scene_seconds: float = Field(default=8, gt=0, le=60)
    timeout_seconds: int = Field(default=1800, ge=1, le=3600)
    fps: int = Field(default=24, ge=1, le=60)
    workers: Literal[1] = 1
    seed: int = 1030

    @field_validator("runtime_root", "font_path")
    @classmethod
    def absolute(cls, value):
        return value.resolve()


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def asset(name):
    return files("fabrica.renderers").joinpath(name)


def atomic_json(path, value):
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temp.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temp.replace(path)


def paths(config):
    root = config.runtime_root
    name = config.renderer
    return dict(
        node=root / NODE_DIR / "bin/node",
        browser=root / CHROME_REL,
        libraries=root / "browser-libs/root/usr/lib/x86_64-linux-gnu",
        package=root / name / "node_modules" / name,
        lock=root / name / "package-lock.json",
    )


def available(config):
    if config.renderer not in PINS:
        raise RendererUnavailable("Only givemotion or hyperframes are native renderers")
    p = paths(config)
    for key in ("node", "browser", "package", "lock"):
        if not p[key].exists():
            raise RendererUnavailable(
                f"{config.renderer} unavailable: missing {key}. Provision this renderer explicitly at {config.runtime_root}; no automatic fallback."
            )
    entry = p["package"] / (
        "src/cli.js" if config.renderer == "givemotion" else "bin/hyperframes.mjs"
    )
    if not entry.is_file() or not all(
        os.access(p[k], os.X_OK) for k in ("node", "browser")
    ):
        raise RendererUnavailable("Native executables or selected CLI are missing")
    installed = json.loads((p["package"] / "package.json").read_text())
    if (installed.get("name"), installed.get("version")) != (
        config.renderer,
        PINS[config.renderer],
    ):
        raise RendererUnavailable("Installed renderer differs from pinned version")
    expected = asset(f"locks/{config.renderer}/package-lock.json").read_bytes()
    if p["lock"].read_bytes() != expected:
        raise RendererUnavailable("Renderer lockfile differs from the approved lock")
    if not config.font_path.is_file():
        raise RendererUnavailable("Project font is missing")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RendererUnavailable("FFmpeg and ffprobe are required")
    return p


def environment(config, directory):
    p = paths(config)
    cache, temp = directory / "cache", directory / "tmp"
    cache.mkdir(parents=True, exist_ok=True)
    temp.mkdir(parents=True, exist_ok=True)
    return {
        "PATH": f"{p['node'].parent}:/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "LD_LIBRARY_PATH": str(p["libraries"]),
        "TMPDIR": str(temp),
        "XDG_CACHE_HOME": str(cache),
        "GIVEMOTION_CACHE": str(cache / "givemotion"),
        "GIVEMOTION_CHROME": str(p["browser"]),
        "HYPERFRAMES_BROWSER_PATH": str(p["browser"]),
        "HYPERFRAMES_NO_TELEMETRY": "1",
        "HYPERFRAMES_NO_UPDATE_CHECK": "1",
        "DO_NOT_TRACK": "1",
        "GIVEMOTION_MAX_BROWSERS": "1",
    }


def command(args, *, config, directory, timeout=120):
    try:
        result = subprocess.run(
            list(map(str, args)),
            cwd=directory,
            env=environment(config, directory),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RenderFailure(f"Tool failed: {type(exc).__name__}") from exc
    if result.returncode:
        (directory / "tool-error.log").write_text(result.stdout + result.stderr)
        raise RenderFailure(
            f"Tool exited {result.returncode}; see {directory / 'tool-error.log'}"
        )
    return result.stdout


def fingerprint(config):
    p = available(config)
    source = {
        str(x.relative_to(Path(__file__).parent)): sha(x)
        for x in Path(__file__).parent.rglob("*")
        if x.is_file() and x.suffix in (".py", ".js", ".css", ".html", ".json")
    }
    for name in ("visual_storyboard.py", "visual_planner.py"):
        source["../" + name] = sha(Path(__file__).parent.parent / name)
    engine = {
        str(x.relative_to(p["package"])): sha(x)
        for x in p["package"].rglob("*")
        if x.is_file() and x.suffix in (".js", ".mjs", ".json", ".css")
    }
    return dict(
        renderer=config.renderer,
        engine_version=PINS[config.renderer],
        node_sha256=sha(p["node"]),
        browser_sha256=sha(p["browser"]),
        font_sha256=sha(config.font_path),
        lockfile_sha256=sha(p["lock"]),
        application=source,
        engine_sources=engine,
        config=config.model_dump(mode="json"),
    )


def provision(name, root, source):
    """Promote only the selected engine from the already verified local runtime cache."""
    if name not in PINS:
        raise RendererUnavailable("Disabled or unknown renderer")
    root, source = Path(root).resolve(), Path(source).resolve()
    # Validate source before copying. No mandatory sibling engine, npm, network or global install.
    available(RendererConfig(renderer=name, runtime_root=source))
    root.mkdir(parents=True, exist_ok=True)
    for part in (NODE_DIR, "chrome157", "browser-libs", name):
        destination = root / part
        if destination.exists():
            continue
        pending = root / f".{part}-{uuid.uuid4().hex}.install"
        shutil.copytree(source / part, pending, symlinks=True)
        if part == name:
            for filename in ("package.json", "package-lock.json"):
                (pending / filename).write_bytes(
                    asset(f"locks/{name}/{filename}").read_bytes()
                )
        pending.rename(destination)
    config = RendererConfig(renderer=name, runtime_root=root)
    p = available(config)
    versions = {
        "node": command(
            [p["node"], "--version"], config=config, directory=root
        ).strip(),
        "browser": command(
            [p["browser"], "--version"], config=config, directory=root
        ).strip(),
        "engine": PINS[name],
    }
    if versions["node"] != "v22.16.0" or "157.0.8103.78" not in versions["browser"]:
        raise RendererUnavailable("Runtime version mismatch; nothing will render")
    atomic_json(
        root / f"{name}-installation.json",
        versions | {"lockfile_sha256": sha(p["lock"])},
    )
    return versions
