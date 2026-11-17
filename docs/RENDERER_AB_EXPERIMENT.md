# A/B de motor visual — Mente y Capital

## Por qué existe

El primer MOCK (75 s, 5 escenas) demostró que el pipeline audiovisual funciona, pero no que el resultado esté listo para retener audiencia. Se observó ausencia de variación visual, textos no centrados dentro de tarjetas y recursos conceptualmente genéricos. El propietario aprueba paleta y tipografía. El objetivo es mejorar composición, contenido semántico y ritmo **sin reemplazar la aplicación por cuatro productos independientes**.

## Reglas de comparabilidad

1. Mantener **exactamente el mismo** `experiments/renderer_ab/fixture.json`, paleta, fuentes, tiempos, resolución, fps, captions y datos para todos los motores.
2. Ejecutar **un solo motor por corrida**. No mezclar animaciones/frames de varios motores en un video durante comparación.
3. Conservar una línea base del renderizador Python/Pillow/FFmpeg. Comparar por separado HyperFrames y givemotion, dejando Motion Canvas y Remotion desactivados.
4. `config.json` define el estado `enabled` por motor. **Habilitado significa candidato a prueba, NO significa ya instalado ni que haya generado un MP4**.
5. No cambiar el guion, los textos, el número de escenas ni los intervalos para hacer lucir mejor a un candidato. Un motor puede mejorar el diseño sin cambiar el significado.
6. Registrar para cada prueba: repositorio SHA y versión exacta del motor, lockfile, versión Node/Chrome/FFmpeg/OS, duración, fps, CPU, tiempo total, RAM máxima, bytes, SHA-256, framehash, capturas y hallazgos de QA.
7. Repetir cada render **dos veces** desde inputs y versiones fijados; comparar frames decodificados y manifest de inputs, no exigir igualdad binaria del archivo comprimido si hay metadata variable.
8. Aislar dependencias JS en `experiments/renderer_ab/engines/<engine>`, nunca instalarlas globalmente ni en el Python principal. Ejecutar desde el mismo Python coordinador por subprocess sin shell, con timeouts y sin acceso a credenciales.
9. No habilitar servicios cloud ni componentes AI generativos pagos de los motores; producir local/offline después de instalación inicial.
10. No modificar el `src/fabrica/render.py` existente antes de elegir ganador.

## Comandos y viabilidad confirmados por documentación de los proyectos

- HyperFrames: Node >=22, FFmpeg; CLI `npx hyperframes lint`, `npx hyperframes check`, `npx hyperframes snapshot --at 0,2,5`, `npx hyperframes render --output ...`. Fuente: https://github.com/heygen-com/hyperframes/blob/main/docs/developers/cli.mdx
- givemotion: Node >=20, Chrome, FFmpeg; `npx givemotion doctor`, `npx givemotion init <project>`, `npx givemotion dev <project>`. Proporciona API `render`, `check`, `snapshot`; revisar la versión fijada para los comandos concretos. Fuente: https://github.com/givemotion/givemotion
- Motion Canvas: MIT, render vía paquete `@motion-canvas/ffmpeg`; **desactivado** por defecto. Fuente: https://motioncanvas.io/docs/rendering/video/
- Remotion: licencia especial; uso comercial gratuito para individuo elegible, revisar cambios de entidad y reglas en https://www.remotion.dev/docs/license/pricing; **desactivado** por defecto. Las plantillas de https://github.com/reactvideoeditor/remotion-templates declaran MIT en README, pero no sustituyen licencia del motor.

## Fases

**0. Preparación:** chequear estado Git, fijar dependencias y capturar snapshot del video ORIGINAL. No tocar rama local de fase 2B.

**1. Control:** generar baseline con pipeline actual sobre fixture simplificado de 20 s. Si el motor existente no soporta este fixture, crear un adaptador mínimo sin tocar código productivo o informar limitación claramente. Se dispone también de una referencia visual producida en otro entorno con Pillow/FFmpeg, pero **NO cuenta como ejecución de motores candidatos ni sustituye el baseline real**.

**2. HyperFrames aislado:** instalar una versión fija e implementar únicamente escenas del fixture (reloj, dos tarjetas, opción descartada, conclusión), ejecutar lint/check/snapshot/render y almacenar MP4 y reporte.

**3. givemotion aislado:** mismo fixture y criterios; ejecutar doctor/check/snapshot/render, producir MP4 y reporte.

**4. Repetición:** render #2 sin cambiar fuentes, código, paquetes ni fixtures. Comparar resultados, registrar diferencias.

**5. Selección:** puntuar cada motor 1–5 por claridad semántica, layouts correctos, dinamismo útil, integración, costo de render en hardware CPU, licencias y mantenimiento. **No usar métricas de diferencia de píxeles como proxy de retención real**. Un motor de referencia más atractivo puede seguir teniendo peor rendimiento operativo.

**6. Posterior:** si ninguno supera baseline con una mejora convincente, probar Motion Canvas y luego Remotion, pero nunca habilitar todos a la vez.

## Criterios de aceptación

- Dos MP4 de candidatos distintos, cada uno 1080×1920, 24 fps, 20 s, decodificables y con capturas. Faltas de instalación o red se reportan como `BLOCKED_ENVIRONMENT`, no como benchmark aprobado.
- Bordes, alineaciones, legibilidad móvil y espacio de subtítulos correctos.
- Recursos distintos para reloj, alternativas y costo descartado.
- Al menos una acción visual relevante cada 3–5 segundos (orientación de edición, no regla automática ciega).
- No captions sobre elementos ni elementos truncados.
- Sin assets de licencias inciertas y sin publicación.
- Informe incluye parámetros/versiones/hashes y opción de repetición.
- Ninguna modificación de aplicación principal sin resultado comparativo y aceptación del propietario.

## Informe requerido

`out/renderer_ab/report.json`, `out/renderer_ab/compare.md`, contact sheets y videos separados (ignorados en Git). Documentar ganador propuesto y costo de migración. Mantener resultados puros: si un motor no corre, no inventar medidas ni producir video con otra herramienta etiquetándolo como suyo.

**Siguiente paso para Codex:** implementar adaptadores aislados y un runner que lea `config.json`, procese únicamente `enabled=true`, ejecute motores **secuencialmente**, permita `--renderer hyperframes` o `--renderer givemotion` y `--repeat 2`, respete el mismo `fixture.json`, y genere comparativas. Usar APIs CLI comprobadas de versiones fijadas, no instrucciones supuestas.
