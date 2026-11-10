"""Trabajos locales reanudables; no publica ni certifica calidad editorial."""

import fcntl
import hashlib
import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .cards import create_cards
from .editorial import check
from .gpt import generate_checked
from .models import VideoScript
from .render import compose, quality, subtitles
from .tts import MockTTS, PiperTTS, duration


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def save(path, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def mock_script(topic):
    if "ganar" in topic.lower() or "ingreso" in topic.lower():
        from .demo_scripts import income_script

        return income_script(topic)
    return VideoScript(
        topic=topic,
        title=topic[:100],
        description="Ejemplo determinista simulado",
        language="es-419",
        hook="Cada decisión tiene una alternativa.",
        disclaimer="Contenido educativo. Audio técnico simulado.",
        references=[],
        scenes=[
            dict(
                narration=text,
                headline=title,
                visual_type=visual,
                visual_label="Ejemplo hipotético",
                visual_data=data,
            )
            for text, title, visual, data in [
                (
                    "El costo de oportunidad es el valor de la mejor alternativa que dejamos al elegir. No siempre aparece como un pago en dinero.",
                    "Elegir implica renunciar",
                    "comparison",
                    ["Elección", "Alternativa"],
                ),
                (
                    "Por ejemplo, dedicar una hora a estudiar puede significar renunciar a una hora de descanso. Ambas opciones tienen valor para la persona que decide.",
                    "Una hora disponible",
                    "big_number",
                    ["1"],
                ),
                (
                    "Comparar alternativas permite reconocer ese intercambio. Este ejemplo es hipotético y no recomienda una decisión financiera particular ni promete resultados económicos.",
                    "Compará alternativas",
                    "bar_chart",
                    ["Estudio:2", "Descanso:1"],
                ),
                (
                    "En un ejemplo hipotético, dedicar una, dos o tres horas a estudiar deja tres, dos o una horas para descansar dentro de cuatro horas disponibles. Elegir exige reconocer esa alternativa.",
                    "Pensá en lo que resignás",
                    "line_chart",
                    ["Estudiar 1h:3", "Estudiar 2h:2", "Estudiar 3h:1"],
                ),
            ]
        ],
    )


def produce(
    topic,
    mode="mock",
    root=Path("out/jobs"),
    job_id=None,
    script_path=None,
    width=1080,
    height=1920,
    mock_seconds=1.0,
    subtitle_style=None,
    catalog_path=None,
):
    if mode not in ("mock", "real") or not topic.strip():
        raise ValueError("Modo o tema inválido")
    job_id = job_id or uuid.uuid4().hex
    if not job_id.replace("-", "").replace("_", "").isalnum():
        raise ValueError("Identificador inválido")
    root = Path(root)
    job = root / job_id
    job.mkdir(parents=True, exist_ok=True)
    from .subtitle_style import SubtitleStyle

    style = subtitle_style or SubtitleStyle()
    config = dict(
        pipeline_version="1.5",
        topic=topic,
        mode=mode,
        width=width,
        height=height,
        mock_seconds=mock_seconds,
        subtitle_style=style.config(),
        script_sha=digest(Path(script_path)) if script_path else None,
    )
    with (job / ".lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        path = job / "result.json"
        state = (
            json.loads(path.read_text())
            if path.exists()
            else dict(config=config, stages={}, events=[], costs=[], api_pending=False)
        )
        if state["config"] != config:
            raise ValueError("El trabajo existente tiene otra configuración")

        def event(status):
            state["status"] = status
            state["events"].append(
                dict(status=status, at=datetime.now(timezone.utc).isoformat())
            )
            save(path, state)

        def stage(name, files, action):
            previous = state["stages"].get(name)
            if previous and all(
                p.is_file() and digest(p) == previous.get(p.name) for p in files
            ):
                return
            # Invalidar resultados posteriores cuando se reconstruye una etapa.
            keys = list(state["stages"])
            if name in keys:
                for key in keys[keys.index(name) :]:
                    state["stages"].pop(key, None)
            action()
            state["stages"][name] = {p.name: digest(p) for p in files}
            event(name)

        try:
            event("STARTED")
            if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
                raise RuntimeError("Instalar FFmpeg y ffprobe en Codex Cloud")
            script_file = job / "script.json"

            def script_action():
                if script_path:
                    script = VideoScript.model_validate_json(
                        Path(script_path).read_text()
                    )
                elif mode == "mock":
                    script = mock_script(topic)
                else:
                    # Reserva persistente global: evita duplicar gasto entre trabajos/reintentos.
                    with (root / ".budget.lock").open("w") as budget_lock:
                        fcntl.flock(budget_lock, fcntl.LOCK_EX)
                        budget_path = root / "budget.json"
                        budget = (
                            json.loads(budget_path.read_text())
                            if budget_path.exists()
                            else {"reserved_usd": 0}
                        )
                        limit = float(os.getenv("MAX_API_BUDGET_USD", "5"))
                        reserve = float(os.getenv("OPENAI_REQUEST_RESERVE_USD", "1"))
                        if state["api_pending"]:
                            raise RuntimeError(
                                "Llamada pendiente: conciliar consumo antes de reintentar"
                            )
                        import math

                        if (
                            not all(
                                math.isfinite(x) and x > 0 for x in (limit, reserve)
                            )
                            or budget["reserved_usd"] + reserve > limit
                        ):
                            raise RuntimeError("Presupuesto agotado")
                        budget["reserved_usd"] += reserve
                        save(budget_path, budget)
                        state["api_pending"] = True
                        save(path, state)
                        script, usage, issues = generate_checked(
                            topic, remaining_usd=reserve
                        )
                        state["costs"].append(usage)
                        save(path, state)
                        if issues or usage["estimated_usd"] > reserve:
                            raise RuntimeError(
                                "Guion o consumo bloqueado; revisar registro"
                            )
                        # Reserva conservadora retenida; no garantiza techo duro del proveedor.
                issues = check(script)
                if issues:
                    raise ValueError("; ".join(issues))
                save(script_file, script.model_dump(mode="json"))

            stage("SCRIPT", [script_file], script_action)
            script = VideoScript.model_validate_json(script_file.read_text())
            if check(script):
                raise ValueError("Guion bloqueado por reglas preliminares")
            from .catalog import Catalog

            catalog = Catalog(catalog_path or root / "editorial.sqlite3")
            issues = catalog.review(job_id, script)
            state["editorial_reasons"] = issues
            save(path, state)
            if issues:
                raise ValueError("; ".join(issues))
            images = [
                job / "cards" / f"scene_{i:02}.png"
                for i in range(1, len(script.scenes) + 1)
            ]
            stage("CARDS", images, lambda: create_cards(script, job / "cards"))
            provider = MockTTS(mock_seconds) if mode == "mock" else PiperTTS()
            audios = [job / f"audio_{i:02}.wav" for i in range(len(script.scenes))]
            for i, (scene, audio) in enumerate(zip(script.scenes, audios)):
                stage(
                    f"AUDIO_{i}",
                    [audio],
                    lambda s=scene, p=audio: provider.synthesize(s.narration, p),
                )
            durations = [duration(p) for p in audios]
            if mode == "real" and not 60 <= sum(durations) <= 90:
                raise ValueError(
                    "Narración real fuera del rango comercial de 60–90 segundos"
                )
            srt = job / "subtitles.srt"
            stage(
                "SUBTITLES",
                [srt],
                lambda: subtitles(script.scenes, durations, srt, mode == "mock"),
            )
            video = job / "final.mp4"
            # Renderizar de nuevo si cualquier entrada cambió desde la última composición.
            inputs = hashlib.sha256(
                "".join(digest(p) for p in images + audios + [srt]).encode()
            ).hexdigest()
            if state.get("render_inputs") != inputs:
                state["stages"].pop("RENDER", None)
            stage(
                "RENDER",
                [video],
                lambda: compose(
                    images,
                    audios,
                    durations,
                    srt,
                    video,
                    width,
                    height,
                    script.scenes,
                    style,
                ),
            )
            state["render_inputs"] = inputs
            state["quality"] = quality(
                video, width, height, sum(durations), srt, style.burn
            )
            if list(job.glob("*.partial.mp4")):
                raise ValueError("Archivo incompleto presente")
            state.pop("error", None)
            state.update(
                audio_simulated=mode == "mock",
                publish_enabled=False,
                editorial_status="REQUIRES_REVIEW",
                duration=sum(durations),
            )
            event("TECHNICALLY_READY")
            return job
        except Exception as exc:
            state["error"] = {
                "type": type(exc).__name__,
                "message": str(exc)
                if not hasattr(exc, "stderr")
                else "Fallo de herramienta audiovisual",
            }
            event("BLOCKED")
            raise


def produce_auto(catalog_path, root=Path("out/jobs"), job_id=None, **kwargs):
    from .catalog import Catalog

    catalog = Catalog(catalog_path)
    catalog.seed()
    job_id = job_id or uuid.uuid4().hex
    topic = catalog.reserve(job_id)
    try:
        job = produce(
            topic["title"],
            root=root,
            job_id=job_id,
            catalog_path=catalog_path,
            **kwargs,
        )
        catalog.finish(job_id, "TECHNICALLY_READY", {"path": str(job)})
        return job
    except Exception as exc:
        catalog.finish(job_id, "BLOCKED", {"error_type": type(exc).__name__})
        raise
