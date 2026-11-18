"""Measured narration, authorization and recoverable audio stages."""

import json
from pathlib import Path

import pytest

from fabrica.audio_providers import (
    ExternalAudio,
    NarrationBlocked,
    NarrationConfig,
    create_audio_provider,
    inspect_wav,
)
from fabrica.models import VideoScript
from fabrica.narration_audio import NarrationStages, prepare_narration
from fabrica.narration_subtitles import write_subtitles
from fabrica.narration_timeline import NarrationTimeline, plan_narration
from fabrica.normalization import normalize
from fabrica.pipeline import save
from fabrica.renderers.runtime import RendererConfig, sha
from fabrica.tts import MockTTS
from fabrica.visual_planner import plan_script

ROOT = Path(__file__).resolve().parents[1]


def board():
    script = VideoScript.model_validate_json(
        (ROOT / "src/fabrica/data/costo_oportunidad.json").read_text()
    )
    return plan_script(script, "test")


def prepare(tmp_path, config=None, state=None):
    state = state if state is not None else dict(stages={}, events=[])
    stages = NarrationStages(tmp_path, state, save)
    adjusted, timeline = prepare_narration(
        board(),
        tmp_path,
        "test",
        config or NarrationConfig(mock_seconds=0.1),
        RendererConfig(),
        stages,
        save,
    )
    return adjusted, timeline, state


def test_wav_measured_and_truncated(tmp_path):
    p = tmp_path / "audio.wav"
    assert MockTTS(0.317).synthesize("texto", p) > 0
    measured = inspect_wav(p)
    assert measured["samples"] / measured["sample_rate"] == measured["duration"]
    assert measured["channels"] == 1
    p.write_bytes(p.read_bytes()[:-100])
    with pytest.raises(ValueError):
        inspect_wav(p)


@pytest.mark.parametrize(
    "source,expected",
    [
        ("ARS 1.200.000", "un millón doscientos mil pesos argentinos"),
        ("USD 30,50", "treinta coma cinco cero dólares estadounidenses"),
        ("-12,5%", "menos doce coma cinco por ciento"),
        ("-$30.000", "menos treinta mil pesos argentinos"),
        ("18/11/2026", "dieciocho de noviembre de dos mil veintiséis"),
        (
            "IPC, PIB e IVA",
            "índice de precios al consumidor, producto interno bruto e impuesto al valor agregado",
        ),
    ],
)
def test_normalization(source, expected):
    assert normalize(source, "ARS") == expected


def test_corpus_and_budget_preserve_editorial():
    normalize((ROOT / "examples/tts_comparison.txt").read_text(), "ARS")
    from fabrica.visual_storyboard import VisualStoryboard

    b = VisualStoryboard.model_validate_json(
        (ROOT / "src/fabrica/data/budget_55_storyboard.json").read_text()
    )
    requests = plan_narration(b, "ARS")
    assert "$1.200.000" in " ".join(r["subtitle_text"] for r in requests)
    assert "un millón doscientos mil" in " ".join(r["spoken_text"] for r in requests)
    assert (
        b.data
        == json.loads(
            (ROOT / "src/fabrica/data/budget_55_storyboard.json").read_text()
        )["data"]
    )


def test_explicit_voice_and_commercial_rejection():
    with pytest.raises(NarrationBlocked):
        create_audio_provider(NarrationConfig(provider="piper"))
    with pytest.raises(NarrationBlocked):
        create_audio_provider(NarrationConfig(authorization_mode="commercial"))
    with pytest.raises(NarrationBlocked):
        create_audio_provider(NarrationConfig(provider="external"))


def test_measured_timeline_captions_and_cache(tmp_path, monkeypatch):
    adjusted, timeline, state = prepare(tmp_path)
    assert timeline.duration == adjusted.duration != board().duration
    assert timeline.total_samples == inspect_wav(tmp_path / "narration.wav")["samples"]
    assert all(abs(s.start * 24 - round(s.start * 24)) < 1e-6 for s in adjusted.scenes)
    assert all(s.duration == s.samples / s.sample_rate for s in timeline.segments)
    assert all(e.narration_anchor for s in adjusted.scenes for e in s.elements)
    assert adjusted.data == board().data
    config = NarrationConfig(mock_seconds=0.1)
    write_subtitles(timeline, adjusted, config, tmp_path, save)
    assert "[Events]" in (tmp_path / "subtitles.ass").read_text()
    assert (
        json.loads((tmp_path / "subtitle_validation.json").read_text())[
            "phonetic_alignment"
        ]
        is False
    )
    old = sha(tmp_path / "narration.wav")
    monkeypatch.setattr(
        MockTTS, "synthesize", lambda *a: pytest.fail("Audio must be reused")
    )
    _, again, _ = prepare(tmp_path, config, state)
    assert again.sha256 == old
    with pytest.raises(ValueError):
        data = timeline.model_dump()
        data["segments"][0]["end"] -= 0.01
        NarrationTimeline.model_validate(data)
    with pytest.raises(ValueError):
        write_subtitles(
            timeline,
            adjusted.model_copy(
                update={
                    "safe_area": adjusted.safe_area.model_copy(update={"bottom": 1000})
                }
            ),
            config,
            tmp_path,
            save,
        )


def test_tts_failure_resume_and_limit(tmp_path, monkeypatch):
    state = dict(stages={}, events=[])
    original = MockTTS.synthesize
    calls = []

    def fail(self, text, path):
        calls.append(text)
        if len(calls) == 2:
            raise RuntimeError("injected TTS failure")
        return original(self, text, path)

    monkeypatch.setattr(MockTTS, "synthesize", fail)
    with pytest.raises(RuntimeError):
        prepare(tmp_path, state=state)
    first = calls[0]
    prepare(tmp_path, state=state)
    assert calls.count(first) == 1
    with pytest.raises(NarrationBlocked, match="BLOCKED_NARRATION_DURATION"):
        prepare(tmp_path, NarrationConfig(mock_seconds=0.1, max_seconds=0.5), state)
    assert not list(tmp_path.rglob("*.partial.wav"))


def test_external_rights_transcript_and_hash(tmp_path):
    wav = tmp_path / "owned.wav"
    MockTTS(0.3).synthesize("hola", wav)
    from fabrica.narration_timeline import text_hash

    clip = dict(
        segment_id="seg1",
        path="owned.wav",
        sha256=sha(wav),
        source="Generated original test tone, not a human recording",
        license="Owner permission for this technical test only",
        commercial_allowed=False,
        evidence=["Explicit test fixture authorization"],
        authorized_by="Test fixture owner",
        test_use_authorized=True,
        regional_language="es-419",
        spoken_text_sha256=text_hash("hola"),
    )
    manifest = tmp_path / "external.json"
    save(manifest, dict(manifest_id="owned", clips=[clip]))
    provider = ExternalAudio(manifest, "test")
    assert (
        provider.for_segment("seg1", text_hash("hola")).synthesize(
            "hola", tmp_path / "copy.wav"
        )
        == 0.3
    )
    with pytest.raises(NarrationBlocked):
        ExternalAudio(manifest, "commercial").authorize("seg1", text_hash("hola"))
    with pytest.raises(ValueError):
        provider.authorize("seg1", text_hash("otro texto"))
    wav.write_bytes(wav.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="hash"):
        provider.authorize("seg1", text_hash("hola"))


def test_audio_change_invalidates_identity(tmp_path):
    wav = tmp_path / "audio.wav"
    MockTTS(0.2).synthesize("a", wav)
    manifest = tmp_path / "external.json"
    save(manifest, dict(clips=[dict(segment_id="x", path="audio.wav")]))
    config = NarrationConfig(provider="external", external_manifest=manifest)
    before = config.identity()
    wav.write_bytes(wav.read_bytes() + b"x")
    assert config.identity() != before


def test_piper_voice_permissions_and_hash_are_independent(tmp_path, monkeypatch):
    from fabrica import audio_providers
    from fabrica.audio_providers import load_voice

    monkeypatch.setattr(audio_providers, "version", lambda name: "fixture-version")

    model = tmp_path / "fixture.onnx"
    model.write_bytes(b"not-a-voice-only-contract-test")
    Path(str(model) + ".json").write_text("{}")
    Path(str(model) + ".license.json").write_text("{}")
    assets = [
        dict(
            path=str(p),
            sha256=sha(p),
            source="Explicit unit fixture; never synthesized",
            license="Test only",
            evidence=["fixture"],
        )
        for p in (model, Path(str(model) + ".json"), Path(str(model) + ".license.json"))
    ]
    manifest = dict(
        voice_id="fixture",
        provider="piper",
        engine_version="fixture-version",
        engine_license="GPL-3.0-or-later",
        model_version="test-fixture",
        regional_language="es_MX",
        artifacts=assets,
        rights_chain=[
            dict(
                name="Explicit test-only permission",
                license="test only",
                evidence=["fixture permission"],
                verified=True,
            )
        ],
        chain_complete=True,
        technical_execution_allowed=True,
        test_use_authorized=True,
        rights_status="RESEARCH_ONLY",
    )
    path = tmp_path / "voice.json"
    save(path, manifest)
    cfg = NarrationConfig(provider="piper", voice_id="fixture", voice_manifest=path)
    assert load_voice(cfg)[1] == model
    with pytest.raises(NarrationBlocked, match="Commercial"):
        load_voice(cfg.model_copy(update={"authorization_mode": "commercial"}))
    with pytest.raises(NarrationBlocked):
        load_voice(cfg.model_copy(update={"voice_id": "other"}))
    save(path, manifest | dict(regional_language="es_ES"))
    with pytest.raises(NarrationBlocked, match="es_ES"):
        load_voice(cfg)
    save(path, manifest | dict(technical_execution_allowed=False))
    with pytest.raises(NarrationBlocked, match="Technical"):
        load_voice(cfg)
    save(path, manifest)
    model.write_bytes(b"altered")
    with pytest.raises(NarrationBlocked, match="SHA-256"):
        load_voice(cfg)
