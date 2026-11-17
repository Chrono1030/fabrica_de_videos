# Repositorios externos a evaluar dentro de una sola fábrica

Este inventario prioriza **bibliotecas internas** y ejemplos, sin reemplazar la aplicación existente ni instalar otro producto que haya que administrar. La licencia indicada es del repositorio/biblioteca, no necesariamente de modelos, datasets, música, iconos o servicios asociados. Codex debe inspeccionar versiones, licencias de transitivas y riesgos antes de copiar código.

| Módulo interno | Candidato | Uso | Decisión inicial |
|---|---|---|---|
| Scheduler | https://github.com/agronholm/apscheduler (MIT) | Ejecución cron/intervalos y jobs | Estudiar versión estable 3.x frente a planificador SQLite mínimo; v4 aún pre-release |
| Upload YouTube | https://github.com/googleapis/google-api-python-client (Apache-2.0) | API oficial videos.insert/videolist, uploads reanudables | Adoptar SDK oficial y ejemplos del proveedor |
| OAuth YouTube | https://github.com/googleapis/google-auth-library-python-oauthlib (Apache-2.0) | Login OAuth inicial y refresh | Adoptar; secretos privados |
| Cliente TikTok | https://github.com/encode/httpx (BSD-3) | HTTP para endpoints oficiales | Adoptar si TikTok autorizado; no paquetes de browser automation |
| Subtítulos | https://github.com/tkarabela/pysubs2 (MIT) | Construcción/edición SRT/ASS | Comparar con implementación actual; adoptar solo si reduce código |
| Alineación audio | https://github.com/SYSTRAN/faster-whisper (MIT) | Segmentación y tiempos de subtítulos | Futuro opcional; benchmark CPU |
| Movimiento de gráficos | https://github.com/ManimCommunity/manim (MIT) | Animaciones económicas más sofisticadas | Posterior; comparar coste de render con FFmpeg/Pillow |
| Recursos visuales | https://github.com/lucide-icons/lucide (licencias según paquete) | Iconos SVG | Adoptar selectivamente y registrar procedencia |
| Proyecto de referencia | https://github.com/harry0703/MoneyPrinterTurbo (MIT reportada) | Patrones de generación de guiones y edición | Auditar, no instalar como otro servicio |
| Otro proyecto referencia | https://github.com/RayVentura/ShortGPT | Arquitectura audiovisual | Auditar mantenimiento y licencias antes de copiar |
| TTS actual | https://github.com/OHF-Voice/piper1-gpl (GPL-3.0-or-later) | Síntesis local | Ya integrado, voz todavía bloqueada por derechos |
| TTS candidato | https://github.com/hexgrad/kokoro y https://huggingface.co/hexgrad/Kokoro-82M (Apache-2.0 pesos) | Comparativa de naturalidad en español | Auditar voces y pronunciación; posible fallback |

**No adoptar n8n para el MVP:** aprobado producto único con scheduler interno. Uptime Kuma es monitor externo ya existente, no pieza editorial. No trasladar composición a Remotion por defecto: implicaría stack TypeScript/React y régimen de licencias específico según uso.

## Prioridad de auditoría de Codex

1. YouTube SDK/OAuth + upload resumable; crear tests de dobles y seguridad antes de credenciales.
2. APScheduler 3.x vs scheduler simple con SQLite atómico; priorizar una sola instancia y baja huella de memoria.
3. pysubs2 sólo si simplifica SRT/ASS sin romper subtítulos cinematográficos.
4. Proveniencia de voz comercialmente viable: nunca desbloquear publicación por una licencia genérica del motor.
5. MoneyPrinterTurbo/ShortGPT: identificar funciones concretas reutilizables, SHA, copyright y dependencia pagada; no reescribir el pipeline.
6. Analítica: APIs oficiales YouTube Analytics solo después del MVP, no screen scraping.

## Criterios de adopción

Para cada candidato: URL, commit/tag evaluado, license SPDX, transitive licenses, CPU/memoria/disco, compatibilidad Python 3.12/Rocky Linux, grado de acoplamiento, mantenimiento, tests aislados, seguridad de red, beneficio medible y plan de rollback. Prohibido copiar fragmentos sin atribución/aviso de licencia requeridos.

## Referencias de versiones/políticas

https://github.com/agronholm/apscheduler
https://github.com/googleapis/google-api-python-client
https://github.com/tkarabela/pysubs2
https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/LICENSING.md
https://www.remotion.dev/docs/license/pricing

## Prioridad audiovisual a partir del MOCK de 75 s (revisión 2026-11-17)

El primer MOCK de Mente y Capital tiene paleta/fuentes aceptadas y un render funcional, pero mucho espacio central permanece estático, hay labels descentrados, símbolos genéricos ($/%) no asociados al tema, barras cualitativamente irrelevantes y elementos repetidos en apertura/cierre. **No resolver agregando imágenes aleatorias**: se requiere planificación visual semántica y render 2D animado con autoevaluación de layout.

| Motor o recurso | URL | Licencia divulgada | Por qué evaluar | Riesgo/condición |
|---|---|---|---|---|
| **HyperFrames** | https://github.com/heygen-com/hyperframes | Apache-2.0 | Motor de HTML a video para agentes, catálogo visual amplio, verificaciones de clipping/layout, ejemplos de explainer | Dependencias JS y Chrome/Bun; benchmark local en CPU, auditar política de ejecución de código generado |
| **givemotion** | https://github.com/givemotion/givemotion | MIT, v0.1.5 (noviembre 2026) | Render HTML/CSS/JS, check de solapamientos/contraste/ritmo, snapshots/contact sheet, bloques compare/chart/steps, render incremental | Proyecto joven; validar promesas de performance, mantenimiento y seguridad antes de adoptar |
| **Motion Canvas** | https://github.com/motion-canvas/motion-canvas | MIT | Motion graphics vectoriales específicamente para voz en off, timeline y sincronía | TypeScript; piezas animadas deben diseñarse; no genera semántica desde guion |
| **Remotion** | https://github.com/remotion-dev/remotion | Licencia propietaria source-available, Free License para individuo/equipo <=3 sujeto a términos | Render visual React y ecosistema amplio de plantillas | Revisar términos comerciales y obligaciones si el proyecto cambia de estructura |
| **81 templates Remotion** | https://github.com/reactvideoeditor/remotion-templates | MIT para plantillas (independiente del motor) | Charts animados, numeradores, transiciones y layouts | Asegurar diseño responsive vertical, revisar atribuciones y no repetir template sin valor adicional |
| **50 templates Remotion** | https://github.com/RenderComp/free-remotion-templates | MIT para templates | Charts, KPIs y algunos 9:16 listos | Igual: motor Remotion sujeto a su licencia |
| **Canvas explainer videos** | https://github.com/junjie721/canvas-explainer-videos | Verificar LICENSE antes de usar | Ejemplos de explainer 15–90 s y sincronización opcional TTS | Proyecto menor, ejemplos chinos; no incorporar como dependencia sin evaluar |
| **explainer-studio** | https://github.com/DV0x/explainer-studio | Verificar LICENSE antes de copiar | Referencia para estilo ilustración dibujada + captions + FFmpeg | Menos madurez, estilo no necesariamente coincide con marca |

**Primera recomendación: POC HyperFrames vs givemotion**, con Motion Canvas como alternativa sólida si la sincronía fina de diagramas es más importante. No sustituir FFmpeg ni el orquestador Python; el renderer candidato se ejecuta como módulo/subproceso interno sin servicio independiente. Mantener contratos Pydantic/SQLite, composición de audio/subtítulos y QA existente.

### Arquitectura visual objetivo

`VideoScript Pydantic -> VisualStoryboard (scene_type, semantic_intent, layout, data, timing, actions) -> renderer adapter (Pillow actual / HTML candidato) -> escenas renderizadas -> FFmpeg + WAV + subtítulos -> QA`.

Planificador de planos (reglas + IA) debe elegir entre: `decision_split`, `choice_tradeoff`, `timeline_clock`, `number_compare`, `cause_effect`, `flow_diagram`, `illustrated_concept`, `summary_reveal`. Para cada escena, generar eventos con tiempo relativo a narración real. Nunca inventar números para graficar; ejemplos hipotéticos marcados.

### Experimento comparativo obligatorio

- Misma muestra de 12–20 s del guion de costo de oportunidad (dos opciones, elegir/renunciar, costo invisible), branding azul-marfil-dorado y tipografía existente, 1080×1920/24–30 fps.
- Realizar 2 prototipos aislados, uno HyperFrames y otro givemotion. Opcional Motion Canvas como control, pero no implementar 3 pipelines de producción.
- Requisitos: textos centrados en tarjetas, sin clipping ni superposiciones con subtítulos; al menos tres recursos semánticos distinguibles, no icono '$ %' ni barras iguales arbitrarias; eventos visuales sincronizables con pista de audio; primer hook específico y cierre diferente; contenido determinista y testable.
- Medir tiempo de generación del código, tasa de layouts inválidos, duración render CPU, RAM pico, bytes de salida, mantenimiento de versiones, licencia/seguridad. Capturar frames clave e informes automáticos. Inspeccionar visualmente en escala móvil.
- Elegir **un solo** renderer ganador como dependencia interna tras informe; no reemplazar pipeline actual ni rebasar trabajos de Codex CLI sin aprobación.

Demos para revisar: https://hyperframes.heygen.com/ (videos tipo Explainer, Motion design), https://givemotion.org/ (muestras MP4 y comparación), https://motioncanvas.io/ y https://www.reactvideoeditor.com/remotion-templates.
