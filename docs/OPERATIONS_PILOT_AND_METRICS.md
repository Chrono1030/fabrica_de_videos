# Calendario, métricas y continuidad operativa

Se implementa **dentro de la misma aplicación**; no paneles ni automatizadores independientes. SQLite almacena programación, producción, publicaciones, métricas y fallos. Servicio único bajo supervisión externa Uptime Kuma en el despliegue final.

## Calendario inicial

Un slot candidato diario, con timezone IANA America/Argentina/Catamarca y fecha UTC persistida. El horario específico no fue elegido por propietario; parámetro configurable, no asumir hora universal. La elección de horario se revisará cuando existan datos reales de audiencia. Si un video no supera QA o faltan licencias, se salta la publicación: no sustituir por plantilla repetida.

Planificador: comparar APScheduler estable 3.x y scheduler mínimo propio; fijar límite de una producción/render simultáneos según hardware, lock SQLite transaccional, job_id determinista por slot/versión, reanudación tras corte, backoff con jitter. No adelantar una publicación si el reloj está en error, caducó el slot o la zona horaria cambió.

## Métricas MVP

Operativas: trabajos iniciados, finalizados, bloqueados, fallas por etapa, tiempo de GPT/TTS/render/upload, CPU/RAM/disco, tokens y USD por video, cuota por plataforma, número de reintentos, porcentaje con QA aceptado, uploads privados verificados, duplicados (meta: cero).

Calidad y audiencia (tras autorización de Analytics): viewed vs swiped away, vistas válidas de Shorts, porcentaje medio visto, duración media, retención por segmento, likes/comentarios, suscriptores ganados, geografía, principales temas, tasas de retorno. Consultar definiciones y permisos oficiales antes de implementar; no usar conteo de vistas bruto como única métrica. Registrar snapshot diario y ventanas de 24 h/7 d/30 d, teniendo en cuenta retrasos de la API.

Monetización cuando elegible: ingreso por contenido, RPM disponible, coste de infraestructura/API por video, coste por 1000 vistas, retorno neto estimado y coste de intervención humana. No suponer ingresos publicitarios antes de admisión a YPP.

## Viabilidad de ingresos pasivos y supuestos

**Objetivo declarado por propietario:** generar un flujo de ingresos pasivos con mínima intervención rutinaria; la rentabilidad es un criterio de éxito del producto, **pero no puede garantizarse** monetización, admisión al YPP, distribución ni retorno. El sistema debe medir si el proyecto es viable económicamente en lugar de dar por hecho que las vistas se convierten en dinero. Tratar ingresos como escenario, nunca como entrada asegurada en el presupuesto personal.

Desde el primer video registrar: costes API y TTS/hosting, coste de generación/revisión, horas humanas, publicaciones, visualizaciones cualificadas y suscriptores. Tras admisión a YPP: ingresos reales y RPM/ingresos por mil vistas **elegibles**; antes de YPP ingresos publicitarios reconocidos = 0.

Modelo de escenarios con variables configurables, no cifras de RPM inventadas:
- Ingreso estimado = vistas monetizables / 1000 * RPM neto supuesto.
- Margen operativo = ingreso estimado - costes variables API/hosting/licencias - horas humanas valorizadas.
- Punto de equilibrio en vistas = 1000 * costes imputables / RPM supuesto, solo si RPM > 0 y elegibilidad verificada.
- Probar escenarios pesimista, base y optimista con supuestos declarados y sensibilidad; no confundir vistas brutas con vistas elegibles.

Puertas: validación técnica, calidad/originalidad, legalidad de activos, 30 videos piloto y revisión económica. Si el canal no crece o el costo por video es insostenible, adaptar temas/duración/distribución o suspender producción; escalar solo con evidencia. Las reglas de YouTube pueden cambiar y deben revisarse antes de lanzamiento y antes de monetizar.

## Cambio de monetización Shorts anunciado para 2027

YouTube anuncia que **a partir del 1 de febrero de 2027**, para participar mensualmente en el reparto de ingresos publicitarios de Shorts y YouTube Premium será necesario alcanzar **10 millones de visualizaciones cualificadas de Shorts en los últimos 90 días**, medidos sobre la ventana que la plataforma especifica para el mes correspondiente. Las condiciones futuras deben revisarse nuevamente al lanzar y antes de activar monetización. Esto hace importante no asumir ingresos estables únicamente con un video diario de Shorts: medir probabilidad de alcanzar el umbral y considerar formatos largos originales como una vía de diversificación editorial en una fase posterior, sin ampliar el MVP hoy.

Fuentes oficiales: https://support.google.com/youtube/answer/12504220 y https://support.google.com/youtube/answer/72851

## Piloto

1. Validar 10 producciones distintas sin intervención manual ni pruebas falsas de voz.
2. Subir cinco videos privados con aprobación humana inicial; verificar estado y no duplicados.
3. Activar paso público supervisado tras licencia, originalidad y adecuación comprobadas.
4. Probar hasta 30 videos en ritmo máximo diario; medir engagement/costes, no exigir publicación si QA bloquea.
5. Revisar resultados semanalmente y decidir continuar/modificar/pausar con datos, sin umbrales monetarios inventados.

No existe mínimo de publicaciones diarias exigido por el algoritmo de YouTube. La frecuencia estable sirve para experimentos operativos, no garantiza distribución.

## Recuperación

Backups de SQLite consistentes, manifests editoriales, result.json, assets finales y fuente/licencias. Separar cifrado de secretos OAuth/keys y sus backups. Política inicial sugerida: backup diario, revisión semanal de recuperación en entorno aislado; retención a definir según espacio; nunca arriesgar el backup del Homelab. Healthcheck interno y heartbeat de último trabajo completado; alertas por cola estancada, disco bajo, OAuth revocado, presupuesto agotado y permisos cambiados.

Revocación: comando seguro que deshabilita PUBLISH_ENABLED, invalida tokens y no afecta archivos personales. Recuperación de upload interrumpido debe conciliar IDs remotos antes de reintentar. No prometer disponibilidad o idempotencia total sin ensayos.

Fuentes:
https://support.google.com/youtube/answer/11914225
https://support.google.com/youtube/answer/141805
https://support.google.com/youtube/answer/72851
https://github.com/agronholm/apscheduler
