import sqlite3
from pathlib import Path

import pytest
from pydantic import ValidationError

from fabrica.factory_store import FactoryStore
from fabrica.metadata import (
    Originality,
    Resource,
    generate_package,
    sha256,
    validate_correspondence,
)
from fabrica.models import VideoScript


@pytest.fixture
def script():
    return VideoScript.model_validate_json(Path('examples/costo_oportunidad.json').read_text())


@pytest.fixture
def package(tmp_path, script):
    video = tmp_path / 'video.mp4'
    video.write_bytes(b'unit-test-media')
    cover = tmp_path / 'cover.png'
    cover.write_bytes(b'unit-test-cover')
    return generate_package(
        script, job_id='test', channel_id='MOCK_CHANNEL', video_path=video,
        thumbnail_path=cover, category='Economía cotidiana', category_id='27',
        duration=75, resources=[Resource(path=str(video), sha256=sha256(video),
        source='fixture', license='test-only', evidence=['fixture'])], originality=Originality(
            question=script.hook, own_development=script.scenes[1].narration,
            original_example=script.scenes[2].narration,
            economic_relationship=script.scenes[3].narration,
            practical_conclusion=script.scenes[-1].narration),
        made_for_kids=False, audience_reason='Ensayo para público adulto; requiere revisión.',
        synthetic=False, synthetic_reason='Gráficos abstractos y tonos MOCK, sin imitación realista.')


def test_package_deterministic_and_private(package, script):
    validate_correspondence(package, script)
    body = package.youtube_body()
    assert body['status']['privacyStatus'] == 'private'
    assert 'Mente y Capital' in package.description
    assert package.source_credits == []
    assert package.model_dump_json() == package.model_dump_json()


@pytest.mark.parametrize('change', [
    {'privacy': 'public'}, {'title': 'Rentabilidad garantizada para todos'},
    {'hashtags': ['#x', '#x']}, {'default_language': 'es-ES'},
])
def test_reject_unsafe(package, change):
    with pytest.raises(ValidationError):
        type(package).model_validate(package.model_dump() | change)


def test_correspondence_and_duplicate_metadata(package, script, tmp_path):
    with pytest.raises(ValueError, match='Fuentes'):
        validate_correspondence(package.model_copy(update={'source_credits': ['inventada']}), script)
    store = FactoryStore(tmp_path / 'state.sqlite3')
    store.save_package(package)
    store.save_package(package)
    with pytest.raises(sqlite3.IntegrityError):
        store.save_package(package.model_copy(update={'job_id': 'other'}))
    assert store.package(package.job_id) == package
