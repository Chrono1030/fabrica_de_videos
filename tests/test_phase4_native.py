"""Real engines through produce/cycle, including recovery. No renderer doubles."""

import json
import os
import struct
import wave
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from fabrica import narration_composition, pipeline
from fabrica.audio_providers import NarrationConfig
from fabrica.factory import Factory
from fabrica.factory_store import FactoryStore
from fabrica.narration_timeline import plan_narration
from fabrica.pipeline import save
from fabrica.renderers.runtime import RendererConfig, RenderFailure, sha
from fabrica.scheduler import ScheduleConfig
from fabrica.tts import MockTTS
from fabrica.visual_planner import plan_script

pytestmark = [
    pytest.mark.native_renderer,
    pytest.mark.skipif(
        os.getenv("FABRICA_NATIVE_TESTS") != "1",
        reason="Requires provisioned local native engines and Chromium loopback",
    ),
]


def config(name="givemotion"):
    return RendererConfig(
        renderer=name,
        runtime_root=Path(os.getenv("FABRICA_RUNTIME_ROOT", ".renderers")),
        scene_seconds=0.5,
    )


def test_phase4_cycle_composition_recovery(tmp_path, monkeypatch):
    rendering = config()
    monkeypatch.setattr(
        pipeline, "generate_checked", lambda *a, **k: pytest.fail("No paid API")
    )
    store = FactoryStore(tmp_path / "factory.sqlite3")
    factory = Factory(
        store,
        ScheduleConfig(
            timezone="America/Argentina/Catamarca",
            local_time="12:00",
            start_date=date(2026, 11, 18),
        ),
        tmp_path / "factory",
        rendering,
    )
    at = datetime(2026, 11, 18, 16, tzinfo=timezone.utc)
    cfg = NarrationConfig(mock_seconds=0.15)
    actual = narration_composition.command

    def fail(args, **kwargs):
        if "libx264" in args:
            raise RenderFailure("injected composition failure")
        return actual(args, **kwargs)

    monkeypatch.setattr(narration_composition, "command", fail)
    with pytest.raises(RenderFailure, match="injected composition failure"):
        factory.cycle(clock=at, width=180, height=320, narration_config=cfg)
    job = next((tmp_path / "factory/jobs").iterdir())
    first = {"job_id": job.name}
    with store.connect() as db:
        assert (
            db.execute(
                "SELECT state FROM calendar WHERE job_id=?", (job.name,)
            ).fetchone()[0]
            == "RETRY_WAIT"
        )
    assert (job / "video_silent.mp4").is_file() and not (job / "final.mp4").exists()
    silent_before = (
        sha(job / "video_silent.mp4"),
        (job / "video_silent.mp4").stat().st_mtime_ns,
    )
    monkeypatch.setattr(narration_composition, "command", actual)
    monkeypatch.setattr(
        MockTTS,
        "synthesize",
        lambda *a: pytest.fail("TTS reused after composition failure"),
    )
    second = factory.cycle(
        clock=at + timedelta(minutes=2),
        width=180,
        height=320,
        narration_config=cfg,
        fault="uncertain",
    )
    assert second["job_id"] == first["job_id"] and second["state"] == "RETRY_WAIT"
    final_before = (sha(job / "final.mp4"), (job / "final.mp4").stat().st_mtime_ns)
    done = factory.cycle(
        clock=at + timedelta(minutes=4), width=180, height=320, narration_config=cfg
    )
    assert done["state"] == "SIMULATED_DONE" and done["job_id"] == first["job_id"]
    assert silent_before == (
        sha(job / "video_silent.mp4"),
        (job / "video_silent.mp4").stat().st_mtime_ns,
    )
    assert final_before == (
        sha(job / "final.mp4"),
        (job / "final.mp4").stat().st_mtime_ns,
    )
    result = json.loads((job / "result.json").read_text())
    assert result["quality"]["decoded"] and result["audio_simulated"]
    assert (
        result["quality"]["audio_channels"] == 1
        and result["quality"]["audio_sample_rate"] == 48000
    )
    assert len(list((job / "render").glob("attempt-*"))) == 1
    assert json.loads((job / "publication.json").read_text())["real_upload"] is False
    assert store.package(done["job_id"]).asset_hash == sha(job / "final.mp4")
    with store.connect() as db:
        assert db.execute("SELECT count(*) FROM mock_remote").fetchone()[0] == 1
    with pytest.raises(ValueError):
        pipeline.produce(
            result["config"]["topic"],
            root=job.parent,
            job_id=job.name,
            script_path=tmp_path / "factory/scripts" / f"{job.name}.json",
            width=180,
            height=320,
            mock_seconds=result["config"]["mock_seconds"],
            renderer_config=rendering,
            catalog_path=store.path,
            narration_config=NarrationConfig(mock_seconds=0.3),
        )


@pytest.mark.parametrize("engine", ["givemotion", "hyperframes"])
def test_external_audio_change_recomposes_without_rerender(tmp_path, engine):
    script = pipeline.mock_script("Costo de oportunidad")
    script_path = tmp_path / "input.json"
    save(script_path, script.model_dump(mode="json"))
    rendering = config(engine)
    b = plan_script(script, "audio-cache", width=180, height=320, scene_seconds=0.5)
    requests = plan_narration(b)
    clips = []
    for i, r in enumerate(requests):
        path = tmp_path / f"owned-{i}.wav"
        MockTTS(0.15).synthesize(r["spoken_text"], path)
        clips.append(
            dict(
                segment_id=r["segment_id"],
                path=str(path),
                sha256=sha(path),
                source="Original test tones, not real voice",
                license="Owner-authorized technical test fixture",
                commercial_allowed=False,
                evidence=["Explicit fixture authorization"],
                authorized_by="Test fixture owner",
                test_use_authorized=True,
                regional_language="es-419",
                spoken_text_sha256=r["spoken_text_sha256"],
            )
        )
    manifest = tmp_path / "external.json"
    save(manifest, dict(manifest_id="owned-test", clips=clips))
    cfg = NarrationConfig(provider="external", external_manifest=manifest)
    kwargs = dict(
        topic=script.topic,
        root=tmp_path / "jobs",
        job_id="audio-cache",
        script_path=script_path,
        width=180,
        height=320,
        renderer_config=rendering,
        narration_config=cfg,
    )
    job = pipeline.produce(**kwargs)
    before = (
        sha(job / "video_silent.mp4"),
        (job / "video_silent.mp4").stat().st_mtime_ns,
    )
    old_audio = sha(job / "narration.wav")
    path = Path(clips[0]["path"])
    with wave.open(str(path), "rb") as wav:
        params = wav.getparams()
        data = wav.readframes(wav.getnframes())
    samples = struct.unpack("<" + "h" * (len(data) // 2), data)
    with wave.open(str(path), "wb") as wav:
        wav.setparams(params)
        wav.writeframes(struct.pack("<" + "h" * len(samples), *[-x for x in samples]))
    clips[0]["sha256"] = sha(path)
    save(manifest, dict(manifest_id="owned-test", clips=clips))
    pipeline.produce(**kwargs)
    assert before == (
        sha(job / "video_silent.mp4"),
        (job / "video_silent.mp4").stat().st_mtime_ns,
    )
    assert old_audio != sha(job / "narration.wav")
    assert len(list((job / "render").glob("attempt-*"))) == 1
    assert len(list((job / "composition").iterdir())) == 2
    assert json.loads((job / "qa.json").read_text())["decoded"]
