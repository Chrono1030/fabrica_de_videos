"""Calendario diario SQLite + lock POSIX. Un solo trabajador, sin n8n ni daemon externo."""

import uuid
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from pydantic import Field, field_validator

from .catalog import now
from .metadata import Contract

# Existing MOCK templates cover these two topics. Other topics require original scripts.
MOCK_TOPICS = (
    "Elegir una alternativa implica renunciar",
    "Ganar más no siempre significa ahorrar más",
)


class ScheduleConfig(Contract):
    timezone: str
    local_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    start_date: date
    every_days: int = Field(default=1, ge=1, le=365)
    max_attempts: int = Field(default=3, ge=1, le=5)

    @field_validator("timezone")
    @classmethod
    def valid_zone(cls, value):
        ZoneInfo(value)
        return value

    @field_validator("local_time")
    @classmethod
    def valid_time(cls, value):
        time.fromisoformat(value)
        return value


def utc(value):
    if value.tzinfo is None:
        raise ValueError("Fecha/hora debe incluir zona horaria")
    return value.astimezone(timezone.utc)


def due(day, config):
    zone = ZoneInfo(config.timezone)
    local = datetime.combine(day, time.fromisoformat(config.local_time), zone)
    converted = utc(local)
    if converted.astimezone(zone).replace(tzinfo=None) != local.replace(tzinfo=None):
        raise ValueError("Hora local inexistente por cambio de horario")
    # For a repeated hour (DST), fold=0 and UNIQUE(local_day) guarantee one slot.
    return converted


class Scheduler:
    def __init__(self, store, config):
        self.store, self.config = store, config
        with store.connect() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS factory_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT value FROM factory_settings WHERE key='schedule'"
            ).fetchone()
            encoded = config.model_dump_json()
            if row and row["value"] != encoded:
                raise ValueError(
                    "Calendario existente tiene otra configuración; revisar slots antes de migrar"
                )
            db.execute(
                "INSERT OR IGNORE INTO factory_settings VALUES('schedule',?)",
                (encoded,),
            )

    def plan(self, start, days=7):
        if not 1 <= days <= 366:
            raise ValueError("Horizonte fuera de rango")
        start = utc(start).astimezone(ZoneInfo(self.config.timezone)).date()
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            for offset in range(days):
                day = start + timedelta(days=offset)
                if (
                    day < self.config.start_date
                    or (day - self.config.start_date).days % self.config.every_days
                ):
                    continue
                at = due(day, self.config)
                job_id = (
                    "slot-"
                    + uuid.uuid5(
                        uuid.NAMESPACE_URL,
                        day.isoformat() + self.config.model_dump_json(),
                    ).hex
                )
                db.execute(
                    "INSERT OR IGNORE INTO calendar(local_day,due_utc,timezone,job_id,state,config) "
                    "VALUES(?,?,?,?,?,?)",
                    (
                        day.isoformat(),
                        at.isoformat(),
                        self.config.timezone,
                        job_id,
                        "PLANNED",
                        self.config.model_dump_json(),
                    ),
                )
        return self.upcoming()

    def upcoming(self):
        with self.store.connect() as db:
            return [
                dict(r) for r in db.execute("SELECT * FROM calendar ORDER BY due_utc")
            ]

    def claim(self, clock):
        """Caller holds factory worker lock through completion. Topic and slot reserved together."""
        clock = utc(clock)
        today = clock.astimezone(ZoneInfo(self.config.timezone)).date().isoformat()
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "UPDATE calendar SET state='EXPIRED',error='slot_expired' "
                "WHERE local_day<? AND state IN ('PLANNED','RETRY_WAIT','RUNNING')",
                (today,),
            )
            row = db.execute(
                "SELECT * FROM calendar WHERE local_day=? AND due_utc<=? "
                "AND state IN ('PLANNED','RETRY_WAIT','RUNNING')",
                (today, clock.isoformat()),
            ).fetchone()
            if not row or (
                row["retry_at"] and clock < datetime.fromisoformat(row["retry_at"])
            ):
                return None
            if row["attempts"] >= self.config.max_attempts:
                db.execute(
                    "UPDATE calendar SET state='BLOCKED',error='retry_limit' WHERE local_day=?",
                    (today,),
                )
                return None
            topic_id = row["topic_id"]
            if topic_id is None:
                topic = db.execute(
                    "SELECT * FROM topics WHERE state='AVAILABLE' AND title IN (?,?) "
                    "ORDER BY priority DESC,id LIMIT 1",
                    MOCK_TOPICS,
                ).fetchone()
                if topic is None:
                    db.execute(
                        "UPDATE calendar SET state='BLOCKED',error='no_supported_mock_topic' WHERE local_day=?",
                        (today,),
                    )
                    return None
                topic_id = topic["id"]
                db.execute(
                    "UPDATE topics SET state='RESERVED',selected_at=?,job_id=? WHERE id=?",
                    (now(), row["job_id"], topic_id),
                )
                db.execute(
                    "INSERT INTO history(topic_id,job_id,state,at,details) VALUES(?,?,?,?,?)",
                    (topic_id, row["job_id"], "RESERVED", now(), "{}"),
                )
            db.execute(
                "UPDATE calendar SET topic_id=?,state='RUNNING',attempts=attempts+1,retry_at=NULL WHERE local_day=?",
                (topic_id, today),
            )
            return dict(
                db.execute(
                    "SELECT c.*,t.title,t.category FROM calendar c JOIN topics t ON c.topic_id=t.id "
                    "WHERE local_day=?",
                    (today,),
                ).fetchone()
            )

    def finish(self, slot, state, error=None, retry_at=None):
        if state not in ("SIMULATED_DONE", "BLOCKED", "RETRY_WAIT", "REVIEW_REQUIRED"):
            raise ValueError("Estado de calendario inválido")
        with self.store.connect() as db:
            db.execute(
                "UPDATE calendar SET state=?,error=?,retry_at=? WHERE job_id=?",
                (state, error, retry_at, slot["job_id"]),
            )
