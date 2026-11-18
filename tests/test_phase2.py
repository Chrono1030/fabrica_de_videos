import hashlib
import json
import subprocess
import sys
from types import SimpleNamespace

import pytest

from fabrica import tts
from fabrica.normalization import normalize


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("12,5%", "doce coma cinco por ciento"),
        ("ARS $1.250,50", "mil doscientos cincuenta coma cinco cero pesos argentinos"),
        ("25 USD", "veinticinco dólares estadounidenses"),
        ("USD 10.25", "diez coma dos cinco dólares estadounidenses"),
        ("17/11/2026", "diecisiete de noviembre de dos mil veintiséis"),
        ("PIB e IPC", "producto interno bruto e índice de precios al consumidor"),
        ("5 kg", "cinco kilogramos"),
        ("1.250 personas", "mil doscientos cincuenta personas"),
    ],
)
def test_normalize(source, expected):
    assert normalize(source) == expected


def test_currency_context_and_invalid_date():
    with pytest.raises(ValueError, match="ambiguo"):
        normalize("$25")
    assert normalize("$25", "ARS") == "veinticinco pesos argentinos"
    assert normalize("$25", "USD") == "veinticinco dólares estadounidenses"
    with pytest.raises(ValueError):
        normalize("31/02/2026")
    assert normalize("PIBfinal") == "PIBfinal"


def model_fixture(tmp_path, monkeypatch):
    model = tmp_path / "voice.onnx"
    model.write_bytes(b"double")
    (tmp_path / "voice.onnx.json").write_text('{"language":{"code":"es_MX"}}')
    monkeypatch.setenv("PIPER_VOICE_MODEL", str(model))
    monkeypatch.setenv("PIPER_EXECUTABLE", "fake-piper")
    manifest = {
        "sha256": hashlib.sha256(model.read_bytes()).hexdigest(),
        "license": "fixture only",
        "evidence": ["test"],
        "approved_local_use": True,
    }
    (tmp_path / "voice.onnx.license.json").write_text(json.dumps(manifest))
    return model


def test_piper_failure_atomic_and_license(tmp_path, monkeypatch):
    model = model_fixture(tmp_path, monkeypatch)
    target = tmp_path / "audio.wav"
    tts.MockTTS(0.2).synthesize("", target)
    original = target.read_bytes()

    def fail(args, **kwargs):
        (tmp_path / "audio.partial.wav").write_bytes(b"broken")
        raise subprocess.TimeoutExpired(args, 1)

    monkeypatch.setattr(tts.subprocess, "run", fail)
    with pytest.raises(subprocess.TimeoutExpired):
        tts.PiperTTS().synthesize("hola", target)
    assert target.read_bytes() == original
    assert not (tmp_path / "audio.partial.wav").exists()
    model.write_bytes(b"changed")
    with pytest.raises(RuntimeError, match="Licencia"):
        tts.PiperTTS().synthesize("hola", target)


def test_truncated_wav(tmp_path):
    path = tmp_path / "truncated.wav"
    tts.MockTTS(0.2).synthesize("", path)
    path.write_bytes(path.read_bytes()[:-100])
    with pytest.raises(ValueError, match="incompleto"):
        tts.duration(path)


def test_python_api_reuses_voice(tmp_path, monkeypatch):
    loads, configs = [], []

    class Voice:
        @staticmethod
        def load(model):
            loads.append(model)
            return Voice()

        def synthesize_wav(self, text, wav_file, syn_config):
            configs.append(syn_config)
            wav_file.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
            wav_file.writeframes(b"\0\0" * 3200)

    monkeypatch.setitem(
        sys.modules,
        "piper",
        SimpleNamespace(PiperVoice=Voice, SynthesisConfig=lambda **kw: kw),
    )

    class Connection:
        def __init__(self):
            self.requests = iter(
                [
                    ("uno", str(tmp_path / "a.wav")),
                    ("dos", str(tmp_path / "b.wav")),
                    None,
                ]
            )
            self.results = []

        def recv(self):
            return next(self.requests)

        def send(self, result):
            self.results.append(result)

        def close(self):
            pass

    conn = Connection()
    tts._piper_worker(conn, "fixture.onnx", 1.1)
    assert loads == ["fixture.onnx"]
    assert configs == [{"length_scale": 1.1}] * 2
    assert conn.results == [(True, 0.2), (True, 0.2)]


def test_native_invalid_model(tmp_path, monkeypatch):
    pytest.importorskip("piper")
    model_fixture(tmp_path, monkeypatch)
    monkeypatch.delenv("PIPER_EXECUTABLE")
    provider = tts.PiperTTS()
    with pytest.raises(RuntimeError, match="Piper:"):
        provider.synthesize("hola", tmp_path / "audio.wav")
    assert provider.process is None
    assert not (tmp_path / "audio.partial.wav").exists()


def test_local_requires_script_and_no_api(tmp_path, monkeypatch):
    from fabrica import pipeline

    def forbidden(*args, **kwargs):
        pytest.fail("La producción local no debe usar GPT")

    monkeypatch.setattr(pipeline, "generate_checked", forbidden)
    with pytest.raises(ValueError, match="requiere --script"):
        pipeline.produce("Costo", mode="local", root=tmp_path, renderer="legacy")
    script = tmp_path / "script.json"
    script.write_text(pipeline.mock_script("Costo").model_dump_json())
    monkeypatch.setattr(pipeline, "PiperTTS", lambda: tts.MockTTS(0.2))
    with pytest.raises(ValueError, match="60–90"):
        pipeline.produce(
            "Costo", mode="local", root=tmp_path, script_path=script, renderer="legacy"
        )


def test_fingerprint_tracks_model_bytes(tmp_path, monkeypatch):
    model = model_fixture(tmp_path, monkeypatch)
    before = tts.piper_fingerprint()
    model.write_bytes(b"new model")
    assert before != tts.piper_fingerprint()


def test_worker_timeout_cleans_up(tmp_path, monkeypatch):
    import multiprocessing

    model_fixture(tmp_path, monkeypatch)
    monkeypatch.delenv("PIPER_EXECUTABLE")

    class Connection:
        def send(self, request):
            tts.MockTTS(0.2).synthesize("", tmp_path / "audio.partial.wav")

        def poll(self, timeout):
            return False

        def close(self):
            pass

    class Process:
        stopped = False

        def __init__(self, **kwargs):
            pass

        def start(self):
            pass

        def terminate(self):
            Process.stopped = True

        def join(self, timeout):
            pass

    monkeypatch.setattr(
        multiprocessing,
        "get_context",
        lambda _: SimpleNamespace(
            Pipe=lambda: (Connection(), Connection()), Process=Process
        ),
    )
    provider = tts.PiperTTS()
    with pytest.raises(TimeoutError):
        provider.synthesize("hola", tmp_path / "audio.wav")
    assert Process.stopped and provider.process is None
    assert not (tmp_path / "audio.partial.wav").exists()
    assert not (tmp_path / "audio.wav").exists()
