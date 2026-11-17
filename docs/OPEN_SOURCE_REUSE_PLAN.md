# Repositorios externos a evaluar dentro de una sola fábrica

Este inventario prioriza **bibliotecas internas** y ejemplos, sin reemplazar la aplicación existente ni instalar otro producto que haya que administrar. La licencia indicada es del repositorio/biblioteca, no necesariamente de modelos, datasets, música, iconos o servicios asociados. Codex debe inspeccionar versiones, licencias de transitivas y riesgos antes de copiar código.

| Módulo interno | Candidato | Uso | Decisión inicial |
|---|---|---|---|
| Scheduler | https://github.com/agronholm/apscheduler (MIT) | Ejecución cron/intervalos y jobs | Estudiar versión estable 3.x frente a planificador SQLite mínimo; v4 aún pre-release |
| Upload YouTube | https://github.com/googleapis/google-api-python-client (Apache-2.0) | API oficial videos.insert/videolist, uploads reanudables | Adoptar SDK oficial y ejemplos del proveedor |
| OAuth YouTube | https://github.com/googleapis/google-auth-library-python-oauthlib (Apache-2.0) | Login OAuth inicial y refresh | Adoptar; secretos privados |
| Cliente TikTok | https://github.com/encode/httpx (BSD-3) | HTTP para endpoints oficiales | Adoptar si TikTok autorizado; no paquetes de browser automation |
| Subtítulos | https://github.com/tkarabela/pysubs2 (MIT) | Construcción/edición SRT/ASS | Comparar con implementación actual; adoptar solo si reduce código |
| Alineación audio | https://github.com/SYSTRAN/faster-whisper (MIT) | Segmentación y tiempos de subtítulos | Futuro opcional; benchmark CPU |
| Movimiento de gráficos | https://github.com/ManimCommunity/manim (MIT) | Animaciones económicas más sofisticadas | Posterior; comparar coste de render con FFmpeg/Pillow |
| Recursos visuales | https://github.com/lucide-icons/lucide (licencias según paquete) | Iconos SVG | Adoptar selectivamente y registrar procedencia |
| Proyecto de referencia | https://github.com/harry0703/MoneyPrinterTurbo (MIT reportada) | Patrones de generación de guiones y edición | Auditar, no instalar como otro servicio |
| Otro proyecto referencia | https://github.com/RayVentura/ShortGPT | Arquitectura audiovisual | Auditar mantenimiento y licencias antes de copiar |
| TTS actual | https://github.com/OHF-Voice/piper1-gpl (GPL-3.0-or-later) | Síntesis local | Ya integrado, voz todavía bloqueada por derechos |
| TTS candidato | https://github.com/hexgrad/kokoro y https://huggingface.co/hexgrad/Kokoro-82M (Apache-2.0 pesos) | Comparativa de naturalidad en español | Auditar voces y pronunciación; posible fallback |

**No adoptar n8n para el MVP:** aprobado producto único con scheduler interno. Uptime Kuma es monitor externo ya existente, no pieza editorial. No trasladar composición a Remotion por defecto: implicaría stack TypeScript/React y régimen de licencias específico según uso.

## Prioridad de auditoría de Codex

1. YouTube SDK/OAuth + upload resumable; crear tests de dobles y seguridad antes de credenciales.
2. APScheduler 3.x vs scheduler simple con SQLite atómico; priorizar una sola instancia y baja huella de memoria.
3. pysubs2 sólo si simplifica SRT/ASS sin romper subtítulos cinematográficos.
4. Proveniencia de voz comercialmente viable: nunca desbloquear publicación por una licencia genérica del motor.
5. MoneyPrinterTurbo/ShortGPT: identificar funciones concretas reutilizables, SHA, copyright y dependencia pagada; no reescribir el pipeline.
6. Analítica: APIs oficiales YouTube Analytics solo después del MVP, no screen scraping.

## Criterios de adopción

Para cada candidato: URL, commit/tag evaluado, license SPDX, transitive licenses, CPU/memoria/disco, compatibilidad Python 3.12/Rocky Linux, grado de acoplamiento, mantenimiento, tests aislados, seguridad de red, beneficio medible y plan de rollback. Prohibido copiar fragmentos sin atribución/aviso de licencia requeridos.

## Referencias de versiones/políticas

https://github.com/agronholm/apscheduler
https://github.com/googleapis/google-api-python-client
https://github.com/tkarabela/pysubs2
https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/LICENSING.md
https://www.remotion.dev/docs/license/pricing
