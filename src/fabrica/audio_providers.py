"""Segment audio providers and explicit authorization, independent of rendering."""

import json
import shutil
import wave
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from typing import Literal

from pydantic import ConfigDict, Field, field_validator

from .metadata import Contract, Resource
from .renderers.runtime import sha
from .tts import MockTTS, PiperTTS, duration
from .tts_registry import VoiceManifest

LATAM = {
    "es-419",
    "es_AR",
    "es_MX",
    "es_CL",
    "es_CO",
    "es_PE",
    "es_VE",
    "es_UY",
    "es_EC",
    "es_BO",
    "es_PY",
    "es_CR",
    "es_PR",
    "es_DO",
    "es_GT",
    "es_PA",
    "es_HN",
    "es_SV",
    "es_NI",
    "es_CU",
}


class NarrationBlocked(ValueError):
    def __init__(self, message, code="BLOCKED_VOICE_RIGHTS"):
        self.code = code
        super().__init__(f"{code}: {message}")


class NarrationConfig(Contract):
    model_config = ConfigDict(
        extra="forbid", frozen=True, allow_inf_nan=False, validate_default=True
    )
    provider: Literal["mock", "piper", "external"] = "mock"
    authorization_mode: Literal["test", "commercial"] = "test"
    voice_id: str | None = None
    voice_manifest: Path | None = None
    external_manifest: Path | None = None
    currency: Literal["ARS", "USD"] | None = None
    mock_seconds: float = Field(default=2.0, ge=0.1, le=30)
    mock_durations: dict[str, float] = Field(default_factory=dict)
    phrase_pause: float = Field(default=0.08, ge=0, le=3)
    scene_pause: float = Field(default=0.25, ge=0, le=5)
    max_seconds: float = Field(default=90, gt=0, le=180)
    sample_rate: Literal[48000] = 48000
    channels: Literal[1, 2] = 1
    piper_length_scale: float = Field(default=1, ge=0.5, le=2)
    timeout_seconds: int = Field(default=180, ge=1, le=600)
    subtitle_size: int = Field(default=44, ge=24, le=52)
    subtitle_margin: int = Field(default=400, ge=200, le=400)

    @field_validator("voice_manifest", "external_manifest")
    @classmethod
    def absolute(cls, value):
        return value.resolve() if value else None

    def identity(self):
        data = self.model_dump(mode="json")
        data["manifest_hashes"] = {
            str(p): sha(p) if p.is_file() else None
            for p in [self.voice_manifest, self.external_manifest]
            if p
        }
        # Media changes are distinct from manifest changes; never trust a stale declared SHA.
        if self.external_manifest and self.external_manifest.is_file():
            try:
                clips = json.loads(self.external_manifest.read_text()).get("clips", [])
                data["external_media_hashes"] = {
                    c["segment_id"]: sha(
                        resolve_asset(self.external_manifest, c["path"])
                    )
                    if resolve_asset(self.external_manifest, c["path"]).is_file()
                    else None
                    for c in clips
                }
            except (ValueError, KeyError, TypeError):
                data["external_media_hashes"] = {"invalid_manifest": True}
        return data


def resolve_asset(manifest_path, value):
    path = Path(value)
    return (
        path.resolve()
        if path.is_absolute()
        else (Path(manifest_path).parent / path).resolve()
    )


def inspect_wav(path):
    path = Path(path)
    try:
        seconds = duration(path)  # Reuses the existing complete PCM payload check.
        with wave.open(str(path), "rb") as wav:
            rate, channels, width, frames = (
                wav.getframerate(),
                wav.getnchannels(),
                wav.getsampwidth(),
                wav.getnframes(),
            )
            if (
                wav.getcomptype() != "NONE"
                or channels not in (1, 2)
                or width not in (1, 2, 3, 4)
                or not 8000 <= rate <= 96000
            ):
                raise ValueError("Unsupported PCM WAV format")
    except (wave.Error, EOFError, OSError) as exc:
        raise ValueError(f"Invalid or incomplete WAV: {path.name}") from exc
    return dict(
        duration=seconds,
        sample_rate=rate,
        channels=channels,
        sample_width=width,
        samples=frames,
        sha256=sha(path),
    )


class ExternalClip(Resource):
    segment_id: str
    spoken_text_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    regional_language: str
    authorized_by: str = Field(min_length=1)
    test_use_authorized: bool = False
    listening_approved: bool = False


class ExternalManifest(Contract):
    manifest_id: str
    clips: list[ExternalClip] = Field(min_length=1)


class ExternalAudio:
    """WAV assets selected explicitly by segment, never inferred commercial grants."""

    def __init__(self, manifest_path, mode="test"):
        self.path = Path(manifest_path).resolve()
        self.manifest = ExternalManifest.model_validate_json(self.path.read_text())
        self.clips = {c.segment_id: c for c in self.manifest.clips}
        if len(self.clips) != len(self.manifest.clips):
            raise ValueError("Duplicate external audio segment")
        self.mode = mode
        self.selected = None

    def authorize(self, segment_id, text_hash):
        if segment_id not in self.clips:
            raise ValueError(f"External WAV missing for segment {segment_id}")
        c = self.clips[segment_id]
        if c.regional_language not in LATAM or not c.evidence or not c.license:
            raise NarrationBlocked(
                "External recording provenance or es-419 variant missing"
            )
        if self.mode == "commercial" and not c.commercial_allowed:
            raise NarrationBlocked("External recording has no commercial permission")
        if self.mode == "test" and not (c.test_use_authorized or c.commercial_allowed):
            raise NarrationBlocked("External recording is not authorized for this test")
        if c.spoken_text_sha256 != text_hash:
            raise ValueError(
                "External transcript differs from the requested spoken segment"
            )
        path = resolve_asset(self.path, c.path)
        if not path.is_file() or sha(path) != c.sha256:
            raise ValueError(
                "External WAV hash differs from manifest; refresh authorization explicitly"
            )
        info = inspect_wav(path)
        return c, path, info

    def synthesize_segment(self, request, target):
        c, path, info = self.authorize(
            request["segment_id"], request["spoken_text_sha256"]
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".partial.wav")
        try:
            shutil.copyfile(path, temporary)
            inspect_wav(temporary)
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
        return info["duration"]

    def for_segment(self, segment_id, spoken_text_sha256):
        self.selected = (segment_id, spoken_text_sha256)
        return self

    def synthesize(self, text, path):
        import hashlib

        digest = hashlib.sha256(text.encode()).hexdigest()
        if self.selected is None or self.selected[1] != digest:
            raise ValueError(
                "Select a matching segment explicitly before ExternalAudio.synthesize"
            )
        return self.synthesize_segment(
            dict(segment_id=self.selected[0], spoken_text_sha256=digest), path
        )


def load_voice(config):
    if (
        not config.voice_id
        or not config.voice_manifest
        or not config.voice_manifest.is_file()
    ):
        raise NarrationBlocked(
            "Select an explicit voice ID and a verified VoiceManifest"
        )
    manifest = VoiceManifest.model_validate_json(config.voice_manifest.read_text())
    if manifest.voice_id != config.voice_id or manifest.provider != "piper":
        raise NarrationBlocked("Voice selection and manifest do not match Piper")
    if manifest.regional_language not in LATAM:
        raise NarrationBlocked(
            "es_ES or an unspecified Spanish voice cannot replace es-419"
        )
    if not manifest.technical_execution_allowed or not manifest.test_use_authorized:
        raise NarrationBlocked(
            "Technical permission and test authorization are separate and required"
        )
    if (
        manifest.rights_status == "BLOCKED"
        or not manifest.chain_complete
        or not all(link.verified for link in manifest.rights_chain)
    ):
        raise NarrationBlocked("Voice provenance chain is incomplete or blocked")
    if config.authorization_mode == "commercial" and not (
        manifest.rights_status == "APPROVED" and manifest.commercial_approved
    ):
        raise NarrationBlocked(
            "Commercial voice authorization and required approvals are missing"
        )
    for resource in manifest.artifacts:
        path = resolve_asset(config.voice_manifest, resource.path)
        if not path.is_file() or sha(path) != resource.sha256:
            raise NarrationBlocked("Voice artifact SHA-256 mismatch")
    if manifest.engine_version != version("piper-tts"):
        raise NarrationBlocked("Installed Piper version differs from VoiceManifest")
    models = [
        resolve_asset(config.voice_manifest, r.path)
        for r in manifest.artifacts
        if r.path.endswith(".onnx")
    ]
    if len(models) != 1:
        raise NarrationBlocked("Manifest must identify exactly one Piper ONNX model")
    # The established adapter still checks its local technical-license sidecar.
    required = {str(models[0]) + ".json", str(models[0]) + ".license.json"}
    if not required <= {
        str(resolve_asset(config.voice_manifest, r.path)) for r in manifest.artifacts
    }:
        raise NarrationBlocked(
            "Config and local permission sidecar must also be hashed artifacts"
        )
    return manifest, models[0]


@dataclass
class ProviderBundle:
    provider: object
    provenance: dict


def create_audio_provider(config):
    if config.provider == "mock":
        if config.authorization_mode == "commercial":
            raise NarrationBlocked("MOCK tones cannot authorize a commercial narration")
        return ProviderBundle(
            MockTTS(config.mock_seconds),
            dict(
                provider="mock",
                voice_id=None,
                model=None,
                authorization="MOCK_TEST_ONLY",
                commercial_allowed=False,
                human_listening_approved=False,
            ),
        )
    if config.provider == "external":
        if not config.external_manifest or not config.external_manifest.is_file():
            raise NarrationBlocked(
                "An explicit owner-authorized external segment manifest is required"
            )
        external = ExternalAudio(config.external_manifest, config.authorization_mode)
        return ProviderBundle(
            external,
            dict(
                provider="external",
                manifest_sha256=sha(config.external_manifest),
                manifest_id=external.manifest.manifest_id,
                authorization="PER_SEGMENT_EXPLICIT",
            ),
        )
    voice, model = load_voice(config)
    provider = PiperTTS(
        model=model,
        scale=config.piper_length_scale,
        timeout=config.timeout_seconds,
        currency=config.currency,
        normalized=True,
        api_only=True,
    )
    return ProviderBundle(
        provider,
        dict(
            provider="piper",
            engine_version=voice.engine_version,
            voice_id=voice.voice_id,
            model=voice.model_version,
            regional_language=voice.regional_language,
            manifest_sha256=sha(config.voice_manifest),
            authorization=voice.rights_status,
            commercial_allowed=voice.commercial_approved,
            human_listening_approved=voice.listening_approved,
            artifacts=[r.model_dump(mode="json") for r in voice.artifacts],
        ),
    )
