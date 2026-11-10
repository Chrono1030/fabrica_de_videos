"""Controles deterministas PRELIMINARES: no son una revisión editorial semántica."""

import re

from .models import VideoScript

UNSAFE_PROMISES = (
    r"ganancia(s)? garantizada(s)?",
    r"rendimiento(s)? garantizado(s)?",
    r"sin (ningún )?riesgo",
    r"ganar dinero seguro",
)


def check(script: VideoScript) -> list[str]:
    failures = []
    all_text = " ".join(
        [script.title, script.description] + [s.narration for s in script.scenes]
    ).lower()
    for pattern in UNSAFE_PROMISES:
        if re.search(pattern, all_text, flags=re.I):
            failures.append(f"Promesa sospechosa: {pattern}")
    if len(set(s.narration.strip().lower() for s in script.scenes)) != len(
        script.scenes
    ):
        failures.append("Narraciones duplicadas")
    if not script.hook.strip():
        failures.append("Gancho vacío")
    if len(" ".join(s.narration for s in script.scenes).split()) < 35:
        failures.append("Narración insuficiente")
    return failures


def review(script, previous=()):
    """Heurísticas conservadoras; aprobar no equivale a verificar hechos o fuentes."""
    from difflib import SequenceMatcher

    from .cards import visual_values
    from .catalog import normalized

    issues = check(script)
    body = " ".join(s.narration for s in script.scenes)
    if not all(
        x.strip()
        for x in (script.topic, script.title, script.description, script.disclaimer)
    ):
        issues.append("Guion incompleto")
    if not re.search(
        r"costo|ahorr|dinero|eleg|elecci|presupuesto|recurso|riesgo|interés|interes|gasto|decisi|productiv",
        body,
        re.I,
    ):
        issues.append("Sin explicación económica reconocible")
    for prior in previous:
        if (
            SequenceMatcher(None, normalized(body), normalized(prior["body"])).ratio()
            >= 0.85
        ):
            issues.append("Guion duplicado o excesivamente similar")
        if (
            SequenceMatcher(
                None, normalized(script.title), normalized(prior["title"])
            ).ratio()
            >= 0.9
        ):
            issues.append("Tema excesivamente similar")
    narrations = [normalized(s.narration) for s in script.scenes]
    if any(
        SequenceMatcher(None, a, b).ratio() >= 0.88
        for i, a in enumerate(narrations)
        for b in narrations[i + 1 :]
    ):
        issues.append("Narraciones repetitivas")
    if script.references:
        issues.append("Referencias pendientes de verificación independiente")
    for scene in script.scenes:
        if re.search(
            r"\d", scene.narration + " ".join(scene.visual_data)
        ) and not re.search(
            r"hipotétic|hipotetic|simulad", scene.narration + scene.visual_label, re.I
        ):
            issues.append("Datos numéricos sin naturaleza hipotética verificable")
        if scene.visual_type in ("bar_chart", "line_chart"):
            try:
                if not 2 <= len(scene.visual_data) <= 4:
                    raise ValueError("Se requieren 2–4 magnitudes")
                visual_values(scene.visual_data)
            except ValueError as exc:
                issues.append(f"Escena incompatible: {exc}")
        if len(scene.headline) > 70 or len(scene.visual_label) > 60:
            issues.append("Texto incompatible con zona gráfica segura")
    return list(dict.fromkeys(issues))
