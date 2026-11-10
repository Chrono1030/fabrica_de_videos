# Arquitectura de software

```text
n8n (schedule / disparador)
  -> coordinador Python
     -> catálogo editorial + SQLite
     -> GPT API -> contrato Pydantic -> QA editorial
     -> Piper TTS es_MX
     -> escena Pillow/SVG -> FFmpeg -> ffprobe QA técnico
     -> YouTube / TikTok (publicadores oficiales)
     -> registros JSONL/SQLite y métricas de gasto
  -> Uptime Kuma (HTTP /healthz + heartbeat de trabajo exitoso)
```

## Máquina de estados
`NEW → RESEARCHED → SCRIPTED → VALIDATED → VOICED → RENDERED → QA_PASSED → PUBLISH_PENDING → PUBLISHED → MEASURED`.

Errores: `RETRYABLE_ERROR`, `BLOCKED_CONTENT`, `BLOCKED_PERMISSION`, `BUDGET_EXCEEDED`, `QUARANTINED`.

Cada transición debe persistirse transaccionalmente. Conservar hash SHA-256 del guion/MP4, clave de idempotencia y external_video_id. Nunca repetir un upload sin comprobar el estado remoto.

## Contrato
VideoScript: topic, title, description, language (es-419), hook, scenes, disclaimer, references.
Scene: narration, visual_type, headline, visual_label, visual_data.
Tipos inicialmente soportados: concept, big_number, comparison y bar_chart.
Los gráficos de cifras reales exigen fuente; usar ejemplos hipotéticos etiquetados cuando no haya fuentes verificadas.

## Diseño visual
1080×1920 con márgenes seguros, fondo azul oscuro, acentos dorados, texto marfil. Las escenas siguen la longitud de la narración WAV, no una duración supuesta por GPT.

## Seguridad
- Credenciales fuera del repositorio y fuera de logs; almacenamiento cifrado y permisos mínimos.
- Control de llamadas, presupuesto, timeout, backoff y circuit breaker.
- Solo URL de investigación desde dominios permitidos; prevenir SSRF.
- n8n no recibe el socket Docker.
- Sin publicación fuera de QA_PASSED; comprobar identificador real del canal.
- Contenedores con mínimos privilegios, SELinux y bind mounts con contexto adecuado.

## Operabilidad
Uptime Kuma monitorea disponibilidad y heartbeat de **último trabajo exitoso**. SQLite/JSONL conserva el detalle editorial y económico; un HTTP 200 por sí solo no prueba que se esté publicando. Dimensionar CPU, RAM y disco antes de asumir que el servidor renderizará 1080×1920 con fluidez.


## Componentes locales implementados (Fase 1.5)

`cli → Catalog.reserve → pipeline.produce → Catalog.review → Pillow/TTS →
SRT/ASS → FFmpeg → quality → Catalog.finish`.

`catalog.py` usa tablas topics, history y scripts. UNIQUE(title normalizado) y
UNIQUE(job_id), junto a BEGIN IMMEDIATE, hacen la reserva idempotente. Historial
conserva eventos y motivos; BLOCKED retiene la asociación para reintento. El
registro de guiones se inserta transaccionalmente tras controles deterministas.
El estado audiovisual JSON conserva hashes por etapa; un trabajo reservado y su
producción no forman una transacción larga: un corte se recupera por job_id.

El estilo de subtítulos se serializa en la configuración del trabajo. SRT conserva
fragmentos de dos líneas y ASS define PlayRes 1080×1920; burn y track son alternativas.
El quemado requiere una segunda codificación de video. Los gráficos se sitúan
por encima de la reserva inferior y los textos se ajustan por ancho real.

Las transiciones listadas anteriormente describen el objetivo de producción.
Actualmente el terminal técnico es TECHNICALLY_READY, con REQUIRES_REVIEW y
publish_enabled=false. El QA editorial determinista no certifica hechos; todos
los publicadores y la revisión semántica independiente siguen pendientes.
