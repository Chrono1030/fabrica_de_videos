# Especificación de producto (v1.0)

## Propósito
Crear una plataforma autónoma de videos breves de divulgación económica, con narrativa original, acompañamiento visual minimalista y métricas de gasto. Los ingresos pasivos son una hipótesis de negocio, no una garantía.

## Audiencia y línea editorial
Español latinoamericano (es-419), sin regionalismos excesivos. Economía cotidiana, psicología del dinero, ahorro, decisiones bajo incertidumbre, productividad, concentración, hábitos y negociación. Los libros pueden inspirar **conceptos** pero nunca ser copiados ni recontados capítulo por capítulo.

Ejemplos: aumentar el sueldo no siempre aumenta el ahorro; ser rico frente a parecer rico; costo de oportunidad; trabajar más horas no siempre produce más valor; diversificación hipotética; gastos fijos y libertad financiera.

## Requisitos funcionales
- RF-01: elegir automáticamente temas no publicados.
- RF-02: generar con GPT guiones JSON estructurados y originales.
- RF-03: controlar veracidad, originalidad y riesgos financieros.
- RF-04: narrar con TTS local en español latinoamericano.
- RF-05: generar escenas programáticas sincronizadas con el audio.
- RF-06: exportar MP4 H.264/AAC, vertical 1080×1920, 60–90 segundos.
- RF-07: publicar automáticamente por APIs oficiales cuando exista autorización, sin duplicados.
- RF-08: conservar costo de GPT, estados, errores y URL de publicación.
- RF-09: ofrecer healthchecks y heartbeat para Uptime Kuma.
- RF-10: reintentar acotadamente, con control de presupuestos.

## No funcionales
Trazabilidad, funcionamiento desatendido con fallos seguros, contenedores sin privilegios, secretos fuera del código, portabilidad a Rocky Linux + Docker + SELinux, backup y recuperación.

## Exclusiones del MVP
Video generado mediante servicios comerciales; extracción o reproducción de libros; APIs de datos económicos; múltiples canales; panel analítico adicional a Kuma; monetización integrada.
