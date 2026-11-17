# Segunda prueba audiovisual: presupuesto de 55 segundos

Contrato editorial: `src/fabrica/visual_storyboard.py` y `storyboard.json`. Siete escenas contiguas, identificadores narrativos para TTS posterior, eventos e intención semántica, safe area y presupuestos que suman exactamente el ingreso. No contiene selección ni APIs de motor.

`adapters.py` ofrece un protocolo `Renderer`: validate, build, render, inspect, collect_metrics. Selección parametrizada con rechazo de Pillow, existing, Motion Canvas, Remotion y desconocidos. Cada adaptador genera su propio proyecto y solo invoca su motor. Reutiliza el muestreador de RSS de renderer_ab y los comandos nativos probados en esa etapa. No modifica la primera prueba, producción ni YouTube.

Versiones instaladas conservadas: givemotion 0.1.6, HyperFrames 0.9.59, Node 22.16.0, Chrome headless shell 157.0.8103.78. Usa los runtimes, bibliotecas locales y lockfiles de `experiments/renderer_ab/engines/`. No ejecuta npm install, llamadas pagas ni descargas. Fuente DejaVu Sans instalada en el sistema; SVG original y gráficos, sin imágenes externas. FFmpeg del sistema.

Desde la raíz del repositorio:

```bash
.venv/bin/python -m experiments.renderer_advanced.run --renderer all
# O, siempre secuencialmente:
# .venv/bin/python -m experiments.renderer_advanced.run --renderer givemotion
# .venv/bin/python -m experiments.renderer_advanced.run --renderer hyperframes
.venv/bin/python -m experiments.renderer_advanced.report
.venv/bin/ruff check .
.venv/bin/pytest -q
```

El runner rechaza directorios run-1/run-2 existentes, incluso si un intento falló. Conservar evidencia archivando toda la salida antes de repetir. Nunca usar un segundo renderizador para completar una salida fallida. Los dos renders de un motor deben usar fuentes, storyboard, composición, lockfile y Git SHA idénticos; se comprueban entre repeticiones. No editar fuentes durante las mediciones. Chromium y el servidor local necesitan permiso de loopback/ejecución fuera del sandbox; los procesos JS reciben únicamente variables permitidas y no heredan secretos de aplicación.

Los MP4 van a `out/renderer_advanced/<motor>/run-{1,2}/final.mp4`, con manifest, recursos, logs nativos, ffprobe, decodificación, hashes de los 1320 frames, 16 capturas y hoja de fotogramas FFmpeg. El informe compara todos los frames dentro de cada motor mediante igualdad exacta y SSIM global y mínimo por frame. No exige igualdad binaria ni deduce calidad estética de píxeles. Se copian dos hojas principales a `<motor>/contact-sheet.jpg`.

Los tiempos de render excluyen build, check y QA. `build_wall_seconds` mide la escritura local del proyecto, no el esfuerzo manual de autoría. GNU time mide CPU y pico RSS individual; el muestreador reutilizado suma RSS simultáneo del árbol cada 50 ms, contando páginas compartidas por proceso. No se borra caché del SO. Check y capturas precalientan; no son corridas en frío. Sin reutilización de partes: givemotion --no-cache y HyperFrames sin --resume. Un worker por motor, nunca simultáneos.

`iterations.json` registra el trabajo comparable y las correcciones de capturas, sin inventar horas de autoría. Solo QA técnico visual: no QA editorial completo, voz ni alineación fonética. El visor `review.html` tiene reproducción/pausa, búsqueda, escenas, frame, selección de run y PNG comparables sin dependencias externas. Las puntuaciones estéticas y la decisión definitiva quedan para revisión humana.

En PowerShell:

```powershell
wsl.exe -l -q
$p = wsl.exe -d Ubuntu-24.04 -- wslpath -w /home/devvideo/proyectos/fabrica_de_videos/out/renderer_advanced/review.html
Start-Process ($p.Trim())
# Para abrir la carpeta completa:
$p = wsl.exe -d Ubuntu-24.04 -- wslpath -w /home/devvideo/proyectos/fabrica_de_videos/out/renderer_advanced
explorer.exe ($p.Trim())
```

Sustituir el nombre de distribución si corresponde. Los artefactos grandes están ignorados por Git; las fuentes y un resumen persistente quedan versionados. No hay push, merge ni publicación.

Resultado final registrado: `docs/RENDERER_ADVANCED_RESULTS_20261117.md`. Baseline 72 tests; final 88 tests. Cinco iteraciones por motor; lotes previos conservados en `out/renderer_advanced_iteration-3` y `iteration-4`, excluidos del informe final. `execution-history.json` distingue los cuatro PASS finales de los intentos anteriores; un intento previo fue rechazado por el guard de fuentes al corregir la arquitectura.

Smoke test reproducible del visor, después de generar el informe:

```bash
.venv/bin/python -c 'from experiments.renderer_advanced.adapters import *; (OUT/"checks").mkdir(exist_ok=True); print(execute([NODE,EXP/"verify_review.mjs",CHROME,OUT/"review.html",OUT/"checks"],timeout=120))'
```

La prueba usa Chrome headless local y videos H.264 reales; no sustituye una ejecución directa en Windows. Log JSON y captura en checks/. No modifica los MP4 ni los datos medidos.
