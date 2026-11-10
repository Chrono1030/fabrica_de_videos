"""CLI de prototipo. Faltan orquestación y publicación real para el MVP final."""

import argparse
import json
import os
from pathlib import Path

from .cards import create_cards
from .editorial import check
from .models import VideoScript


def load(path: Path) -> VideoScript:
    return VideoScript.model_validate_json(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(
        prog="fabrica", description="Prototipo de fábrica de videos"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    prod = sub.add_parser("produce", help="Producir MP4 local; no publica")
    prod.add_argument("--topic")
    prod.add_argument("--auto", action="store_true")
    prod.add_argument("--catalog", type=Path, default=Path("out/editorial.sqlite3"))
    prod.add_argument("--subtitles", choices=["burn", "track"], default="burn")
    prod.add_argument("--subtitle-font", default="DejaVu Sans")
    prod.add_argument("--subtitle-size", type=int, default=44)
    prod.add_argument("--subtitle-margin", type=int, default=320)
    prod.add_argument("--subtitle-color", default="F4EEDD")
    prod.add_argument("--subtitle-outline", type=int, default=2)
    prod.add_argument("--mode", choices=["mock", "real"], default="mock")
    prod.add_argument("--script", type=Path)
    prod.add_argument("--output", type=Path, default=Path("out/jobs"))
    prod.add_argument("--job-id")
    prod.add_argument("--width", type=int, default=1080)
    prod.add_argument("--height", type=int, default=1920)
    prod.add_argument("--mock-seconds", type=float, default=1.0)
    val = sub.add_parser(
        "validate", help="Validar contrato estructural y reglas preliminares"
    )
    val.add_argument("script", type=Path)
    cards = sub.add_parser("cards", help="Dibujar escenas PNG 1080x1920")
    cards.add_argument("script", type=Path)
    cards.add_argument("--output", type=Path, default=Path("out/cards"))
    for command in (val, cards):
        command.add_argument("--font", default=os.getenv("FONT_PATH"))
    args = parser.parse_args()
    if args.cmd == "produce":
        from .pipeline import produce, produce_auto
        from .subtitle_style import SubtitleStyle

        style = SubtitleStyle(
            args.subtitles == "burn",
            args.subtitle_font,
            args.subtitle_size,
            args.subtitle_margin,
            args.subtitle_color,
            args.subtitle_outline,
        )
        kwargs = dict(
            mode=args.mode,
            root=args.output,
            job_id=args.job_id,
            script_path=args.script,
            width=args.width,
            height=args.height,
            mock_seconds=args.mock_seconds,
            subtitle_style=style,
        )
        if args.auto:
            if args.topic:
                parser.error("--auto no admite --topic")
            print(produce_auto(args.catalog, **kwargs))
        else:
            if not args.topic:
                parser.error("Indicar --topic o --auto")
            print(produce(args.topic, catalog_path=args.catalog, **kwargs))
        return
    script = load(args.script)
    issues = check(script)
    if issues:
        parser.error("Validación preliminar fallida: " + "; ".join(issues))
    if args.cmd == "validate":
        print(
            json.dumps(
                {
                    "ok": True,
                    "scenes": len(script.scenes),
                    "warning": "No incluye verificación semántica",
                },
                ensure_ascii=False,
            )
        )
    else:
        outputs = create_cards(script, args.output, args.font)
        print(json.dumps({"cards": [str(x) for x in outputs]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
