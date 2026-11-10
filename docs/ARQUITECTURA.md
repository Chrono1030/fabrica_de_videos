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
