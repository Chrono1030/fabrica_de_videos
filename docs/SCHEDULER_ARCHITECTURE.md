# Calendario editorial interno

Decisión: mantener SQLite y el trabajador existente. Se evaluó
[APScheduler 3.x](https://github.com/agronholm/apscheduler/blob/3.x/docs/userguide.rst)
(MIT): triggers, ejecutores y job stores son útiles para varios tipos de tareas,
pero para un único canal y un slot diario agregarían otra persistencia y
coordinación. La guía 3.x advierte sobre compartir job stores entre schedulers.
La rama master documenta una API distinta; no se mezclan interfaces ni se instala
una versión experimental. Reconsiderar APScheduler si aparecen requisitos reales
que excedan un trabajador y una frecuencia diaria o cada N días.

`ScheduleConfig`: zona IANA y hora obligatorias, fecha inicial, intervalo de días,
límite de intentos. El ejemplo usa America/Argentina/Catamarca; hora 12:00 solo
para la simulación. Nunca se adelanta un slot futuro. Se guardan fecha local,
instante UTC, timezone y configuración exacta. Los relojes deben incluir zona.

SQLite comparte `topics/history/scripts` existentes con `calendar`, `packages`,
`publications`, `publication_events`, `mock_remote` y `metrics`. No hay otra base
operativa para el ciclo. `BEGIN IMMEDIATE` reserva tema y slot en una transacción;
`UNIQUE(local_day)` impide dos slots el mismo día y el job_id es determinista.

El lock POSIX `.worker.lock` cubre todo el ciclo: solo un render/publicador activo
por base. Al caer el proceso el SO libera el lock; un slot RUNNING recupera el
mismo job, tema y etapas del pipeline. No se necesitan leases con expiración que
puedan vencer durante un render largo. `Scheduler.claim` se llama con ese lock
adquirido; no es un ejecutor independiente seguro fuera de `Factory.cycle`.

Estados: PLANNED → RUNNING → SIMULATED_DONE; RETRY_WAIT para errores recuperables,
BLOCKED para contenido/licencias/permisos, EXPIRED para slots vencidos. Máximo
inicial tres intentos, backoff persistido; el publicador tiene su propio límite y
reloj de reintento. No se rellena una cola histórica con una ráfaga de publicaciones.
Una hora DST inexistente se rechaza; una hora repetida usa fold=0 con un slot por
fecha. Cambiar hora o zona en una base con calendario exige migración revisada:
no se reinterpreta silenciosamente el historial.

Las plantillas MOCK se limitan a dos temas realmente soportados. Catálogo agotado,
ningún tema compatible o rechazo editorial pueden dejar un día sin video.
Actualmente `cycle` ejecuta un tick finito y reanudable; no se instaló un servicio
permanente en el host. La futura supervisión ejecutará este mismo proceso, sin n8n.

Probar recuperación en una copia consistente de SQLite y artefactos. Los locks
son locales POSIX; no se promete coordinación distribuida ni soporte multi-host.
