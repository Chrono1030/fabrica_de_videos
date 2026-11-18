# Inventario para limpieza posterior a Fase 3

Este inventario no autoriza eliminaciones. El renderer nativo se integra en el ciclo existente y conserva los resultados anteriores. La validación y sus rutas se registran en el informe de Fase 3.

| Código/artefacto | Estado | Acción posterior propuesta |
|---|---|---|
| src/fabrica/cards.py: dibujo Pillow, make_card y create_cards | Legado; no invocado por el pipeline nativo | Retirar plantillas solo tras auditar consumidores y decidir compatibilidad del comando cards |
| src/fabrica/render.py: compose y composición de segmentos/counter PNG | Legado, seleccionado explícitamente | Retirar después de migrar o archivar trabajos pipeline_version=2A |
| src/fabrica/render.py: subtitles y timestamp | Compartido, sigue utilizado | Conservar o mover a un módulo de subtítulos sin alterar la API durante la limpieza |
| cards.font y cards.visual_values | Dependencias compartidas por QA/editorial y código anterior | Separar carga tipográfica y parseo de datos antes de quitar Pillow |
| Pipeline: etapas CARDS/AUDIO y PiperTTS/MockTTS de 2A | Ruta legado | No tocar voces/contratos existentes; nueva ruta separa audio de gráficos |
| Tests históricos de escenas, audio y publicación con renderer=legacy | Regresión vigente | Conservar mientras exista compatibilidad 2A; no sustituir por asserts más débiles |
| Comando fabrica cards y opciones antiguas de subtítulos | Utilidad legado explícita | Deprecar con comunicación previa; no eliminada en Fase 3 |
| experiments/renderer_ab y renderer_advanced | Evidencia experimental histórica | Archivar solo en una limpieza autorizada; no son dependencias de import de producción |
| Runtimes en experiments/renderer_ab/engines | Caché de migración | Producción ya usa .renderers; liberar espacio solo tras verificar copias, licencias y hashes y obtener autorización |
| out/renderer_ab y out/renderer_advanced | Diez MP4 de referencia y sus informes | Preservar; comprobar hashes durante la entrega |
| out/phase3/smoke, primera ejecución de factory y sesiones de tests | Evidencia local de integración y correcciones | Conservar separados del informe de rendimiento final; no presentarlos como candidatos finales |
| Dependencia Python Pillow | Necesaria por compatibilidad y utilidades compartidas | No desinstalar todavía |

El único cambio en render.py en esta fase es marcar su composición como legado. No se desarrollan ni mejoran plantillas Pillow. Los módulos de publicación conservan exclusivamente el cliente MOCK; la adaptación en validate_job es únicamente el despacho a la inspección técnica del video nativo silencioso.
