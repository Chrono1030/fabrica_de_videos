"""Ejemplo original y determinista; cifras hipotéticas, no estadísticas."""

from .models import VideoScript


def income_script(topic):
    return VideoScript(
        topic=topic,
        title="Ganar más no siempre significa ahorrar más",
        description="Un presupuesto hipotético ilustra el aumento del consumo.",
        language="es-419",
        hook="Un aumento puede desaparecer entre nuevos gastos.",
        disclaimer="Ejemplo educativo hipotético. Audio simulado.",
        references=[],
        scenes=[
            dict(
                narration=n,
                headline=h,
                visual_type=v,
                visual_label="Ejemplo hipotético",
                visual_data=d,
            )
            for n, h, v, d in [
                (
                    "En un ejemplo hipotético, una persona recibe un aumento. Su ingreso pasa de mil a mil doscientas unidades, pero eso no determina cuánto podrá ahorrar.",
                    "Más ingreso, ¿más ahorro?",
                    "bar_chart",
                    ["Antes:1000", "Después:1200"],
                ),
                (
                    "Si el gasto crece al mismo ritmo que el ingreso, el margen disponible puede mantenerse. Una mejora del sueldo no sustituye la revisión del presupuesto.",
                    "El consumo también puede crecer",
                    "line_chart",
                    ["Antes:800", "Después:1000"],
                ),
                (
                    "En este presupuesto hipotético quedan doscientas unidades en ambos casos. La diferencia entre ingresos y gastos explica el ahorro, no el ingreso por sí solo.",
                    "El margen queda igual",
                    "big_number",
                    ["200"],
                ),
                (
                    "Antes de asumir un nuevo gasto fijo, conviene comparar necesidades y prioridades. No hay una proporción universal correcta: cada hogar enfrenta restricciones distintas.",
                    "Revisar antes de comprometer",
                    "diagram",
                    ["Ingreso", "Gastos", "Margen"],
                ),
            ]
        ],
    )
