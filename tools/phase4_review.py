"""Build read-only Phase 4 delivery evidence from an existing integrated job.

This does not produce jobs, synthesize audio, render visuals or publish anything.
"""

import argparse
import html
import json
import os
import sqlite3
from pathlib import Path

from fabrica.audio_providers import inspect_wav
from fabrica.renderers.runtime import RendererConfig, command, sha


def build(job, output):
    job, output = job.resolve(), output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    from fabrica.narration_timeline import NarrationTimeline
    from fabrica.visual_storyboard import VisualStoryboard

    state = json.loads((job / "result.json").read_text())
    timeline = json.loads((job / "narration_timeline.json").read_text())
    NarrationTimeline.model_validate(timeline)
    board = VisualStoryboard.model_validate_json(
        (job / "base_storyboard.json").read_text()
    )
    for scene in board.scenes:
        reconstructed = " ".join(
            s["editorial_text"]
            for s in timeline["segments"]
            if s["scene_id"] == scene.id
        )
        if " ".join(scene.narrative.split()) != reconstructed:
            raise ValueError("Narration changed the original editorial text")
    for segment in timeline["segments"]:
        if (
            sha(Path(segment["wav"])) != segment["sha256"]
            or sha(Path(segment["raw_wav"])) != segment["raw_sha256"]
        ):
            raise ValueError("Segment audio hash changed")
        if inspect_wav(segment["wav"])["samples"] != segment["samples"]:
            raise ValueError("Segment samples differ from narration timeline")
    render = json.loads((job / "render.json").read_text())
    qa = json.loads((job / "qa.json").read_text())
    publication = json.loads((job / "publication.json").read_text())
    if (
        publication.get("real_upload") is not False
        or publication.get("simulated") is not True
    ):
        raise ValueError("This review accepts only a verified MOCK publication receipt")
    manifest = json.loads((job / "manifest.json").read_text())
    for name, entry in manifest["artifacts"].items():
        if sha(job / name) != entry["sha256"]:
            raise ValueError("Artifact changed: " + name)
    before = json.loads((output / "before-retry.json").read_text())
    reused = all(
        sha(job / name) == entry["sha256"]
        and (job / name).stat().st_mtime_ns == entry["mtime_ns"]
        for name, entry in before.items()
    )
    database = job.parent.parent / "state.sqlite3"
    with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as db:
        metrics = json.loads(
            db.execute(
                "SELECT record FROM metrics WHERE job_id=?", (job.name,)
            ).fetchone()[0]
        )
        remote = db.execute("SELECT count(*) FROM mock_remote").fetchone()[0]
        jobs = db.execute(
            "SELECT count(*) FROM calendar WHERE job_id=?", (job.name,)
        ).fetchone()[0]
    if not reused or jobs != 1 or remote != 1:
        raise ValueError(
            "Recovery did not preserve one job, one MOCK publication and unchanged artifacts"
        )
    with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as db:
        calendar_state = db.execute(
            "SELECT state FROM calendar WHERE job_id=?", (job.name,)
        ).fetchone()[0]
    if calendar_state != "SIMULATED_DONE":
        raise ValueError("Calendar cycle is incomplete")
    previous = json.loads((output / "preserved.json").read_text())
    preserved = {
        p: Path(p).is_file() and sha(Path(p)) == digest
        for p, digest in previous.items()
    }
    if not all(preserved.values()):
        raise ValueError("A previous delivered video changed")
    config = RendererConfig.model_validate(state["config"]["rendering"])
    frames = output / "frames"
    frames.mkdir(exist_ok=True)
    timestamps = []
    for i, span in enumerate(timeline["scene_spans"]):
        group = [s for s in timeline["segments"] if s["scene_id"] == span["scene_id"]]
        segment = group[len(group) // 2]
        stamp = (segment["start"] + segment["end"]) / 2
        timestamps.append(stamp)
        command(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-ss",
                str(stamp),
                "-i",
                job / "final.mp4",
                "-frames:v",
                "1",
                "-vf",
                "scale=360:-1",
                "-update",
                "1",
                frames / f"frame-{i + 1:02}.png",
            ],
            config=config,
            directory=output,
        )
    command(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-pattern_type",
            "glob",
            "-i",
            str(frames / "frame-*.png"),
            "-vf",
            f"tile={len(timestamps)}x1",
            "-frames:v",
            "1",
            "-update",
            "1",
            output / "contact-sheet.png",
        ],
        config=config,
        directory=output,
    )
    raw = json.loads((job / "audio_segments.json").read_text())
    report = dict(
        phase=4,
        job=str(job),
        status=calendar_state,
        publication_state=publication["state"],
        publish_ready=False,
        result_a="PASS_MOCK_TECHNICAL",
        result_b=json.loads((output / "real_voice/result.json").read_text()),
        original_script_sha256=sha(job / "script.json"),
        storyboard_sha256=sha(job / "visual_storyboard.json"),
        artifacts=manifest["artifacts"],
        quality=qa,
        narration=dict(
            provider="mock",
            human_voice=False,
            segments=len(timeline["segments"]),
            scenes=len(timeline["scene_spans"]),
            wav=inspect_wav(job / "narration.wav"),
            duration=timeline["duration"],
            phonetic_alignment=False,
            alignment=timeline["alignment"],
            synthesis_wall_seconds=sum(
                r["synthesis_wall_seconds"] for r in raw["segments"]
            ),
            implementation_sha256=state["config"]["narration"]["implementation_sha256"],
        ),
        performance=dict(
            factory=metrics,
            native={
                k: render[k]
                for k in (
                    "render_wall_seconds",
                    "cpu_seconds",
                    "peak_process_tree_rss_mib",
                    "peak_individual_rss_mib",
                    "memory_method",
                )
            },
            composition_wall_including_qa_seconds=qa["composition_wall_seconds"],
            composition_command_cpu_seconds=qa["composition_cpu_seconds"],
            composition_child_high_water_kib=qa["children_max_rss_kib"],
            ram_scope_note=qa["max_rss_scope"],
        ),
        dependencies=dict(
            engine=render["engine_version"],
            native_receipt=str(job / "render.json"),
            runtime=render.get("versions"),
            fingerprints=render["dependencies"],
        ),
        costs=dict(
            api_calls=metrics["api_calls"],
            api_usd=metrics["production_cost_usd"],
            electricity_or_hardware_cost_measured=False,
        ),
        recovery=dict(
            same_job=jobs == 1,
            unchanged_hashes_and_mtimes=reused,
            native_attempts=len(list((job / "render").glob("attempt-*"))),
            composition_attempts=len(list((job / "composition").iterdir())),
            mock_remote_count=remote,
            real_upload=publication["real_upload"],
        ),
        preserved_previous_videos=preserved,
        tests=dict(
            pytest=(output / "checks/pytest.txt").read_text().strip().splitlines()[-1],
            ruff=(output / "checks/ruff.txt").read_text().strip(),
        ),
        contact_sheet_timestamps=timestamps,
        viewer_check=json.loads((output / "viewer-smoke.json").read_text())
        if (output / "viewer-smoke.json").exists()
        else None,
        limitations=[
            "MOCK tones are not intelligible narration",
            "Phrase-level measured alignment; no word phonetic alignment",
            "Human content, voice, rights, pronunciation and device review still required",
            "Real voice blocked, not a failure of the technical MOCK pipeline",
        ],
    )
    (output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    relative = Path(os.path.relpath(job, output)).as_posix()
    links = " · ".join(
        f'<a href="{html.escape(relative + "/" + name)}">{html.escape(name)}</a>'
        for name in (
            "final.mp4",
            "narration.wav",
            "narration_timeline.json",
            "visual_storyboard.json",
            "video_silent.mp4",
            "subtitles.srt",
            "subtitles.ass",
            "qa.json",
            "manifest.json",
        )
    )
    data = json.dumps(timeline["segments"], ensure_ascii=False).replace("<", r"\u003c")
    page = """<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Fase 4 · Mente y Capital</title>
<style>body{background:#112037;color:#f6eedb;font:17px system-ui;margin:24px}a{color:#e6b864}main{display:flex;gap:28px;flex-wrap:wrap}video{width:min(360px,90vw);max-height:78vh}section{max-width:760px;flex:1;min-width:280px}button,input{font:inherit}button{margin:4px;padding:8px;color:#112037;background:#e6b864;border:0;border-radius:4px;cursor:pointer}input{width:100%}li{margin:12px 0}#caption{min-height:3em;white-space:pre-line;background:#182b40;padding:15px;text-align:center}.active{outline:2px solid #e6b864}p{line-height:1.5}small{color:#9cb0c4}</style>
<h1>Mente y Capital · Fase 4</h1><p>Ensayo técnico MOCK: tonos, sin voz humana. Subtítulos quemados. Revisión humana pendiente; publicación real deshabilitada.</p>
<main><video id="video" controls preload="metadata" src="VIDEO"></video><section><h2>Audio medido y subtítulos</h2><button id="toggle">Reproducir / pausar</button><button id="home">Inicio</button><p id="time"></p><input id="seek" aria-label="Marca temporal" type="range" min="0" max="DURATION" step="0.01" value="0"><p id="caption"></p><small>El texto auxiliar muestra el cue de la timeline. El video conserva los subtítulos aunque se abra en otro reproductor. No hay alineación fonética por palabra.</small><ol id="segments"></ol></section></main><p>LINKS</p><p><a href="report.json">Reporte JSON</a> · <a href="report.md">Informe</a> · <a href="voice_audit.json">Auditoría</a> · <a href="contact-sheet.png">Fotogramas</a></p>
<script>const segments=DATA;const v=document.getElementById('video'),seek=document.getElementById('seek'),caption=document.getElementById('caption'),clock=document.getElementById('time');v.volume=.25;document.getElementById('toggle').onclick=()=>v.paused?v.play().catch(e=>clock.textContent=e.message):v.pause();document.getElementById('home').onclick=()=>{v.pause();v.currentTime=0};seek.oninput=()=>{v.currentTime=Number(seek.value)};const list=document.getElementById('segments');segments.forEach(s=>{const li=document.createElement('li'),b=document.createElement('button'),label=document.createElement('span');b.textContent=s.start.toFixed(2)+'–'+s.end.toFixed(2)+' s';b.onclick=()=>{v.currentTime=s.start;v.play().catch(e=>clock.textContent=e.message)};label.textContent=s.subtitle_text.replaceAll('\\n',' ');const details=document.createElement('details'),sum=document.createElement('summary'),p=document.createElement('p');sum.textContent=s.segment_id+' · texto hablado';p.textContent=s.spoken_text;details.append(sum,p);li.append(b,label,details);list.append(li)});function update(){seek.value=v.currentTime;clock.textContent=v.currentTime.toFixed(2)+' / '+v.duration.toFixed(2)+' s';const index=segments.findIndex(s=>s.start<=v.currentTime&&v.currentTime<s.end);caption.textContent=index<0?'Pausa registrada':segments[index].subtitle_text;[...list.children].forEach((li,i)=>li.classList.toggle('active',i===index))}v.addEventListener('timeupdate',update);v.addEventListener('loadedmetadata',update);</script></html>"""
    page = (
        page.replace("VIDEO", html.escape(relative + "/final.mp4"))
        .replace("DURATION", str(timeline["duration"]))
        .replace("LINKS", links)
        .replace("DATA", data)
    )
    (output / "review.html").write_text(page, encoding="utf-8")
    notes = f"""# Fase 4 — entrega técnica

A: PASS_MOCK_TECHNICAL. B: BLOCKED_VOICE_RIGHTS. Ningún video está aprobado para publicación.

[Video final]({relative}/final.mp4) · [Visor](review.html) · [Artefactos]({relative}/manifest.json) · [Auditoría](voice_audit.json)

| Verificación | Resultado |
| --- | --- |
| Formato | H.264/AAC, {qa["width"]}×{qa["height"]}, {qa["fps"]} FPS, {qa["frames"]} frames |
| Duración de muestras WAV | {timeline["duration"]:.6f} s |
| Audio final | {qa["audio_sample_rate"]} Hz, {qa["audio_channels"]} canal(es), {qa["audio_duration"]:.6f} s |
| Segmentos y escenas | {len(timeline["segments"])} frases WAV, {len(timeline["scene_spans"])} escenas |
| Síntesis MOCK | {report["narration"]["synthesis_wall_seconds"]:.3f} s; tonos, no voz |
| Render givemotion | {render["render_wall_seconds"]:.3f} s wall; {render["cpu_seconds"]:.3f} s CPU |
| RSS simultáneo árbol nativo | {render["peak_process_tree_rss_mib"]:.2f} MiB; páginas compartidas contadas por proceso |
| Composición y QA | {qa["composition_wall_seconds"]:.3f} s wall; CPU del comando de composición {qa["composition_cpu_seconds"]:.3f} s |
| Reanudación | mismo job, hashes/mtimes conservados: {reused}; publicaciones MOCK: {remote} |
| Pruebas | {report["tests"]["pytest"]}; {report["tests"]["ruff"]} |
| Resultados anteriores preservados | {sum(preserved.values())}/{len(preserved)} MP4 |
| Costos API | {metrics["api_calls"]} llamadas; USD {metrics["production_cost_usd"]} |

FFprobe y decodificación completa PASS. Los cues corresponden a frases con WAV medido, no a estimación fonética por palabra. La pista completa incluye pausas y padding mínimo al grid de video; no hay aceleración ni truncamiento. Las cifras originales se conservan.

El máximo de RAM de hijos en qa.json es un high-water mark acumulado, no una medición aislada de composición. El tiempo TTS MOCK no predice el de una voz real. Los costos eléctricos y de hardware no se midieron. Las métricas Factory incluyen reintentos y reinspecciones.

Se corrigió un solapamiento del aviso MOCK con el contador detectado en la primera iteración; los artefactos iniciales se conservan en factory/. La entrega actual procede de un nuevo ciclo íntegro tras la corrección.

Pendientes: derechos/versiones/hashes de voz o grabación es-419, revisión de contenido, pronunciación, ritmo y lectura en dispositivo. La infraestructura ExternalAudio está probada con señales originales autorizadas para test; esas señales no sustituyen el ensayo de narración humana B.
"""
    (output / "report.md").write_text(notes, encoding="utf-8")
    print(output / "review.html")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job", type=Path)
    parser.add_argument("--output", type=Path, default=Path("out/phase4"))
    args = parser.parse_args()
    build(args.job, args.output)
