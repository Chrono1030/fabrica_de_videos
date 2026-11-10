"""Proveedores de audio: MOCK produce tonos, nunca voz humana."""

import math
import os
import re
import subprocess
import wave
from array import array
from pathlib import Path
from typing import Protocol


def normalize(text: str) -> str:
    text = re.sub(r"\$(\d+(?:[.,]\d+)?)", r"\1 dólares", text)
    text = re.sub(r"(\d+(?:[.,]\d+)?)\s*%", r"\1 por ciento", text)
    text = text.replace("USD", "dólares estadounidenses").replace(
        "PIB", "producto interno bruto"
    )
    return re.sub(r"(?<=\d)[.,](?=\d)", " coma ", text)


def duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wav:
        if wav.getnframes() == 0:
            raise ValueError("WAV vacío")
        return wav.getnframes() / wav.getframerate()


class TTS(Protocol):
    def synthesize(self, text: str, path: Path) -> float: ...


class MockTTS:
    """Tono determinista de 440 Hz para pruebas técnicas, no narración."""

    def __init__(self, seconds: float = 1.0):
        if not 0.1 <= seconds <= 90:
            raise ValueError("Duración MOCK inválida")
        self.seconds = seconds

    def synthesize(self, text: str, path: Path) -> float:
        path.parent.mkdir(parents=True, exist_ok=True)
        samples = array(
            "h",
            (
                int(2200 * math.sin(2 * math.pi * 440 * i / 16000))
                for i in range(round(16000 * self.seconds))
            ),
        )
        import sys

        if sys.byteorder != "little":
            samples.byteswap()
        with wave.open(str(path), "wb") as wav:
            wav.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
            wav.writeframes(samples.tobytes())
        return duration(path)


class PiperTTS:
    def synthesize(self, text: str, path: Path) -> float:
        model = Path(os.environ.get("PIPER_VOICE_MODEL", ""))
        if not model.is_file() or not Path(str(model) + ".json").is_file():
            raise RuntimeError("Configurar modelo Piper y JSON con licencia verificada")
        import json

        language = json.loads(Path(str(model) + ".json").read_text())["language"][
            "code"
        ]
        if not language.startswith("es_") or language == "es_ES":
            raise ValueError("La voz debe ser español latinoamericano")
        path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                os.getenv("PIPER_EXECUTABLE", "piper"),
                "--model",
                str(model),
                "--output_file",
                str(path),
            ],
            input=normalize(text),
            text=True,
            check=True,
            timeout=180,
            capture_output=True,
        )
        return duration(path)


def narrate(text: str, wav_path: Path):
    PiperTTS().synthesize(text, wav_path)
    return wav_path
