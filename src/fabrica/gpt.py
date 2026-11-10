"""Adaptador inicial para Structured Outputs; no invocarlo sin credenciales reales."""

import os

from openai import OpenAI

from .models import VideoScript

SYSTEM = """Eres guionista de divulgación económica en español latinoamericano neutro.
Escribe explicaciones originales sobre conceptos económicos. Los libros inspiran temas,
pero NO copies, traduzcas ni adaptes pasajes, ejemplos distintivos ni estructuras de capítulos.
No recomiendes inversiones personalizadas ni prometas rentabilidades.
Evita datos actuales, cifras reales sin fuentes y citas inventadas.
Utiliza ejemplos originales y, si hay números hipotéticos, etiquétalos claramente.
Cada escena: narración, titular corto, visual_type en el enum, etiqueta y datos visuales. Para bar_chart y line_chart, visual_data usa etiqueta:valor con valores numéricos no negativos. No inventes referencias: usa lista vacía si no puedes verificarlas.
Las referencias no deben inventarse; si no hay referencias comprobadas, lista vacía.
Produce 5-8 escenas y un narración total aproximada de 140-180 palabras, duración estimada no garantizada.
Idioma exacto: es-419. Nada de modismos regionales ni español peninsular."""


def generate(topic: str) -> tuple[VideoScript, dict]:
    model = os.getenv("OPENAI_MODEL", "gpt-6-luna")
    client = OpenAI()
    response = client.responses.parse(
        model=model,
        input=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"Desarrolla un video sobre: {topic}"},
        ],
        text_format=VideoScript,
    )
    script = response.output_parsed
    if script is None:
        raise ValueError("La API no devolvió un guion estructurado")
    usage = response.usage
    return script, {
        "model": model,
        "input_tokens": usage.input_tokens if usage else 0,
        "output_tokens": usage.output_tokens if usage else 0,
        "response_id": response.id,
    }


def estimate_usd(usage: dict) -> float:
    """Precios de referencia editables: no son garantía de tarifas vigentes."""
    input_rate = float(os.getenv("OPENAI_INPUT_USD_PER_1M", "0.10"))
    output_rate = float(os.getenv("OPENAI_OUTPUT_USD_PER_1M", "0.50"))
    import math

    if not all(math.isfinite(r) and r >= 0 for r in (input_rate, output_rate)):
        raise ValueError("Tarifas inválidas")
    return (
        usage.get("input_tokens", 0) * input_rate
        + usage.get("output_tokens", 0) * output_rate
    ) / 1_000_000


class GenerationError(RuntimeError):
    pass


def generate_checked(topic: str, client=None, remaining_usd: float = 0):
    """Sin reintentos de red automáticos: una respuesta perdida puede tener costo."""
    from decimal import Decimal

    from .editorial import check

    maximum = int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "4000"))
    ceiling = Decimal(os.getenv("OPENAI_REQUEST_RESERVE_USD", "1.0"))
    if not ceiling.is_finite() or ceiling <= 0 or Decimal(str(remaining_usd)) < ceiling:
        raise GenerationError(
            "Presupuesto interno insuficiente para reservar la llamada"
        )
    client = client or OpenAI(timeout=60, max_retries=0)
    try:
        response = client.responses.parse(
            model=os.getenv("OPENAI_MODEL", "gpt-6-luna"),
            input=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": topic},
            ],
            text_format=VideoScript,
            max_output_tokens=maximum,
        )
    except Exception as exc:
        # No persistir texto de errores externos que pudiera incluir secretos.
        raise GenerationError(
            f"Error de API: {type(exc).__name__}; costo desconocido"
        ) from exc
    usage = response.usage
    if usage is None:
        raise GenerationError(
            "Consumo desconocido; requiere conciliación antes de reintentar"
        )
    record = {
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "response_id": response.id,
        "model": os.getenv("OPENAI_MODEL", "gpt-6-luna"),
    }
    record["estimated_usd"] = estimate_usd(record)
    script = response.output_parsed
    # Retornar consumo incluso si el contenido no pasa validación.
    issues = ["Sin guion estructurado"] if script is None else check(script)
    return script, record, issues
