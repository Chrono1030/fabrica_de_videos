# Contrato de publicación YouTube — solo simulación

Se evaluó el [SDK oficial](https://github.com/googleapis/google-api-python-client)
(Apache-2.0). Extra `youtube` fija google-api-python-client 2.202.0. Se reutiliza
`MediaFileUpload` local con `resumable=True`, MIME video/mp4 y bloques de 1 MiB
(múltiplos de 256 KiB). No se crea un servicio autenticado ni un transporte HTTP.
Se mantiene una interfaz interna channel/start/resume/verify, y el publicador
actual **solo acepta MockYouTubeClient**. No hay endpoint para subir de verdad.

El request preparado utiliza `part=snippet,status`, `notifySubscribers=False`,
y `status.privacyStatus=private` explícito. No contiene publishAt ni permite
privacidad pública. Público infantil y declaración sintética llevan decisiones
por video. El SDK es opcional: el MOCK también funciona sin instalarlo.

## Persistencia y recuperación

`publications`: job_id único, canal, hash del paquete y del video, estado, sesión,
cursor, remote_id único, intentos, próximo reintento, error y fecha.
`publication_events` conserva transiciones y rechazos. `mock_remote` representa el
servidor simulado y persiste entre procesos; no es evidencia de una carga real.
Una restricción única sobre asset_hash impide reinsertar el mismo video con otro
job. El lock `.publish.lock` protege la publicación por base durante todo el intento.

Estados:

| Estado | Acción |
| --- | --- |
| READY | Validación y reserva del paquete |
| STARTING | Intención durable antes de iniciar sesión |
| UPLOADING | Sesión/cursor persistidos |
| UPLOADED_PRIVATE | ID remoto recibido |
| SIMULATED_PRIVATE_VERIFIED | Canal, privacidad y procesamiento simulados comprobados |
| RETRY_WAIT | Conexión/cursor parcial: backoff exponencial; cuota: espera de un día |
| RECONCILE | Respuesta incierta: consultar/reanudar misma sesión |
| BLOCKED_PERMISSION | Token o permiso; requiere intervención |
| BLOCKED_PERMANENT | Error no recuperable |
| QUARANTINED | Sesión perdida, discrepancia remota o límite de reintentos |

Ante éxito repetido se consulta el mismo ID. Ante reinicio tras completar la carga
se recupera el mismo ID desde la sesión persistida. Ante pérdida entre inicio de
sesión y persistencia, se pone en cuarentena: **no hay un segundo insert ciego**.
YouTube no ofrece una clave de idempotencia general para videos.insert; no se
traslada la deduplicación del servidor MOCK como garantía de la API real.
La seguridad ante respuesta incierta puede requerir conciliación humana.

Antes de publicar se revalida el paquete, el canal, el guion, contenido pendiente,
hashes, recursos, duración, estado TECHNICALLY_READY y decodificación del MP4.
La simulación no transforma REQUIRES_REVIEW en aprobación editorial real.
Paquetes no simulados exigen licencias comerciales y aprobación no simulada;
este módulo aun así no permite un cliente real.

## OAuth real: plan posterior, sin credenciales solicitadas

1. Con autorización del propietario, validar canal y región con channels.list
   mine=true y videoCategories.list; activar solo scopes necesarios. No crear
   cuentas ni utilizar cuentas de servicio para el canal.
2. Resolver consentimiento OAuth, almacenamiento cifrado, permisos locales,
   refresco/revocación y condiciones de Testing; nunca serializar tokens en Git.
3. Implementar transporte de sesión que consulte rangos HTTP 308 y el estado
   remoto antes de reanudar. Cifrar URI de sesión real: puede ser sensible.
4. Ensayar cinco uploads privados aprobados, cortes en cada transición, expiración
   de sesión/token, cuota, procesamiento y recuperación sin duplicados.
5. Verificar el remote_id, canal y privacidad con videos.list. Evaluar miniaturas
   solo después del procesamiento. Requiere aprobación adicional para carga real;
   programación pública queda fuera de esta implementación.

Fuentes primarias revisadas: [videos.insert](https://developers.google.com/youtube/v3/docs/videos/insert),
[SDK media upload](https://googleapis.github.io/google-api-python-client/docs/media.html),
[protocolo reanudable](https://developers.google.com/youtube/v3/guides/using_resumable_upload_protocol).
Cuotas y valores por defecto se volverán a revisar antes de cualquier prueba real;
no se fijó el antiguo costo de 1600 unidades como una verdad vigente.
