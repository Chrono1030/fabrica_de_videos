# Publicación y metadatos como módulos de la misma aplicación

YouTube es primera plataforma; TikTok se integra mediante un adaptador interno sujeto a autorizaciones. No depender de servicios externos de publicación ni automatización por navegador.

## Paquete publicable único

Esquema propuesto PlatformPackage: job_id, asset_hash, platform, channel_id, title, description, hashtags, tags, category_id, default_language, audience_setting, contains_synthetic_media, thumbnail_path, privacy, scheduled_at_utc, source_credits, publication_policy_version. Validación Pydantic local con reglas específicas por plataforma.

Metadatos generados desde el guion VERIFICADO, no sobreprometer el contenido. Título: idea concreta y términos de interés real, sin promesas de enriquecimiento ni clickbait engañoso. Descripción: síntesis útil, fuentes cuando corresponda, disclaimer educativo no intrusivo y crédito de recursos si una licencia lo exige. Hashtags pocos, pertinentes y no repetitivos, sin copiar listas de tendencia indiscriminadamente. Registrar variantes para futuros tests; no generar docenas de publicaciones duplicadas. Elegir categoryId mediante videoCategories.list cuando se configure región, no inventar IDs.

YouTube Shorts: vertical 9:16, objetivo 60–90 s, máximo actual de Shorts hasta 3 minutos según política, idioma español latinoamericano. Controlar margen de subtítulos, duración, legibilidad, audiencia y medios sintéticos. Los parámetros de portada/miniatura dependen de capacidades de plataforma; desde 2026-11-03 thumbnails.set soporta custom thumbnails para Shorts tras procesamiento, sujeto a condiciones de API. Probar antes de depender de ello.

## YouTube OAuth y seguridad

Una cuenta propietaria humana, un proyecto Google Cloud, cliente OAuth2 adecuado, scope mínimo compatible con upload. NO cuenta de servicio para cargas al canal. Inicio de autorización interactivo una vez, refresh seguro automático, detección de revocación/expiración, secretos cifrados y separados del repositorio. En OAuth externo Testing los refresh tokens pueden expirar en 7 días, por lo que el entorno definitivo debe ser evaluado antes de dejarlo desatendido. Guardar channel_id obtenido de channels.list(mine=true) y confirmar coincidencia con el configurado antes de cada upload.

API: google-api-python-client, google-auth-oauthlib y google-auth; usar videos.insert resumable, videos.list para estado, thumbnails.set cuando corresponda, videos.update para programar solo con controles estrictos. Google ha cambiado cuotas: consultar documentación y consola en cada fase; a noviembre 2026 la referencia indica bucket de 100 videos.insert/día y 1 unidad por llamada; NO conservar números antiguos de 1600 por insert como certeza actual.

**Crítico (cambio 2026-11-02):** videos.insert puede crear un video público por defecto. En todo upload de pruebas enviar explicitamente status.privacyStatus=private. Verificar respuesta remota y estado privado. No habilitar autopublicación pública por defecto. status.publishAt requiere private y nunca publicado; verificar fecha futura para evitar publicación inmediata.

## Idempotencia y recovery

Persistir SQLite por plataforma: job_id, publish_attempt_id, channel_id, media_sha256, upload_session_uri (secret privado), upload_cursor, external_video_id, privacy, publish_at, status, attempt_count, last_error, updated_at. UNIQUE(platform, channel_id, job_id). Hash del artefacto y paquete editorial.

Antes de POST: bloquear fila y confirmar que no existe un upload completado para job. Tras desconexión consultar sesión resumable: HTTP 308 y Range; NO iniciar nuevo insert a ciegas si el estado remoto es incierto. Ante éxito guardar external_video_id y consultar API. Ante error de cuota/permiso bloquear o reintentar acotadamente según clasificación; nunca repetir upload sin reconciliación. Separar UPLOADED_PRIVATE, PROCESSED, SCHEDULED, PUBLISHED y BLOCKED.

Config: PUBLISH_ENABLED=false y PUBLISH_MODE=private por defecto. Un cambio a publicación pública requiere aprobación explícita y test de integración, no basta con pasar ffprobe.

## TikTok (después de YouTube)

Evaluar TikTok Content Posting API Direct Post, scope video.publish, creator_info, requisitos de consentimiento y permisos de privacidad. Sin auditoría los posts están restringidos a privado; además no asumir que un flujo autónomo sin confirmación individual del creador es compatible con requisitos de producto. Mantener TIKTOK_PUBLISH_ENABLED=false y estado BLOCKED_PERMISSION hasta verificar autorización y compatibilidad del caso de uso. No automatizar web UI para eludir restricciones.

## Pruebas

Unitarias: validación de paquete, títulos engañosos, duplicados, fechas, ID de canal, privacidad y flags. Contratos: SDK con dobles de 308/403/429/5xx, timeout tras completar upload, errores de OAuth y recuperación sin duplicados. Integración real con cuenta autorizada: upload privado comprobado remotamente; solo después permitir publicación programada de prueba.

Referencias:
- https://developers.google.com/youtube/v3/docs/videos/insert
- https://developers.google.com/youtube/v3/docs/videos
- https://developers.google.com/youtube/data/revision_history
- https://developers.google.com/youtube/data/determine_quota_cost
- https://developers.google.com/youtube/data/guides/using_resumable_upload_protocol
- https://developers.google.com/youtube/data/guides/authentication
- https://developers.google.com/identity/protocols/oauth2
- https://developers.tiktok.com/docs/en/content-posting-api-reference-direct-post
