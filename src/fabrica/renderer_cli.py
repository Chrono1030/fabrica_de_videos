"""Renderer configuration for the existing application CLI; no automatic install."""

import json
from pathlib import Path

from .renderers.native import AudioTrack
from .renderers.runtime import RendererConfig, RendererUnavailable, available, provision


def add_options(parser):
    parser.add_argument("--renderer", choices=["givemotion", "hyperframes", "legacy"])
    parser.add_argument("--renderer-config", type=Path)
    parser.add_argument("--runtime-root", type=Path)
    parser.add_argument("--scene-seconds", type=float)
    parser.add_argument("--storyboard", type=Path)
    parser.add_argument("--audio-manifest", type=Path)
    parser.add_argument("--narration-config", type=Path)


def options(args):
    config = None
    if (
        args.renderer_config
        or args.renderer
        or args.runtime_root
        or args.scene_seconds is not None
    ):
        data = (
            json.loads(args.renderer_config.read_text()) if args.renderer_config else {}
        )
        for key, value in [
            ("renderer", args.renderer),
            ("runtime_root", args.runtime_root),
            ("scene_seconds", args.scene_seconds),
        ]:
            if value is not None:
                data[key] = value
        config = RendererConfig.model_validate(data)
    audio = None
    if args.audio_manifest:
        data = json.loads(args.audio_manifest.read_text())
        path = Path(data["path"])
        data["path"] = (
            path
            if path.is_absolute()
            else (args.audio_manifest.parent / path).resolve()
        )
        audio = AudioTrack.model_validate(data)
        audio.verify()
    narration = None
    if getattr(args, "narration_config", None):
        from .audio_providers import NarrationConfig

        data = json.loads(args.narration_config.read_text())
        for key in ("voice_manifest", "external_manifest"):
            if data.get(key):
                path = Path(data[key])
                data[key] = (
                    path
                    if path.is_absolute()
                    else (args.narration_config.parent / path).resolve()
                )
        narration = NarrationConfig.model_validate(data)
    return dict(
        renderer_config=config,
        storyboard_path=args.storyboard,
        audio=audio,
        narration_config=narration,
    )


def add_command(sub):
    cmd = sub.add_parser(
        "renderer", help="Inspeccionar o provisionar un motor local, sin descargas"
    )
    cmd.add_argument("action", choices=["status", "provision"])
    cmd.add_argument(
        "--engine", choices=["givemotion", "hyperframes"], default="givemotion"
    )
    cmd.add_argument("--runtime-root", type=Path, default=Path(".renderers"))
    cmd.add_argument(
        "--source", type=Path, help="Caché local de runtimes ya fijados; solo provision"
    )


def dispatch(args):
    if args.cmd != "renderer":
        return False
    if args.action == "provision":
        if args.source is None:
            raise ValueError(
                "Provision requires an explicit local --source; no downloads"
            )
        result = provision(args.engine, args.runtime_root, args.source)
    else:
        try:
            p = available(
                RendererConfig(renderer=args.engine, runtime_root=args.runtime_root)
            )
            result = dict(
                renderer=args.engine,
                available=True,
                paths={k: str(v) for k, v in p.items()},
            )
        except RendererUnavailable as exc:
            result = dict(renderer=args.engine, available=False, error=str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return True
