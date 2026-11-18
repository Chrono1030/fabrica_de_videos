"""Registro local de procedencia; no descarga modelos ni concede derechos."""

from typing import Literal

from pydantic import Field, model_validator

from .metadata import Contract, Resource, sha256
from .tts import TTS, MockTTS, PiperTTS


class LicenseLink(Contract):
    name: str = Field(min_length=1)
    license: str = Field(min_length=1)
    evidence: list[str] = Field(min_length=1)
    commercial_allowed: bool = False
    verified: bool = False


class VoiceManifest(Contract):
    voice_id: str
    provider: Literal["piper", "kokoro"]
    engine_version: str
    engine_license: str
    model_version: str
    regional_language: str
    artifacts: list[Resource] = Field(min_length=1)
    # Include engine, weights, voice embedding, own dataset and every training base.
    rights_chain: list[LicenseLink] = Field(min_length=1)
    chain_complete: bool = False
    reviewed_by: str | None = None
    reviewed_at: str | None = None
    listening_approved: bool = False
    commercial_approved: bool = False
    # Separate execution permission, rights research and listening review.
    technical_execution_allowed: bool = False
    test_use_authorized: bool = False
    rights_status: Literal["APPROVED", "RESEARCH_ONLY", "BLOCKED"] = "BLOCKED"
    source_url: str | None = None
    attribution: list[str] = []
    restrictions: list[str] = []

    @model_validator(mode="after")
    def approval_needs_evidence(self):
        if self.commercial_approved and not (
            self.chain_complete
            and self.reviewed_by
            and self.reviewed_at
            and self.listening_approved
            and self.regional_language.startswith("es_")
            and self.regional_language != "es_ES"
            and all(a.commercial_allowed for a in self.artifacts)
            and all(
                link.verified and link.commercial_allowed for link in self.rights_chain
            )
        ):
            raise ValueError(
                "Cadena comercial, variante regional o aprobación auditiva pendiente"
            )
        return self


def register_voice(store, manifest):
    manifest = VoiceManifest.model_validate(manifest.model_dump())
    for asset in manifest.artifacts:
        if sha256(asset.path) != asset.sha256:
            raise ValueError("Hash del modelo o voz incorrecto")
    with store.connect() as db:
        db.execute(
            "CREATE TABLE IF NOT EXISTS tts_models (voice_id TEXT PRIMARY KEY, manifest TEXT NOT NULL)"
        )
        previous = db.execute(
            "SELECT manifest FROM tts_models WHERE voice_id=?", (manifest.voice_id,)
        ).fetchone()
        if previous and previous["manifest"] != manifest.model_dump_json():
            raise ValueError("Versión de voz ya registrada; usar otro identificador")
        db.execute(
            "INSERT OR IGNORE INTO tts_models VALUES(?,?)",
            (manifest.voice_id, manifest.model_dump_json()),
        )


def create_provider(provider="mock", *, mock_seconds=1.0) -> TTS:
    if provider == "mock":
        return MockTTS(mock_seconds)
    if provider == "piper":
        return PiperTTS()
    if provider == "kokoro":
        raise ValueError(
            "Kokoro no habilitado: procedencia de voces y variante regional pendientes"
        )
    raise ValueError("Proveedor TTS desconocido")
