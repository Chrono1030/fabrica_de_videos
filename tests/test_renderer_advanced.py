"""Contract and adapter boundaries without browsers or external services."""

import json

import pytest
from pydantic import ValidationError

from experiments.renderer_advanced import adapters
from fabrica.visual_storyboard import VisualStoryboard


def fixture_data():
    return json.loads((adapters.EXP / "storyboard.json").read_text())


@pytest.mark.parametrize("name", ["givemotion", "hyperframes"])
def test_adapter_selection_and_independent_projects(name, tmp_path):
    adapter = adapters.select_adapter(name)
    assert adapter.name == name
    storyboard = VisualStoryboard.model_validate(fixture_data())
    adapter.validate(storyboard)
    project = tmp_path / name
    adapter.build(storyboard, project)
    files = "\n".join(p.read_text() for p in project.rglob("*.html"))
    for scene in storyboard.scenes:
        assert scene.narrative in files
        assert scene.narrative_segment_id in files
    assert "gm.onFrame" in files if name == "givemotion" else "gsap.timeline" in files
    assert (
        ("gsap.timeline" not in files)
        if name == "givemotion"
        else ("gm.onFrame" not in files)
    )


@pytest.mark.parametrize(
    "name", ["pillow", "existing", "motion_canvas", "remotion", "unknown"]
)
def test_disabled_renderers_rejected(name):
    with pytest.raises(ValueError, match="disabled"):
        adapters.select_adapter(name)


def test_storyboard_has_exact_timing_and_balanced_transfer():
    board = VisualStoryboard.model_validate(fixture_data())
    assert [(s.start, s.end) for s in board.scenes] == [
        (0, 5),
        (5, 12),
        (12, 20),
        (20, 28),
        (28, 37),
        (37, 46),
        (46, 55),
    ]
    before, after = board.budgets["initial"], board.budgets["alternative"]
    assert before.income == after.income == 1200000
    assert before.variable - after.variable == after.savings - before.savings == 30000
    assert board.audio == "none"


@pytest.mark.parametrize("fault", ["sum", "gap", "event", "duplicate", "engine"])
def test_invalid_storyboard_rejected(fault):
    data = fixture_data()
    if fault == "sum":
        data["budgets"]["initial"]["savings"] += 1
    elif fault == "gap":
        data["scenes"][1]["start"] = 6
    elif fault == "event":
        data["scenes"][0]["events"][0]["duration"] = 9
    elif fault == "duplicate":
        data["scenes"][1]["narrative_segment_id"] = data["scenes"][0][
            "narrative_segment_id"
        ]
    else:
        data["renderer"] = "givemotion"
    with pytest.raises(ValidationError):
        VisualStoryboard.model_validate(data)


def test_configuration_and_sanitized_environment(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "never-inherit")
    assert "never-inherit" not in str(adapters.environment())
    config = adapters.load_config()
    assert config["renderers"] == {"givemotion": "0.1.6", "hyperframes": "0.9.59"}
    monkeypatch.setattr(
        adapters,
        "load_config",
        lambda: {**config, "renderers": {"givemotion": "0.0.0"}},
    )
    with pytest.raises(ValueError, match="pinned"):
        adapters.select_adapter("givemotion").validate(
            VisualStoryboard.model_validate(fixture_data())
        )
