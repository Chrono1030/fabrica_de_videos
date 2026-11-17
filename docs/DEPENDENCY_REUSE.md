# Reutilización de bibliotecas — iteración integrada

No se copió código de aplicaciones externas. Se conservaron Pydantic, SQLite,
Pillow y FFmpeg. Las siguientes decisiones se basan en documentación primaria y
en metadatos del entorno local, no en una auditoría completa de distribución.

| Componente | Decisión | Motivo |
| --- | --- | --- |
| Metadatos | Pydantic existente + resumen extractivo | Contrato local verificable, sin generador pago ni aplicación adicional |
| Calendario | SQLite + zoneinfo + flock | Reutiliza transacciones y locks; no precisa scheduler general |
| APScheduler | Evaluado, no instalado | 3.x permitiría triggers y stores; agrega persistencia que el caso diario no necesita |
| Publicador | SDK oficial opcional 2.202.0 | Prepara MediaFileUpload local; interfaz MOCK sin transporte HTTP |
| Subtítulos | Motor ASS/SRT existente | No incorporar pysubs2 ni Whisper sin beneficio medido |
| Kokoro | Dry-run de wheel 0.9.4, sin instalación/inferencia | CPU disponible en API; derechos por voz y acento pendientes |
| MoneyPrinterTurbo / ShortGPT | No incorporados | La fábrica ya tiene pipeline; no se auditó ni copió código de estos proyectos |

Licencias declaradas en paquetes instalados:

| Paquete | Versión | Licencia declarada |
| --- | --- | --- |
| piper-tts | 1.8.0 | GPL-3.0-or-later |
| google-api-python-client | 2.202.0 | Apache 2.0 |
| google-auth | 2.62.2 | Apache 2.0 |
| google-auth-httplib2 | 0.4.4 | Apache 2.0 |
| google-api-core | 2.44.0 | Apache 2.0 |
| httplib2 | 0.32.1 | MIT |
| uritemplate | 4.2.0 | BSD-3-Clause OR Apache-2.0 |
| requests | 2.34.2 | Apache-2.0 |

Se revisaron transitivas principales del SDK; no se afirma haber completado un
SBOM o revisión de cada dependencia binaria. `pip check` no encontró requisitos
rotos. Kokoro agregaría Torch, Misaki y fonemización espeak-ng con licencias
independientes; el binario externo espeak-ng no está instalado. Piper incorpora
su propio fonemizador. No se modificó el sistema para instalar otro motor.

Fuentes: [APScheduler 3.x](https://github.com/agronholm/apscheduler/tree/3.x),
[SDK Google](https://github.com/googleapis/google-api-python-client),
[Kokoro pyproject](https://github.com/hexgrad/kokoro/blob/main/pyproject.toml).
