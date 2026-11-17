# Revisión audiovisual del primer MOCK — Mente y Capital
Fecha de revisión: 2026-11-17

**Material analizado:** MP4 de 75.083 s recibido del propietario (`MenteYCapital_MOCK.mp4`); no versionado. Esta revisión examina artefacto local, no video publicado ni métricas reales de retención.

## Validación técnica observada

- 1080×1920, vertical 9:16, 24 fps, video H.264 yuv420p, audio AAC mono a 16 kHz (tonos simulados).
- 5 escenas de aproximadamente 15 s, una tarjeta editorial por escena; subtítulos ASS quemados inferiores.
- Archivo reproducible y fotogramas examinados en 1–73 s. **Sin narración TTS real**, no es posible aprobar sincronización, tono, dicción ni retención efectiva.
- La tipografía principal, el fondo azul marino, el marfil y los acentos dorados se consideran **aprobados por el propietario**. Mejoras enfocadas en composición, contenido visual y movimiento; NO rehacer identidad gráfica.

## Hallazgos concretos

| Tiempo | Escena | Hallazgo |
|---|---|---|
| 00–15 s | TU TIEMPO TAMBIÉN CUENTA | Círculo con símbolos «$ %» decorativo, no explica el tiempo ni el costo de oportunidad. El elemento central queda esencialmente estático durante el bloque. |
| 15–30 s | LA MEJOR ALTERNATIVA | Dos tarjetas «Elegir»/«Renunciar» con texto alineado a la izquierda aunque la construcción sugiere centrado o disposición simétrica. La relación entre términos podría representarse mejor con flechas/contraste. |
| 30–45 s | UNA TARDE, DOS OPCIONES | Barras sí muestran animación progresiva, pero tienen alturas iguales y etiquetas genéricas «Curso:2»/«Visita:2»; el gráfico aporta poco significado al dilema. |
| 45–60 s | DEPENDE DE TUS PRIORIDADES | Tarjetas «Aprender» y «Compartir» con texto descentrado dentro de superficies grandes; amplio espacio desaprovechado sin una imagen o comparación significativa. |
| 60–75 s | HACÉ VISIBLE EL INTERCAMBIO | Reutiliza círculo «$ %» de apertura; cierre sin nuevo recurso gráfico ni síntesis visual del concepto. |

**Movimiento:** contraste de frames muestreados por segundo en la región visual central (80:1000 px horizontales, 200:1170 verticales) arrojó diferencias medias de píxel inferiores a 0.15 en 52 de 74 intervalos entre segundos consecutivos; es un indicador de poca variación, no una medida de retención. Solo la tercera escena exhibe movimiento sostenido notable. Títulos/subtítulos NO se incluyen en esa región.

**Composición:** títulos bien centrados, pero elementos internos (tarjetas/labels) descentrados. Un marco perimetral, títulos grandes y etiqueta repetida «Ejemplo hipotético» consumen espacio sin aportar narrativa nueva. Los subtítulos inferiores son legibles en cuadros revisados y deben conservar su estilo sobrio y las zonas seguras.

## Priorización para siguiente iteración (sin bloquear Fase 2B)

**P1 — Corregir en plantillas reutilizables, no mediante retoques manuales por video**
1. Composición basada en contenedores y anclas: centrar títulos/labels visualmente según medición real de tipografía y bounding boxes; soportar alineaciones explícitas, paddings y altura de renglones. Probar los casos «Elegir»/«Renunciar», «Aprender»/«Compartir».
2. El recurso visual debe explicar el mensaje: añadir componentes de comparación de alternativas, líneas de decisión, un recurso de tiempo (reloj/agenda) y consecuencias, en lugar de placeholders genéricos «$ %».
3. Distribuir eventos visuales de forma coherente con narración real y guion; objetivo editorial experimental: cambio visual significativo aproximadamente cada 3–5 s (no imponer transiciones arbitrarias ni efectos excesivos). Respetar 60–90 s de duración total.
4. Variar la disposición entre escenas. Evitar que las cinco repitan exactamente título superior + icono central + etiqueta «Ejemplo hipotético» + subtítulos. Mostrar etiqueta hipotética solo cuando se requiere por una cifra/ejemplo.
5. En comparaciones de valores iguales, usar elementos visuales que representen opciones cualitativas en lugar de una barra igual que aparenta comparación numérica sin conclusión.
6. Primeros segundos: construir un hook visual/escrito específico. Últimos segundos: conclusión y CTA visual original; no reutilizar el mismo placeholder.

**P2 — Cuando exista TTS real**
- La segmentación se determina por pausas y significado, no escenas fijas de 15 s.
- Sincronizar entrada/revelación de gráficos con la oración narrada; inspeccionar subtítulos reales.
- Exportar AAC para publicación con frecuencia de muestreo y bitrate apropiados (por ejemplo 48 kHz y 96–128 kbps para voz), sin exigir estéreo artificial.
- Validar contraste y tamaño legible en un móvil; superposiciones de Shorts y recortes seguros.

## Pruebas automáticas sugeridas

- Golden screenshots para cada tipo de plantilla (1080×1920 y miniatura de móvil); error de centrado frente al centro del contenedor menor que tolerancia configurable (~5% del ancho de contenedor) salvo alineación solicitada.
- Detección de solapamientos con subtítulos/zona segura; reducción de zoom del 25–35% para inspección humana.
- Test de diversidad visual del mismo guion: evitar iconos comodín repetidos en portada y cierre.
- Test de render con varias longitudes de título y labels; ninguna cadena truncada o fuera de bounds.
- No usar métricas de diferencias de pixel como sustituto de una medición real de retención; tras publicar, comparar retención/«viewed vs swiped away» por variante.

## Criterios de aceptación

Un video de prueba con misma paleta y fuente, títulos bien centrados, labels centrados según componente, al menos tres recursos visuales **semánticamente diferentes**, sin el icono «$ %» genérico repetido en portada y cierre, con eventos visuales vinculados al guion. Documentar capturas de los cinco momentos clave. QA audiovisual permanece independiente de QA editorial y publicación deshabilitada hasta superar todos los gates.
