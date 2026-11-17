"""Measured comparison and offline review, no aesthetic scores fabricated."""

import json
import shutil
import statistics

from .adapters import EXP, OUT, execute


def frame_rows(path):
    return [
        r.split(",")[-1].strip()
        for r in path.read_text().splitlines()
        if not r.startswith("#")
    ]


def main():
    report = {
        "experiment": "renderer_advanced",
        "human_review": "pending",
        "aesthetic_scores": None,
        "technical_recommendation": "provisional",
        "engines": {},
        "iterations": json.loads((EXP / "iterations.json").read_text()),
        "qa_scope": "Technical visual experiment only; no full editorial or voice QA",
    }
    lines = [
        "# Segunda prueba audiovisual · 55 segundos",
        "",
        "Dos ejecuciones nativas por motor, secuenciales, sin audio. Mismo VisualStoryboard y siete segmentos. Paleta marino/marfil/dorado y DejaVu Sans. Sin puntuaciones estéticas definitivas.",
        "",
        "| Motor | Render s (1 / 2) | CPU s (1 / 2) | RAM árbol MiB (1 / 2) | Tamaño MiB (1 / 2) | Frames exactos | SSIM |",
        "|---|---|---|---|---|---|---|",
    ]
    for name in ["givemotion", "hyperframes"]:
        runs = [
            json.loads((OUT / name / f"run-{i}/manifest.json").read_text())
            for i in (1, 2)
        ]
        assert all(r["status"] == "PASS" for r in runs)
        keys = [
            "storyboard_sha256",
            "source_sha256",
            "composition_sha256",
            "lockfile_sha256",
            "engine_package_sha256",
            "git_sha",
            "node",
            "browser",
            "ffmpeg",
        ]
        stable = all(runs[0][key] == runs[1][key] for key in keys)
        assert stable, "Measurement inputs differ"
        frames = [frame_rows(OUT / name / f"run-{i}/frames.md5") for i in (1, 2)]
        assert len(frames[0]) == len(frames[1]) == 1320
        exact = sum(a == b for a, b in zip(*frames))
        log = execute(
            [
                "ffmpeg",
                "-i",
                OUT / name / "run-1/final.mp4",
                "-i",
                OUT / name / "run-2/final.mp4",
                "-lavfi",
                f"ssim=stats_file={OUT / name / 'repro-ssim-frames.log'}",
                "-f",
                "null",
                "-",
            ]
        )
        (OUT / name / "repro-ssim.log").write_text(log)
        summary = next(row for row in reversed(log.splitlines()) if "SSIM Y:" in row)
        ssim = float(summary.split("All:")[1].split()[0])
        stats = [
            row
            for row in (OUT / name / "repro-ssim-frames.log").read_text().splitlines()
            if row.strip()
        ]
        minimum = min(float(row.split("All:")[1].split()[0]) for row in stats)
        details = {
            "runs": runs,
            "inputs_equal": stable,
            "exact_decoded_frames": exact,
            "compared_frames": 1320,
            "ssim_global": ssim,
            "ssim_min_frame": minimum,
            "binary_equal": runs[0]["sha256"] == runs[1]["sha256"],
            "reproducibility": "exact decoded frames"
            if exact == 1320
            else "near-equivalent; inspect SSIM and frame comparisons",
            "manual_aesthetic_score": None,
        }
        report["engines"][name] = details

        def pair(key, scale=1):
            return " / ".join(f"{r[key] / scale:.2f}" for r in runs)

        lines.append(
            f"| {name} {runs[0]['engine_version']} | {pair('render_wall_seconds')} | {pair('cpu_seconds')} | {pair('peak_process_tree_rss_mb')} | {pair('out_bytes', 2**20)} | {exact}/1320 | {ssim:.6f} (mín. {minimum:.6f}) |"
        )
        shutil.copy(
            OUT / name / "run-1/contact-sheet.jpg", OUT / name / "contact-sheet.jpg"
        )
    gm, hf = [report["engines"][n] for n in ("givemotion", "hyperframes")]
    ratio = statistics.mean(
        r["render_wall_seconds"] for r in hf["runs"]
    ) / statistics.mean(r["render_wall_seconds"] for r in gm["runs"])
    report["hyperframes_to_givemotion_wall_ratio"] = ratio
    report["preferred_engine"] = "givemotion"
    lines += [
        "",
        "## Comparación cualitativa provisional",
        "",
        "| Criterio | givemotion | HyperFrames |",
        "|---|---|---|",
        "| Composición | Presupuesto continuo; jerarquía importe → reparto → decisión | Anillo central y filas; cambia a comparación de ahorro |",
        "| Animación | Callback nativo por frame; transformación del importe, flujo y transferencia con suma conservada | Subcomposiciones y GSAP; anillo, rutas, énfasis y barras escalonadas |",
        "| Claridad de gráficos | Cinta proporcional al ingreso y dos cintas antes/después | Ángulos proporcionales y barras con escala común; comparación de ahorro a escala propia explícita |",
        "| Variedad de recursos | Importe, cinta, tarjetas, puntos sobre rutas, transferencia y comparación | Anillo, diagrama de flujo, barras, transferencia y comparación |",
        "| Representar storyboard | Continuidad sencilla con reloj global; requiere mantener estados y límites manualmente | Escenas locales explícitas; más montaje y cambios entre escenas |",
        "| Generación y render | Plantilla local sin generación remota; tiempos medidos arriba | Igual flujo local; tiempos medidos arriba |",
        "| Memoria | Pico del árbol y pico individual en cada manifest | Misma metodología; valores medidos arriba |",
        "| Reproducibilidad | 1320 frames comparados más SSIM | 1320 frames comparados más SSIM |",
        "| Complejidad | Una composición continua y callback; poca infraestructura de autoría | Siete subcomposiciones y timeline GSAP; mayor estructura |",
        "| Reutilización | Tarjetas, cinta y transferencia parametrizables; extraer componentes al integrar | Filas, anillo y montaje de escenas parametrizables; GSAP disponible para secuencias |",
        "",
        "La revisión del agente comprueba composición en capturas, transición y datos; la valoración estética y de atractivo en móvil corresponde a revisión humana. Los holds de lectura son deliberados: no se agregaron adornos para ocultar quietud.",
        "",
        "## Método y límites",
        "",
        "- 55,000 s, H.264, 1080×1920, 24 FPS, 1320 frames y una sola pista sin audio, comprobados con ffprobe y decodificación completa con -xerror. Los números finales y mensajes son idénticos entre motores.",
        "- CPU es user + system de GNU time. RAM árbol suma RSS simultáneo cada 50 ms y cuenta páginas compartidas por proceso. El máximo individual de GNU time se conserva aparte; no son la misma medida.",
        "- Tiempo de render excluye preparación de archivos, check nativo y QA posterior. Los comandos, versiones, hashes y logs están en cada manifest.json. La generación local de proyectos se mide aparte como build_wall_seconds; no hay un cronometraje confiable del trabajo manual de autoría.",
        "- Ambos motores usan un worker y preset nativo standard. No es un benchmark aislado de rasterizador con idéntico codificador. givemotion usa --no-cache; HyperFrames no usa --resume. No se limpia caché del SO. Check precalienta la primera corrida; la segunda vuelve a renderizar desde cero con archivos calientes. Dos muestras no permiten atribuir causalmente una diferencia temporal a caché.",
        "- Comparación de todos los frames decodificados dentro del mismo motor. SSIM global y mínimo por frame complementan la igualdad exacta; no se exige igualdad binaria de MP4. No se comparan píxeles entre diseños distintos para inferir estética.",
        "- Capturas a los mismos segundos en cada run y contact sheets 4×4 hechas con FFmpeg. Zonas seguras propias: x=80..1000, y=160..1660. No se exige QA editorial completo ni sincronización fonética; siete narrative_segment_id quedan listos para TTS posterior.",
        "",
        "## Esfuerzo e iteraciones",
        "",
        "Registro completo en iterations.json: un diseño inicial, una ronda de correcciones de capturas y una ronda de correcciones del QA nativo por motor antes de las mediciones. No hay evidencia de horas de autoría exactas; no se afirma igualdad cronometrada de esfuerzo. Ambos recibieron recursos semánticos equivalentes y corrección de problemas detectados.",
        "",
    ]
    for name in ["givemotion", "hyperframes"]:
        p = EXP / "templates" / f"{name}.html"
        details = report["engines"][name]
        details["template_lines"] = len(p.read_text().splitlines())
        details["template_bytes"] = p.stat().st_size
        lines.append(
            f"- {name}: plantilla {details['template_lines']} líneas / {details['template_bytes']} bytes; sin copiar HTML/CSS/JS del otro adaptador. Minificación y densidad hacen que líneas no sean una medida fiable de complejidad."
        )
    faster = "givemotion" if ratio > 1 else "HyperFrames"
    report["fastest_measured"] = faster
    lines += [
        "",
        "## Recomendación técnica provisional",
        "",
        f"El motor más rápido en estas dos muestras es **{faster}**; relación de tiempo HyperFrames/givemotion: **{ratio:.2f}×**. Conservar givemotion como preferido mientras la revisión humana compara el valor visual. HyperFrames aporta un montaje explícito de subcomposiciones y GSAP; la existencia de esos recursos no demuestra por sí sola una ventaja estética o de retención. No hay ganador estético definitivo.",
        "",
        "## Reproducir y revisar",
        "",
        "```bash",
        ".venv/bin/python -m experiments.renderer_advanced.run --renderer all",
        ".venv/bin/python -m experiments.renderer_advanced.report",
        "```",
        "",
        "El runner rechaza salidas existentes. Para repetir, archivar out/renderer_advanced con otro nombre. Reutiliza los runtimes y lockfiles de renderer_ab sin reinstalar ni actualizarlos. Requiere Chromium y loopback permitidos; comandos JS con entorno permitido mínimo y sin secretos de aplicación.",
        "",
        "Abrir review.html con Edge/Chrome desde Windows, conservando toda la carpeta. Controles sincronizados: play, pausa, marca temporal, escena, frame y selección de ejecución. También muestra PNG del mismo instante. No requiere servidor ni dependencias externas.",
        "",
        "```powershell",
        "$p = wsl.exe -d Ubuntu-24.04 -- wslpath -w /home/devvideo/proyectos/fabrica_de_videos/out/renderer_advanced/review.html",
        "Start-Process ($p.Trim())",
        "```",
        "",
        "Si tu distribución tiene otro nombre, reemplazá Ubuntu-24.04 por el mostrado en wsl.exe -l -q.",
        "",
        "## Pruebas y preservación",
        "",
        "Baseline: 72 tests y Ruff PASS. Resultados finales en checks/. La primera prueba y src/fabrica/render.py se preservan. Sin cambios en publicación YouTube, sin credenciales, Rocky Linux, audio, APIs pagas, push ni merge. Motion Canvas, Remotion y Pillow rechazados por el selector de este experimento.",
        "",
    ]
    checks = {p.name: p.read_text() for p in (OUT / "checks").glob("*.txt")}
    report["repository_checks"] = checks
    report["visual_review"] = (
        json.loads((OUT / "visual-review.json").read_text())
        if (OUT / "visual-review.json").exists()
        else {"status": "pending agent frame inspection"}
    )
    for key, value in checks.items():
        lines.append(f"{key}:\n```text\n{value.strip()}\n```")
    (OUT / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    (OUT / "compare.md").write_text("\n".join(lines) + "\n")
    captures = json.loads((EXP / "config.json").read_text())["captures"]
    (OUT / "review.html").write_text(
        (EXP / "templates/review.html")
        .read_text()
        .replace("__CAPTURES__", json.dumps(captures))
    )
    shutil.copy(EXP / "iterations.json", OUT / "iterations.json")
    paths = [
        str(p.relative_to(OUT))
        for p in OUT.rglob("*")
        if p.is_file() and "/project/" not in str(p) and "/cache/" not in str(p)
    ]
    (OUT / "artifact-paths.txt").write_text("\n".join(sorted(paths)) + "\n")
    print(OUT / "compare.md")


if __name__ == "__main__":
    main()
