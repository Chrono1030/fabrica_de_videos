# Decisiones de arquitectura

| ID | Elección | Motivo |
|---|---|---|
| ADR-001 | Conceptos originales basados en ideas generales de libros, sin reproducción ni reformulación mecánica | Valor educativo propio y menor riesgo jurídico/editorial |
| ADR-002 | es-419 | Audiencia panlatinoamericana |
| ADR-003 | TTS local: Piper primero, Kokoro alternativo; voz concreta **bloqueada hasta validar derechos de toda la cadena** | Uso comercial responsable; acento latinoamericano por evaluar |
| ADR-004 | Pillow/SVG/FFmpeg | Costo marginal mínimo; visuales deterministas |
| ADR-005 | GPT Responses API con salidas estructuradas | Guiones automáticos y costo medible |
| ADR-006 | Sin APIs macroeconómicas en MVP | Enfoque atemporal, menos dependencias |
| ADR-007 | Uptime Kuma y logs internos | Alertas sin construir otro panel |
| ADR-008 | **Sustituido:** n8n + SQLite | Diseño anterior; consultar ADR-011 |
| ADR-009 | YouTube primero; TikTok tras permisos, auditoría y validación del caso de uso | Cumplir condiciones de plataforma |
| ADR-010 | Publicación con fail-closed | Evitar errores irreversibles |
| ADR-011 | **Un producto Python integrado** con scheduler interno, SQLite y módulos de guion, medios, publicación y métricas | Menor fricción y una sola superficie operativa; n8n no obligatorio |
| ADR-012 | Un propietario y un canal YouTube inicialmente | Minimizar credenciales, operaciones y duplicados |
| ADR-013 | Subida YouTube privada por defecto y validación explícita de canal/estado | API puede publicar como público por defecto desde noviembre de 2026 |
| ADR-014 | Originalidad sustancial y control de repetición son bloqueantes | Aspirar a monetización sin garantizar aceptación de YPP |
| ADR-015 | Branding no decidido; cinco candidatos documentados | Usuario elegirá nombre y handle tras verificar disponibilidad |
| ADR-016 | Métricas/analítica avanzada se difieren; registros operativos básicos desde MVP | Evitar sobreingeniería |
 
Documentos actuales:
- [Roadmap unificado](UNIFIED_FACTORY_ROADMAP.md)
- [Marca y cuenta](CHANNEL_BRAND_OPTIONS.md)
- [Política editorial y publicación](EDITORIAL_AND_PUBLICATION_POLICY.md)
- [Integraciones y metadatos](PLATFORM_PUBLISHING_AND_METADATA.md)
- [Auditoría de open source](OPEN_SOURCE_REUSE_PLAN.md)
- [Bloqueo de licencia de voz](TTS_LICENSE_AND_ALTERNATIVES.md)
- [Operación y métricas](OPERATIONS_PILOT_AND_METRICS.md)
