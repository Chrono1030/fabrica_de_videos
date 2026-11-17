"""Safety boundaries of the isolated experiment; no browser/network in unit tests."""

import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def runner(monkeypatch):
    directory = Path(__file__).resolve().parents[1] / "experiments/renderer_ab"
    monkeypatch.syspath_prepend(str(directory))
    spec = importlib.util.spec_from_file_location(
        "renderer_ab_run", directory / "run.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("name", ["motion_canvas", "remotion"])
def test_disabled_engine_cannot_create_outputs(runner, monkeypatch, tmp_path, name):
    monkeypatch.setattr(runner, "OUT", tmp_path / "results")
    with pytest.raises(ValueError, match="disabled"):
        runner.run(name, 2, False)
    assert not (tmp_path / "results").exists()


def test_existing_results_are_preserved(runner, monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "OUT", tmp_path)
    target = tmp_path / "existing/run-1"
    target.mkdir(parents=True)
    video = target / "final.mp4"
    video.write_bytes(b"prior render")
    with pytest.raises(FileExistsError):
        runner.run("existing", 2, False)
    assert video.read_bytes() == b"prior render"
    assert not (tmp_path / "existing/run-2").exists()


def test_js_environment_excludes_application_secrets(runner, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret")
    monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", "test-secret")
    child = runner.env()
    assert not any("test-secret" in str(v) for v in child.values())
    assert "OPENAI_API_KEY" not in child
    assert child["HYPERFRAMES_NO_TELEMETRY"] == "1"
    assert child["DO_NOT_TRACK"] == "1"
