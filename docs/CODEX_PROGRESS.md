# Progreso de implementación

## Fase 1 — registro histórico

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


## Fase 1.5 — completado en Codex Cloud

- Subtítulos SRT fragmentados, ASS con coordenadas explícitas y quemado FFmpeg;
  estilo y margen configurables, pista seleccionable alternativa sin duplicación.
- Ajuste de textos por medidas, reserva inferior, barras/líneas animadas,
  números progresivos y fundidos. Inspección visual de fotogramas realizada.
- SQLite con 50 ideas originales, diez categorías, reserva atómica por trabajo,
  persistencia, historial, prioridades y reintentos con la misma reserva.
- Historial de guiones con comparación determinista; rechazo documentado de
  similitud, repetición, datos no identificados y referencias no verificadas.
- GitHub Actions configurado con pruebas y Ruff; test completo local: **21 pasan**.
  Incluye concurrencia de 20 reservas, persistencia, selección automática completa,
  diferencias de píxeles con subtítulos quemados, alternativa seleccionable y animación.
- Demos A y B distintas: `out/fase15/jobs/demo-a-final/final.mp4` y
  `out/fase15/jobs/demo-b-final/final.mp4`, 1080×1920, cuatro escenas y audio
  simulado. Sus controles ffprobe/decodificación se guardan en `result.json`.

### Límites vigentes

No hay voz humana en MOCK, alineación fonética, verificación semántica independiente
ni publicación. Las dos plantillas MOCK no cubren los 50 temas: nuevas producciones
con la misma plantilla se bloquean por similitud. La revisión de referencias es
conservadora: no se comprueban bibliografías por red y toda referencia requiere
revisión. Las cifras solo se admiten automáticamente si se identifican como
hipotéticas; las fuentes reales quedan para un flujo de verificación futuro.

SQLite coordina procesos con la misma base local; no hay coordinación distribuida.
Los fundidos pasan por el fondo oscuro, no hay transiciones solapadas. La animación
usa hasta 72 cuadros intermedios por escena para limitar trabajo y disco. Los
subtítulos se distribuyen por cantidad de palabras, sin sincronización fonética;
fuentes alternativas requieren revisión manual. La seguridad de interfaz debe
revisarse si una plataforma cambia sus superposiciones.

La API de GitHub respondió `Forbidden`: no se pudo consultar/editar el cuerpo del
PR ni confirmar resultados remotos de Actions. Publicar la rama actualiza los
commits del PR que apunte a ella. El workflow está verificado localmente por sus
comandos; no se presenta como una ejecución remota confirmada.
