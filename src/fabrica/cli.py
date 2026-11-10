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
    prod.add_argument("--topic", required=True)
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
        from .pipeline import produce

        print(
            produce(
                args.topic,
                args.mode,
                args.output,
                args.job_id,
                args.script,
                args.width,
                args.height,
                args.mock_seconds,
            )
        )
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
