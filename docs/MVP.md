# MVP — definición verificable

## Objetivo
Probar producción autónoma **de extremo a extremo** a ritmo de un video diario, con intervención únicamente para configurar credenciales, consentimientos, corrección de fallos excepcionales y mantenimiento. Este objetivo **no está implementado aún**.

## Flujo de producción
1. n8n dispara el planificador y elige un tema aún no publicado.
2. La API de GPT produce un JSON estructurado y verificable.
3. Se ejecuta QA editorial; afirmaciones inciertas o contenido no original se bloquean.
4. Piper sintetiza escenas en español latinoamericano y registra duraciones reales.
5. El motor Python produce ilustraciones, números, comparaciones y gráficos con datos hipotéticos identificados.
6. FFmpeg ensambla MP4 1080×1920 (H.264/AAC), subtítulos y portada.
7. ffprobe y pruebas de decodificación comprueban duración, video, audio y subtítulos.
8. YouTube recibe el video mediante OAuth y API oficial; TikTok únicamente cuando cuente con permisos y condiciones adecuadas.
9. Se almacenan costos, errores y evidencia de publicación; Uptime Kuma vigila el servicio y los éxitos de ejecución.

## Definición de terminado
- 10 videos consecutivos originales procesados sin edición manual.
- MP4 vertical 1080×1920 decodificable y con audio; duración 60–90 s y subtítulos sincronizados.
- Sin publicaciones duplicadas tras reintentos, reinicios o interrupciones.
- Cada corrida registra ID, estado, fecha, presupuesto, consumo y URL del video.
- Verificación editorial independiente del LLM que genera el guion; bloqueos ante dudas de fuentes o licencias.
- YouTube completa una publicación real de prueba con cuenta autorizada.
- TikTok queda en BLOCKED_PERMISSION hasta autorización y auditoría; no se simula publicar.
- Voz local de español latinoamericano y licencia de uso comercial verificadas.
- Presupuesto máximo interno objetivo para piloto de API: USD 5; no equivale a un límite duro garantizado por el proveedor.

## Piloto de producto
30 días, máximo 30 videos originales, una cuenta por plataforma. Métricas de costo por video, fallas, intervención, retención y vistas cuando se disponga legalmente de los datos.

## No implementar
Dashboard alternativo a Uptime Kuma, múltiples canales, analítica avanzada, APIs estadísticas, generación comercial de clips y videos largos.
