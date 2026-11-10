# Fábrica de videos

**Estado:** diseño aprobado y andamiaje técnico inicial del MVP. **No desplegado; no conectado aún a cuentas reales.**

Proyecto para producir automáticamente videos cortos educativos en **español latinoamericano** sobre economía, finanzas personales, hábitos y productividad, inspirados en conceptos generales de libros, pero con guiones originales. El flujo previsto es:

`Programador → catálogo editorial → GPT API (guiones estructurados) → validación → TTS local → escenas SVG/Pillow → composición FFmpeg → control de calidad → API de publicación → registro y alertas`

## Decisiones aprobadas

- **Automatización de extremo a extremo**, con bloqueo seguro y alertas cuando haya errores o dudas.
- **OpenAI API por consumo**, con registro por ejecución y presupuesto inicial de ensayo.
- **Piper** como candidato prioritario a narración local en español latinoamericano; Kokoro TTS como alternativa a evaluar, tras verificar voces y licencias.
- **Identidad visual:** minimalismo, azul oscuro, marfil y acentos dorados; gráficos y figuras programáticas; sin generación comercial de clips.
- **Investigación:** contenidos conceptuales y atemporales; sin conexión obligatoria a APIs de indicadores económicos.
- **Orquestación:** n8n + Python; estados y auditoría internos, disponibilidad mediante Uptime Kuma.
- **Piloto:** 1 short de 60–90 s diarios, 1080 × 1920, hasta 30 videos para validar costos y respuesta de audiencia.
- **Publicación:** YouTube por API oficial tras credenciales y permisos. TikTok por Content Posting API solo cuando obtengamos autorización para visibilidad pública.

## Contenido del repositorio

- `docs/PRODUCTO.md`: visión, alcance y requisitos.
- `docs/MVP.md`: criterios de aceptación.
- `docs/ARQUITECTURA.md`: componentes, estados y tolerancia a fallos.
- `docs/RIESGOS.md`: riesgos técnicos, legales y operativos.
- `docs/POLITICA_EDITORIAL.md`: originalidad, calidad y comprobación.
- `docs/IMPLEMENTACION.md`: preparación y secuencia de integración.
- `docs/ROADMAP.md`: tareas y fases.
- `src/fabrica/`: prototipo de esquema, validación y tarjetas gráficas.
- `examples/guion_demo.json`: guion de prueba estructurado.

## Inicio rápido (prototipo; requiere dependencias locales)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
python -m fabrica.cli validate examples/guion_demo.json
python -m fabrica.cli cards examples/guion_demo.json --output out/cards
pytest -q
```

La narración real requiere instalar Piper y un modelo de voz con licencia adecuada. El render y la publicación completos **todavía no están implementados**. No incorporar credenciales, tokens OAuth, modelos ni videos al control de versiones.

## Referencias

- [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [YouTube videos.insert](https://developers.google.com/youtube/v3/docs/videos/insert)
- [YouTube: políticas de monetización](https://support.google.com/youtube/answer/1311392)
- [TikTok Content Posting API](https://developers.tiktok.com/docs/en/content-posting-api-reference-direct-post)
- [Ley argentina 11.723](https://www.argentina.gob.ar/normativa/nacional/42755/actualizacion)
