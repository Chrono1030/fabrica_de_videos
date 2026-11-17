# Política editorial, originalidad y puerta de publicación

Propósito: producir una explicación educativa **original y diferenciada** en cada video; la automatización no equivale a autorización de monetización.

## Investigación desde libros y fuentes

Se permite partir de ideas generales que aparecen en libros de economía o productividad, contrastándolas con otras fuentes y creando ejemplos, análisis, conclusiones y estructuras originales. No copiar o reescribir pasajes, capítulos, tablas, ilustraciones, secuencias distintivas, títulos engañosos ni usar marcas para sugerir afiliación. Una paráfrasis superficial no es suficientemente transformativa. No existe un porcentaje universal de cambios que elimine riesgos de copyright. Las excepciones por cita/comentario dependen de jurisdicción y hechos; si son necesarias citas o material protegido, hacer revisión específica.

Cada job guarda: source_id, tipo de fuente, URL/obra, autor, idea general consultada, afirmaciones a verificar, evidencia, fecha de consulta y decisiones editoriales. Preferir temas atemporales, ejemplos numéricos explícitamente hipotéticos y explicaciones con matices. No imputar ideas inventadas a autores.

## Política de elegibilidad aspiracional

La política YouTube sobre inauthentic content prohíbe monetizar contenido masivo/repetitivo que aporte escaso valor, incluso si cada texto se genera mediante IA. Reused content requiere aportes originales sustanciales. El cumplimiento automático NO certifica elegibilidad: la plataforma evalúa el canal completo.

Para aprobar un guion debe incluir: problema específico, explicación no genérica, ejemplo propio pertinente, conexión lógica y conclusión útil. Las escenas deben variar por contenido, no solo colores/cifras. No aprobar repetición de hooks, estructura, ejemplificación o narrativa por simple cambio de términos. Mantener historial semántico y reglas deterministas; verificación factual independiente cuando existan afirmaciones sensibles.

## Gate técnico y editorial

Valores iniciales **de producto**, configurables tras piloto:
- Video vertical 1080x1920; MP4 H.264/AAC, 60–90 s, audio audible, subtítulos inferiores legibles sin solapamientos, decodificación FFmpeg, sin watermark ajeno.
- 1 publicación diaria máxima inicial; tolerar días sin publicación si no existe contenido válido.
- Todo título claro, original, no engañoso; descripción informativa y sin enlaces fraudulentos; hashtags pertinentes (pocos y sin spam); thumbnail compatible con Shorts y política de plataforma.
- Metadatos completos y revisados: language es-419 cuando sea aceptado, categoryId, audience/madeForKids evaluado (canal para adultos no implica automáticamente que cada video sea no apto para menores), licencia, privacidad y flag de medios sintéticos cuando corresponda.
- TTS y cada recurso gráfico/musical con licencia y procedencia verificadas; sin música por defecto.
- No consejos financieros personalizados, garantía de retorno, presión de inversión ni datos de mercado inventados.
- Fallo de cualquiera de estos criterios => BLOCKED_CONTENT, BLOCKED_LICENSE, BLOCKED_PERMISSION o REVIEW_REQUIRED; NUNCA publicar silenciosamente.

Para pruebas API y primera publicación usar privacyStatus=private explícito. Importante: desde 2026-11-02, YouTube API ya no fuerza private para proyectos sin verificar; el valor por defecto de la API puede ser public. Paso a público solo tras autorización y validación de publicación.

Cuando el video haya sido **alterado o generado sintéticamente de modo realista** y cumpla criterios de declaración, completar el indicador de plataforma. No asumir que todo video con TTS/ilustraciones abstractas exige la misma divulgación; revisar política por video.

## Indicadores de control

Registros por trabajo: cantidad de afirmaciones sustentadas, pendientes, razones de bloqueo, hash de guion, similitud temática, similitud de estructura, tipo de ejemplo, recursos usados, checklist, revisión requerida, resultado del uploader. Revisar manualmente los primeros cinco videos finales y los cinco primeros uploads privados.

## Fuentes oficiales

https://support.google.com/youtube/answer/1311392
https://support.google.com/youtube/answer/72851
https://support.google.com/youtube/answer/15424877
https://support.google.com/youtube/blog/424874071/updates-to-ai-content-disclosure-and-labels
https://developers.google.com/youtube/data/revision_history
