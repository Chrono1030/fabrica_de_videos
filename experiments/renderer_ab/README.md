# Experimento aislado de renderizadores

Fuentes: fixture.json inalterado; config.json fija HyperFrames 0.9.59 (0.9.60 no publicado), givemotion 0.1.6; Motion Canvas y Remotion permanecen desactivados. No se modifica src/fabrica/render.py.

Desde la raíz del repositorio, Ubuntu x86_64 con Python 3.12 y FFmpeg:

```bash
.venv/bin/python experiments/renderer_ab/setup.py
.venv/bin/python experiments/renderer_ab/run.py --renderer existing --repeat 2
.venv/bin/python experiments/renderer_ab/run.py --renderer hyperframes --repeat 2
.venv/bin/python experiments/renderer_ab/run.py --renderer givemotion --repeat 2
.venv/bin/python experiments/renderer_ab/report.py
# O ejecutar los tres secuencialmente:
# .venv/bin/python experiments/renderer_ab/run.py --renderer all --repeat 2
```

El setup usa runtime-lock.json, comprueba SHA-256, instala Node y Chrome dentro de engines/, extrae bibliotecas Ubuntu localmente y ejecuta npm ci por candidato. No instala motores globales. Requiere acceso de red; los renders posteriores usan archivos locales. Si las versiones Ubuntu fijadas desaparecen del mirror, obtener esos mismos .deb del archivo Ubuntu conservando sus hashes; no cambiar silenciosamente la versión. Python productivo se reutiliza sin instalar dependencias nuevas; su pip freeze se guarda en out/renderer_ab/setup/python-freeze.txt.

El runner rechaza resultados existentes antes de construir proyectos. Para repetir sin perder evidencia, mover out/renderer_ab fuera de esa ruta. --overwrite es la autorización explícita para reemplazar resultados y no debe usarse para conservar una medición anterior. Las fuentes y Git SHA se verifican entre repeticiones. No cambiar código, dependencias, configuración o fixture durante las mediciones.

Pillow dibuja frames y reutiliza fabrica.cards.font; FFmpeg codifica sin audio. HyperFrames monta cuatro subcomposiciones, anima con GSAP local y exporta con su CLI. givemotion crea su propio HTML con data-sequence y callbacks gm.onFrame. Comparten iconos vectoriales y contrato tipográfico, sin intercambiar HTML generado ni frames entre motores. Los MP4 de candidatos proceden exclusivamente de su render nativo.

Cada corrida conserva el comando exacto, versiones, hashes, tiempo de CPU/render, dos medidas de memoria, logs, diagnóstico nativo, ffprobe, decodificación completa, framemd5 de 480 frames, ocho PNG y contact sheet. El pico del árbol suma RSS de procesos simultáneos cada 50 ms, con páginas compartidas contadas por proceso. ru_maxrss de GNU time es el mayor RSS de un proceso individual. No confundir ambas medidas.

La primera corrida está precalentada por los diagnósticos; no se limpia caché del SO. No se reutilizan partes renderizadas (--no-cache de givemotion, sin --resume de HyperFrames). El benchmark usa presets nativos, no un encoder idéntico. Sus tiempos representan el flujo elegido y no una comparación pura del rasterizador.

Las herramientas JS reciben solo variables permitidas, sin credenciales de la aplicación. Telemetría y update checks están desactivados. El directorio servido contiene únicamente composiciones del experimento, GSAP local y datos del fixture. En Codex, el sandbox impide loopback y Chromium: ejecutar esos comandos con la aprobación de ejecución externa correspondiente.

Los avisos de quietud se interpretan como holds de lectura en escenas 2, 3 y cierre; los tiempos del fixture no se alteran. La banda propia de captions y=1680..1840 es distinta de los presets de redes sociales de los verificadores. Los textos subjetivos y la puntuación ponderada quedan pendientes de revisión humana; no inferir calidad de diferencias de píxeles.

Licencias: motores Apache-2.0 y MIT; revisar GSAP y dependencias transitivas antes de integrar. FFmpeg instalado tiene GPL habilitada; fuente DejaVu según licencia instalada. El inventario no sustituye auditoría jurídica. Sin publicación, TTS, servicios pagos, API GPT, push ni merge.

Ver out/renderer_ab/review.html para abrir los tres videos y segundas ejecuciones localmente. compare.md y report.json contienen las mediciones; artifact-paths.txt enumera rutas Linux y UNC de Windows. Los artefactos, navegadores y node_modules están ignorados por Git.
