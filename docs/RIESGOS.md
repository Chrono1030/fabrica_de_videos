# Matriz de riesgos

| ID | Riesgo | Severidad | Mitigación |
|---|---|---|---|
| R1 | Copiar expresión protegida de un libro | Alta | Ideas generales, guiones y ejemplos originales, sin resúmenes capítulo a capítulo |
| R2 | Monetización rechazada por repetición | Alta | Aportes originales, ejemplos distintos y control de similitud editorial |
| R3 | TikTok no permite publicación pública | Alta | API oficial, autorización, auditoría y consentimiento; bloquear mientras no se obtengan |
| R4 | Información económica inexacta | Alta | Evitar actualidad sin fuentes; verificación semántica y cuarentena |
| R5 | Licencias de voz, música o iconos | Alta | Inventario, revisión por activo y sin música por defecto |
| R6 | Consumo imprevisto de GPT API | Media | Metering, presupuesto transaccional, límite de concurrencia y alertas |
| R7 | Pronunciación artificial o incorrecta | Media | Benchmark de voz es_MX, normalización de cantidades y siglas |
| R8 | Audio/video desincronizado o ilegible | Media | ffprobe, decodificación completa, márgenes y duración basada en WAV |
| R9 | Publicaciones duplicadas | Alta | Idempotencia, hashes, estado persistente, verificación remota |
| R10 | Secretos filtrados | Alta | Volúmenes privados, cifrado, .gitignore, permisos mínimos |
| R11 | Caída del servidor o disco lleno | Media | Backups, reintentos acotados y Uptime Kuma |
| R12 | Contenido sintético engañoso | Alta | Etiquetado apropiado, sin identidades simuladas |
| R13 | Retorno comercial negativo | Alta | Piloto de 30 publicaciones, seguimiento de costo y criterio de parada |

## Fuentes normativas
- [Ley de propiedad intelectual argentina 11.723](https://www.argentina.gob.ar/normativa/nacional/42755/actualizacion)
- [YouTube: monetización de canales](https://support.google.com/youtube/answer/1311392)
- [TikTok: Content Posting API](https://developers.tiktok.com/docs/en/content-posting-api-reference-direct-post)

## Reglas operativas
Ante permisos incompletos, licencias inciertas, fuentes contradictorias o validación fallida: **no publicar**. Registrar causa, job_id, timestamps y severidad, y emitir heartbeat de incidente para Uptime Kuma.
