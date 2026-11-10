"""Catálogo editorial SQLite; reservas idempotentes por trabajo y transacciones IMMEDIATE."""

import json
import sqlite3
import unicodedata
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

GROUPS = {
    "Psicología del dinero": [
        "Por qué el saldo cambia nuestra percepción",
        "El dinero como señal de seguridad",
        "Compararnos con vecinos tiene un costo",
        "La compra que busca aprobación",
        "Cómo afecta el miedo a perder",
    ],
    "Economía cotidiana": [
        "El precio de cocinar en casa",
        "Por qué una fila también cuesta",
        "Reparar o reemplazar un objeto",
        "Compartir herramientas entre vecinos",
        "Qué paga realmente un alquiler",
    ],
    "Ahorro y consumo": [
        "Ganar más no siempre significa ahorrar más",
        "El descuento que aumenta el gasto",
        "Planificar compras evita decisiones apuradas",
        "Suscripciones pequeñas y presupuesto",
        "Separar deseos de necesidades",
    ],
    "Productividad personal": [
        "El costo de cambiar de tarea",
        "Descansar como inversión de energía",
        "Una agenda con espacio para imprevistos",
        "Medir resultados en lugar de horas",
        "Reducir decisiones repetidas",
    ],
    "Libertad financiera": [
        "Autonomía y gastos fijos",
        "Construir margen para elegir",
        "La diferencia entre riqueza e ingresos",
        "Objetivos propios frente a expectativas ajenas",
        "Flexibilidad antes que lujo",
    ],
    "Interés compuesto": [
        "Crecimiento sobre una base acumulada",
        "El tiempo y la reinversión hipotética",
        "Las comisiones también se acumulan",
        "Deudas y crecimiento acumulativo",
        "Por qué el crecimiento no es una promesa",
    ],
    "Costo de oportunidad": [
        "Elegir una alternativa implica renunciar",
        "Estudiar o trabajar una hora adicional",
        "Espacio ocupado por objetos sin uso",
        "Tiempo de viaje y decisiones laborales",
        "El costo de posponer una elección",
    ],
    "Riesgo e incertidumbre": [
        "No saber no equivale a perder",
        "Una reserva ante gastos imprevistos",
        "Diversificar sin prometer protección total",
        "Probabilidad y gravedad son distintas",
        "Decidir con información incompleta",
    ],
    "Hábitos financieros": [
        "Revisar gastos sin castigarse",
        "Un registro simple de decisiones",
        "Automatizar una pequeña reserva",
        "Conversaciones sobre dinero en pareja",
        "Cambiar un hábito por vez",
    ],
    "Decisiones económicas": [
        "Comparar costos totales y no cuotas",
        "La comodidad también tiene valor",
        "Costos hundidos y decisiones nuevas",
        "Elegir bajo restricciones reales",
        "Cómo evaluar una alternativa reversible",
    ],
}


def normalized(text):
    return " ".join(
        "".join(
            c
            for c in unicodedata.normalize("NFKD", text.lower())
            if not unicodedata.combining(c)
        ).split()
    )


class Catalog:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""CREATE TABLE IF NOT EXISTS topics (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, key TEXT UNIQUE NOT NULL,
            category TEXT NOT NULL, description TEXT NOT NULL, priority INTEGER NOT NULL,
            state TEXT NOT NULL DEFAULT 'AVAILABLE', created_at TEXT NOT NULL,
            selected_at TEXT, job_id TEXT UNIQUE);
            CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY, topic_id TEXT,
            job_id TEXT, state TEXT, at TEXT, details TEXT);
            CREATE TABLE IF NOT EXISTS scripts (job_id TEXT PRIMARY KEY, title TEXT, body TEXT);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def seed(self):
        with self.connect() as db:
            for category, titles in GROUPS.items():
                for title in titles:
                    db.execute(
                        "INSERT OR IGNORE INTO topics(id,title,key,category,description,priority,created_at) VALUES(?,?,?,?,?,?,?)",
                        (
                            uuid.uuid5(uuid.NAMESPACE_URL, title).hex,
                            title,
                            normalized(title),
                            category,
                            f"Explicar {title.lower()} mediante un ejemplo cotidiano original, con matices y sin recomendaciones personalizadas.",
                            10,
                            now(),
                        ),
                    )

    def reserve(self, job_id):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM topics WHERE job_id=?", (job_id,)
            ).fetchone()
            if row:
                return dict(row)
            row = db.execute(
                "SELECT * FROM topics WHERE state='AVAILABLE' ORDER BY priority DESC, created_at, id LIMIT 1"
            ).fetchone()
            if row is None:
                raise ValueError("Catálogo agotado")
            db.execute(
                "UPDATE topics SET state='RESERVED', selected_at=?, job_id=? WHERE id=?",
                (now(), job_id, row["id"]),
            )
            db.execute(
                "INSERT INTO history(topic_id,job_id,state,at,details) VALUES(?,?,?,?,?)",
                (row["id"], job_id, "RESERVED", now(), "{}"),
            )
            return dict(
                db.execute("SELECT * FROM topics WHERE id=?", (row["id"],)).fetchone()
            )

    def finish(self, job_id, state, details):
        if state not in ("BLOCKED", "TECHNICALLY_READY"):
            raise ValueError("Estado inválido")
        with self.connect() as db:
            row = db.execute(
                "SELECT id FROM topics WHERE job_id=?", (job_id,)
            ).fetchone()
            if row is None:
                raise ValueError("Trabajo sin reserva")
            db.execute("UPDATE topics SET state=? WHERE job_id=?", (state, job_id))
            db.execute(
                "INSERT INTO history(topic_id,job_id,state,at,details) VALUES(?,?,?,?,?)",
                (row["id"], job_id, state, now(), json.dumps(details)),
            )

    def review(self, job_id, script):
        from .editorial import review

        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            previous = [
                dict(r)
                for r in db.execute(
                    "SELECT * FROM scripts WHERE job_id != ?", (job_id,)
                )
            ]
            issues = review(script, previous)
            if not issues:
                db.execute(
                    "INSERT OR REPLACE INTO scripts VALUES(?,?,?)",
                    (
                        job_id,
                        script.title,
                        " ".join(s.narration for s in script.scenes),
                    ),
                )
            return issues


def now():
    return datetime.now(timezone.utc).isoformat()
