import json
from pathlib import Path

import pytest

from fabrica.cards import create_cards
from fabrica.editorial import check
from fabrica.models import VideoScript

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "guion_demo.json"


def demo():
    return VideoScript.model_validate_json(EXAMPLE.read_text(encoding="utf-8"))


def test_example_contract():
    script = demo()
    assert script.language == "es-419"
    assert len(script.scenes) >= 2
    assert not check(script)


def test_language_rejected():
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    data["language"] = "es-ES"
    with pytest.raises(ValueError):
        VideoScript.model_validate(data)


def test_creates_cards(tmp_path):
    outputs = create_cards(demo(), tmp_path)
    assert len(outputs) == len(demo().scenes)
    assert all(x.is_file() and x.stat().st_size > 1000 for x in outputs)
