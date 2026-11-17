# Comparación real de renderizadores

Dos renders completos por motor, ejecutados secuencialmente. Sin audio, APIs generativas, cloud ni publicación. La revisión del agente usa capturas del MP4 y diagnósticos; la puntuación estética y la decisión final quedan pendientes de revisión humana.

| Motor | Versión | Técnica | Render s (1 / 2) | CPU s (1 / 2) | RAM árbol MiB (máx.) | MP4 MiB (1 / 2) | Frames idénticos | Layout | Claridad semántica / valor visual | Integración / mantenimiento | Licencia |
|---|---|---|---|---|---|---|---|---|---|---|
| existing | Pillow 12.3.0 / FFmpeg 6.1.1 | PASS ×2 | 13.79 / 15.02 | 27.52 / 30.20 | 454.1 | 0.311 / 0.311 | 480/480 | Sin clipping en capturas; revisión humana pendiente | 4 escenas; nota humana pendiente | Bajo costo; mantiene stack actual | Pillow HPND; FFmpeg GPL build; DejaVu |
| hyperframes | 0.9.59 | PASS ×2 | 37.38 / 35.76 | 44.97 / 44.01 | 1463.3 | 0.659 / 0.661 | 61/480 | 0 errores; 15 avisos nativos | 4 escenas; nota humana pendiente | Subcomposiciones y GSAP; 82 paquetes npm; mayor superficie | Apache-2.0; GSAP 3.15 términos propios; DejaVu |
| givemotion | 0.1.6 | PASS ×2 | 21.38 / 21.75 | 34.93 / 34.96 | 1084.8 | 0.706 / 0.706 | 480/480 | 0 errores; 5 avisos (todos los checks) | 4 escenas; nota humana pendiente | HTML + gm.onFrame; 1 paquete npm; proyecto joven | MIT; DejaVu |


Mediciones completas: `/home/devvideo/proyectos/fabrica_de_videos/out/renderer_ab/compare.md` y `report.json` (artefactos locales ignorados por Git). Reproducir con los comandos de `experiments/renderer_ab/README.md`. No se eligió ganador definitivo.
