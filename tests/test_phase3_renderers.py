"""Application renderer contracts. Test doubles are unit-only, never delivery videos."""

import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from importlib.resources import files
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from fabrica import pipeline
from fabrica.factory import Factory
from fabrica.factory_store import FactoryStore
from fabrica.renderers import select_renderer
from fabrica.renderers.native import AudioTrack, RenderProduct
from fabrica.renderers.runtime import (
    CHROME_REL,
    NODE_DIR,
    RendererConfig,
    RendererUnavailable,
    RenderFailure,
    asset,
    available,
    environment,
    sha,
)
from fabrica.scheduler import ScheduleConfig
from fabrica.visual_planner import plan_script, validate_correspondence
from fabrica.visual_storyboard import VisualStoryboard


def board():
    return plan_script(
        pipeline.mock_script("Costo de oportunidad"), "unit-job", scene_seconds=1
    )


@pytest.fixture
def runtime(tmp_path):
    root = tmp_path / "runtimes"
    for relative in (f"{NODE_DIR}/bin/node", CHROME_REL):
        p = root / relative
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("unit fixture, never executed")
        p.chmod(0o755)
    for name, version, entry in [
        ("givemotion", "0.1.6", "src/cli.js"),
        ("hyperframes", "0.9.59", "bin/hyperframes.mjs"),
    ]:
        pkg = root / name / "node_modules" / name
        (pkg / entry).parent.mkdir(parents=True, exist_ok=True)
        (pkg / entry).write_text("// unit fixture")
        (pkg / "package.json").write_text(
            json.dumps({"name": name, "version": version})
        )
        (root / name / "package-lock.json").write_bytes(
            asset(f"locks/{name}/package-lock.json").read_bytes()
        )
    gsap = root / "hyperframes/node_modules/gsap/dist/gsap.min.js"
    gsap.parent.mkdir(parents=True)
    gsap.write_text("// unit fixture")
    font = root / "font.ttf"
    font.write_bytes(b"unit-font-not-for-real-rendering")
    return lambda name="givemotion": RendererConfig(
        renderer=name, runtime_root=root, font_path=font
    )


@pytest.mark.parametrize("name", ["givemotion", "hyperframes"])
def test_selection_and_prepare_shared_storyboard(runtime, tmp_path, name):
    b = board()
    r = select_renderer(runtime(name))
    r.validate(b)
    p = r.prepare(b, tmp_path / name)
    text = "\n".join(x.read_text() for x in p.project.rglob("*.html"))
    assert r.name == name and p.inputs["runtime"]["engine_version"] in (
        "0.1.6",
        "0.9.59",
    )
    assert all(s.narrative in text and s.title in text for s in b.scenes)
    assert all(s.narrative_segment_id in text for s in b.scenes)
    assert "gm.onFrame" in text if name == "givemotion" else "gsap.timeline" in text
    assert (
        p.inputs["storyboard_sha256"]
        == hashlib.sha256(b.model_dump_json().encode()).hexdigest()
    )
    assert b.budgets == {}


def test_default_and_only_selected_engine_required(runtime):
    assert RendererConfig().renderer == "givemotion"
    config = runtime()
    other = config.runtime_root / "hyperframes/node_modules/hyperframes/package.json"
    other.unlink()
    select_renderer(config).validate(board())
    with pytest.raises((RendererUnavailable, FileNotFoundError)):
        select_renderer(runtime("hyperframes")).validate(board())


@pytest.mark.parametrize("name", ["remotion", "motion_canvas", "pillow", "unknown"])
def test_disabled_or_unknown_engine_rejected(name):
    with pytest.raises(ValidationError):
        RendererConfig(renderer=name)


def test_missing_version_and_lock_rejected(runtime, tmp_path):
    with pytest.raises(RendererUnavailable, match="unavailable"):
        available(RendererConfig(runtime_root=tmp_path / "missing"))
    config = runtime()
    p = available(config)["package"] / "package.json"
    p.write_text('{"name":"givemotion","version":"9.9.9"}')
    with pytest.raises(RendererUnavailable, match="pinned"):
        select_renderer(config).validate(board())
    p.write_text('{"name":"givemotion","version":"0.1.6"}')
    (config.runtime_root / "givemotion/package-lock.json").write_text("{}")
    with pytest.raises(RendererUnavailable, match="lock"):
        select_renderer(config).validate(board())


def test_environment_excludes_credentials(runtime, tmp_path, monkeypatch):
    for key in ("OPENAI_API_KEY", "AWS_SECRET_ACCESS_KEY", "YOUTUBE_CLIENT_SECRET"):
        monkeypatch.setenv(key, "unit-secret-must-not-leak")
    env = environment(runtime(), tmp_path / "attempt")
    assert "unit-secret-must-not-leak" not in str(env)
    assert not any(
        key in env for key in ("OPENAI_API_KEY", "HOME", "AWS_SECRET_ACCESS_KEY")
    )
    assert env["TMPDIR"].startswith(str(tmp_path)) and env["DO_NOT_TRACK"] == "1"


def test_generic_plan_has_varied_layouts_and_narrative_anchors():
    b = board()
    assert len({s.layout for s in b.scenes}) >= 3
    assert b.duration == 4 and b.data and not b.budgets
    assert all(
        a.start == s.start and a.end == s.end and a.text == s.narrative
        for s in b.scenes
        for a in s.anchors
    )
    validate_correspondence(pipeline.mock_script("Costo de oportunidad"), b)


@pytest.mark.parametrize(
    "fault", ["missing-data", "unknown-element", "anchor", "timing", "nan", "total"]
)
def test_invalid_visual_plan_rejected(fault):
    data = board().model_dump(mode="json")
    if fault == "missing-data":
        data["scenes"][1]["elements"][0]["data_key"] = "missing"
    elif fault == "unknown-element":
        data["scenes"][0]["events"][0]["elements"] = ["absent"]
    elif fault == "anchor":
        data["scenes"][0]["anchors"][0]["end"] = 99
    elif fault == "timing":
        data["scenes"][0]["start"] = 0.001
    elif fault == "nan":
        data["data"][data["scenes"][1]["elements"][0]["data_key"]] = float("nan")
    else:
        data["totals"] = [
            {"total_key": list(data["data"])[0], "parts": list(data["data"])[1:]}
        ]
    with pytest.raises(ValueError):
        VisualStoryboard.model_validate(data)


@pytest.mark.parametrize("name", ["givemotion", "hyperframes"])
def test_financial_data_and_palette_propagate_to_both_adapters(runtime, tmp_path, name):
    b = VisualStoryboard.model_validate_json(
        files("fabrica").joinpath("data/budget_55_storyboard.json").read_text()
    )
    data = b.model_dump(mode="json")
    data["palette"]["gold"] = "#CCA855"
    data["data"] = {k: v * 2 for k, v in data["data"].items()}
    changed = VisualStoryboard.model_validate(data)
    p = select_renderer(runtime(name)).prepare(changed, tmp_path / "financial")
    pages = "\n".join(x.read_text() for x in p.project.rglob("*.html"))
    assert "2400000" in pages and "1400000" in pages and "#CCA855" in pages
    components = (p.project / "components.js").read_text()
    assert "1200000" not in components and "700000" not in components
    assert changed.duration == 55
    for prefix in ("initial", "alternative"):
        assert (
            sum(
                changed.data[prefix + "." + k] for k in ("fixed", "variable", "savings")
            )
            == 2400000
        )
    assert changed.data["decision.amount"] == 60000


def test_script_and_storyboard_mismatch_rejected():
    b = board()
    script = pipeline.mock_script("Costo de oportunidad")
    script.scenes[0].narration += " Otra frase."
    with pytest.raises(ValueError, match="narrative"):
        validate_correspondence(script, b)


def test_untrusted_copy_revalidated_and_no_executable_text(runtime, tmp_path):
    b = board()
    data = b.model_dump(mode="json")
    data["scenes"][0]["title"] = "</script><script>alert(1)</script>"
    p = select_renderer(runtime()).prepare(
        VisualStoryboard.model_validate(data), tmp_path / "escaping"
    )
    html = (p.project / "index.html").read_text()
    assert "</script><script>alert(1)</script>" not in html and "\\u003c/script" in html
    bad = b.model_copy(update={"schema_version": 2, "duration": 99})
    with pytest.raises(ValueError):
        select_renderer(runtime()).validate(bad)


def test_external_audio_requires_verified_manifest(runtime, tmp_path):
    p = tmp_path / "tone.wav"
    p.write_bytes(b"unit-only-not-voice")
    values = dict(
        path=p,
        sha256=sha(p),
        commercial_allowed=True,
        license="Unit fixture",
        evidence=["Generated test tone, no voice"],
    )
    track = AudioTrack(**values)
    with pytest.raises(ValidationError):
        AudioTrack(**(values | {"commercial_allowed": False}))
    external = board().model_copy(update={"audio": "external"})
    with pytest.raises(ValueError, match="manifest"):
        select_renderer(runtime()).validate(external)
    select_renderer(runtime()).validate(external, track)
    p.write_bytes(b"changed")
    with pytest.raises(ValueError, match="hash"):
        track.verify()


@pytest.mark.parametrize("failure", ["exit", "timeout"])
def test_subprocess_error_no_fallback_or_promotion(
    runtime, tmp_path, monkeypatch, failure
):
    from fabrica.renderers import native

    r = select_renderer(runtime())
    prepared = r.prepare(board(), tmp_path / "attempt")

    def fail(*a, **k):
        if failure == "timeout":
            raise TimeoutError("test")
        return 17, 1

    monkeypatch.setattr(native, "measured", fail)
    with pytest.raises(RenderFailure, match="fallback"):
        r.render(prepared)
    assert not (tmp_path / "final.mp4").exists()
    assert "render_failed" in (prepared.directory / "events.jsonl").read_text()


@pytest.fixture
def fake_renderer(monkeypatch):
    """Unit-only render/inspection protocol mocks, never native evidence or delivery artifacts."""
    from fabrica import quality, visual_job

    monkeypatch.setattr(
        quality, "inspect_job", lambda *a, **k: {"decoded": True, "test_double": True}
    )
    calls = []

    class Double:
        def __init__(self, config):
            self.config = config

        def inputs(self, b, a=None):
            return {
                "renderer": self.config.renderer,
                "board": b.model_dump_json(),
                "audio": None,
            }

        def prepare(self, b, d, a=None):
            d.mkdir()
            return SimpleNamespace(board=b, directory=d)

        def render(self, p, a=None):
            calls.append(self.config.renderer)
            video = p.directory / "unit-double.mp4"
            video.write_bytes(b"UNIT TEST DOUBLE, NOT A VALID VIDEO")
            thumb = p.directory / "unit-thumbnail.png"
            thumb.write_bytes(b"unit thumbnail")
            quality = {"decoded": True, "test_double": True}
            metrics = {
                "renderer": self.config.renderer,
                "sha256": sha(video),
                "thumbnail_sha256": sha(thumb),
                "render_wall_seconds": 0.1,
                "cpu_seconds": 0.05,
                "test_double": True,
            }
            return RenderProduct(video, thumb, metrics, quality)

    monkeypatch.setattr(visual_job, "select_renderer", Double)
    return calls


def test_main_pipeline_default_silent_resume_corruption_and_metrics(
    tmp_path, monkeypatch, fake_renderer
):
    for name in ("PiperTTS", "MockTTS", "create_cards"):
        monkeypatch.setattr(
            pipeline,
            name,
            lambda *a, **k: pytest.fail(
                "Native pipeline must not synthesize voices or Pillow scenes"
            ),
        )
    args = dict(topic="Costo de oportunidad", root=tmp_path, job_id="native-unit")
    job = pipeline.produce(**args)
    result = json.loads((job / "result.json").read_text())
    assert (
        result["renderer"] == "givemotion"
        and result["config"]["pipeline_version"] == "3"
    )
    assert not result["audio_present"] and not list(job.glob("audio_*.wav"))
    assert (
        result["render_metrics"]["cpu_seconds"] == 0.05
        and result["render_metrics"]["test_double"]
    )
    before = (job / "final.mp4").stat().st_mtime_ns
    pipeline.produce(**args)
    assert (
        fake_renderer == ["givemotion"]
        and (job / "final.mp4").stat().st_mtime_ns == before
    )
    (job / "final.mp4").write_bytes(b"corrupt")
    pipeline.produce(**args)
    assert (
        len(fake_renderer) == 2 and len(list((job / "render").glob("attempt-*"))) == 2
    )
    with pytest.raises(ValueError, match="configuraci"):
        pipeline.produce(**args, renderer="hyperframes")


def factory_context(tmp_path, renderer="givemotion"):
    cfg = ScheduleConfig(
        timezone="America/Argentina/Catamarca",
        local_time="12:00",
        start_date=date(2026, 11, 18),
    )
    store = FactoryStore(tmp_path / "state.sqlite3")
    return (
        Factory(store, cfg, tmp_path / "factory", RendererConfig(renderer=renderer)),
        store,
        datetime(2026, 11, 18, 16, tzinfo=timezone.utc),
    )


@pytest.mark.parametrize("name", ["givemotion", "hyperframes"])
def test_factory_preserves_mock_metadata_schedule_and_safe_resume(
    tmp_path, fake_renderer, name
):
    factory, store, clock = factory_context(tmp_path, name)
    first = factory.cycle(clock=clock, fault="uncertain")
    assert first["state"] == "RETRY_WAIT"
    package = store.package(first["job_id"])
    assert package.simulated and package.privacy == "private"
    done = factory.cycle(clock=clock + timedelta(minutes=2))
    assert done["state"] == "SIMULATED_DONE" and fake_renderer == [name]
    publication = json.loads((Path(done["job"]) / "publication.json").read_text())
    assert publication["real_upload"] is False and publication["remote_id"].startswith(
        "mock-"
    )
    with store.connect() as db:
        assert db.execute("SELECT count(*) FROM mock_remote").fetchone()[0] == 1
        metrics = json.loads(db.execute("SELECT record FROM metrics").fetchone()[0])
        assert (
            metrics["renderer"] == name
            and metrics["render_wall_seconds"] == 0.1
            and metrics["api_calls"] == 0
        )


def test_packaged_asset_corruption_blocks_replacement(tmp_path, fake_renderer):
    factory, store, clock = factory_context(tmp_path)
    first = factory.cycle(clock=clock, fault="uncertain")
    job = Path(first["job"])
    (job / "final.mp4").write_bytes(b"corrupt after package")
    with pytest.raises(ValueError, match="Packaged asset"):
        factory.cycle(clock=clock + timedelta(minutes=2))
    assert fake_renderer == ["givemotion"]
    assert store.package(first["job_id"]).asset_hash != sha(job / "final.mp4")


def test_native_pipeline_records_blocked_subprocess_and_same_engine_retry(
    tmp_path, monkeypatch
):
    from fabrica import visual_job

    class Failure:
        def __init__(self, c):
            pass

        def inputs(self, *a):
            return {"test": 1}

        def prepare(self, *a):
            raise RenderFailure("subprocess timeout; no fallback")

    monkeypatch.setattr(visual_job, "select_renderer", Failure)
    with pytest.raises(RenderFailure):
        pipeline.produce("Costo", root=tmp_path, job_id="failed")
    state = json.loads((tmp_path / "failed/result.json").read_text())
    assert state["status"] == "BLOCKED" and state["config"]["renderer"] == "givemotion"
    assert (
        state["error"]["type"] == "RenderFailure"
        and not (tmp_path / "failed/final.mp4").exists()
    )
