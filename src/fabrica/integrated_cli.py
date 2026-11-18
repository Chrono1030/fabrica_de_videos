"""Comandos integrados, sin credenciales ni publicaciones reales."""

import json
from datetime import datetime, timezone
from pathlib import Path

from .economics import Scenario, VideoMetrics, metrics_report, save_metrics
from .factory import Factory
from .factory_store import FactoryStore
from .scheduler import ScheduleConfig, Scheduler
from .tts_registry import VoiceManifest, register_voice


def add_commands(sub):
    calendar = sub.add_parser(
        "calendar", help="Planificar o inspeccionar calendario SQLite"
    )
    calendar.add_argument("action", choices=["plan", "next"])
    cycle = sub.add_parser(
        "cycle", help="Ejecutar un ciclo completo exclusivamente MOCK"
    )
    for command in (calendar, cycle):
        command.add_argument(
            "--db", type=Path, default=Path("out/factory/state.sqlite3")
        )
        command.add_argument("--config", type=Path, required=True)
        command.add_argument("--at", help="Reloj ISO con zona; solo simulación")
    calendar.add_argument("--days", type=int, default=7)
    from .renderer_cli import add_options

    add_options(cycle)
    cycle.add_argument("--script", type=Path)
    cycle.add_argument("--output", type=Path, default=Path("out/factory/jobs"))
    cycle.add_argument("--width", type=int, default=1080)
    cycle.add_argument("--height", type=int, default=1920)
    cycle.add_argument(
        "--fault",
        choices=[
            "connection",
            "quota",
            "token",
            "uncertain",
            "permanent",
            "crash",
            "partial",
        ],
    )
    metrics = sub.add_parser(
        "metrics", help="Registros básicos; no inventa datos de Analytics"
    )
    metrics.add_argument("--db", type=Path, default=Path("out/factory/state.sqlite3"))
    metrics.add_argument("--job-id")
    metrics.add_argument("--human-hours", type=float)
    economics = sub.add_parser(
        "economics", help="Evaluar escenarios hipotéticos explícitos"
    )
    economics.add_argument("scenarios", type=Path)
    voice = sub.add_parser(
        "voice-register", help="Registrar un manifiesto de voz local, sin descargas"
    )
    voice.add_argument("manifest", type=Path)
    voice.add_argument("--db", type=Path, default=Path("out/factory/state.sqlite3"))


def dispatch(args):
    if args.cmd in ("calendar", "cycle"):
        config = ScheduleConfig.model_validate_json(args.config.read_text())
        clock = (
            datetime.fromisoformat(args.at) if args.at else datetime.now(timezone.utc)
        )
        store = FactoryStore(args.db)
        scheduler = Scheduler(store, config)
        if args.cmd == "calendar":
            value = (
                scheduler.plan(clock, args.days)
                if args.action == "plan"
                else scheduler.upcoming()
            )
        else:
            from .renderer_cli import options

            visual = options(args)
            rendering = visual.pop("renderer_config")
            value = Factory(
                store, config, args.output, renderer_config=rendering
            ).cycle(
                clock=clock,
                width=args.width,
                height=args.height,
                fault=args.fault,
                script_path=args.script,
                **visual,
            )
    elif args.cmd == "metrics":
        store = FactoryStore(args.db)
        if args.human_hours is not None:
            if not args.job_id:
                raise ValueError("--human-hours requiere --job-id")
            with store.connect() as db:
                row = db.execute(
                    "SELECT record FROM metrics WHERE job_id=?", (args.job_id,)
                ).fetchone()
            if row is None:
                raise ValueError("Trabajo sin métricas")
            record = VideoMetrics.model_validate_json(row["record"])
            save_metrics(
                store,
                VideoMetrics.model_validate(
                    record.model_dump() | {"human_hours": args.human_hours}
                ),
            )
        value = metrics_report(store)
    elif args.cmd == "economics":
        data = json.loads(args.scenarios.read_text())
        scenarios = [Scenario.model_validate(item) for item in data]
        if {s.name for s in scenarios} != {"pesimista", "base", "optimista"} or len(
            scenarios
        ) != 3:
            raise ValueError(
                "Definir exactamente tres escenarios: pesimista, base, optimista"
            )
        value = [s.calculate() for s in scenarios]
    elif args.cmd == "voice-register":
        register_voice(
            FactoryStore(args.db),
            VoiceManifest.model_validate_json(args.manifest.read_text()),
        )
        value = {"registered": True, "publication_enabled": False}
    else:
        return False
    print(json.dumps(value, ensure_ascii=False, indent=2))
    return True
