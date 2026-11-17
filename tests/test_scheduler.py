from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from fabrica.factory_store import FactoryStore
from fabrica.scheduler import ScheduleConfig, Scheduler, due


@pytest.fixture
def config():
    return ScheduleConfig(
        timezone="America/Argentina/Catamarca",
        local_time="18:00",
        start_date=date(2026, 11, 17),
    )


def test_calendar_timezone_restart_and_daily_limit(tmp_path, config):
    path = tmp_path / "state.sqlite3"
    store = FactoryStore(path)
    store.seed()
    scheduler = Scheduler(store, config)
    clock = datetime(2026, 11, 17, 21, tzinfo=timezone.utc)
    with ThreadPoolExecutor(max_workers=5) as pool:
        list(pool.map(lambda _: scheduler.plan(clock, 3), range(10)))
    assert len(scheduler.upcoming()) == 3
    assert scheduler.upcoming()[0]["due_utc"] == "2026-11-17T21:00:00+00:00"
    assert scheduler.claim(clock - timedelta(minutes=1)) is None
    slot = scheduler.claim(clock)
    assert slot["attempts"] == 1 and slot["topic_id"]
    restarted = Scheduler(FactoryStore(path), config)
    recovered = restarted.claim(clock)
    assert recovered["job_id"] == slot["job_id"]
    assert recovered["topic_id"] == slot["topic_id"]
    restarted.finish(recovered, "SIMULATED_DONE")
    assert restarted.claim(clock) is None
    with pytest.raises(ValueError, match="otra configuración"):
        Scheduler(store, config.model_copy(update={"local_time": "19:00"}))


def test_expired_and_retry_bound(tmp_path, config):
    scheduler = Scheduler(FactoryStore(tmp_path / "state.sqlite3"), config)
    scheduler.store.seed()
    clock = datetime(2026, 11, 17, 21, tzinfo=timezone.utc)
    scheduler.plan(clock, 2)
    for _ in range(3):
        assert scheduler.claim(clock)
    assert scheduler.claim(clock) is None
    assert scheduler.upcoming()[0]["state"] == "BLOCKED"
    tomorrow = clock + timedelta(days=1)
    assert scheduler.claim(tomorrow)["local_day"] == "2026-11-18"


def test_no_backfill_and_dst(tmp_path, config):
    scheduler = Scheduler(FactoryStore(tmp_path / "s.sqlite3"), config)
    scheduler.store.seed()
    clock = datetime(2026, 11, 17, 21, tzinfo=timezone.utc)
    scheduler.plan(clock, 2)
    scheduler.claim(clock + timedelta(days=1))
    assert scheduler.upcoming()[0]["state"] == "EXPIRED"
    dst = ScheduleConfig(
        timezone="America/New_York", local_time="02:30", start_date=date(2026, 3, 8)
    )
    with pytest.raises(ValueError, match="inexistente"):
        due(date(2026, 3, 8), dst)
    repeated = dst.model_copy(update={"local_time": "01:30"})
    assert due(date(2026, 11, 1), repeated).astimezone(ZoneInfo(dst.timezone)).fold == 0
    with pytest.raises(ValueError):
        scheduler.plan(datetime(2026, 11, 17))
