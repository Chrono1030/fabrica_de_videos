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
    all_text = " ".join([script.title, script.description] + [s.narration for s in script.scenes]).lower()
    for pattern in UNSAFE_PROMISES:
        if re.search(pattern, all_text, flags=re.I):
            failures.append(f"Promesa sospechosa: {pattern}")
    if len(set(s.narration.strip().lower() for s in script.scenes)) != len(script.scenes):
        failures.append("Narraciones duplicadas")
    if not script.hook.strip():
        failures.append("Gancho vacío")
    if len(" ".join(s.narration for s in script.scenes).split()) < 35:
        failures.append("Narración insuficiente")
    return failures
