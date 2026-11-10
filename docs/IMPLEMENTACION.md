# Implementación inicial (plan, no despliegue completado)

## Requisitos
Rocky Linux 9.8, Docker + Compose, SELinux Enforcing, Python >=3.11, FFmpeg/ffprobe, fuente TrueType con licencia y motor Piper + voz es_MX cuya licencia permita el uso previsto.

Rutas de referencia: `/srv/appdata/fabrica-videos` para configuración persistente y `/srv/fabrica-videos` para recursos audiovisuales; establecer fcontext de SELinux y UID correctos antes de montar volúmenes.

La suscripción de ChatGPT **no** reemplaza la facturación independiente de la API. Crear clave de proyecto, definir permisos, presupuesto y revisar precios oficiales. Tokens OAuth de YouTube/TikTok se configurarán más adelante.

## Preparación del prototipo

```bash
git clone https://github.com/Chrono1030/fabrica_de_videos.git
cd fabrica_de_videos
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
python -m fabrica.cli validate examples/guion_demo.json
python -m fabrica.cli cards examples/guion_demo.json --output out/cards
pytest -q
```

No es un flujo de producción completo: los comandos anteriores validan guion y generan PNG. Todavía falta integrar llamadas reales GPT, TTS, render de MP4, QA semántico, orquestación y publicadores.

## Orquestación
`deploy/compose.orchestration.yml` arranca n8n ligado exclusivamente a `127.0.0.1:5678`. Establecer `N8N_ENCRYPTION_KEY` por canal privado, fijar digest de la imagen antes de producción y no montar Docker socket en n8n.

```bash
docker compose -f deploy/compose.orchestration.yml config --quiet
docker compose -f deploy/compose.orchestration.yml up -d
```

Acceso remoto mediante VPN o túnel autenticado, sin exposición directa del puerto.

## Publicación
`PUBLISH_ENABLED=false` por defecto. YouTube requiere OAuth, videos.insert y verificación del ID remoto; empezar con visibilidad privada. TikTok requiere permisos de publicación, auditoría y consentimiento conforme al flujo aceptado. No usar automatización por navegador para sortear estas reglas.

## Operación y monitoreo
Kuma verificará /healthz y heartbeat del **último trabajo publicado con éxito**; los logs internos y SQLite mantienen errores y costos. Hacer copias verificables de estados, almacenar credenciales fuera del repositorio y evitar claves en logs. Los límites de gasto implementados por código no garantizan bloquear cargos concurrentes o diferidos del proveedor.
