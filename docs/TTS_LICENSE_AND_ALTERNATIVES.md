# Bloqueo de voz comercial — Fase 2A

Informe recibido de Codex: rama local codex/phase2-piper-local, Piper 1.8.0, tests 37 aprobados, guion 185 palabras/cinco escenas, video MOCK 75 s a 1080x1920. El reporte NO equivale a verificación de la rama en GitHub ni a voz real habilitada. Falta modelo TTS de español latinoamericano con cadena de derechos documentada.

## Hechos de licencias

Motor mantenido OHF Piper GPL-3.0-or-later. El software no otorga licencias sobre modelos. Cada voz tiene MODEL_CARD: licencia de su dataset, más necesidad de comprobar datasets/voz base de toda cadena de fine tuning. Una voz aparentemente CC0/CC BY puede heredar una base restrictiva.

A fecha de revisión 2026-11-16, la lista comercial de Piper **no incluye** es_AR-daniela-high ni es_MX-claude-high porque no está documentado su modelo base. es_MX-ald desciende de Lessac y figura expresamente fuera de la lista. **No usarlas en videos monetizables sin documentación posterior suficiente.**

La lista Piper sí incluye voces es_ES como es_ES-davefx-medium (cadena CC0 desde rdh, verificar versión retrain actual) y es_ES-carlfm-x_low (dominio público). **Pero no son es-419**: el acento/idioma es una decisión editorial distinta de la licencia. La implementación actual de Piper rechaza es_ES; solo valorar permitir excepciones si el propietario acepta la voz y se registran sus licencias.

Alternativa de investigación: Kokoro 82M con pesos Apache-2.0 y voces españolas ef_dora, em_alex y em_santa. Auditar licencias de voces, procedencia, fonemización, calidad y variante regional antes de aprobar su uso. Apache-2.0 del repositorio o pesos no sustituye una revisión de todos los recursos implicados.

Alternativas adicionales: obtener licencia expresa de una voz latinoamericana comercial, entrenar con grabaciones propias licenciadas y herramientas cuyas condiciones lo permitan, o contratar TTS comercial solo si el costo y términos lo justifican. No usar voces de sitios externos sin claridad de derechos de salida.

## Puerta de habilitación

Aprobar TTS solo con:
- MOTOR y version/hash conocidos; modelo y MODEL_CARD guardados fuera de Git.
- Evidencia archivada de licencia de dataset propio y todas las bases, usos comerciales permitidos y atribuciones requeridas.
- Muestras en frases es-419 (números, monedas ARS/USD, siglas, fechas); aprobación auditiva del propietario.
- Benchmark de síntesis local, carga por escena, fallos, sincronización, reintentos y resultado final.
- Manifest del asset con source URL, hash SHA-256, licencias y snapshot de revisión.

Mientras no se cumpla, real_voice_publish_allowed=false; se permiten demos MOCK con tonos y pruebas con dobles, no subida pública monetizable.

## Fuentes

https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/COMMERCIAL_USE.md
https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/LICENSING.md
https://huggingface.co/hexgrad/Kokoro-82M
https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md
