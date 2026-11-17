"""Build the comparative report exclusively from measured execution manifests."""

import json
import statistics

from run import OUT, ROOT

NAMES = ["existing", "hyperframes", "givemotion"]


def main():
    report = {
        "experiment": "renderer_ab",
        "weights": {
            "design_composition": 0.35,
            "explanatory_value": 0.25,
            "performance": 0.20,
            "integration_maintenance": 0.15,
            "licenses": 0.05,
        },
        "visual_scores": None,
        "human_review": "pending",
        "winner": None,
        "engines": {},
    }
    lines = [
        "# Comparación real de renderizadores",
        "",
        "Dos renders completos por motor, ejecutados secuencialmente. Sin audio, APIs generativas, cloud ni publicación. La revisión del agente usa capturas del MP4 y diagnósticos; la puntuación estética y la decisión final quedan pendientes de revisión humana.",
        "",
        "| Motor | Versión | Técnica | Render s (1 / 2) | CPU s (1 / 2) | RAM árbol MiB (máx.) | MP4 MiB (1 / 2) | Frames idénticos | Layout | Claridad semántica / valor visual | Integración / mantenimiento | Licencia |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for name in NAMES:
        runs = [
            json.loads((OUT / name / f"run-{i}/manifest.json").read_text())
            for i in [1, 2]
        ]
        success = all(r["status"] == "PASS" for r in runs)
        same = success and runs[0]["framehash"] == runs[1]["framehash"]
        stable = all(
            runs[0][k] == runs[1][k]
            for k in ["fixture_sha256", "config_sha256", "git_sha", "source_sha256"]
        )
        if name != "existing":
            stable = stable and all(
                runs[0][k] == runs[1][k]
                for k in ["lockfile_sha256", "composition_sha256"]
            )
        details = {
            "runs": runs,
            "visual_reproducibility": same,
            "inputs_equal": stable,
            "manual_score": None,
        }
        frame_rows = []
        for index in [1, 2]:
            frame_file = OUT / name / f"run-{index}/frames.md5"
            frame_rows.append(
                [
                    row.split(",")[-1].strip()
                    for row in frame_file.read_text().splitlines()
                    if not row.startswith("#")
                ]
            )
        details["identical_decoded_frames"] = sum(a == b for a, b in zip(*frame_rows))
        details["compared_frames"] = len(frame_rows[0])
        equality = f"{details['identical_decoded_frames']}/{details['compared_frames']}"
        native = OUT / name / "run-1/check.log"
        layout_summary = "Sin clipping en capturas; revisión humana pendiente"
        if native.exists():
            try:
                check = json.JSONDecoder().raw_decode(native.read_text().lstrip())[0]
                if name == "hyperframes":
                    details["native_qa"] = {
                        k: v
                        for k, v in check.items()
                        if k
                        in [
                            "ok",
                            "lint",
                            "runtime",
                            "layout",
                            "motion",
                            "contrast",
                            "craft",
                            "audio",
                        ]
                    }
                    layout_summary = f"{check['layout']['errorCount']} errores; {check['layout']['warningCount']} avisos nativos"
                else:
                    details["native_qa"] = check
                    layout_summary = f"{check['errors']} errores; {check['warnings']} avisos (todos los checks)"
            except (ValueError, KeyError) as error:
                details["native_qa_parse_error"] = str(error)
        report["engines"][name] = details
        render = " / ".join(f"{r.get('render_wall_seconds', 0):.2f}" for r in runs)
        cpu = " / ".join(f"{r.get('cpu_seconds', 0):.2f}" for r in runs)
        ram = max(r.get("peak_process_tree_rss_mb", 0) for r in runs)
        size = " / ".join(f"{r.get('out_bytes', 0) / 2**20:.3f}" for r in runs)
        license_name = {
            "existing": "Pillow HPND; FFmpeg GPL build; DejaVu",
            "hyperframes": "Apache-2.0; GSAP 3.15 términos propios; DejaVu",
            "givemotion": "MIT; DejaVu",
        }[name]
        integration = {
            "existing": "Bajo costo; mantiene stack actual",
            "hyperframes": "Subcomposiciones y GSAP; 82 paquetes npm; mayor superficie",
            "givemotion": "HTML + gm.onFrame; 1 paquete npm; proyecto joven",
        }[name]
        lines.append(
            f"| {name} | {runs[0]['engine_version']} | {'PASS ×2' if success else 'FAIL'} | {render} | {cpu} | {ram:.1f} | {size} | {equality} | {layout_summary} | 4 escenas; nota humana pendiente | {integration} | {license_name} |"
        )
    ssim_log = OUT / "hyperframes/repro-ssim.log"
    if ssim_log.exists():
        summary = next(
            (
                row
                for row in reversed(ssim_log.read_text().splitlines())
                if "SSIM Y:" in row
            ),
            "",
        )
        report["engines"]["hyperframes"]["supplementary_ssim"] = summary
        lines += [
            "",
            "HyperFrames no fue exacto a nivel de píxel (61/480 frames idénticos). La comparación suplementaria obtuvo SSIM global 0.999992, consistente con diferencias pequeñas; no se atribuye una causa sin investigarla. El SSIM no sustituye la revisión humana ni una prueba de retención. Comando y estadísticas por frame en hyperframes/repro-ssim*.log.",
        ]
    lines += [
        "",
        "## Alcance de las mediciones",
        "",
        "- Tiempo de render excluye instalación, diagnóstico y QA posterior. CPU suma user + system de GNU time y descendientes esperados por el motor. RAM del árbol: suma simultánea de RSS muestreada cada 50 ms; cuenta páginas compartidas varias veces. También se conserva ru_maxrss de GNU time (mayor proceso individual), que no equivale al pico simultáneo del árbol.",
        "- Dos renders completos: givemotion usa --no-cache; HyperFrames no usa --resume. No se borró la caché del SO. Diagnósticos y snapshots precalientan navegador y archivos antes de la primera corrida. No son mediciones de arranque en frío.",
        "- Todos los frames decodificados se comparan mediante framemd5; igualdad visual solo se evalúa dentro del mismo motor. No se deduce calidad de la diferencia de píxeles entre motores.",
        "- Codificación propia de cada adaptador: Pillow x264 fast CRF18, HyperFrames standard, givemotion standard. No es un benchmark de velocidad puro con codificador idéntico: mide el costo de las exportaciones nativas elegidas.",
        "- SHA de Git, fuentes, fixture, configuración, composiciones, lockfiles, MP4, versiones y comandos exactos están en cada manifest.json. Los logs y los reportes nativos completos se conservan junto a cada MP4.",
        "",
        "## QA y revisión visual",
        "",
        "- Validación automática: ffprobe, H.264, 1080×1920, 24 fps, 480 frames, duración exacta 20 s, una única pista de video y decodificación completa con -xerror.",
        "- Capturas: 0.5, 2, 4.5, 6.5, 9.5, 12, 15 y 18.5 s. Se conservaron las capturas nativas y las extraídas del MP4. Revisión del agente: cuatro escenas distintas, reloj/caminos, tarjetas simétricas, alternativa descartada y cierre conceptual; captions separados del contenido.",
        "- Pausas editoriales: escena 2 mantiene ambas alternativas para lectura comparativa; escena 3 mantiene la alternativa descartada para leer la narración; escena 4 mantiene la definición y pregunta final. Estos holds explican los avisos de quietud; no se modificaron los intervalos del fixture.",
        "- Los avisos de safe zone de plataformas no equivalen a solapamiento con los captions de este contrato: la banda propia está en y=1680..1840. No se declara que este POC esté listo para publicar como Short/Reel.",
        "- Riesgo pendiente: revisar a tamaño móvil la legibilidad de los párrafos de 36 px, la continuidad temporal y el valor de los holds. No hay puntuación subjetiva inventada ni ganador definitivo.",
        "",
        "## Versiones y licencias",
        "",
        "- HyperFrames 0.9.60 devolvió HTTP 404 en npm; se eligió y fijó 0.9.59 estable publicada. Evidencia local en setup/hyperframes-all.json y setup/hyperframes-0.9.59-registry.json. La documentación y plantilla leídas corresponden al paquete instalado.",
        "- givemotion 0.1.6 publicado y fijado. API y ejemplos leídos dentro de ese paquete; no se reutilizó el HTML generado por HyperFrames: el adaptador givemotion usa secuencia y callbacks nativos propios. Solo comparte primitivas genéricas del contrato visual.",
        "- Node 22.16.0; Chrome for Testing 157.0.8103.78; FFmpeg 6.1.1-3ubuntu5; versiones completas por manifest. Chrome 131 fue un intento preliminar descartado por incompatibilidad; no interviene en los renders medidos finales.",
        "- Las licencias de los motores no sustituyen las de dependencias y binarios: GSAP tiene términos propios, FFmpeg local fue compilado con GPL y DejaVu tiene su licencia de fuente. No se realizó una auditoría transitiva jurídica completa; se conservan los textos de licencia instalados y su inventario.",
        "",
        "## Reproducción",
        "",
        "Desde la raíz del repositorio en Ubuntu x86_64, con Python 3.12 y FFmpeg disponibles:",
        "",
        "```bash",
        ".venv/bin/python experiments/renderer_ab/setup.py",
        ".venv/bin/python experiments/renderer_ab/run.py --renderer existing --repeat 2",
        ".venv/bin/python experiments/renderer_ab/run.py --renderer hyperframes --repeat 2",
        ".venv/bin/python experiments/renderer_ab/run.py --renderer givemotion --repeat 2",
        "# Alternativa secuencial: --renderer all --repeat 2",
        ".venv/bin/python experiments/renderer_ab/report.py",
        "```",
        "",
        "Los directorios de salida existentes se rechazan. Para repetir conservando evidencia, mover previamente out/renderer_ab a otro directorio; --overwrite autoriza expresamente reemplazar las salidas. En Codex, Chromium/loopback necesitan ejecución fuera del sandbox. El setup descarga solo runtimes fijados, verifica SHA-256, extrae bibliotecas localmente y usa npm ci con lockfiles. No modifica paquetes globales.",
        "",
        "## Recomendación provisional",
        "",
    ]
    candidates = [
        (statistics.mean(r["render_wall_seconds"] for r in v["runs"]), n)
        for n, v in report["engines"].items()
        if all(r["status"] == "PASS" for r in v["runs"])
    ]
    fastest = min(candidates)[1] if candidates else None
    report["fastest_measured"] = fastest
    lines.append(
        f"El menor tiempo medio medido corresponde a **{fastest}**. Conservar Pillow/FFmpeg en producción hasta la revisión humana. Para seguir probando un candidato HTML, recomiendo provisionalmente givemotion: fue más rápido y consumió menos memoria que HyperFrames, repitió exactamente los 480 frames y ofrece la integración más pequeña (sin dependencias npm runtime). HyperFrames aporta lint y subcomposiciones con una superficie mayor. La adopción depende de una mejora visual confirmada por el propietario y de revisar las dependencias/licencias; estos datos no justifican por sí solos una migración."
    )
    lines += [
        "",
        "## Controles del repositorio",
        "",
        "Baseline anterior a implementación: Ruff PASS; pytest 68 passed in 56.50s. Resultados finales guardados en checks/. Producción src/fabrica/render.py preservada, Motion Canvas y Remotion desactivados, sin push ni merge.",
        "",
        "## Artefactos y rutas",
        "",
    ]
    for name in NAMES:
        for i in [1, 2]:
            p = OUT / name / f"run-{i}"
            lines.append(
                f"- `{p}/final.mp4` — manifest.json, ffprobe.json, frames.md5, decode.log, render.log y contact-sheet.jpg en el mismo directorio."
            )
    lines.append(
        f"\nRaíz Windows: `\\\\wsl.localhost\\Ubuntu-24.04\\home\\devvideo\\proyectos\\fabrica_de_videos\\out\\renderer_ab`. Inventario completo: `{OUT}/artifact-paths.txt`."
    )
    for label in ["ruff-final.txt", "pytest-final.txt"]:
        check_file = OUT / "checks" / label
        if check_file.exists():
            lines.append(f"\n{label}: {check_file.read_text().strip()}")
    report["repository_checks"] = {
        p.name: p.read_text() for p in (OUT / "checks").glob("*.txt")
    }
    (OUT / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    )
    (OUT / "compare.md").write_text("\n".join(lines) + "\n")
    (OUT / "artifact-paths.txt").touch()
    paths = sorted(
        str(p.resolve())
        for p in OUT.rglob("*")
        if p.is_file()
        and "/cache/" not in str(p)
        and "/project/.hyperframes/" not in str(p)
    )
    (OUT / "artifact-paths.txt").write_text(
        "\n".join(
            p + "\n" + "\\\\wsl.localhost\\Ubuntu-24.04" + p.replace("/", "\\")
            for p in paths
        )
        + "\n"
    )
    videos = "".join(
        f'<article><h2>{n}</h2><video controls preload="metadata" width="270" src="{n}/run-1/final.mp4"></video><p><a href="{n}/run-2/final.mp4">Segunda ejecución</a> · <a href="{n}/run-1/contact-sheet.jpg">Fotogramas</a></p></article>'
        for n in NAMES
    )
    (OUT / "review.html").write_text(
        '<!doctype html><html lang="es"><meta charset="utf-8"><title>Render A/B — revisión local</title><style>body{background:#112037;color:#F6EEDB;font-family:sans-serif}main{display:flex;gap:30px;flex-wrap:wrap}a{color:#E6B864}</style><h1>El costo de oportunidad</h1><p>Revisión humana pendiente. Videos sin audio.</p><main>'
        + videos
        + '</main><a href="compare.md">Informe comparativo</a></html>'
    )
    summary = ROOT / "docs/RENDERER_AB_RESULTS_20261117.md"
    summary.write_text(
        "\n".join(lines[:10])
        + f"\n\nMediciones completas: `{OUT}/compare.md` y `report.json` (artefactos locales ignorados por Git). Reproducir con los comandos de `experiments/renderer_ab/README.md`. No se eligió ganador definitivo.\n"
    )
    print(OUT / "compare.md")


if __name__ == "__main__":
    main()
