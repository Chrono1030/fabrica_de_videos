> Actualización Fase 4 (2026-11-18): ver [auditoría vigente](PHASE4_VOICE_AUDIT.md) y [registro estructurado](PHASE4_VOICE_AUDIT.json). Este informe anterior se conserva como antecedente; ninguna voz queda habilitada por el nombre o la licencia del motor.

# Voz comercial: evaluación acotada, todavía bloqueada

Revisión 17/11/2026. No se descargaron pesos ni voces adicionales. No hay permiso
para publicar comercialmente una voz real. La falta de voz no bloquea calendario,
metadatos, render MOCK ni publicación simulada.

## Piper

Motor OHF Piper, GPL-3.0-or-later según metadatos instalados; paquete instalado 1.8.0, ONNX Runtime CPU 1.32.0. El motor
no concede derechos sobre voces. Se revisaron nuevamente
[licencias](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/LICENSING.md) y
[lista comercial](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/COMMERCIAL_USE.md).

| Alternativa | Evidencia disponible | Resultado |
| --- | --- | --- |
| es_AR-daniela-high | Ficha archivada en fase 2A y lista OHF con advertencias de procedencia/base | No aprobar |
| es_MX-ald-medium / x_low | Cadena histórica desde davefx/Lessac; la versión sintética x_low no la resuelve | No aprobar |
| es_MX-claude-high | Apache-2.0 en fuente enlazada, base no documentada | No aprobar |
| es_ES-davefx-medium actual | Lista OHF: cadena CC0 desde rdh; exigir ficha y hash de versión reentrenada | Alternativa regional distinta, requiere decisión explícita |
| es_ES-carlfm-x_low | Lista OHF: dominio público, entrenada desde cero | Alternativa regional distinta, requiere decisión explícita |

Cambiar el davefx actual no cambia la historia del ald ya entrenado. No basta el
nombre del archivo: los reentrenamientos conservan nombres. No se habilitó es_ES.
Ver también la evidencia fijada a revisión de voces en [PHASE2_PIPER.md](PHASE2_PIPER.md).

## Kokoro

[Motor](https://github.com/hexgrad/kokoro) Apache-2.0; pyproject consultado: 0.9.4,
Python >=3.10,<3.14. Pesos [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M)
v1.0 declarados Apache-2.0; hash **publicado por el autor**, no calculado localmente:
`496dba118d1a58f5f3db2efc88dbdc216e0483fc89fe6e47ee1f2c53f18ad1e4`.

[VOICES.md](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md) enumera
`ef_dora`, `em_alex`, `em_santa` como español, con fonemización espeak `es`.
No acredita una variante latinoamericana por voz. Los prefijos/hashes abreviados
publicados no constituyen revisión legal ni hashes completos calculados aquí.

La ficha describe datos permisivos y audio sintético de proveedores cerrados,
además de conjuntos CC BY declarados. No aporta en lo revisado una trazabilidad
individual completa de proveedores, condiciones de salidas sintéticas y hablantes
para esas tres voces. Bajo el requisito del propietario de comprobar toda la
cadena, **Apache-2.0 general no es suficiente para aprobarlas**. Falta aclaración
por voz y obligaciones de atribución/base. No se generaron muestras con ellas.

Evaluación de instalación: `pip install --dry-run --no-deps kokoro==0.9.4` resolvió
el wheel de Python. Esto no verifica transitivas ni ejecuta inferencia. Se inspeccionó
la API `KPipeline(device='cpu')`: no exige GPU, pero incorpora Torch, Misaki y
espeak-ng, con sus licencias independientes. No se instalaron esas dependencias
para Kokoro ni se midieron CPU/RAM/velocidad de síntesis. No se presentan cifras de
benchmark o juicios auditivos que no se hayan obtenido.

| Comparación | Piper | Kokoro |
| --- | --- | --- |
| Ejecución CPU | Entorno instalado; adaptador persistente | API CPU documentada; dry-run de paquete |
| Naturalidad/pronunciación | Pendiente con voz autorizada | Pendiente con voz autorizada |
| Rendimiento de voz real | Sin benchmark | Sin benchmark |
| es_AR/es_MX verificable comercialmente | No resuelto | No resuelto para voces españolas examinadas |
| Dependencias | ONNX Runtime + espeak embebido | Torch + Misaki + espeak-ng |

## Contrato y registro interno

Se conserva `TTS.synthesize(text, path) -> duración` y MOCK determinista. La factoría
interna `create_provider` selecciona MOCK/Piper; Kokoro responde con bloqueo explícito
hasta aclarar derechos y variante regional. No importa Kokoro ni descarga modelos.
No se incorporó un segundo servicio TTS.

`VoiceManifest` registra proveedor, versión/licencia de motor, versión del modelo,
variante regional, cada artefacto y SHA-256 completo, origen, evidencia, cadena de
licencias, revisión humana y aprobación auditiva. `voice-register` comprueba hashes
de archivos locales y guarda el manifiesto en `tts_models`, en la misma SQLite.
Una aprobación comercial requiere cadena completa, permisos comerciales por
eslabón/artefacto y aprobación regional/auditiva. El registro no concede derechos
ni habilita uploads. El adaptador Piper conserva además su revisión local sidecar;
no se confunde permiso local de investigación con permiso comercial.

Corpus preparado: `examples/tts_comparison.txt`, con ARS, USD, porcentajes, fechas,
PIB/IPC/IVA. La normalización sí se prueba con texto; no se afirma haber escuchado
su pronunciación. Tras obtener derechos: sintetizar el mismo corpus, guardar WAV,
manifest y tiempos, comparar pronunciación/acentos, revisar a oído y después medir
un video completo con sus subtítulos.

Alternativas humanas: conseguir licencia explícita de voz regional con procedencia,
grabaciones propias con permisos documentados y entrenamiento autorizado, o evaluar
TTS comercial con costo/condiciones aprobados. Aceptar una variante es_ES sería una
decisión editorial explícita posterior, nunca un cambio automático de requisito.
