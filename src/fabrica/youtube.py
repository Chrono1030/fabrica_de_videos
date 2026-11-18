"""Publicación exclusivamente simulada. No construye clientes OAuth ni transportes HTTP."""

import fcntl
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Protocol

from .catalog import now
from .editorial import review
from .metadata import PublicationPackage, sha256, validate_correspondence
from .models import VideoScript
from .render import quality


class UploadError(Exception):
    def __init__(self, kind, cursor=None):
        super().__init__(kind)
        self.kind, self.cursor = kind, cursor


class YouTubeClient(Protocol):
    simulated: bool

    def channel(self) -> str: ...
    def start(self, intent: str, body: dict) -> str: ...
    def resume(self, session: str, size: int) -> dict: ...
    def verify(self, remote_id: str) -> dict: ...


def sdk_media(package):
    """SDK oficial: preparar archivo reanudable no realiza ninguna llamada de red."""
    from googleapiclient.http import MediaFileUpload

    return MediaFileUpload(
        package.video_path, mimetype="video/mp4", chunksize=1024 * 1024, resumable=True
    )


def prepare_upload(package):
    """Declaración inspeccionable; SDK media local cuando está instalado."""
    request = {
        "part": "snippet,status",
        "body": package.youtube_body(),
        "notifySubscribers": False,
        "resumable": True,
        "mimetype": "video/mp4",
        "chunksize": 1024 * 1024,
        "network_enabled": False,
        "sdk_available": False,
    }
    try:
        media = sdk_media(package)
    except ImportError:
        return request
    try:
        request.update(
            sdk_available=True, chunksize=media.chunksize(), resumable=media.resumable()
        )
    finally:
        media.stream().close()
    return request


class MockYouTubeClient:
    simulated = True

    def __init__(self, store, channel_id="MOCK_MENTE_Y_CAPITAL", fault=None):
        self.store, self.channel_id, self.fault = store, channel_id, fault

    def channel(self):
        return self.channel_id

    def start(self, intent, body):
        if body["status"]["privacyStatus"] != "private":
            raise ValueError("Privacidad debe ser private")
        session = "mock-session-" + intent
        with self.store.connect() as db:
            db.execute(
                "INSERT OR IGNORE INTO mock_remote(session,intent,channel_id,body,state) "
                "VALUES(?,?,?,?,?)",
                (session, intent, self.channel_id, json.dumps(body), "OPEN"),
            )
        return session

    def resume(self, session, size):
        with self.store.connect() as db:
            row = db.execute(
                "SELECT * FROM mock_remote WHERE session=?", (session,)
            ).fetchone()
        if row is None:
            raise UploadError("session_missing")
        if row["remote_id"]:
            return dict(row)
        fault, self.fault = self.fault, None
        if fault == "partial":
            cursor = max(row["cursor"], size // 2)
            with self.store.connect() as db:
                db.execute(
                    "UPDATE mock_remote SET cursor=? WHERE session=?", (cursor, session)
                )
            raise UploadError("partial", cursor=cursor)
        if fault in ("connection", "quota", "token", "permanent"):
            raise UploadError(fault)
        remote_id = "mock-video-" + hashlib.sha256(session.encode()).hexdigest()[:16]
        with self.store.connect() as db:
            db.execute(
                "UPDATE mock_remote SET remote_id=?,cursor=?,state=? WHERE session=?",
                (remote_id, size, "processed", session),
            )
        if fault == "uncertain":
            # Remote completed, but the response disappeared before local persistence.
            raise UploadError("uncertain")
        if fault == "crash":
            raise KeyboardInterrupt(
                "simulated process interruption after remote completion"
            )
        return self.verify(remote_id)

    def verify(self, remote_id):
        with self.store.connect() as db:
            row = db.execute(
                "SELECT * FROM mock_remote WHERE remote_id=?", (remote_id,)
            ).fetchone()
        if row is None:
            raise UploadError("remote_missing")
        return dict(row) | {
            "privacy": json.loads(row["body"])["status"]["privacyStatus"]
        }


def validate_job(package, job, *, technical_check=True):
    package = PublicationPackage.model_validate(package.model_dump())
    job = Path(job)
    result = json.loads((job / "result.json").read_text())
    script = VideoScript.model_validate_json((job / "script.json").read_text())
    validate_correspondence(package, script)
    if review(script) or package.originality.claims_pending:
        raise ValueError("Validación editorial rechazada")
    if not package.simulated and (
        not package.originality.approved
        or package.originality.simulated_review
        or not package.originality.reviewer
        or result.get("audio_simulated")
        or result.get("editorial_status") != "APPROVED"
    ):
        raise ValueError("Revisión editorial/licencias reales pendientes")
    if not package.simulated and (
        (
            result.get("quality", {}).get("width"),
            result.get("quality", {}).get("height"),
        )
        != (1080, 1920)
        or not 60 <= result["duration"] <= 90
    ):
        raise ValueError("QA comercial requiere 1080×1920 y 60–90 segundos")
    video = job / "final.mp4"
    if (
        Path(package.video_path).resolve() != video.resolve()
        or sha256(video) != package.asset_hash
    ):
        raise ValueError("Video modificado o distinto del paquete")
    render = result.get("stages", {}).get("RENDER", {}).get("final.mp4")
    if render != package.asset_hash or result.get("status") != "TECHNICALLY_READY":
        raise ValueError("Trabajo sin QA válido")
    if not result.get("quality", {}).get("decoded"):
        raise ValueError("QA de decodificación ausente")
    if abs(result["duration"] - package.duration_seconds) > 0.1:
        raise ValueError("Duración del paquete distinta del trabajo")
    if not package.resources:
        raise ValueError("Falta manifiesto de recursos")
    for asset in package.resources:
        if not Path(asset.path).is_file() or sha256(asset.path) != asset.sha256:
            raise ValueError("Recurso modificado o ausente")
    if not Path(package.thumbnail_path).is_file():
        raise ValueError("Falta portada")
    # Test fixtures may inject this function; production paths always decode the actual file.
    if technical_check:
        if result["config"].get("pipeline_version") in ("3", "4"):
            from .quality import inspect_job

            inspect_job(job)
        else:
            q = result["quality"]
            quality(
                video,
                q["width"],
                q["height"],
                result["duration"],
                job / "subtitles.srt",
                result["config"]["subtitle_style"]["burn"],
            )
    return result


class YouTubePublisher:
    def __init__(self, store, client: YouTubeClient, *, max_attempts=3):
        if not isinstance(client, MockYouTubeClient):
            raise ValueError("Esta fase solo admite el cliente simulado")
        self.store, self.client, self.max_attempts = store, client, max_attempts

    def publish(self, package, job, *, clock=None):
        clock = clock or datetime.now(timezone.utc)
        if clock.tzinfo is None:
            raise ValueError("Reloj debe incluir zona horaria")
        package = PublicationPackage.model_validate(package.model_dump())
        # One local publisher across all jobs/channels for this database.
        with self.store.path.with_suffix(".publish.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if self.client.channel() != package.channel_id:
                self._rejection(
                    package.job_id, "BLOCKED_PERMISSION", "channel_mismatch"
                )
                raise ValueError("ID de canal incorrecto")
            try:
                validate_job(package, job)
            except ValueError as exc:
                self._rejection(package.job_id, "BLOCKED_CONTENT", str(exc))
                raise
            self.store.save_package(package)
            digest = hashlib.sha256(package.model_dump_json().encode()).hexdigest()
            with self.store.connect() as db:
                db.execute("BEGIN IMMEDIATE")
                row = db.execute(
                    "SELECT * FROM publications WHERE job_id=?", (package.job_id,)
                ).fetchone()
                if row is None:
                    db.execute(
                        "INSERT INTO publications(job_id,channel_id,package_hash,asset_hash,state,updated_at) "
                        "VALUES(?,?,?,?,?,?)",
                        (
                            package.job_id,
                            package.channel_id,
                            digest,
                            package.asset_hash,
                            "READY",
                            now(),
                        ),
                    )
            row = self.store.publication(package.job_id)
            if row["package_hash"] != digest or row["channel_id"] != package.channel_id:
                raise ValueError("Intento de reemplazar un paquete reservado")
            if row["state"] == "SIMULATED_PRIVATE_VERIFIED":
                try:
                    self._verify(row["remote_id"], package)
                except UploadError as exc:
                    self.store.publication_state(
                        package.job_id, "QUARANTINED", error=exc.kind
                    )
                    return self.store.publication(package.job_id)
                return row
            if row["state"] in (
                "BLOCKED_PERMISSION",
                "BLOCKED_PERMANENT",
                "QUARANTINED",
            ):
                return row
            if row["retry_at"] and clock < datetime.fromisoformat(row["retry_at"]):
                return row
            if row["attempts"] >= self.max_attempts:
                self.store.publication_state(
                    package.job_id, "QUARANTINED", error="retry_limit"
                )
                return self.store.publication(package.job_id)
            self.store.publication_state(
                package.job_id, "UPLOADING", attempts=row["attempts"] + 1, retry_at=None
            )
            try:
                session = row["session"]
                if session is None:
                    if row["state"] != "READY":
                        # No session persisted: never issue another insert blindly.
                        raise UploadError("session_missing")
                    self.store.publication_state(package.job_id, "STARTING")
                    session = self.client.start(package.job_id, package.youtube_body())
                    self.store.publication_state(
                        package.job_id, "UPLOADING", session=session
                    )
                remote = self.client.resume(
                    session, Path(package.video_path).stat().st_size
                )
                self.store.publication_state(
                    package.job_id,
                    "UPLOADED_PRIVATE",
                    remote_id=remote["remote_id"],
                    cursor=remote["cursor"],
                )
                self._verify(remote["remote_id"], package)
                self.store.publication_state(
                    package.job_id, "SIMULATED_PRIVATE_VERIFIED", error=None
                )
            except UploadError as exc:
                state = {
                    "connection": "RETRY_WAIT",
                    "partial": "RETRY_WAIT",
                    "quota": "RETRY_WAIT",
                    "token": "BLOCKED_PERMISSION",
                    "uncertain": "RECONCILE",
                    "permanent": "BLOCKED_PERMANENT",
                }.get(exc.kind, "QUARANTINED")
                delay = 86400 if exc.kind == "quota" else 30 * 2 ** row["attempts"]
                delay += (
                    int(hashlib.sha256(package.job_id.encode()).hexdigest()[:2], 16)
                    % 11
                )
                self.store.publication_state(
                    package.job_id,
                    state,
                    error=exc.kind,
                    cursor=exc.cursor if exc.cursor is not None else row["cursor"],
                    retry_at=(clock + timedelta(seconds=delay)).isoformat()
                    if state == "RETRY_WAIT"
                    else None,
                )
            return self.store.publication(package.job_id)

    def _rejection(self, job_id, state, error):
        with self.store.connect() as db:
            db.execute(
                "INSERT INTO publication_events(job_id,state,at,details) VALUES(?,?,?,?)",
                (job_id, state, now(), json.dumps({"error": error})),
            )

    def _verify(self, remote_id, package):
        remote = self.client.verify(remote_id)
        if remote["channel_id"] != package.channel_id or remote["privacy"] != "private":
            raise UploadError("remote_mismatch")
        if remote["state"] != "processed":
            raise UploadError("processing_pending")
