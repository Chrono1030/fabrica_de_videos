# Segunda prueba audiovisual · resultados 2026-11-17

Cuatro MP4 nativos completos de 55 s, H.264, 1080×1920, 24 FPS, 1320 frames y sin audio. Rama codex/renderer-advanced-poc, derivada de codex/renderer-ab-local. Fuentes de los renders congeladas en `95466c4`.

| Motor | Render s (1 / 2) | CPU s (1 / 2) | RSS árbol MiB (1 / 2) | Reproducción de frames |
|---|---|---|---|---|
| givemotion 0.1.6 | 59.69 / 60.94 | 91.70 / 95.37 | 1087.43 / 1092.11 | 1320/1320 exactos; SSIM 1.000000, mínimo 1.000000 |
| hyperframes 0.9.59 | 94.47 / 96.37 | 101.40 / 102.75 | 1471.85 / 1467.37 | 1119/1320 exactos; SSIM 0.999996, mínimo 0.999945 |

StoryBoard SHA-256: `16682b9fa1a855d3836010f9411180274d6eb5381f2541b8267820d1089ff880`. Node `v22.16.0`; navegador `Google Chrome for Testing 157.0.8103.78`; `ffmpeg version 6.1.1-3ubuntu5 Copyright (c) 2000-2023 the FFmpeg developers`.

La relación de tiempo HyperFrames/givemotion fue 1.58×. Mantener givemotion como preferido por eficiencia, memoria y reproducción exacta en estas dos muestras. HyperFrames aporta GSAP y subcomposiciones; una ventaja estética o educativa adicional requiere revisión humana. Sin puntuaciones estéticas definitivas.

CPU: GNU time user + system. RSS árbol: suma simultánea cada 50 ms, con páginas compartidas contadas por proceso. Pico individual de GNU time conservado por separado. Un worker y calidad standard nativa por motor, sin partes reutilizadas ni caché del SO limpiada. Check precalienta la primera corrida; no se atribuye causalmente la diferencia de tiempos a caché con dos muestras. givemotion usó BeginFrame; HyperFrames screenshot nativo en Linux/WSL sin GPU de hardware. No es una comparación de codificador idéntico.

`VisualStoryboard` en `src/fabrica/visual_storyboard.py`: narrativa, tiempos, segmentos para futuro TTS, presupuestos balanceados, datos, eventos, semántica, identidad, safe area y origen. Adaptadores `validate/build/render/inspect/collect_metrics` en `experiments/renderer_advanced/adapters.py`; valores y proporciones consumen el contrato. Solo se admiten givemotion y HyperFrames.

Evidencia local ignorada por Git: `out/renderer_advanced/report.json`, `compare.md`, `review.html`; cuatro rutas `<motor>/run-{1,2}/final.mp4`; dos `<motor>/contact-sheet.jpg`; dos `transition-sheet.jpg`; 16 capturas equivalentes por run; manifests, decodificación, framemd5, recursos, logs y SSIM por frame.

QA técnico: todos los formatos y 1320 frames validados y decodificados; revisión de capturas y 18 frames de límites por motor sin cuadros vacíos ni clipping observado. Safe area propia x=80..1000 e y=160..1660. givemotion: cero errores nativos, siete avisos (holds y no-expect). HyperFrames: cero errores; 57 avisos de presets de redes sociales y uno por silencio requerido. No son las zonas seguras del contrato. Revisión estética móvil pendiente; no se ejecutó QA editorial completo ni se simuló sincronización fonética.

Visor offline probado en Chrome local: nueve comprobaciones PASS (dos MP4, siete escenas, salto, frame, reproducción/pausa, PNG y run-2), cero excepciones JavaScript. Windows no fue ejecutado directamente. Abrir desde Windows conservando la carpeta:

```powershell
$p = wsl.exe -d Ubuntu-24.04 -- wslpath -w /home/devvideo/proyectos/fabrica_de_videos/out/renderer_advanced/review.html
Start-Process ($p.Trim())
$p = wsl.exe -d Ubuntu-24.04 -- wslpath -w /home/devvideo/proyectos/fabrica_de_videos/out/renderer_advanced
explorer.exe ($p.Trim())
```

Baseline: 72 tests en 56.22 s y Ruff PASS. Final: **88 tests en 57.75 s y Ruff PASS**. Los 16 tests nuevos cubren contrato, presupuestos, tiempos/eventos, IDs, adaptadores, versiones/configuración, entorno sin secretos, motores rechazados y consumo de datos/paleta. Preservación comprobada por hashes de los seis MP4 originales y 22 fuentes Python revisadas (incluido el contrato nuevo). Sin cambios en publicación YouTube, credenciales, Rocky Linux, servicios pagados, push, merge ni eliminación de Pillow.

Cinco iteraciones por motor registradas. Lotes previos en `out/renderer_advanced_iteration-3` (cuatro exportaciones completas) y `iteration-4` (tres PASS y una ejecución rechazada por el guard de fuentes al corregir datos duplicados). Excluidos del benchmark final. El último lote tiene cuatro PASS y un mismo conjunto de hashes de fuentes/storyboard/Git/runtimes; `execution-history.json` conserva la trazabilidad. No se afirma igualdad cronometrada del esfuerzo manual.

Reproducir con los comandos de `experiments/renderer_advanced/README.md`; archivar antes la salida porque el runner preserva resultados existentes.
