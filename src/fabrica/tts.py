"""Interfaz preliminar Piper CLI. Requiere modelo y ejecutable instalados localmente."""
import os
from pathlib import Path
import subprocess


def narrate(text: str, wav_path: Path):
    model = os.getenv("PIPER_VOICE_MODEL")
    if not model or not Path(model).is_file():
        raise RuntimeError("Configurar PIPER_VOICE_MODEL con un modelo local licenciado")
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([os.getenv("PIPER_EXECUTABLE", "piper"), "--model", model,
                    "--output_file", str(wav_path)], input=text.encode("utf-8"),
                   check=True, timeout=180)
    if not wav_path.exists() or wav_path.stat().st_size < 1024:
        raise RuntimeError("Piper no produjo un WAV válido")
    return wav_path
