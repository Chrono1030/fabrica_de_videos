import json
from types import SimpleNamespace

import pytest

from fabrica import pipeline
from fabrica.cards import create_cards, visual_values
from fabrica.gpt import GenerationError, generate_checked
from fabrica.render import quality
from fabrica.tts import MockTTS, PiperTTS, duration, normalize


def test_mock_wav_deterministic(tmp_path):
    a, b = tmp_path / "a.wav", tmp_path / "b.wav"
    assert MockTTS(0.25).synthesize("prueba", a) == 0.25
    MockTTS(0.25).synthesize("otra", b)
    assert a.read_bytes() == b.read_bytes()
    assert duration(a) == 0.25
    assert (
        normalize("$25 y 5% del PIB")
        == "25 dólares y 5 por ciento del producto interno bruto"
    )
    with pytest.raises(ValueError):
        MockTTS(0)


def test_visual_values_and_types(tmp_path):
    assert visual_values(["A:10", "B:5"]) == [10, 5]
    for item in ["A", "A:nan", "A:-1"]:
        with pytest.raises(ValueError):
            visual_values([item])
    script = pipeline.mock_script("Economía")
    for kind in [
        "diagram",
        "icon",
        "concept",
        "big_number",
        "comparison",
        "bar_chart",
        "line_chart",
    ]:
        scene = script.scenes[0]
        scene.visual_type = kind
        scene.visual_data = ["A:1", "B:2"]
        assert create_cards(script, tmp_path / kind)


def test_real_mp4_resume_and_corruption(tmp_path):
    args = dict(
        topic="Costo de oportunidad",
        root=tmp_path,
        job_id="integration",
        width=180,
        height=320,
        mock_seconds=0.3,
    )
    job = pipeline.produce(**args)
    state = json.loads((job / "result.json").read_text())
    assert state["status"] == "TECHNICALLY_READY"
    assert state["costs"] == [] and state["audio_simulated"]
    assert state["publish_enabled"] is False
    assert state["quality"]["decoded"]
    assert not state["quality"]["editorial_verified"]
    before = {
        p: p.stat().st_mtime_ns for p in [job / "final.mp4", job / "audio_00.wav"]
    }
    pipeline.produce(**args)
    assert all(p.stat().st_mtime_ns == m for p, m in before.items())
    (job / "final.mp4").write_bytes(b"broken")
    pipeline.produce(**args)
    assert (job / "final.mp4").stat().st_size > 1000
    with pytest.raises(ValueError):
        pipeline.produce(**(args | {"topic": "Otro"}))
    with pytest.raises((AssertionError, ValueError)):
        quality(job / "final.mp4", 360, 640, 1.2, job / "subtitles.srt")


def test_failure_and_retry(tmp_path, monkeypatch):
    args = dict(
        topic="Costo",
        root=tmp_path,
        job_id="retry",
        width=180,
        height=320,
        mock_seconds=0.2,
    )
    original = pipeline.compose

    def fail(*a, **kw):
        raise RuntimeError("Fallo deliberado")

    monkeypatch.setattr(pipeline, "compose", fail)
    with pytest.raises(RuntimeError):
        pipeline.produce(**args)
    job = tmp_path / "retry"
    assert json.loads((job / "result.json").read_text())["status"] == "BLOCKED"
    audio_mtime = (job / "audio_00.wav").stat().st_mtime_ns
    monkeypatch.setattr(pipeline, "compose", original)
    pipeline.produce(**args)
    assert (job / "audio_00.wav").stat().st_mtime_ns == audio_mtime


def test_api_contract_usage_budget(monkeypatch):
    calls = []

    def parse(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            output_parsed=pipeline.mock_script("Costo"),
            id="test",
            usage=SimpleNamespace(input_tokens=100, output_tokens=200),
        )

    client = SimpleNamespace(responses=SimpleNamespace(parse=parse))
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    monkeypatch.setenv("OPENAI_REQUEST_RESERVE_USD", "1")
    with pytest.raises(GenerationError):
        generate_checked("Costo", client, 0.5)
    assert not calls
    script, usage, issues = generate_checked("Costo", client, 1)
    assert not issues and usage["input_tokens"] == 100
    assert calls[0]["model"] == "test-model"
    assert calls[0]["text_format"] is type(script)
    client.responses.parse = lambda **kw: SimpleNamespace(
        output_parsed=None, usage=None
    )
    with pytest.raises(GenerationError):
        generate_checked("Costo", client, 1)


def test_api_failure_reservation_blocks_retry(tmp_path, monkeypatch):
    def fail(*a, **kw):
        raise GenerationError("Timeout simulado")

    monkeypatch.setattr(pipeline, "generate_checked", fail)
    monkeypatch.setenv("MAX_API_BUDGET_USD", "2")
    monkeypatch.setenv("OPENAI_REQUEST_RESERVE_USD", "1")
    with pytest.raises(GenerationError):
        pipeline.produce("Costo", "real", tmp_path, "api")
    state = json.loads((tmp_path / "api/result.json").read_text())
    assert state["api_pending"]
    with pytest.raises(RuntimeError, match="conciliar"):
        pipeline.produce("Costo", "real", tmp_path, "api")
    assert json.loads((tmp_path / "budget.json").read_text())["reserved_usd"] == 1


def test_invalid_script_blocked(tmp_path):
    script = tmp_path / "invalid.json"
    script.write_text("{}")
    with pytest.raises(ValueError):
        pipeline.produce(
            "Costo", root=tmp_path / "jobs", job_id="bad", script_path=script
        )
    assert (
        json.loads((tmp_path / "jobs/bad/result.json").read_text())["status"]
        == "BLOCKED"
    )


def test_piper_requires_local_model(tmp_path, monkeypatch):
    monkeypatch.setenv("PIPER_VOICE_MODEL", str(tmp_path / "missing.onnx"))
    with pytest.raises(RuntimeError):
        PiperTTS().synthesize("Prueba", tmp_path / "audio.wav")


def test_api_invalid_response_keeps_usage():
    response = SimpleNamespace(
        output_parsed=None,
        id="invalid",
        usage=SimpleNamespace(input_tokens=5, output_tokens=10),
    )
    client = SimpleNamespace(responses=SimpleNamespace(parse=lambda **kw: response))
    script, usage, issues = generate_checked("Prueba", client, 1)
    assert script is None and issues and usage["output_tokens"] == 10

    def timeout(**kw):
        raise TimeoutError("sin conexión")

    client.responses.parse = timeout
    with pytest.raises(GenerationError, match="TimeoutError"):
        generate_checked("Prueba", client, 1)


def test_empty_narration_rejected():
    from fabrica.models import VideoScript

    data = pipeline.mock_script("Costo").model_dump(mode="json")
    data["scenes"][0]["narration"] = " "
    with pytest.raises(ValueError):
        VideoScript.model_validate(data)


def test_piper_local_double(tmp_path, monkeypatch):
    import fabrica.tts as tts

    model = tmp_path / "voice.onnx"
    model.write_bytes(b"test-double-not-a-model")
    model.with_suffix(".onnx.json").write_text('{"language":{"code":"es_MX"}}')
    monkeypatch.setenv("PIPER_VOICE_MODEL", str(model))
    calls = []

    def fake_run(args, **kwargs):
        calls.append(kwargs["input"])
        MockTTS(0.2).synthesize("", tmp_path / "voice.wav")

    monkeypatch.setattr(tts.subprocess, "run", fake_run)
    assert PiperTTS().synthesize("5%", tmp_path / "voice.wav") == 0.2
    assert calls == ["5 por ciento"]


def test_short_real_audio_blocked(tmp_path, monkeypatch):
    script = tmp_path / "script.json"
    script.write_text(pipeline.mock_script("Costo").model_dump_json())
    monkeypatch.setattr(pipeline, "PiperTTS", lambda: MockTTS(0.2))
    with pytest.raises(ValueError, match="60–90"):
        pipeline.produce("Costo", "real", tmp_path / "jobs", "short", script)
    assert not (tmp_path / "jobs/short/final.mp4").exists()
