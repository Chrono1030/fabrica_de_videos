"""Real optional native integration tests: never replace engines with fake MP4s.

Run explicitly with FABRICA_NATIVE_TESTS=1 after local renderer provisioning.
"""

import json
import os
import wave
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from fabrica import pipeline
from fabrica.factory import Factory
from fabrica.factory_store import FactoryStore
from fabrica.renderers.native import AudioTrack
from fabrica.renderers.runtime import RendererConfig, available, sha
from fabrica.scheduler import ScheduleConfig

pytestmark = [
    pytest.mark.native_renderer,
    pytest.mark.skipif(
        os.getenv("FABRICA_NATIVE_TESTS") != "1",
        reason="Native integration requires explicitly provisioned local engines and Chromium loopback",
    ),
]


def config(name="givemotion"):
    result = RendererConfig(
        renderer=name,
        runtime_root=Path(os.getenv("FABRICA_RUNTIME_ROOT", ".renderers")),
        scene_seconds=0.5,
    )
    available(result)
    return result


def test_real_factory_cycle_givemotion_and_resume(tmp_path, monkeypatch):
    monkeypatch.setattr(
        pipeline, "generate_checked", lambda *a, **k: pytest.fail("No paid API")
    )
    monkeypatch.setattr(pipeline, "PiperTTS", lambda *a, **k: pytest.fail("No voice"))
    settings = ScheduleConfig(
        timezone="America/Argentina/Catamarca",
        local_time="12:00",
        start_date=date(2026, 11, 18),
    )
    store = FactoryStore(tmp_path / "factory.sqlite3")
    factory = Factory(store, settings, tmp_path / "factory", config())
    at = datetime(2026, 11, 18, 16, tzinfo=timezone.utc)
    first = factory.cycle(clock=at, width=180, height=320, fault="uncertain")
    assert first["state"] == "RETRY_WAIT"
    job = Path(first["job"])
    video = job / "final.mp4"
    before = (sha(video), video.stat().st_mtime_ns)
    result = json.loads((job / "result.json").read_text())
    assert result["renderer"] == "givemotion" and result["quality"]["decoded"]
    assert result["quality"]["frames"] == 48 and result["audio_present"] is False
    assert not result["render_metrics"].get("test_double") and result["costs"] == []
    done = factory.cycle(clock=at + timedelta(minutes=2), width=180, height=320)
    assert done["state"] == "SIMULATED_DONE" and before == (
        sha(video),
        video.stat().st_mtime_ns,
    )
    assert len(list((job / "render").glob("attempt-*"))) == 1
    assert json.loads((job / "publication.json").read_text())["real_upload"] is False
    assert store.package(done["job_id"]).asset_hash == sha(video)
    with store.connect() as db:
        metrics = json.loads(db.execute("SELECT record FROM metrics").fetchone()[0])
        assert (
            metrics["renderer"] == "givemotion"
            and metrics["render_wall_seconds"] > 0
            and metrics["api_calls"] == 0
        )
        assert db.execute("SELECT count(*) FROM mock_remote").fetchone()[0] == 1


def test_real_hyperframes_main_pipeline(tmp_path):
    job = pipeline.produce(
        "Costo de oportunidad",
        root=tmp_path,
        job_id="native-hyperframes",
        width=180,
        height=320,
        renderer_config=config("hyperframes"),
    )
    result = json.loads((job / "result.json").read_text())
    assert result["renderer"] == "hyperframes" and result["quality"]["decoded"]
    assert result["quality"]["frames"] == 48 and not result["quality"]["audio"]
    assert result["render_metrics"]["engine_version"] == "0.9.59"
    assert (
        result["render_metrics"]["cpu_seconds"] > 0
        and result["render_metrics"]["peak_process_tree_rss_mib"] > 0
    )


def test_real_optional_audio_is_external_original_tone(tmp_path):
    # Original synthetic silence, not a voice and not a TTS provider.
    audio = tmp_path / "original-silence.wav"
    with wave.open(str(audio), "wb") as wav:
        wav.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        wav.writeframes(b"\0\0" * 8000)
    manifest = AudioTrack(
        path=audio,
        sha256=sha(audio),
        commercial_allowed=True,
        license="Original test signal, no voice",
        evidence=["Generated zero-valued samples in this test"],
    )
    job = pipeline.produce(
        "Costo de oportunidad",
        root=tmp_path / "jobs",
        job_id="native-audio",
        width=180,
        height=320,
        renderer_config=config(),
        audio=manifest,
    )
    result = json.loads((job / "result.json").read_text())
    assert result["quality"]["decoded"] and result["quality"]["audio"]
    assert result["render_metrics"]["audio"]["sha256"] == sha(audio)
    assert result["render_metrics"]["audio_end_padding_seconds"] == 1.5
    assert result["duration"] == 2 and result["audio_simulated"] is False


def test_real_js_transfer_uses_storyboard_and_conserves_values(tmp_path):
    from importlib.resources import files

    from fabrica.renderers.runtime import asset, command, paths

    board = json.loads(
        files("fabrica").joinpath("data/budget_55_storyboard.json").read_text()
    )
    source = (
        "globalThis.window={};"
        + asset("assets/components.js").read_text()
        + "\nconst b="
        + json.dumps(board)
        + ";const s=b.scenes[4];const values=[0,4,8].map(t=>FactoryVisuals.state(s,b,t).values);console.log(JSON.stringify(values));"
    )
    # In Node the exported browser namespace lives on the explicit window object.
    source = source.replace("FactoryVisuals.state", "window.FactoryVisuals.state")
    script = tmp_path / "state.cjs"
    script.write_text(source)
    cfg = config()
    actual = json.loads(
        command([paths(cfg)["node"], script], config=cfg, directory=tmp_path)
    )
    assert actual == [
        [700000, 380000, 120000],
        [700000, 365000, 135000],
        [700000, 350000, 150000],
    ]
    assert all(sum(row) == 1200000 for row in actual)
