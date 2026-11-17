# Viabilidad económica — registros y escenarios

`VideoMetrics` guarda tiempo de ciclo, CPU, memoria máxima aproximada, bytes de
artefactos, costo API registrado, llamadas, errores, reintentos y horas humanas.
SQLite es la fuente persistente; `metrics.json` es una exportación regenerable.
Memoria es el high-water mark del proceso/hijos en Linux, no una medición aislada
perfecta por video. CPU incluye hijos FFmpeg; no mide consumo eléctrico ni dinero
por CPU. Los ceros MOCK reflejan gasto API nulo, **no infraestructura gratuita**.

Las horas humanas se cargan explícitamente:

```bash
fabrica metrics --db out/integrated-demo/state.sqlite3 \
  --job-id slot-8e1c55a30251599ab528a5b936bb4097 --human-hours 0.25
```

Ese valor es un ejemplo de entrada manual, no una medición realizada. La ausencia
de carga queda como `null`: horas aún no registradas, no cero horas de trabajo. No se suman como ingresos
las reproducciones o los IDs simulados. Los ingresos reales empiezan en `null` y
requieren fuente oficial, trabajo no simulado y métricas autorizadas posteriores.
No se implementó acceso a YouTube Analytics ni un panel.

`Scenario` permite escenarios pesimista/base/optimista: videos mensuales, vistas
**elegibles hipotéticas**, RPM configurable, costo unitario, costos fijos, horas
humanas y valor de la hora. No se incluyó un RPM supuesto de mercado. El archivo
`examples/economic_scenarios.json` es una plantilla con entradas cero y
monetización desactivada, para completar con supuestos explícitos.

- Costo mensual = videos × costo unitario + costos fijos + horas × valor hora.
- Ingreso estimado = vistas elegibles / 1000 × RPM, solo si los supuestos de
  elegibilidad YPP y del mes Shorts están habilitados explícitamente.
- Resultado = ingreso estimado − costo; margen = resultado / ingreso cuando sea positivo.
- Equilibrio = techo(1000 × costo / RPM) si hay elegibilidad y RPM > 0; si no, `null`.

La salida conserva los supuestos y `kind=hypothetical_scenario`. No predice
probabilidad de conseguir vistas ni presupone aprobación de YPP.

## Monetización: revisión oficial de noviembre de 2026

Actualmente la entrada completa requiere 1000 suscriptores y 4000 horas públicas
válidas anuales o 10 millones de vistas válidas Shorts/90 días, además de país
admitido, políticas, ausencia de strikes activos, 2FA, funciones avanzadas y AdSense.
Cumplir cifras solo habilita evaluación: no garantiza admisión.
[Requisitos oficiales](https://support.google.com/youtube/answer/72851?hl=en).

Desde **1/2/2027**, nuevos aspirantes a anuncios/Premium: 1000 suscriptores y
8000 horas/365 días o 20 millones de Shorts/90 días. Los ya admitidos no pierden
su estado por ese aumento. Para mantenerse activo: 1000 horas/365 días, un millón
de Shorts/90 días o dos videos largos/cinco Shorts cada 90 días. Si se pierde
actividad, existe una ventana de recuperación de 90 días según condiciones.
Los módulos de términos actualizados deben aceptarse antes del 31/1/2027 para
mantener los ingresos asociados. Los umbrales de fan funding no cambian.
[Anuncio oficial](https://support.google.com/youtube/answer/12843009?hl=en).

Además, el reparto mensual Shorts/Premium requiere 10 millones de vistas
cualificadas en 90 días, con ventana terminada el día 15 del mes previo al mes de
cálculo. No alcanzar ese mínimo no equivale a expulsión del YPP.
[Condiciones Shorts](https://support.google.com/youtube/answer/12504220?hl=en).

Las políticas sobre contenido reutilizado, masivo/repetitivo y derechos se revisan
por canal. Nuestros controles no garantizan aprobación. No asumir que un video
diario alcanza ninguno de estos umbrales. Revalidar reglas al lanzar y antes de
monetizar, y revisar costos/valor educativo tras el piloto antes de escalar.

## Monetización: condiciones y cambios anunciados

Consulta oficial: 17/11/2026. Hasta el cambio anunciado, acceso al reparto de
anuncios/Premium: 1000 suscriptores y 4000 horas públicas cualificadas en doce meses,
o 10 millones de vistas Shorts cualificadas en 90 días. Las horas del feed Shorts
no cuentan para el umbral de videos largos. Se requieren país elegible, políticas,
ausencia de strikes activos, verificación en dos pasos, funciones avanzadas y
AdSense vinculado; alcanzar cifras no evita la revisión del canal.
[Requisitos actuales](https://support.google.com/youtube/answer/72851?hl=en).

Desde **1/2/2027**, nuevas entradas a anuncios/Premium: 1000 suscriptores y
8000 horas cualificadas en 365 días, o 20 millones de vistas Shorts cualificadas
en 90 días. Miembros existentes no pierden YPP solo por ese aumento. Las vías de
financiación de fans conservan umbrales inferiores y condiciones propias.

Actividad YPP desde esa fecha: 1000 horas en 365 días, o un millón de vistas Shorts
en 90 días, o dos videos largos/cinco Shorts subidos en 90 días. YouTube anuncia
una ventana adicional de recuperación de 90 días con requisitos propios. Los
módulos contractuales actualizados deben aceptarse hasta 31/1/2027 para conservar
los ingresos asociados. [Anuncio oficial](https://support.google.com/youtube/answer/12843009?hl=en).

Además, el cobro mensual del fondo Shorts y Premium exige **10 millones de vistas
Shorts cualificadas** en una ventana de 90 días que termina el día 15 del mes
anterior al de cálculo. Esto es distinto de entrar o permanecer en YPP; no
alcanzarlo no elimina por sí solo las demás vías de ingresos del programa.
[Regla mensual Shorts](https://support.google.com/youtube/answer/12504220?hl=en).

No confundir vistas brutas con vistas elegibles. `ypp_eligible` y
`monthly_shorts_eligible` son supuestos explícitos de escenarios, no estados
oficiales certificados por la aplicación. Revalidar políticas, ventanas y términos
antes del lanzamiento. Los controles de originalidad y QA no garantizan admisión
ni mantenimiento del canal en YPP.
