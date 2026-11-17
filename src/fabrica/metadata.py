"""Paquetes deterministas de Mente y Capital; no llaman a servicios externos."""

import hashlib
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .editorial import UNSAFE_PROMISES, check
from .models import VideoScript


class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)


class Resource(Contract):
    path: str
    sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    source: str = Field(min_length=1)
    license: str = Field(min_length=1)
    commercial_allowed: bool = False
    evidence: list[str] = Field(min_length=1)


class Inspiration(Contract):
    source_id: str
    work_or_url: str
    author: str
    general_idea: str
    consulted_at: str
    evidence: list[str]


class Originality(Contract):
    question: str = Field(min_length=10)
    own_development: str = Field(min_length=20)
    original_example: str = Field(min_length=20)
    economic_relationship: str = Field(min_length=20)
    practical_conclusion: str = Field(min_length=20)
    inspirations: list[Inspiration] = []
    claims_pending: list[str] = []
    reviewer: str | None = None
    approved: bool = False
    # MOCK is a technical exercise, never an editorial approval for real uploads.
    simulated_review: bool = True


class PublicationPackage(Contract):
    job_id: str = Field(pattern=r'^[A-Za-z0-9_-]+$')
    brand: Literal['Mente y Capital'] = 'Mente y Capital'
    platform: Literal['youtube'] = 'youtube'
    channel_id: str = Field(min_length=1)
    title: str = Field(min_length=5, max_length=100)
    description: str = Field(min_length=30, max_length=5000)
    hashtags: list[str] = Field(min_length=1, max_length=5)
    tags: list[str] = Field(max_length=15)
    default_language: Literal['es-419'] = 'es-419'
    category_id: str = Field(pattern=r'^\d+$')
    editorial_category: str
    made_for_kids: bool
    audience_reason: str = Field(min_length=10)
    contains_synthetic_media: bool
    synthetic_reason: str = Field(min_length=10)
    privacy: Literal['private'] = 'private'
    duration_seconds: float = Field(gt=0, le=180, allow_inf_nan=False)
    video_path: str
    asset_hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    script_hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    thumbnail_path: str
    resources: list[Resource] = Field(min_length=1)
    source_credits: list[str]
    originality: Originality
    simulated: bool = True
    publication_policy_version: Literal['integrated-1'] = 'integrated-1'

    @model_validator(mode='after')
    def safe(self):
        body = (self.title + ' ' + self.description).lower()
        if any(re.search(p, body, re.I) for p in UNSAFE_PROMISES):
            raise ValueError('Metadatos con promesa engañosa')
        if '<' in self.title or '>' in self.title:
            raise ValueError('Título incompatible con YouTube')
        if len(set(self.hashtags)) != len(self.hashtags) or any(
            not re.fullmatch(r'#[\w]+', tag) for tag in self.hashtags
        ):
            raise ValueError('Hashtags inválidos o repetidos')
        if not self.simulated and not all(r.commercial_allowed for r in self.resources):
            raise ValueError('Licencias comerciales pendientes')
        return self

    def youtube_body(self):
        return {
            'snippet': {'title': self.title, 'description': self.description,
                        'tags': self.tags, 'categoryId': self.category_id,
                        'defaultLanguage': self.default_language},
            'status': {'privacyStatus': 'private',
                       'selfDeclaredMadeForKids': self.made_for_kids,
                       'containsSyntheticMedia': self.contains_synthetic_media},
        }


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def script_hash(script):
    return hashlib.sha256(script.model_dump_json().encode()).hexdigest()


def generate_package(script: VideoScript, *, job_id, channel_id, video_path,
                     thumbnail_path, category, category_id, duration, resources,
                     originality, made_for_kids, audience_reason, synthetic,
                     synthetic_reason, simulated=True):
    if issues := check(script):
        raise ValueError('; '.join(issues))
    # Extractive summary preserves the actual explanation and its original example.
    description = (f'Mente y Capital | {script.topic}\n\n{script.hook}\n\n'
                   f'{script.scenes[0].narration}\n\n{script.scenes[-1].narration}\n\n'
                   f'{script.disclaimer}')
    if script.references:
        description += '\n\nFuentes declaradas:\n' + '\n'.join(script.references)
    hashtags = ['#MenteYCapital', '#EconomíaCotidiana']
    if 'productiv' in category.lower():
        hashtags[-1] = '#Productividad'
    description += '\n\n' + ' '.join(hashtags)
    return PublicationPackage(
        job_id=job_id, channel_id=channel_id, title=script.title,
        description=description, hashtags=hashtags, tags=[category, script.topic],
        editorial_category=category, category_id=category_id,
        made_for_kids=made_for_kids, audience_reason=audience_reason,
        contains_synthetic_media=synthetic, synthetic_reason=synthetic_reason,
        duration_seconds=duration, video_path=str(Path(video_path).resolve()),
        asset_hash=sha256(video_path), script_hash=script_hash(script),
        thumbnail_path=str(Path(thumbnail_path).resolve()), resources=resources,
        source_credits=script.references, originality=originality, simulated=simulated,
    )


def validate_correspondence(package, script):
    """Extractive MOCK contract: generated text cannot invent supporting sources."""
    if package.script_hash != script_hash(script) or package.title != script.title:
        raise ValueError('El paquete no corresponde al guion')
    if package.source_credits != script.references:
        raise ValueError('Fuentes distintas del guion')
    for scene in (script.scenes[0], script.scenes[-1]):
        if scene.narration not in package.description:
            raise ValueError('Descripción no corresponde al contenido')
