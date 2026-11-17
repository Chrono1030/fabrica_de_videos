# Fábrica integrada — Mente y Capital

Desarrollo local, 17/11/2026. Rama `codex/phase2-integrated-factory`, derivada del
estado Piper validado y preservado en `8349a52` en `codex/phase2-piper-local`.
No se hicieron merge, push, OAuth, llamadas pagas ni publicaciones reales.

## Decisiones consultadas

Se leyeron los seis documentos solicitados del
[PR 2](https://github.com/Chrono1030/fabrica_de_videos/pull/2), fijados a
`638dc05b4d5442f7e267678d8b67e779c3d811c1`: UNIFIED_FACTORY_ROADMAP,
OPEN_SOURCE_REUSE_PLAN, PLATFORM_PUBLISHING_AND_METADATA,
TTS_LICENSE_AND_ALTERNATIVES, EDITORIAL_AND_PUBLICATION_POLICY y
OPERATIONS_PILOT_AND_METRICS. No se integró automáticamente su rama.
La marca Mente y Capital es definitiva; el handle no se comprobó ni reservó.

Una aplicación Python, catálogo y estado en una SQLite, FFmpeg/Pillow como motor
existente, TTS intercambiable. El calendario no requiere n8n. YouTube es la única
plataforma implementada y **su cliente es exclusivamente simulado**.

## Ejecución reproducible sin credenciales

```bash
.venv/bin/pip install -e '.[dev,piper,youtube]'
.venv/bin/fabrica calendar plan --config examples/schedule_mock.json \
  --db out/integrated-demo/state.sqlite3 --at 2026-11-17T16:00:00+00:00 --days 7
.venv/bin/fabrica calendar next --config examples/schedule_mock.json \
  --db out/integrated-demo/state.sqlite3
.venv/bin/fabrica cycle --config examples/schedule_mock.json \
  --db out/integrated-demo/state.sqlite3 --output out/integrated-demo \
  --at 2026-11-17T16:00:00+00:00
.venv/bin/fabrica metrics --db out/integrated-demo/state.sqlite3
.venv/bin/fabrica economics examples/economic_scenarios.json
```

`--at` mueve únicamente el reloj del simulador, nunca programa una carga real.
El horario del archivo de ejemplo es de prueba; no es una decisión de publicación
del propietario. Una segunda ejecución del mismo día terminado devuelve `IDLE`.
El ciclo reserva un tema, conserva un guion original local, valida, sintetiza tonos
MOCK, renderiza, vuelve a decodificar, empaqueta metadatos, simula upload privado y
registra resultado/métricas. No existe modo de upload real ni público.

Los extras Piper/YouTube son opcionales: la simulación funciona sin ellos. Si está
instalado el SDK oficial, también se prepara `MediaFileUpload` sin transporte ni
red; su ausencia se declara en `upload_request.json`.

## Entrega observada

`out/integrated-demo/jobs/slot-8e1c55a30251599ab528a5b936bb4097/` contiene:

- `final.mp4`: 1080×1920, unos 75 s, gráficos animados, audio MOCK, subtítulos
  inferiores; QA ffprobe y decodificación completa aprobados.
- `script.json`, `metadata.json`, manifiestos con hashes y fotograma de portada.
- `upload_request.json`: privacidad `private`, upload reanudable preparado localmente.
- `publication.json`: `SIMULATED_PRIVATE_VERIFIED`, ID `mock-video-cccbc310fc8c61c6`.
- `result.json`: QA técnico y revisión editorial real pendiente.

La SQLite está en `out/integrated-demo/state.sqlite3`; `metrics.json` es un informe
regenerable, no una segunda fuente de estado. Los artefactos no están en Git.

## Alcance real y límites

Las plantillas MOCK solo cubren dos temas compatibles del catálogo: costo de
oportunidad y ganar más frente a ahorrar. Otros temas no se producen con una
plantilla mal etiquetada. Repetir una plantilla en otro trabajo se bloquea por el
historial; no hay una fuente ilimitada de guiones originales sin GPT.

El control estructural y la comparación de textos no verifican semánticamente
originalidad, factualidad, derechos ni elegibilidad YPP. La ficha de originalidad
requiere problema, desarrollo, ejemplo, relación económica y conclusión; permite
registrar obras de inspiración, autor, idea general, evidencia y fecha sin sugerir
adaptación autorizada. Toda aprobación del simulador sigue siendo técnica.
No copiar pasajes, capítulos ni ejemplos distintivos de libros. Las fuentes
verificables y las afirmaciones pendientes requieren revisión independiente.

Para producción comercial siguen pendientes voz regional autorizada, evaluación
auditiva, verificación factual/editorial y permisos de plataforma. La sincronía
actual de subtítulos es proporcional por palabras, no alineación fonética.

Contratos y decisiones: [metadatos](METADATA_CONTRACT.md),
[calendario](SCHEDULER_ARCHITECTURE.md), [publicador](YOUTUBE_PUBLISHER.md),
[TTS](TTS_COMMERCIAL_AUDIT.md), [viabilidad](VIABILITY.md).

Decisiones de reutilización y licencias declaradas: [DEPENDENCY_REUSE.md](DEPENDENCY_REUSE.md).

Validación local final: 68 pruebas aprobadas (incluidas las 37 originales), Ruff,
compileall, diff sin errores y pip check. Se probaron recuperación de cursor,
cuota, token, respuesta incierta, reinicio, no duplicación, privacidad, rechazos,
DST, persistencia y economía. No se ensayó el transporte HTTP real de Google.
