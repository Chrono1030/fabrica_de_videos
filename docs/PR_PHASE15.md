## Fase 1.5: calidad audiovisual y catálogo editorial

Extiende el pipeline local con subtítulos cinematográficos quemados configurables, alternativa de pista seleccionable sin duplicación, barras/líneas animadas, ajuste de texto y zona inferior reservada. Mantiene SRT y tiempos aproximados derivados de WAV reales.

Añade SQLite con 50 ideas originales, reservas atómicas por trabajo, historial de producción y controles deterministas de similitud, repetición, contenido incompleto, referencias no verificadas, cifras y compatibilidad gráfica. Los rechazos quedan registrados y la publicación sigue deshabilitada.

### Validación

- 21 pruebas locales pasan, incluidos FFmpeg real, decodificación MP4, concurrencia de reservas, persistencia, reanudación, subtítulos quemados frente a pista y animación de gráficos.
- Dos demos distintas 1080×1920 de 24 segundos con audio simulado y subtítulos visibles; imágenes inspeccionadas en Codex Cloud. Medios excluidos de Git.
- Ruff (errores Python e imports) y git diff --check pasan.
- Workflow GitHub Actions añadido; ejecución remota no confirmada por denegación de API.

### Límites

No se validaron GPT ni Piper reales. Las dos plantillas MOCK no cubren todos los temas del catálogo. Los subtítulos usan distribución por palabras, sin alineación fonética. La verificación editorial determinista no prueba hechos ni originalidad y bloquea referencias pendientes. Sin publicación, acceso a Rocky Linux ni llamadas pagas.
