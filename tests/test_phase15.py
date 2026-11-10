import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher

import pytest

from fabrica.catalog import Catalog
from fabrica.editorial import review
from fabrica.pipeline import mock_script, produce, produce_auto
from fabrica.render import subtitles
from fabrica.subtitle_style import SubtitleStyle, cues


def test_catalog_persistent_atomic_reservation(tmp_path):
    path = tmp_path / "catalog.sqlite3"
    catalog = Catalog(path)
    catalog.seed()
    catalog.seed()
    with catalog.connect() as db:
        assert db.execute("SELECT count(*) FROM topics").fetchone()[0] == 50
    with ThreadPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(lambda i: Catalog(path).reserve(f"job-{i}"), range(20)))
    assert len({r["id"] for r in rows}) == 20
    assert Catalog(path).reserve("job-0")["id"] == rows[0]["id"]
    catalog.finish("job-0", "BLOCKED", {"reason": "test"})
    assert catalog.reserve("job-0")["state"] == "BLOCKED"
    catalog.finish("job-0", "TECHNICALLY_READY", {})
    with catalog.connect() as db:
        assert (
            db.execute("SELECT count(*) FROM history WHERE job_id='job-0'").fetchone()[
                0
            ]
            == 3
        )


def test_editorial_history_and_reasons(tmp_path):
    catalog = Catalog(tmp_path / "db.sqlite3")
    a = mock_script("Costo de oportunidad")
    assert not catalog.review("a", a)
    assert not catalog.review("a", a)  # idempotencia
    assert any("duplicado" in s for s in catalog.review("b", a))
    a.references = ["Autor imaginario. Libro inexistente."]
    a.scenes[0].narration += " Ganancias garantizadas de 50%."
    a.scenes[0].visual_label = "Datos reales"
    issues = review(a)
    assert any("Referencias" in s for s in issues)
    assert any("numéricos" in s for s in issues)
    assert any("Promesa" in s for s in issues)
    a.scenes[2].visual_data = ["sin magnitud"]
    assert any("incompatible" in s for s in review(a))


def test_subtitle_cues_timing_and_style(tmp_path):
    script = mock_script("Costo")
    target = tmp_path / "s.srt"
    subtitles(script.scenes, [4] * 4, target)
    blocks = target.read_text().strip().split("\n\n")
    assert blocks[0].splitlines()[1].startswith("00:00:00,000")
    assert blocks[-1].splitlines()[1].endswith("00:00:16,000")
    assert all(1 <= len(b.splitlines()[2:]) <= 2 for b in blocks)
    assert all(len(line) <= 34 for b in blocks for line in b.splitlines()[2:])
    assert "".join(cues("palabra " * 40)).count("palabra") == 40
    with pytest.raises(ValueError):
        SubtitleStyle(margin=1000)
    with pytest.raises(ValueError):
        SubtitleStyle(font="x':bad")


def test_burned_subtitles_change_pixels_and_track_mode(tmp_path):
    a = produce("Costo", root=tmp_path / "a", width=180, height=320, mock_seconds=0.5)
    b = produce(
        "Costo",
        root=tmp_path / "b",
        width=180,
        height=320,
        mock_seconds=0.5,
        subtitle_style=SubtitleStyle(burn=False),
    )

    def frame(path):
        return subprocess.check_output(
            [
                "ffmpeg",
                "-v",
                "error",
                "-ss",
                "0.25",
                "-i",
                str(path / "final.mp4"),
                "-frames:v",
                "1",
                "-vf",
                "crop=180:90:0:210",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgb24",
                "-",
            ]
        )

    assert frame(a) != frame(b)
    assert "PlayResY: 1920" in (a / "burn.ass").read_text()
    assert json.loads((a / "result.json").read_text())["quality"]["decoded"]


def test_distinct_demos_and_animation(tmp_path):
    from PIL import Image, ImageChops

    from fabrica.cards import make_card

    a = mock_script("Por qué ganar más no significa ahorrar más")
    b = mock_script("El costo de oportunidad")
    assert not review(a) and not review(b)
    assert SequenceMatcher(None, a.model_dump_json(), b.model_dump_json()).ratio() < 0.8
    for scene in (a.scenes[0], b.scenes[3]):
        p, q = tmp_path / "p.png", tmp_path / "q.png"
        make_card(scene, 1, 4, p, progress=0)
        make_card(scene, 1, 4, q, progress=1)
        assert ImageChops.difference(Image.open(p), Image.open(q)).getbbox()


def test_autonomous_production_and_retry(tmp_path):
    path = tmp_path / "catalog.sqlite3"
    job = produce_auto(
        path,
        root=tmp_path / "jobs",
        job_id="auto",
        width=180,
        height=320,
        mock_seconds=0.2,
    )
    assert Catalog(path).reserve("auto")["state"] == "TECHNICALLY_READY"
    assert (
        produce_auto(
            path,
            root=tmp_path / "jobs",
            job_id="auto",
            width=180,
            height=320,
            mock_seconds=0.2,
        )
        == job
    )
