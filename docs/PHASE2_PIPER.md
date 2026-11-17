# Fase 2A — Piper local (17 de noviembre de 2026)

Estado: integración y ensayo audiovisual MOCK completados. **El primer video con
narración real está pendiente por licencias de voces.** No se descargaron modelos
ONNX, no se usó GPT y no se publicó contenido.

## Auditoría

La rama `codex/phase2-piper-local` parte de `codex/mvp-pipeline-phase1` (verificado
con `git merge-base --is-ancestor`); el árbol inicial estaba limpio. Se revisaron
contratos Pydantic, persistencia, catálogo, TTS, render, subtítulos, documentación,
configuración y pruebas.

La base tenía 21 pruebas aprobadas. Ruff pasó con las reglas del workflow:
`ruff check src tests --select E4,E7,E9,F,I`. Un `ruff check .` sin selección
recibió reglas adicionales de la configuración del entorno y encontró avisos de
modernización preexistentes; no se considera equivalente al control de CI.
Se fijaron en `pyproject.toml` las reglas que ya utilizaba CI, de modo que
`ruff check .` sea reproducible fuera de ese entorno.

Producción de auditoría: `out/phase2-audit/phase2-audit/final.mp4`, 1080×1920,
MP4 decodificado íntegramente por el QA del pipeline.

Problemas corregidos:

- `$` se convertía incondicionalmente a dólares. Ahora exige código o contexto.
- El adaptador iniciaba un ejecutable y cargaba el modelo en cada escena. La API
  Python actual se ejecuta en un proceso reutilizado por producción.
- Una escritura fallida podía dejar un WAV final incompleto. Ahora se verifica el
  contenido PCM y se reemplaza el destino atómicamente desde `.partial.wav`.
- Voz, velocidad y bytes del modelo/configuración/licencia no formaban parte de
  la identidad de reanudación. Ahora se incluyen, junto con la versión de Piper.
- Se agregó `--mode local`, que exige JSON local y no puede generar guion con GPT.

La versión del pipeline pasa a `2A`: para trabajos de fases anteriores se debe
usar otro identificador; los resultados existentes se conservan.

## Investigación y licencias separadas

Software: [OHF-Voice/piper1-gpl](https://github.com/OHF-Voice/piper1-gpl), GPL-3.0.
Instalación realizada en `.venv`: `piper-tts==1.8.0`, ONNX Runtime 1.32.0, CPU,
Python 3.12. La [API Python oficial](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/API_PYTHON.md)
usa `PiperVoice.load`, `SynthesisConfig(length_scale=...)` y `synthesize_wav`.
Se inspeccionaron las firmas del paquete instalado y `piper --help`; las opciones
actuales usan guiones, y el CLI también acepta algunos alias antiguos.

Los modelos no heredan automáticamente la licencia del motor ni la etiqueta MIT
global del repositorio de voces. Se consultaron las fichas individuales y la
[guía de licencias](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/LICENSING.md)
y la [revisión de uso comercial](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/COMMERCIAL_USE.md)
del mantenedor. Hay que comprobar también los modelos base históricos.

Inventario fijado a la revisión Hugging Face
`e9ab671f2a0e50a701b34361136ba3e6a3a9eb0c`:

| Voz | Metadatos | Licencia propia / procedencia | Decisión |
| --- | --- | --- | --- |
| es_AR-daniela-high | Argentina, high, 22050 Hz | La ficha remite a Lessac; el corpus requiere acuerdo y limita el uso | No descargar sin derechos acreditados |
| es_MX-ald-medium | México, medium, 22050 Hz | Dataset Unlicense; ajuste desde davefx histórico, señalado por OHF como derivado de Lessac | No inferir permiso del davefx reentrenado actual |
| es_MX-ald-x_low | México, x-low, 22050 Hz | Dataset sintético producido con ald-medium; ficha sin licencia explícita | No descargar |
| es_MX-claude-high | México, high, 22050 Hz | Ficha remite a Space Apache-2.0, sin aclarar base de entrenamiento | No descargar por procedencia incompleta |

Fichas consultadas (sin bajar los pesos):

- [Daniela](https://huggingface.co/rhasspy/piper-voices/blob/e9ab671f2a0e50a701b34361136ba3e6a3a9eb0c/es/es_AR/daniela/high/MODEL_CARD)
- [Ald medium](https://huggingface.co/rhasspy/piper-voices/blob/e9ab671f2a0e50a701b34361136ba3e6a3a9eb0c/es/es_MX/ald/medium/MODEL_CARD)
- [Ald x-low](https://huggingface.co/rhasspy/piper-voices/blob/e9ab671f2a0e50a701b34361136ba3e6a3a9eb0c/es/es_MX/ald/x_low/MODEL_CARD)
- [Claude](https://huggingface.co/rhasspy/piper-voices/blob/e9ab671f2a0e50a701b34361136ba3e6a3a9eb0c/es/es_MX/claude/high/MODEL_CARD)
- [Licencia Lessac](https://www.cstr.ed.ac.uk/projects/blizzard/2013/lessac_blizzard2013/license.html)

Los niveles high/medium/x-low no constituyen una evaluación auditiva. No se
compararon naturalidad, pronunciación ni rendimiento de inferencia: hacerlo
requiere sintetizar con modelos autorizados. No hay una voz ganadora acreditada.
La instalación y los dobles verifican la interfaz, no la calidad de voz.

## Uso cuando se disponga de una voz autorizada

```bash
.venv/bin/pip install -e '.[dev,piper]'
export PIPER_MODELS_DIR=/ruta/a/modelos
export PIPER_VOICE=nombre-de-la-voz
export PIPER_LENGTH_SCALE=1.0
export PIPER_TIMEOUT=180
.venv/bin/fabrica produce \
  --topic 'El costo de oportunidad en las decisiones cotidianas' \
  --mode local --script examples/costo_oportunidad.json \
  --catalog out/phase2-real/editorial.sqlite3 \
  --output out/phase2-real --job-id costo-oportunidad-real
```

`PIPER_VOICE_MODEL` permite una ruta exacta y tiene prioridad. No hay descarga
implícita. El archivo adyacente `.onnx.json` debe declarar español latinoamericano.
`PIPER_LENGTH_SCALE` admite 0.5–2; valores mayores hacen la voz más lenta.
`PIPER_EXECUTABLE` es una alternativa explícita de compatibilidad CLI; dejarlo
vacío para reutilizar el modelo con la API Python. `NARRATION_CURRENCY=ARS` o `USD`
solo debe definirse si ese contexto aplica a todos los símbolos `$` del guion.

Cada modelo debe tener una revisión documentada en `<modelo>.onnx.license.json`:

```json
{
  "sha256": "HASH_SHA256_REAL_DEL_ONNX",
  "license": "IDENTIFICADOR_O_ACUERDO_APLICABLE",
  "evidence": ["URL_O_RUTA_DE_LA_LICENCIA_Y_CADENA_DE_ENTRENAMIENTO"],
  "approved_local_use": true
}
```

Este registro es una declaración de revisión humana, no un verificador jurídico.
No se debe crear para una voz sin derechos determinados. Conservar MODEL_CARD,
licencias, atribuciones y permiso junto al modelo. Los pesos y WAV no se versionan.

Los ensayos MOCK y Piper usan catálogos separados: el control editorial de
duplicados rechaza correctamente el mismo guion con identificadores distintos
si ambos comparten el catálogo predeterminado.

El proceso se cancela al superar el timeout, se cierra al terminar la narración y
se descartan temporales. Un modelo inválido, un WAV vacío/truncado o un fallo de
síntesis bloquean el trabajo. El proveedor conserva `synthesize(text, path)` del
protocolo TTS: un futuro Kokoro puede implementar ese mismo contrato.

## Narración, guion y subtítulos

`examples/costo_oportunidad.json` contiene cinco escenas originales y 185 palabras,
sin referencias inventadas ni recomendaciones de inversión. Su duración de 60–90 s
es un objetivo hasta medir WAV reales. El pipeline guarda `scene_durations`, exige
60–90 s de audio en modo local/real y compone a partir de esas duraciones.

El normalizador verbaliza porcentajes, códigos ARS/USD, agrupaciones como 1.250,
decimales con coma (y punto decimal sin agrupación), fechas día/mes/año, siglas y
abreviaturas frecuentes. Las cifras decimales se leen dígito por dígito; no se
interpretan como centavos. `1,234` es decimal según la convención local. Las fechas
inválidas y las monedas ambiguas se rechazan. No es un analizador lingüístico
universal: no cubre todos los formatos internacionales, ordinales ni siglas.

Se mantienen SRT fragmentado y ASS centrado abajo, quemado con borde y dos líneas.
Los tiempos se distribuyen proporcionalmente por palabras dentro de cada WAV;
**no hay alineación fonética**. Con voz autorizada queda pendiente revisar a oído
los inicios/finales de cada fragmento y ajustar o incorporar alineación.

## Artefacto disponible

Se produjo `out/phase2-preview/costo-oportunidad-preview/final.mp4`, 1080×1920,
75.083 s, H.264/AAC, gráficos animados, subtítulos inferiores y decodificación
completa aprobada. **Es una vista previa con tonos MOCK, sin narración real.**
El JSON de resultado identifica `audio_simulated: true`, cero costos y publicación
deshabilitada. Se inspeccionó el fotograma a los 36 s: texto inferior legible,
gráfico y subtítulos separados. La vista previa no valida sincronía con voz real.

Reproducción del ensayo:

```bash
.venv/bin/fabrica produce \
  --topic 'El costo de oportunidad en las decisiones cotidianas' \
  --mode mock --script examples/costo_oportunidad.json --mock-seconds 15 \
  --catalog out/phase2-preview/editorial.sqlite3 \
  --output out/phase2-preview --job-id costo-oportunidad-preview
```

## Verificación final

- `ruff check .`: aprobado con reglas del repositorio.
- `pytest -q`: **37 pruebas aprobadas** (incluye validación nativa de un
  modelo inválido con Piper instalado; no utiliza pesos reales).
- `python -m compileall -q src` y `git diff --check`: aprobados.
- Intento `--mode local` con el JSON original y catálogo aislado: estado
  `BLOCKED` por falta de modelo autorizado; ningún WAV ni MP4 real generado.
- Las pruebas comprueban contexto monetario, fechas inválidas, normalización,
  WAV truncado, limpieza atómica en timeout, terminación del proceso, API
  reutilizada, hash de licencia y prohibición de GPT en el modo local.
