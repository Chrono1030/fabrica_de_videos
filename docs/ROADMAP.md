# Hoja de ruta de ingeniería

## Fase 0 — Diseño y prototipo [iniciada]
- [x] Definición de alcance, arquitectura, riesgos, política editorial y contrato JSON
- [x] Validador Pydantic, generador de tarjetas Pillow y pruebas unitarias básicas
- [ ] Comparar voces Piper es_MX / Kokoro y verificar licencias comerciales
- [ ] Benchmark de 10 escenas 1080×1920 en el hardware real

## Fase 1 — Producción automática [prioridad]
- [ ] Adaptador GPT Responses API con credenciales reales, costos y presupuesto
- [x] Catálogo SQLite de 50 temas con reservas atómicas e historial anti-duplicados
- [ ] Verificación editorial independiente y trazabilidad de evidencia
- [ ] Piper: normalización de números, segmentación y medición WAV
- [x] Composición FFmpeg con subtítulos cinematográficos y escenas sincronizadas
- [x] ffprobe, decodificación y duración; fotogramas inspeccionados localmente
- [ ] Validar legibilidad y alineación con voz Piper real
- [ ] n8n Schedule Trigger, exclusión mutua, estados persistentes y reintentos

## Fase 2 — Publicación
- [ ] Autorizar YouTube OAuth y almacenar refresh tokens cifrados
- [ ] Implementar videos.insert, subida reanudable y verificación remota idempotente
- [ ] Solicitar TikTok Content Posting API, permisos y auditoría
- [ ] Habilitar TikTok solo cuando el uso desatendido esté permitido

## Fase 3 — Validación
- [ ] Healthcheck y heartbeat para Uptime Kuma
- [ ] Diez renders consecutivos exitosos sin editar a mano
- [ ] Publicación YouTube privada real, luego piloto editorial
- [ ] Hasta 30 videos piloto; costos, fallos, retención e ingresos si son elegibles
- [ ] Decisión basada en resultados antes de escalar

## Futuro
PostgreSQL, varios canales, nuevos componentes animados, videos largos y optimización editorial.


## Fase 1.5 — calidad local
- [x] SRT fragmentado y ASS quemado configurable, sin duplicación de pista
- [x] Barras/líneas animadas, números progresivos y ajuste automático de textos
- [x] Dos guiones MOCK originales y demos 1080×1920
- [x] Controles deterministas con historial y motivos de rechazo
- [x] Workflow Actions y 21 pruebas locales sin servicios externos
- [ ] Confirmar ejecución remota de Actions cuando la API permita consultarla
- [ ] Ampliar plantillas MOCK y validar generación editorial REAL
- [ ] Fuentes verificadas, alineación fonética y revisión semántica independiente

## Fase 2A — narración local

- [x] Auditar fase anterior y producir MOCK con decodificación completa
- [x] Instalar Piper 1.8.0 y adaptar API Python con reutilización por producción
- [x] Timeout cancelable, WAV atómico/truncado, normalización ARS/USD y pruebas
- [x] Configurar directorio, voz y velocidad; identidad de reanudación por hashes
- [x] Guion original local y vista previa 1080×1920 de 75 s con tonos MOCK
- [x] Revisar licencias individuales y cadena base; no descargar voces inciertas
- [ ] Conseguir voz es_AR/es_MX con derechos documentados
- [ ] Comparación auditiva y benchmark real de ambas regiones
- [ ] Render Piper de 60–90 s e inspección de sincronía de subtítulos con voz

Detalle: [PHASE2_PIPER.md](PHASE2_PIPER.md). Esta fase no usa GPT ni publica.

## Iteración integrada — Mente y Capital

Sustituye el requisito histórico de n8n: calendario interno en la aplicación.
Marca aprobada Mente y Capital; handle aún no verificado. Documentos del PR 2
consultados sin merge en revisión `638dc05`.

- [x] Preservar Piper en commit local y derivar rama integrada
- [x] Contrato/generador de metadatos y control de repetición
- [x] Calendario diario con reserva transaccional y recuperación
- [x] Publicador YouTube MOCK persistente, privado y sin OAuth
- [x] Ciclo completo MOCK con MP4 decodificado, paquete y publicación simulada
- [x] Registros de costos/recursos y escenarios económicos configurables
- [x] Registro interno de procedencia de voces y revisión Piper/Kokoro
- [ ] Voz es-419 comercialmente autorizada y comparación auditiva
- [ ] Verificación factual/editorial independiente y piloto humano
- [ ] OAuth real privado tras autorización; sin activar público

Ver [INTEGRATED_FACTORY.md](INTEGRATED_FACTORY.md). TikTok sigue pospuesto.
