import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from fabrica import youtube
from fabrica.factory_store import FactoryStore
from fabrica.metadata import Originality, Resource, generate_package, sha256
from fabrica.models import VideoScript
from fabrica.pipeline import produce


@pytest.fixture(scope="module")
def rendered(tmp_path_factory):
    root = tmp_path_factory.mktemp("youtube-render")
    script_path = Path("examples/costo_oportunidad.json")
    return produce(
        "Costo de oportunidad",
        root=root,
        job_id="rendered",
        script_path=script_path,
        width=180,
        height=320,
        mock_seconds=0.3,
        renderer="legacy",
    )


@pytest.fixture
def context(tmp_path, rendered):
    script = VideoScript.model_validate_json((rendered / "script.json").read_text())
    state = json.loads((rendered / "result.json").read_text())
    cover = rendered / "cards/scene_01.png"
    package = generate_package(
        script,
        job_id="test",
        channel_id="MOCK_MENTE_Y_CAPITAL",
        video_path=rendered / "final.mp4",
        thumbnail_path=cover,
        category="Economía cotidiana",
        category_id="27",
        duration=state["duration"],
        resources=[
            Resource(
                path=str(cover),
                sha256=sha256(cover),
                source="test",
                license="test-fixture",
                evidence=["test"],
            )
        ],
        originality=Originality(
            question=script.hook,
            own_development=script.scenes[1].narration,
            original_example=script.scenes[2].narration,
            economic_relationship=script.scenes[3].narration,
            practical_conclusion=script.scenes[-1].narration,
        ),
        made_for_kids=False,
        audience_reason="Solo prueba para público adulto.",
        synthetic=False,
        synthetic_reason="Gráficos abstractos y tonos, sin suplantación realista.",
    )
    return FactoryStore(tmp_path / "factory.sqlite3"), package, rendered


def count_remote(store):
    with store.connect() as db:
        return db.execute("SELECT count(*) FROM mock_remote").fetchone()[0]


def test_success_and_already_published(context):
    store, package, job = context
    publisher = youtube.YouTubePublisher(store, youtube.MockYouTubeClient(store))
    first = publisher.publish(package, job)
    assert first["state"] == "SIMULATED_PRIVATE_VERIFIED"
    assert publisher.publish(package, job)["remote_id"] == first["remote_id"]
    assert count_remote(store) == 1
    assert first["attempts"] == 1


@pytest.mark.parametrize(
    ("fault", "expected"),
    [
        ("connection", "RETRY_WAIT"),
        ("quota", "RETRY_WAIT"),
        ("token", "BLOCKED_PERMISSION"),
        ("uncertain", "RECONCILE"),
        ("permanent", "BLOCKED_PERMANENT"),
    ],
)
def test_faults_and_no_duplicate(context, fault, expected):
    store, package, job = context
    clock = datetime(2026, 11, 17, tzinfo=timezone.utc)
    publisher = youtube.YouTubePublisher(
        store, youtube.MockYouTubeClient(store, fault=fault)
    )
    first = publisher.publish(package, job, clock=clock)
    assert first["state"] == expected
    restarted = youtube.YouTubePublisher(
        FactoryStore(store.path), youtube.MockYouTubeClient(store)
    )
    result = restarted.publish(package, job, clock=clock + timedelta(days=2))
    if expected in ("RETRY_WAIT", "RECONCILE"):
        assert result["state"] == "SIMULATED_PRIVATE_VERIFIED"
    else:
        assert result["state"] == expected
    assert count_remote(store) == 1


def test_crash_after_remote_completion(context):
    store, package, job = context
    publisher = youtube.YouTubePublisher(
        store, youtube.MockYouTubeClient(store, fault="crash")
    )
    with pytest.raises(KeyboardInterrupt):
        publisher.publish(package, job)
    assert store.publication(package.job_id)["session"]
    resumed = youtube.YouTubePublisher(
        FactoryStore(store.path), youtube.MockYouTubeClient(store)
    )
    assert resumed.publish(package, job)["state"] == "SIMULATED_PRIVATE_VERIFIED"
    assert count_remote(store) == 1


def test_channel_and_editorial_rejected(context):
    store, package, job = context
    publisher = youtube.YouTubePublisher(
        store, youtube.MockYouTubeClient(store, channel_id="WRONG")
    )
    with pytest.raises(ValueError, match="canal"):
        publisher.publish(package, job)
    bad = package.model_copy(
        update={
            "originality": package.originality.model_copy(
                update={"claims_pending": ["Hecho sin verificar"]}
            )
        }
    )
    publisher = youtube.YouTubePublisher(store, youtube.MockYouTubeClient(store))
    with pytest.raises(ValueError, match="editorial"):
        publisher.publish(bad, job)
    assert count_remote(store) == 0


def test_missing_session_quarantines(context):
    store, package, job = context
    publisher = youtube.YouTubePublisher(store, youtube.MockYouTubeClient(store))
    publisher.publish(package, job)
    store.publication_state(package.job_id, "STARTING", session=None, remote_id=None)
    assert publisher.publish(package, job)["state"] == "QUARANTINED"
    assert count_remote(store) == 1


def test_official_sdk_preparation_only(context):
    pytest.importorskip("googleapiclient")
    _, package, _ = context
    media = youtube.sdk_media(package)
    try:
        assert media.resumable()
        assert media.mimetype() == "video/mp4"
        assert media.chunksize() % (256 * 1024) == 0
        assert package.youtube_body()["status"]["privacyStatus"] == "private"
    finally:
        media.stream().close()


def test_only_mock_clients_and_no_license_bypass(context):
    store, package, job = context
    with pytest.raises(ValueError, match="simulado"):
        youtube.YouTubePublisher(store, object())
    with pytest.raises(ValueError, match="Licencias"):
        type(package).model_validate(package.model_dump() | {"simulated": False})


def test_partial_cursor_recovery(context):
    store, package, job = context
    clock = datetime(2026, 11, 17, tzinfo=timezone.utc)
    publisher = youtube.YouTubePublisher(
        store, youtube.MockYouTubeClient(store, fault="partial")
    )
    first = publisher.publish(package, job, clock=clock)
    assert first["state"] == "RETRY_WAIT"
    assert 0 < first["cursor"] < Path(package.video_path).stat().st_size
    publisher = youtube.YouTubePublisher(store, youtube.MockYouTubeClient(store))
    done = publisher.publish(package, job, clock=clock + timedelta(minutes=2))
    assert done["state"] == "SIMULATED_PRIVATE_VERIFIED"
    assert count_remote(store) == 1


def test_lost_session_start_never_reinserts(context):
    store, package, job = context

    class LostStart(youtube.MockYouTubeClient):
        def start(self, intent, body):
            super().start(intent, body)
            raise youtube.UploadError("uncertain")

    publisher = youtube.YouTubePublisher(store, LostStart(store))
    assert publisher.publish(package, job)["state"] == "RECONCILE"
    publisher = youtube.YouTubePublisher(store, youtube.MockYouTubeClient(store))
    assert publisher.publish(package, job)["state"] == "QUARANTINED"
    assert count_remote(store) == 1


def test_retry_limit_and_backoff(context):
    store, package, job = context
    clock = datetime(2026, 11, 17, tzinfo=timezone.utc)
    client = youtube.MockYouTubeClient(store, fault="connection")
    publisher = youtube.YouTubePublisher(store, client, max_attempts=2)
    first = publisher.publish(package, job, clock=clock)
    assert publisher.publish(package, job, clock=clock)["attempts"] == 1
    client.fault = "connection"
    assert (
        publisher.publish(package, job, clock=clock + timedelta(minutes=2))["attempts"]
        == 2
    )
    assert (
        publisher.publish(package, job, clock=clock + timedelta(minutes=5))["state"]
        == "QUARANTINED"
    )
    assert count_remote(store) == 1
    assert first["retry_at"]


def test_remote_privacy_drift_quarantines_without_upload(context):
    store, package, job = context
    publisher = youtube.YouTubePublisher(store, youtube.MockYouTubeClient(store))
    publisher.publish(package, job)
    with store.connect() as db:
        row = db.execute("SELECT body FROM mock_remote").fetchone()
        body = json.loads(row["body"])
        body["status"]["privacyStatus"] = "public"
        db.execute("UPDATE mock_remote SET body=?", (json.dumps(body),))
    assert publisher.publish(package, job)["state"] == "QUARANTINED"
    assert count_remote(store) == 1
