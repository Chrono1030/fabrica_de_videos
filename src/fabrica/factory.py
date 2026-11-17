"""Ciclo único integrado, simulado y reanudable desde el calendario."""

import fcntl
import json
import resource
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from importlib.resources import files
from pathlib import Path

from .economics import VideoMetrics, metrics_report, save_metrics
from .metadata import Originality, Resource, generate_package, sha256
from .models import VideoScript
from .pipeline import mock_script, produce, save
from .scheduler import Scheduler
from .youtube import MockYouTubeClient, YouTubePublisher, prepare_upload


class Factory:
    def __init__(self, store, config, root):
        self.store, self.scheduler, self.root = (
            store,
            Scheduler(store, config),
            Path(root),
        )

    def cycle(self, *, clock=None, width=1080, height=1920, fault=None):
        clock = clock or datetime.now(timezone.utc)
        with self.store.path.with_suffix(".worker.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.store.seed()
            self.scheduler.plan(clock)
            slot = self.scheduler.claim(clock)
            if slot is None:
                return {"state": "IDLE", "simulated": True}
            started = time.monotonic()
            before = resource.getrusage(resource.RUSAGE_CHILDREN)
            job_id = slot["job_id"]
            job = self.root / "jobs" / job_id
            metrics = self._prior_metrics(job_id)
            errors, state = 0, None
            try:
                script_path = self.root / "scripts" / f"{job_id}.json"
                script_path.parent.mkdir(parents=True, exist_ok=True)
                if not script_path.exists():
                    if slot["title"] == "Elegir una alternativa implica renunciar":
                        script = VideoScript.model_validate_json(
                            files("fabrica")
                            .joinpath("data/costo_oportunidad.json")
                            .read_text(encoding="utf-8")
                        )
                        script.topic = slot["title"]
                    else:
                        script = mock_script(slot["title"])
                    save(script_path, script.model_dump(mode="json"))
                script = VideoScript.model_validate_json(script_path.read_text())
                job = produce(
                    slot["title"],
                    mode="mock",
                    root=self.root / "jobs",
                    job_id=job_id,
                    script_path=script_path,
                    width=width,
                    height=height,
                    mock_seconds=75 / len(script.scenes),
                    catalog_path=self.store.path,
                )
                result = json.loads((job / "result.json").read_text())
                try:
                    package = self.store.package(job_id)
                except ValueError:
                    paths = [
                        *sorted((job / "cards").glob("*.png")),
                        *sorted(job.glob("audio_*.wav")),
                    ]
                    resources = [
                        Resource(
                            path=str(p.resolve()),
                            sha256=sha256(p),
                            source="Fabrica_de_videos: generación local",
                            license="local-original-mock",
                            commercial_allowed=False,
                            evidence=[
                                str((job / "script.json").resolve()),
                                "Solo ensayo técnico MOCK",
                            ],
                        )
                        for p in paths
                    ]
                    package = generate_package(
                        script,
                        job_id=job_id,
                        channel_id="MOCK_MENTE_Y_CAPITAL",
                        video_path=job / "final.mp4",
                        thumbnail_path=job / "cards/scene_01.png",
                        category=slot["category"],
                        category_id="27",
                        duration=result["duration"],
                        resources=resources,
                        originality=Originality(
                            question=script.hook,
                            own_development=script.scenes[1].narration,
                            original_example=script.scenes[2].narration,
                            economic_relationship=script.scenes[-2].narration,
                            practical_conclusion=script.scenes[-1].narration,
                        ),
                        made_for_kids=False,
                        audience_reason="Evaluación MOCK para adultos, pendiente de revisión por video.",
                        synthetic=False,
                        synthetic_reason="Tonos y gráficos abstractos; no simula hechos reales.",
                        simulated=True,
                    )
                    self.store.save_package(package)
                save(job / "metadata.json", package.model_dump(mode="json"))
                save(job / "upload_request.json", prepare_upload(package))
                publisher = YouTubePublisher(
                    self.store, MockYouTubeClient(self.store, fault=fault)
                )
                publication = publisher.publish(package, job, clock=clock)
                save(
                    job / "publication.json",
                    publication | {"simulated": True, "real_upload": False},
                )
                if publication["state"] == "SIMULATED_PRIVATE_VERIFIED":
                    state = "SIMULATED_DONE"
                    self.store.finish(
                        job_id, "TECHNICALLY_READY", {"publication": "simulated"}
                    )
                    self.scheduler.finish(slot, state)
                elif publication["state"] in ("RETRY_WAIT", "RECONCILE", "UPLOADING"):
                    state = "RETRY_WAIT"
                    errors = 1
                    self.scheduler.finish(
                        slot,
                        state,
                        publication["error"],
                        publication["retry_at"]
                        or (clock + timedelta(seconds=30)).isoformat(),
                    )
                else:
                    state, errors = "BLOCKED", 1
                    self.scheduler.finish(slot, state, publication["error"])
                return {
                    "state": state,
                    "job_id": job_id,
                    "job": str(job),
                    "publication": publication,
                    "simulated": True,
                }
            except (ValueError, FileNotFoundError, sqlite3.IntegrityError) as exc:
                errors = 1
                self.scheduler.finish(
                    slot, "BLOCKED", type(exc).__name__ + ": " + str(exc)
                )
                self.store.finish(job_id, "BLOCKED", {"error": type(exc).__name__})
                raise
            except Exception as exc:
                errors = 1
                self.scheduler.finish(
                    slot,
                    "RETRY_WAIT",
                    type(exc).__name__,
                    (
                        clock + timedelta(seconds=30 * 2 ** (slot["attempts"] - 1))
                    ).isoformat(),
                )
                raise
            finally:
                after = resource.getrusage(resource.RUSAGE_CHILDREN)
                costs = (
                    json.loads((job / "result.json").read_text()).get("costs", [])
                    if (job / "result.json").exists()
                    else []
                )
                save_metrics(
                    self.store,
                    VideoMetrics(
                        job_id=job_id,
                        simulated=True,
                        production_seconds=metrics.get("production_seconds", 0)
                        + time.monotonic()
                        - started,
                        cpu_seconds=metrics.get("cpu_seconds", 0)
                        + after.ru_utime
                        + after.ru_stime
                        - before.ru_utime
                        - before.ru_stime,
                        peak_rss_kib=max(
                            after.ru_maxrss,
                            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                        ),
                        artifact_bytes=sum(
                            p.stat().st_size for p in job.rglob("*") if p.is_file()
                        )
                        if job.exists()
                        else 0,
                        production_cost_usd=sum(
                            c.get("estimated_usd", 0) for c in costs
                        ),
                        api_calls=len(costs),
                        errors=metrics.get("errors", 0) + errors,
                        retries=max(0, slot["attempts"] - 1),
                        human_hours=metrics.get("human_hours"),
                    ),
                )
                save(self.root / "metrics.json", metrics_report(self.store))

    def _prior_metrics(self, job_id):
        with self.store.connect() as db:
            row = db.execute(
                "SELECT record FROM metrics WHERE job_id=?", (job_id,)
            ).fetchone()
        return json.loads(row["record"]) if row else {}
