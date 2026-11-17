# Producto único: Fábrica de Videos

Estado: decisión arquitectónica aprobada por el propietario. No confundir objetivos con código ya implementado.

## Principio

Una **sola aplicación** Python, un repositorio, una base de estado SQLite y un ciclo automatizado desde idea hasta publicación y medición. Los módulos internos no son herramientas que el operador deba administrar por separado. FFmpeg, TTS y SDK de plataformas son dependencias internas. Docker y Uptime Kuma son infraestructura externa, no productores.

El motor de programación será **interno**, evaluando APScheduler o planificador propio sobre SQLite; **n8n no es requisito del MVP**. El despliegue final sigue previsto en Rocky Linux, pero el desarrollo ocurre en WSL/Codex. Solo un trabajador publica en cada plataforma/canal.

## Pipeline objetivo

1. SCHEDULER: disparar según zona horaria configurada, registrar slot y lock.
2. IDEA: reservar un concepto del catálogo, priorizar diversidad, demanda y ausencia de duplicados.
3. RESEARCH: reunir conceptos generales, evidencia y licencias de fuentes autorizadas; libros solo como inspiración para análisis original.
4. SCRIPT: GPT genera guion Pydantic y variantes de gancho, con costo presupuestado.
5. EDITORIAL_QA: verificación independiente de afirmaciones, originalidad, derechos y contenido no masivo/repetitivo; fail-closed.
6. VOICE: TTS local con voz comercialmente autorizada; guardar procedencia, versión, hash, duración y WAV.
7. VISUALS: escenas y gráficos originales; no inventar estadísticas.
8. RENDER: FFmpeg H.264/AAC 1080x1920, subtítulos cinematográficos inferiores, portada/thumbnail.
9. PACKAGE: generar y validar título, descripción, hashtags, categoría, idioma, público y declaraciones aplicables por red.
10. TECHNICAL_QA: ffprobe, decodificación, duración, zonas seguras, comprobación de audio/texto y licencias.
11. PUBLISH: publicadores nativos YouTube primero, TikTok sujeto a autorización/consentimientos; idempotencia y privacidad explícita.
12. MEASURE: guardar IDs, URLs, estado remoto, costos y métricas de rendimiento, con reintentos y alertas.

Estados orientativos: NEW, RESERVED, RESEARCHED, SCRIPTED, REVIEW_REQUIRED, CONTENT_APPROVED, VOICED, RENDERED, PACKAGED, READY, UPLOAD_PENDING, PRIVATE_UPLOADED, SCHEDULED, PUBLISHED, MEASURED; BLOCKED_CONTENT, BLOCKED_LICENSE, BLOCKED_PERMISSION, BLOCKED_COST, FAILED_RETRYABLE, QUARANTINED.

## Roadmap integrado

| Etapa | Entregable | Criterio |
|---|---|---|
| A: Base local | Fase 1.5: catálogo, escenas, subtítulos, tests | 21 tests reportados; reproducir en WSL y CI |
| B: Voz y evidencia | Piper/Kokoro o alternativa con derechos verificados | Un video de 60–90 s con narración real y documento de licencia |
| C: Guiones y QA | GPT API, investigación trazable, filtro de repetición | Distintos temas generan guiones y ejemplos genuinamente diferentes; bloqueo ante duda |
| D: Paquete social | Metadatos/thumbnail validados, calendario interno SQLite | Un job genera paquete publicable sin intervención rutinaria |
| E: YouTube privado | OAuth, carga reanudable, prueba privada | Se comprueba canal y remote_video_id, sin duplicados |
| F: Piloto supervisado | Publicaciones públicas tras QA y autorización | 10 publicaciones consecutivas sin defectos; hasta 30 para medir demanda |
| G: Autonomía | Política revisada y monitoreo | Publica desatendido SOLO si todos los controles de seguridad están satisfechos |
| H: TikTok | Adaptador oficial y consentimiento/auditoría | Sin post público si el uso requerido no está autorizado |

No activar autopublicación hasta completar E y pasar puertas editoriales. La seguridad prevalece sobre publicar a diario.

## MVP y fuera de alcance

MVP: un canal YouTube, idioma es-419, Shorts orientativos de 60–90 s, una producción diaria como máximo inicial, SQLite y una sola instancia Python, plataforma externa YouTube; TikTok preparado pero bloqueado hasta aprobación. Sin panel complejo, múltiples canales ni analítica avanzada.

Posterior: analítica profunda, optimizador de horarios, multi-canal, videos largos, campañas de experimentación avanzada, ingresos y ERP.

## Decisiones del propietario y pendientes

Confirmado: aplicación única; una persona propietaria; costos mínimos y máxima automatización operativa; economía/dinero/productividad en español; contenido original inspirado en conceptos generales de libros; meta de monetización sin prometer elegibilidad; YouTube primero; TTS local solo con derechos documentados.

Pendiente de selección: marca y @handle disponibles, voz concreta, cuenta Google/Brand Account, presupuesto mensual de API, horario inicial, métrica de éxito del piloto, umbral de similitud, y aprobación para primeras publicaciones públicas. No inventar decisiones en configuraciones.

## Referencias

- YouTube inauthentic/reused content: https://support.google.com/youtube/answer/1311392
- YouTube Shorts: https://support.google.com/youtube/answer/15424877
- YouTube upload API: https://developers.google.com/youtube/v3/docs/videos/insert
- TikTok Direct Post: https://developers.tiktok.com/docs/en/content-posting-api-reference-direct-post
