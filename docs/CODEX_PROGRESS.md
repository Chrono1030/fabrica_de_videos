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

## Fase 2A — integración local, voz real pendiente

Ver [auditoría, licencias y comandos](PHASE2_PIPER.md). Piper 1.8.0 instalado;
proveedor con API Python persistente, timeout cancelable, WAV atómico y duración
verificada. Normalización contextual de ARS/USD, cantidades, fechas y siglas;
modo `local` que exige guion JSON y no utiliza GPT. Reanudación identifica voz,
velocidad, paquete y hashes de modelo/configuración/revisión de licencia.

Guion original de costo de oportunidad: cinco escenas, 185 palabras. Vista previa
MOCK de 75.083 s a 1080×1920 generada y decodificada; fotograma inspeccionado.
**No es el video final con narración real.** No se descargaron modelos: las fichas
es_AR/es_MX revisadas presentan restricciones de base o procedencia incompleta.
Comparación auditiva, benchmark de voces y video Piper quedan pendientes hasta
contar con una voz autorizada. No hubo llamadas GPT ni publicaciones.

Validación final: **37 pruebas aprobadas**, `ruff check .`, compilación Python y
`git diff --check` aprobados. La prueba nativa de Piper usa un modelo inválido
para comprobar errores; no certifica la síntesis ni la calidad de una voz real.

## Iteración integrada — Mente y Capital (17/11/2026)

Base auditada: rama Piper con cambios locales intactos; Ruff y **37 pruebas**
reproducidos. Piper 1.8.0, ONNX Runtime 1.32.0, Python 3.12.3, Pydantic 2.14.3,
Pillow 12.3.0, num2words 0.5.14. Persistencia del catálogo y render FFmpeg existente
conservados. Se preservó el estado en commit `8349a52` en la rama Piper y se creó
`codex/phase2-integrated-factory` desde ese commit.

Se leyeron los seis documentos del PR 2 a `638dc05`, sin merge. Marca pública:
Mente y Capital. No se comprobó handle ni se crearon cuentas. No se tocó Rocky
Linux, Docker Desktop ni infraestructura del propietario.

### Implementado y probado

- Paquetes Pydantic con título/descripcion extractivos, idioma, categoría editorial,
  público, declaración sintética justificada, portada, recursos/hashes y fuentes.
  Control de repetición exacta y similitud textual >=0.90; no generación paga.
- Calendario SQLite con zona IANA, hora/frecuencia, un slot por día, reserva conjunta
  de tema y trabajo, lock del trabajador, recuperación, backoff y slots vencidos.
  APScheduler comparado; no necesario para el caso de un único trabajador diario.
- Publicador MOCK persistente y exclusivamente privado. Sesión y cursor, ID remoto
  simulado, intentos/eventos, conciliación y cuarentena ante incertidumbre.
  SDK oficial 2.202.0 instalado y preparación de MediaFileUpload ejecutada sin red.
- Pruebas de éxito, conexión, cuota, token caducado, respuesta incierta, cursor
  parcial, reinicio tras upload, trabajo ya cargado, canal equivocado, rechazo
  editorial, pérdida de sesión inicial, backoff/límite y cambio remoto de privacidad.
  Todas comprueban ausencia de reinserciones ciegas; solo cliente MOCK habilitado.
- Métricas SQLite por job: tiempos, CPU/hijos, memoria aproximada, disco, API/costos,
  errores/reintentos y horas humanas (`null` si no registradas). Escenarios
  pesimista/base/optimista con RPM y elegibilidad explícitos, equilibrio y margen;
  ingreso real separado y desconocido sin fuente oficial.
- Registro local de versiones, licencias, cadena y hashes de voces. Kokoro 0.9.4
  evaluado con dry-run sin dependencias; no instalado ni sintetizado. Voces Piper
  es_AR/es_MX y Kokoro españolas siguen sin autorización comercial completa.
- CLI `calendar`, `cycle`, `metrics`, `economics` y `voice-register`, dentro de
  `fabrica`. Simulación sin credenciales ni modelos; no n8n.

Demo: `out/integrated-demo/jobs/slot-8e1c55a30251599ab528a5b936bb4097/final.mp4`.
1080×1920, 75.083333 s, H.264/AAC, gráficos y subtítulos inferiores. Decodificación
completa aprobada; fotograma de 36 s inspeccionado. Paquete `metadata.json`, request
local `upload_request.json` y registro `publication.json` disponibles. ID
`mock-video-cccbc310fc8c61c6`, estado SIMULATED_PRIVATE_VERIFIED. Reejecutar mismo
slot devuelve IDLE y no crea otro upload. **Son tonos MOCK y publicación simulada.**

Validación final: **68 pruebas aprobadas en 59.55 s**, `ruff check .`,
`compileall`, `git diff --check` y `pip check` aprobados. Los originales 37 tests
se conservan. No se ejecutó GitHub Actions remoto, OAuth, GPT pago ni cargas reales.

### Límites que permanecen

Solo dos temas del catálogo tienen plantillas MOCK compatibles; no se presenta
como generación automática de guiones nuevos para 50 temas. Las fuentes y la
originalidad semántica requieren revisión independiente. La portada no se cargó
remotamente; categoría 27 es fixture educativa pendiente de consulta regional real.
El calendario es un tick CLI reanudable, sin servicio instalado en el host.
SQLite/locks son locales, no coordinación distribuida.

La prueba SDK prepara medios y payload, pero no prueba transporte HTTP, OAuth ni
protocolo real 308. La idempotencia simulada no certifica exactly-once de YouTube;
una sesión perdida queda en cuarentena. La voz comercial, muestras reales,
benchmark auditivo y acento autorizado siguen pendientes. No se aprobó cambiar a
es_ES ni habilitar publicación pública. Se documentaron umbrales de entrada,
actividad y mantenimiento mensual de Shorts anunciados para febrero de 2027 con
fuentes oficiales, sin asumir monetización del canal.

Especificaciones y comandos: [INTEGRATED_FACTORY.md](INTEGRATED_FACTORY.md),
[METADATA_CONTRACT.md](METADATA_CONTRACT.md),
[SCHEDULER_ARCHITECTURE.md](SCHEDULER_ARCHITECTURE.md),
[YOUTUBE_PUBLISHER.md](YOUTUBE_PUBLISHER.md),
[TTS_COMMERCIAL_AUDIT.md](TTS_COMMERCIAL_AUDIT.md),
[VIABILITY.md](VIABILITY.md), [DEPENDENCY_REUSE.md](DEPENDENCY_REUSE.md).
