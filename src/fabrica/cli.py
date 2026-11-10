"""CLI de prototipo. Faltan orquestación y publicación real para el MVP final."""
import argparse
import json
import os
from pathlib import Path
from .models import VideoScript
from .editorial import check
from .cards import create_cards


def load(path: Path) -> VideoScript:
    return VideoScript.model_validate_json(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(prog="fabrica", description="Prototipo de fábrica de videos")
    sub = parser.add_subparsers(dest="cmd", required=True)
    val = sub.add_parser("validate", help="Validar contrato estructural y reglas preliminares")
    val.add_argument("script", type=Path)
    cards = sub.add_parser("cards", help="Dibujar escenas PNG 1080x1920")
    cards.add_argument("script", type=Path)
    cards.add_argument("--output", type=Path, default=Path("out/cards"))
    for command in (val, cards):
        command.add_argument("--font", default=os.getenv("FONT_PATH"))
    args = parser.parse_args()
    script = load(args.script)
    issues = check(script)
    if issues:
        parser.error("Validación preliminar fallida: " + "; ".join(issues))
    if args.cmd == "validate":
        print(json.dumps({"ok": True, "scenes": len(script.scenes),
                          "warning": "No incluye verificación semántica"}, ensure_ascii=False))
    else:
        outputs = create_cards(script, args.output, args.font)
        print(json.dumps({"cards": [str(x) for x in outputs]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
