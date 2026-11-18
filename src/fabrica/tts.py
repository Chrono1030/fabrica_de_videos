"""Proveedores de audio: MOCK produce tonos, nunca voz humana."""

import hashlib
import json
import math
import os
import subprocess
import wave
from array import array
from pathlib import Path
from typing import Protocol

from .normalization import normalize


def duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wav:
        if wav.getnframes() == 0:
            raise ValueError("WAV vacío")
        expected = wav.getnframes() * wav.getnchannels() * wav.getsampwidth()
        if len(wav.readframes(wav.getnframes())) != expected:
            raise ValueError("WAV incompleto")
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


def _piper_worker(connection, model, scale):
    """Un proceso por proveedor: modelo reutilizado y timeout cancelable."""
    try:
        from piper import PiperVoice, SynthesisConfig

        voice = PiperVoice.load(model)
        config = SynthesisConfig(length_scale=scale)
        while True:
            request = connection.recv()
            if request is None:
                return
            text, target = request
            try:
                with wave.open(target, "wb") as wav:
                    voice.synthesize_wav(text, wav, config)
                connection.send((True, duration(Path(target))))
            except Exception as exc:
                connection.send((False, str(exc)))
    except Exception as exc:
        connection.send((False, str(exc)))
    finally:
        connection.close()


class PiperTTS:
    def __init__(
        self,
        *,
        model=None,
        scale=None,
        timeout=None,
        currency=None,
        normalized=False,
        api_only=False,
    ):
        self.currency, self.normalized, self.api_only = currency, normalized, api_only
        self.model = Path(
            model
            or (
                os.getenv("PIPER_VOICE_MODEL")
                or (
                    Path(os.getenv("PIPER_MODELS_DIR", "out/models"))
                    / (os.getenv("PIPER_VOICE", "es_MX-ald-medium") + ".onnx")
                )
            )
        )
        self.scale = float(
            scale if scale is not None else os.getenv("PIPER_LENGTH_SCALE", "1")
        )
        self.timeout = float(
            timeout if timeout is not None else os.getenv("PIPER_TIMEOUT", "180")
        )
        if not math.isfinite(self.scale) or not 0.5 <= self.scale <= 2:
            raise ValueError("PIPER_LENGTH_SCALE debe estar entre 0.5 y 2")
        if not math.isfinite(self.timeout) or self.timeout <= 0:
            raise ValueError("PIPER_TIMEOUT inválido")
        self.process = self.connection = None

    def synthesize(self, text: str, path: Path) -> float:
        import multiprocessing

        model = self.model
        if not model.is_file() or not Path(str(model) + ".json").is_file():
            raise RuntimeError("Configurar modelo Piper y JSON con licencia verificada")
        language = json.loads(Path(str(model) + ".json").read_text())["language"][
            "code"
        ]
        if language not in ("es_AR", "es_MX", "es_CL", "es_CO", "es_PE", "es_VE"):
            raise ValueError("La voz debe ser español latinoamericano")
        manifest_path = Path(str(model) + ".license.json")
        if not manifest_path.is_file():
            raise RuntimeError("Falta revisión de licencia: .onnx.license.json")
        manifest = json.loads(manifest_path.read_text())
        if (
            manifest.get("sha256") != hashlib.sha256(model.read_bytes()).hexdigest()
            or not manifest.get("license")
            or not manifest.get("evidence")
            or manifest.get("approved_local_use") is not True
        ):
            raise RuntimeError("Licencia no verificada para este modelo")
        normalized = (
            text
            if self.normalized
            else normalize(text, self.currency or os.getenv("NARRATION_CURRENCY"))
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".partial.wav")
        try:
            if not self.api_only and os.getenv("PIPER_EXECUTABLE"):
                # Compatibilidad con ejecutables configurados en instalaciones anteriores.
                subprocess.run(
                    [
                        os.environ["PIPER_EXECUTABLE"],
                        "--model",
                        str(model),
                        "--length-scale",
                        str(self.scale),
                        "--output-file",
                        str(temporary),
                    ],
                    input=normalized,
                    text=True,
                    check=True,
                    timeout=self.timeout,
                    capture_output=True,
                )
            else:
                if self.process is None:
                    context = multiprocessing.get_context("spawn")
                    self.connection, child = context.Pipe()
                    self.process = context.Process(
                        target=_piper_worker,
                        args=(child, str(model), self.scale),
                        daemon=True,
                    )
                    self.process.start()
                    child.close()
                self.connection.send((normalized, str(temporary)))
                if not self.connection.poll(self.timeout):
                    raise TimeoutError("Piper excedió el tiempo permitido")
                ok, result = self.connection.recv()
                if not ok:
                    raise RuntimeError("Piper: " + result)
            seconds = duration(temporary)
            temporary.replace(path)
            return seconds
        except BaseException:
            self.close()
            raise
        finally:
            temporary.unlink(missing_ok=True)

    def close(self):
        if self.process is not None:
            self.process.terminate()
            self.process.join(timeout=5)
            self.process = None
        if self.connection is not None:
            self.connection.close()
            self.connection = None


def narrate(text: str, wav_path: Path):
    provider = PiperTTS()
    try:
        provider.synthesize(text, wav_path)
    finally:
        provider.close()
    return wav_path


def piper_fingerprint():
    """Incluye bytes del modelo y su revisión legal para reanudación segura."""
    from importlib.metadata import PackageNotFoundError, version

    settings = {
        key: os.getenv(key)
        for key in (
            "PIPER_VOICE_MODEL",
            "PIPER_MODELS_DIR",
            "PIPER_VOICE",
            "PIPER_LENGTH_SCALE",
            "PIPER_TIMEOUT",
            "PIPER_EXECUTABLE",
            "NARRATION_CURRENCY",
        )
    }
    model = Path(
        settings["PIPER_VOICE_MODEL"]
        or (
            Path(settings["PIPER_MODELS_DIR"] or "out/models")
            / ((settings["PIPER_VOICE"] or "es_MX-ald-medium") + ".onnx")
        )
    )
    settings["files"] = {
        str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest()
        if p.is_file()
        else None
        for p in (model, Path(str(model) + ".json"), Path(str(model) + ".license.json"))
    }
    try:
        settings["piper_version"] = version("piper-tts")
    except PackageNotFoundError:
        settings["piper_version"] = None
    return settings
