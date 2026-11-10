# Fábrica de videos

**Estado:** pipeline audiovisual local de Fase 1 implementado y probado en modo MOCK. **No desplegado; integraciones reales y publicación pendientes.**

Proyecto para producir automáticamente videos cortos educativos en **español latinoamericano** sobre economía, finanzas personales, hábitos y productividad, inspirados en conceptos generales de libros, pero con guiones originales. El flujo previsto es:

`Programador → catálogo editorial → GPT API (guiones estructurados) → validación → TTS local → escenas SVG/Pillow → composición FFmpeg → control de calidad → API de publicación → registro y alertas`

## Decisiones aprobadas

- **Automatización de extremo a extremo**, con bloqueo seguro y alertas cuando haya errores o dudas.
- **OpenAI API por consumo**, con registro por ejecución y presupuesto inicial de ensayo.
- **Piper** como candidato prioritario a narración local en español latinoamericano; Kokoro TTS como alternativa a evaluar, tras verificar voces y licencias.
- **Identidad visual:** minimalismo, azul oscuro, marfil y acentos dorados; gráficos y figuras programáticas; sin generación comercial de clips.
- **Investigación:** contenidos conceptuales y atemporales; sin conexión obligatoria a APIs de indicadores económicos.
- **Orquestación:** n8n + Python; estados y auditoría internos, disponibilidad mediante Uptime Kuma.
- **Piloto:** 1 short de 60–90 s diarios, 1080 × 1920, hasta 30 videos para validar costos y respuesta de audiencia.
- **Publicación:** YouTube por API oficial tras credenciales y permisos. TikTok por Content Posting API solo cuando obtengamos autorización para visibilidad pública.

## Contenido del repositorio

- `docs/PRODUCTO.md`: visión, alcance y requisitos.
- `docs/MVP.md`: criterios de aceptación.
- `docs/ARQUITECTURA.md`: componentes, estados y tolerancia a fallos.
- `docs/RIESGOS.md`: riesgos técnicos, legales y operativos.
- `docs/POLITICA_EDITORIAL.md`: originalidad, calidad y comprobación.
- `docs/IMPLEMENTACION.md`: preparación y secuencia de integración.
- `docs/ROADMAP.md`: tareas y fases.
- `src/fabrica/`: prototipo de esquema, validación y tarjetas gráficas.
- `examples/guion_demo.json`: guion de prueba estructurado.

## Inicio rápido (prototipo; requiere dependencias locales)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
python -m fabrica.cli validate examples/guion_demo.json
python -m fabrica.cli cards examples/guion_demo.json --output out/cards
pytest -q
```

La narración real requiere instalar Piper y un modelo de voz con licencia adecuada. El render local está implementado; la publicación y la validación de integraciones reales siguen pendientes. No incorporar credenciales, tokens OAuth, modelos ni videos al control de versiones.

## Referencias

- [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [YouTube videos.insert](https://developers.google.com/youtube/v3/docs/videos/insert)
- [YouTube: políticas de monetización](https://support.google.com/youtube/answer/1311392)
- [TikTok Content Posting API](https://developers.tiktok.com/docs/en/content-posting-api-reference-direct-post)
- [Ley argentina 11.723](https://www.argentina.gob.ar/normativa/nacional/42755/actualizacion)

## Fase 1: producción audiovisual local

El pipeline local ya produce **MP4 reales H.264/AAC**, tarjetas, WAV, subtítulos
SRT y subtítulos cinematográficos quemados (o pista seleccionable opcional). Requiere Python >=3.11, FFmpeg/ffprobe con
libx264 y una fuente DejaVu (paquetes Debian `ffmpeg fonts-dejavu-core`).
No necesita Docker, servidor ni credenciales para modo MOCK.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
fabrica produce --topic "El costo de oportunidad" --mode mock
# Prueba rápida de 4 escenas, 1 segundo de tono por escena:
fabrica produce --topic "El costo de oportunidad" --mode mock \
  --width 180 --height 320 --job-id prueba
# Repetir exactamente el comando reanuda el mismo trabajo.
pytest -q
```

`--output` selecciona la raíz de trabajos (por defecto `out/jobs`), `--job-id`
permite reanudar y `--script examples/guion_demo.json` utiliza un guion propio.
Sin identificador se crea uno nuevo. `--mock-seconds` controla exclusivamente la
longitud de los tonos de prueba. MOCK tiene dos plantillas originales: ahorro frente a ingresos (si el tema contiene ganar o ingreso) y costo de oportunidad para los demás temas. No genera contenido semántico arbitrario.

Cada trabajo contiene `script.json`, `cards/`, WAV por escena, `subtitles.srt`,
segmentos intermedios, `final.mp4` y `result.json`. El estado registra etapas,
hashes, errores, costos y controles. Las escrituras de estado son atómicas y hay
bloqueos locales contra ejecuciones simultáneas del mismo trabajo. Los archivos
verificados se reutilizan; los dañados se regeneran. No borrar el registro de
presupuesto para reintentar llamadas reales.

**MOCK genera tonos, no habla humana.** Cada escena identifica su audio como simulado en el primer fragmento de subtítulos.
La duración final deriva de WAV medidos. El modo real bloquea duraciones fuera de
60–90 segundos. Los controles técnicos no prueban exactitud, originalidad ni
licencia editorial: `TECHNICALLY_READY` conserva `REQUIRES_REVIEW` y publicación
deshabilitada. No existe comando de publicación.

### Integración REAL (pendiente de validación con servicios reales)

```bash
# Variables configuradas por un canal seguro; nunca guardar claves en Git.
fabrica produce --topic "El costo de oportunidad" --mode real
# Con guion local no se llama a GPT; sí se requiere Piper:
fabrica produce --topic "El costo de oportunidad" --mode real \
  --script examples/guion_demo.json
```

OpenAI usa Responses API y el esquema Pydantic; Piper requiere ejecutable,
modelo local y su JSON, voz `es_*` excepto `es_ES` y licencia revisada por el
operador. No se descargan voces automáticamente. Las variables no se cargan
automáticamente desde `.env`: exportarlas en la sesión de ejecución.

Variables: `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_MAX_OUTPUT_TOKENS` (4000),
`OPENAI_INPUT_USD_PER_1M`, `OPENAI_OUTPUT_USD_PER_1M`, `MAX_API_BUDGET_USD` (5),
`OPENAI_REQUEST_RESERVE_USD` (1), `PIPER_EXECUTABLE`, `PIPER_VOICE_MODEL`, `FONT_PATH`.
FFmpeg/ffprobe deben estar en PATH. Las tarifas son configurables y deben revisarse.
El registro guarda tokens reportados y costos estimados, no facturas.

Cada llamada reserva presupuesto persistente bajo la raíz de trabajos; la reserva
no se libera automáticamente. Una llamada incierta queda bloqueada para revisión
manual y conciliación con el proveedor antes de reintentar. No hay reintentos de red
automáticos. Este control local no garantiza un límite duro de facturación, ni
coordina presupuestos entre raíces de trabajos o máquinas diferentes.

Visuales: números destacados, comparaciones, barras y líneas con datos explícitos
`etiqueta:valor`, diagramas, iconos y fondos minimalistas. Los segmentos tienen
zoom suave y fundido de entrada/salida. Subtítulos fragmentados, quemados por defecto; no hay alineación fonética.
Ver [arquitectura y progreso](docs/CODEX_PROGRESS.md).


## Fase 1.5: subtítulos, catálogo y calidad editorial

Los subtítulos SRT se dividen en fragmentos de hasta dos líneas (máximo 34
caracteres y ancho tipográfico conservador), con tiempos proporcionales a la
cantidad de palabras dentro de cada WAV. Es una aproximación, no alineación de voz.
ASS conserva coordenadas 1080×1920 y FFmpeg incrusta texto marfil centrado,
sin fondo opaco, con contorno oscuro. Nunca se añade simultáneamente una pista
seleccionable cuando se queman los subtítulos.

Opciones `produce`: `--subtitles burn|track`, `--subtitle-font "DejaVu Sans"`,
`--subtitle-size 44`, `--subtitle-margin 320`, `--subtitle-color F4EEDD`,
`--subtitle-outline 2`. Tamaños y márgenes usan unidades 1080×1920 y se escalan;
se permiten tamaños 24–52 y margen inferior 200–400. Los gráficos terminan antes
de la zona reservada. Las fuentes alternativas deben estar instaladas y requieren
revisión visual. Se necesita FFmpeg con filtro `subtitles`/libass.

Barras y líneas crecen desde cero hasta valores explícitos del guion, con hasta
72 cuadros de animación por escena; números progresivos, zoom y fundidos completan
el movimiento. Los títulos se ajustan por ancho y altura, sin truncarlos.

### Selección automática

```bash
fabrica produce --auto --catalog out/editorial.sqlite3 --mode mock \
  --width 180 --height 320 --job-id automatico-001
```

Se cargan 50 ideas originales en diez categorías. SQLite usa `BEGIN IMMEDIATE`
para reservar un tema y asociarlo a un trabajo; índices únicos evitan doble
asignación. Se priorizan temas disponibles por prioridad y antigüedad. Repetir
el identificador conserva la reserva incluso tras un fallo; no lo libera para
otro trabajo. El historial registra reserva y resultados. El catálogo y registro
de guiones se comparten mediante `--catalog`; no usar bases diferentes si se
necesita detectar duplicados entre ejecuciones.

El selector es autónomo, pero MOCK solo dispone de las dos plantillas descritas:
no valida generación editorial arbitraria. La repetición de una plantilla en
otro trabajo queda bloqueada por el historial; usar REAL con guiones originales
es una integración futura. `--script` permite desarrollar más guiones locales.
Los controles bloquean referencias pendientes de verificación, cifras sin etiqueta
hipotética, contenido repetitivo, guiones similares e incompatibilidades gráficas.
Son heurísticas conservadoras, no pruebas de verdad ni originalidad jurídica.
Un rechazo queda en `result.json`; publicación permanece deshabilitada.

### Regenerar las dos demos

```bash
fabrica produce --topic '¿Por qué ganar más dinero no siempre significa ahorrar más?' \
  --mode mock --mock-seconds 6 --job-id demo-a-final \
  --output out/fase15/jobs --catalog out/fase15/editorial.sqlite3
fabrica produce --topic 'El costo de oportunidad de nuestras decisiones' \
  --mode mock --mock-seconds 6 --job-id demo-b-final \
  --output out/fase15/jobs --catalog out/fase15/editorial.sqlite3
```

Ambas usan 1080×1920 y cuatro escenas de seis segundos con tonos. Los 24 segundos
son solo para demostración técnica, no un video comercial con narración.
Repetir los comandos reanuda cada trabajo. La versión del pipeline forma parte
de la configuración; para trabajos de versiones anteriores elegir nuevos IDs.

CI: `.github/workflows/tests.yml` instala Python 3.12, FFmpeg, fuentes y dependencias;
ejecuta Ruff y pytest con MP4 reducidos reales. `workflow_dispatch` ofrece demos
1080×1920 separadas. No usa APIs pagas. Ver resultados locales y límites en
`docs/CODEX_PROGRESS.md`; la ejecución remota depende de GitHub Actions.
