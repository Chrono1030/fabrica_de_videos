import pytest

from fabrica.factory_store import FactoryStore
from fabrica.metadata import Resource, sha256
from fabrica.tts import MockTTS, duration
from fabrica.tts_registry import (
    LicenseLink,
    VoiceManifest,
    create_provider,
    register_voice,
)


def test_registry_requires_chain_for_commercial_use(tmp_path):
    path = tmp_path / "test-model"
    path.write_bytes(b"fixture-not-real-model")
    manifest = VoiceManifest(
        voice_id="fixture",
        provider="kokoro",
        engine_version="test",
        engine_license="Apache-2.0",
        model_version="test",
        regional_language="es",
        artifacts=[
            Resource(
                path=str(path),
                sha256=sha256(path),
                source="fixture",
                license="fixture",
                evidence=["unit test"],
            )
        ],
        rights_chain=[
            LicenseLink(
                name="undocumented dataset", license="unknown", evidence=["test"]
            )
        ],
    )
    store = FactoryStore(tmp_path / "factory.sqlite3")
    register_voice(store, manifest)
    with pytest.raises(ValueError, match="Cadena comercial"):
        VoiceManifest.model_validate(
            manifest.model_dump() | {"commercial_approved": True}
        )
    path.write_bytes(b"changed")
    with pytest.raises(ValueError, match="Hash"):
        register_voice(store, manifest)


def test_provider_boundary_preserves_mock(tmp_path):
    provider = create_provider("mock", mock_seconds=0.2)
    assert isinstance(provider, MockTTS)
    provider.synthesize("ARS 25 y 5%", tmp_path / "sample.wav")
    assert duration(tmp_path / "sample.wav") == 0.2
    with pytest.raises(ValueError, match="Kokoro no habilitado"):
        create_provider("kokoro")
