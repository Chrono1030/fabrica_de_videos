# Componentes visuales disponibles

Biblioteca propia promovida del A/B avanzado: `src/fabrica/renderers/assets/components.js`. El estado se evalúa como función pura de storyboard, escena y tiempo; no depende del reloj real ni del proveedor de audio. Ambos adaptadores consumen los mismos elementos/datos/eventos. No hay Remotion ni código de templates de terceros instalado.

| Layout | Componentes | Datos del storyboard | Animación compatible |
|---|---|---|---|
| cards | Tarjetas, títulos y rótulos | Etiquetas y valores opcionales | Revelación progresiva, énfasis, entrada moderada |
| flow | Nodos y conexiones verticales | Etiquetas/valores en el orden planificado | Revelación del recorrido |
| counter | Uno o dos números principales | Valor o referencia, formato y unidad | Conteo y etiqueta de apoyo |
| bars | Barras con escala común | Valores no negativos y etiquetas | Crecimiento, valor inicial opcional |
| distribution | Distribución proporcional y tarjetas | Partes positivas/no negativas, total positivo | Revelación conservando la geometría proporcional |
| transfer | Distribución y transferencia entre categorías | IDs origen/destino, cantidad o referencia | Movimiento y reasignación de la misma cantidad |
| comparison | Comparación cuantitativa o de alternativas | Valor inicial/final o etiquetas cualitativas | Barras homogéneas, tarjetas, construcción progresiva |

Elementos: `id`, `label`, `data_key`/`value`, `initial_key`/`initial_value`, `format`, `unit`, `color_role`. Los valores referenciados pertenecen al diccionario `data`, sin eval ni acceso a objetos del motor. Los textos se insertan con textContent; el JSON embebido escapa los caracteres de cierre de script.

Eventos: `at`, `duration`, IDs afectados y acción (`reveal`, `grow`, `count`, `compare`, `highlight`, `transfer`, `transition`). Una transferencia identifica además from_id/to_id y amount/amount_key. `transition=settle` permite una entrada moderada; `cut` mantiene un encuadre estático. No se agregan movimientos ambientales decorativos. La paleta y la tipografía proceden del contrato; actualmente se valida DejaVu Sans, la fuente instalada y usada por el proyecto.

Límites del catálogo inicial: máximo seis elementos por escena, hasta dos contadores principales, gráficos de barras de escala positiva y tipografía de la marca actual. La gramática y el orden los decide el planificador o el storyboard cargado, nunca la selección del renderer. Para otra gramática se agrega un tipo documentado/validado y su implementación; no se reemplaza silenciosamente por una escena genérica o por otro motor. Los textos extensos y el formato móvil requieren revisión visual humana.

Regresiones incluidas:

- `data/budget_55_storyboard.json` y su VideoScript: siete mensajes/intervalos originales, presupuesto y transferencia de ARS 30.000, con totales exactos antes/después. Los MP4 y el contrato V1 originales siguen en renderer_advanced.
- `data/opportunity_storyboard.json` y `data/costo_oportunidad.json`: elección del tiempo, flujos, comparación y cantidades en horas. No contiene presupuestos ni está limitado a siete escenas.
- La planificación automática de los dos temas actuales del calendario produce combinaciones distintas de layouts.

[Issue #5](https://github.com/Chrono1030/fabrica_de_videos/issues/5) queda como referencia de investigación posterior. Sus patrones de comparación, cantidades y construcción progresiva son compatibles con esta separación; en esta fase no se copiaron templates TSX, ni se instaló Remotion, Canvas Explainer, edge-tts o música.
