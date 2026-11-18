import fcntl
import json
from datetime import date, datetime, timedelta, timezone

import pytest

from fabrica.factory import Factory
from fabrica.factory_store import FactoryStore
from fabrica.renderers.runtime import RendererConfig
from fabrica.scheduler import ScheduleConfig


def config():
    return ScheduleConfig(
        timezone="America/Argentina/Catamarca",
        local_time="12:00",
        start_date=date(2026, 11, 17),
    )


def test_complete_mock_cycle_restart_and_metrics(tmp_path, monkeypatch):
    from fabrica import pipeline

    monkeypatch.setattr(
        pipeline, "generate_checked", lambda *a, **kw: pytest.fail("GPT prohibido")
    )
    store = FactoryStore(tmp_path / "state.sqlite3")
    factory = Factory(
        store,
        config(),
        tmp_path / "jobs",
        renderer_config=RendererConfig(renderer="legacy"),
    )
    clock = datetime(2026, 11, 17, 16, tzinfo=timezone.utc)
    result = factory.cycle(clock=clock, width=180, height=320, fault="uncertain")
    assert result["state"] == "RETRY_WAIT"
    job_id = result["job_id"]
    restarted = Factory(
        FactoryStore(store.path),
        config(),
        tmp_path / "jobs",
        renderer_config=RendererConfig(renderer="legacy"),
    )
    done = restarted.cycle(clock=clock + timedelta(minutes=2), width=180, height=320)
    assert done["job_id"] == job_id and done["state"] == "SIMULATED_DONE"
    assert restarted.cycle(
        clock=clock + timedelta(minutes=3), width=180, height=320
    ) == {"state": "IDLE", "simulated": True}
    job = tmp_path / "jobs/jobs" / job_id
    metadata = json.loads((job / "metadata.json").read_text())
    publication = json.loads((job / "publication.json").read_text())
    assert metadata["brand"] == "Mente y Capital"
    assert metadata["privacy"] == "private"
    assert publication["real_upload"] is False
    assert publication["remote_id"].startswith("mock-")
    assert json.loads((job / "result.json").read_text())["quality"]["decoded"]
    metrics = json.loads((tmp_path / "jobs/metrics.json").read_text())
    assert metrics["records"][0]["api_calls"] == 0
    assert metrics["records"][0]["retries"] == 1
    assert metrics["actual_revenue_usd"] is None
    with store.connect() as db:
        assert db.execute("SELECT count(*) FROM mock_remote").fetchone()[0] == 1


def test_worker_lock_prevents_duplicate_cycle(tmp_path):
    store = FactoryStore(tmp_path / "state.sqlite3")
    factory = Factory(
        store,
        config(),
        tmp_path / "jobs",
        renderer_config=RendererConfig(renderer="legacy"),
    )
    with store.path.with_suffix(".worker.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(BlockingIOError):
            factory.cycle(clock=datetime(2026, 11, 17, 16, tzinfo=timezone.utc))
