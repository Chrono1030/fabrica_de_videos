"""Verbalización conservadora, con números en convención latinoamericana."""

import re
from datetime import date

from num2words import num2words

NUMBER = r"\d+(?:[.,]\d+)*"
MONTHS = (
    "enero febrero marzo abril mayo junio julio agosto septiembre octubre "
    "noviembre diciembre"
).split()


def number(value: str) -> str:
    if "," in value and "." in value:
        value = (
            value.replace(".", "")
            if value.rfind(",") > value.rfind(".")
            else value.replace(",", "")
        )
    elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", value):
        value = value.replace(".", "")
    parts = value.replace(",", ".").split(".")
    if len(parts) > 2:
        raise ValueError("Cantidad ambigua: usar formato latinoamericano")
    result = num2words(int(parts[0]), lang="es")
    if len(parts) == 2:
        result += " coma " + " ".join(num2words(int(d), lang="es") for d in parts[1])
    return result


def normalize(text: str, currency: str | None = None) -> str:
    if currency not in (None, "ARS", "USD"):
        raise ValueError("Moneda debe ser ARS o USD")

    def verbal_date(match):
        day, month, year = map(int, match.groups())
        date(year, month, day)
        return f"{number(str(day))} de {MONTHS[month - 1]} de {number(str(year))}"

    text = re.sub(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", verbal_date, text)
    currencies = {"ARS": "pesos argentinos", "USD": "dólares estadounidenses"}
    text = re.sub(
        rf"\b(ARS|USD)\s*\$?\s*({NUMBER})",
        lambda m: f"{number(m[2])} {currencies[m[1]]}",
        text,
    )
    text = re.sub(
        rf"({NUMBER})\s*(ARS|USD)\b",
        lambda m: f"{number(m[1])} {currencies[m[2]]}",
        text,
    )
    if "$" in text:
        if currency is None:
            raise ValueError("Símbolo $ ambiguo: indicar ARS, USD o moneda de contexto")
        text = re.sub(
            rf"\$\s*({NUMBER})",
            lambda m: f"{number(m[1])} {currencies[currency]}",
            text,
        )
        if "$" in text:
            raise ValueError("Importe monetario inválido")
    text = re.sub(rf"({NUMBER})\s*%", lambda m: number(m[1]) + " por ciento", text)
    for short, full in {
        "PIB": "producto interno bruto",
        "PBI": "producto bruto interno",
        "IPC": "índice de precios al consumidor",
        "BCRA": "Banco Central de la República Argentina",
        "IVA": "impuesto al valor agregado",
        "TNA": "tasa nominal anual",
        "TEA": "tasa efectiva anual",
        "USD": currencies["USD"],
        "ARS": currencies["ARS"],
        "aprox.": "aproximadamente",
        "p. ej.": "por ejemplo",
        "EE. UU.": "Estados Unidos",
        "hs.": "horas",
        "km": "kilómetros",
        "kg": "kilogramos",
        "etc.": "etcétera",
    }.items():
        text = re.sub(r"(?<!\w)" + re.escape(short) + r"(?!\w)", full, text)
    return re.sub(rf"(?<!\w){NUMBER}(?!\w)", lambda m: number(m[0]), text)
