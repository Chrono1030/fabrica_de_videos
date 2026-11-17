"""Una SQLite compartida: catálogo, calendario, paquetes, intentos y métricas."""

import json
from difflib import SequenceMatcher

from .catalog import Catalog, normalized, now
from .metadata import PublicationPackage


class FactoryStore(Catalog):
    def __init__(self, path):
        super().__init__(path)
        with self.connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS packages (
              job_id TEXT PRIMARY KEY, title_key TEXT UNIQUE NOT NULL,
              description_key TEXT UNIQUE NOT NULL, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS calendar (
              local_day TEXT PRIMARY KEY, due_utc TEXT NOT NULL, timezone TEXT NOT NULL,
              job_id TEXT UNIQUE NOT NULL, topic_id TEXT, state TEXT NOT NULL,
              attempts INTEGER NOT NULL DEFAULT 0, retry_at TEXT, error TEXT,
              config TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS publications (
              job_id TEXT PRIMARY KEY, channel_id TEXT NOT NULL, package_hash TEXT NOT NULL,
              asset_hash TEXT UNIQUE NOT NULL, state TEXT NOT NULL,
              session TEXT, cursor INTEGER NOT NULL DEFAULT 0, remote_id TEXT UNIQUE,
              attempts INTEGER NOT NULL DEFAULT 0, retry_at TEXT, error TEXT,
              updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS publication_events (
              id INTEGER PRIMARY KEY, job_id TEXT NOT NULL, state TEXT NOT NULL,
              at TEXT NOT NULL, details TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS mock_remote (
              session TEXT PRIMARY KEY, intent TEXT UNIQUE NOT NULL, channel_id TEXT NOT NULL,
              body TEXT NOT NULL, cursor INTEGER NOT NULL DEFAULT 0,
              remote_id TEXT UNIQUE, state TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS metrics (
              job_id TEXT PRIMARY KEY, record TEXT NOT NULL);
            """)

    def save_package(self, package):
        package = PublicationPackage.model_validate(package.model_dump())
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            prior = db.execute(
                "SELECT payload FROM packages WHERE job_id=?", (package.job_id,)
            ).fetchone()
            payload = package.model_dump_json()
            if prior:
                if prior["payload"] != payload:
                    raise ValueError("Paquete ya registrado con otro contenido")
                return
            for previous in db.execute(
                "SELECT title_key,description_key FROM packages"
            ):
                if (
                    SequenceMatcher(
                        None, normalized(package.title), previous["title_key"]
                    ).ratio()
                    >= 0.9
                    or SequenceMatcher(
                        None,
                        normalized(package.description),
                        previous["description_key"],
                    ).ratio()
                    >= 0.9
                ):
                    raise ValueError("Metadatos repetidos o excesivamente similares")
            db.execute(
                "INSERT INTO packages VALUES(?,?,?,?)",
                (
                    package.job_id,
                    normalized(package.title),
                    normalized(package.description),
                    payload,
                ),
            )

    def package(self, job_id):
        with self.connect() as db:
            row = db.execute(
                "SELECT payload FROM packages WHERE job_id=?", (job_id,)
            ).fetchone()
        if row is None:
            raise ValueError("Paquete inexistente")
        return PublicationPackage.model_validate_json(row["payload"])

    def publication(self, job_id):
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM publications WHERE job_id=?", (job_id,)
            ).fetchone()
        return dict(row) if row else None

    def publication_state(self, job_id, state, **values):
        allowed = {"session", "cursor", "remote_id", "attempts", "retry_at", "error"}
        if set(values) - allowed:
            raise ValueError("Campos desconocidos")
        with self.connect() as db:
            db.execute(
                "UPDATE publications SET state=?,updated_at=?"
                + "".join(f",{key}=?" for key in values)
                + " WHERE job_id=?",
                (state, now(), *values.values(), job_id),
            )
            db.execute(
                "INSERT INTO publication_events(job_id,state,at,details) VALUES(?,?,?,?)",
                (job_id, state, now(), json.dumps(values)),
            )
