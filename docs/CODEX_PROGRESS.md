# Fase 1 — implementación y evidencia

## Implementado

- CLI `produce` → guion Pydantic → tarjetas Pillow → TTS intercambiable → WAV
  medidos → SRT → segmentos FFmpeg → MP4 → ffprobe y decodificación completa.
- 1080×1920 por defecto; 9:16 reducido para tests. H.264, AAC y mov_text.
- Trabajo identificado, registro JSON atómico, bloqueo de proceso, hashes por
  etapa, recuperación de archivos dañados y reanudación sin repetir etapas válidas.
- Reglas editoriales preliminares separadas del QA técnico. Un fallo bloquea el
  trabajo; la revisión editorial queda pendiente incluso con QA técnico aprobado.
- Responses API configurable, tokens reportados, estimación de costos, reserva
  conservadora persistente de presupuesto. Costo incierto bloquea reintentos.
- MockTTS determinista y explícitamente simulado. Piper con validación de idioma
  de metadatos, timeout y normalización preliminar de cantidades/símbolos/siglas.
- Gráficos requieren magnitudes explícitas; no se inventan alturas a partir del
  orden de las etiquetas. Animación de cámara y fundidos por segmento.

## Validación en Codex Cloud

FFmpeg y ffprobe instalados. El demo `out/jobs/demo-entrega-1080/final.mp4` se generó
realmente a 1080×1920, con cuatro WAV de un segundo, tonos simulados, imágenes,
subtítulos integrados y decodificación completa. No está versionado.

**Resultado: 15 tests pasados** en Codex Cloud; comprobación estática de imports y errores Python pasada en los archivos de implementación.

La suite prueba contrato y rechazo de guiones, visuales, determinismo y duración
WAV, Responses API mediante dobles, consumo y reserva de costos, timeout,
bloqueo/reintento, corrupción y recuperación, Piper mediante doble local y
producción completa con FFmpeg real. No requiere cuentas ni red externa.

## Límites y pendientes

- GPT y voz Piper reales no ejecutados: pruebas con dobles no validan servicios
  reales, autenticación, voz, licencia ni calidad de pronunciación.
- MOCK usa una plantilla educativa fija de costo de oportunidad y tonos; no
  sintetiza narración humana ni genera contenido semántico de cualquier tema.
- Normalización textual inicial: no es un verbalizador lingüístico completo de
  números, siglas arbitrarias o monedas regionales.
- Zoom, fundidos y contador numérico progresivo implementados; animación de
  series y transiciones solapadas entre escenas quedan pendientes.
- Subtítulos por escena, sin alineación fonética. Pueden necesitar edición de
  líneas o tamaño en el reproductor. No se incrustan visualmente en los píxeles.
- Validación editorial semántica independiente, licencias y referencias requieren
  revisión; no hay publicación, planificación n8n ni monitoreo de producción.
- Recuperación y presupuesto son locales a una raíz, con bloqueos POSIX. No hay
  coordinación distribuida ni conciliación automática de llamadas inciertas.
- Configuración reutilizable cloud no se modifica en esta tarea. No se accedió
  a Rocky Linux ni se solicitaron credenciales.
