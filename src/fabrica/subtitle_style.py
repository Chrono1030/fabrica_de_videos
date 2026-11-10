"""Subtítulos aproximados: distribución por palabras, sin alineación fonética."""

import re
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class SubtitleStyle:
    burn: bool = True
    font: str = "DejaVu Sans"
    size: int = 44
    margin: int = 320
    color: str = "F4EEDD"
    outline: int = 2

    def __post_init__(self):
        if (
            not 200 <= self.margin <= 400
            or not 24 <= self.size <= 52
            or not 0 <= self.outline <= 5
        ):
            raise ValueError("Estilo fuera de la zona segura (unidades 1080×1920)")
        if not re.fullmatch(r"[A-Za-z0-9 _-]+", self.font) or not re.fullmatch(
            r"[0-9A-Fa-f]{6}", self.color
        ):
            raise ValueError("Fuente o color inválido")

    def config(self):
        return asdict(self)

    def ass_style(self):
        rgb = self.color
        return f"FontName={self.font},FontSize={self.size},PrimaryColour=&H00{rgb[4:6]}{rgb[2:4]}{rgb[:2]},OutlineColour=&H00122135,BorderStyle=1,Outline={self.outline},Shadow=1,Alignment=2,MarginV={self.margin},MarginL=110,MarginR=110"


def cues(text):
    from .cards import font

    face = font(52)
    lines, current = [], ""
    # Limitar simultáneamente caracteres y ancho real en el tamaño máximo.
    for word in " ".join(text.split()).replace("\\", "").split():
        while word:
            candidate = (current + " " + word).strip()
            if len(candidate) <= 34 and face.getlength(candidate) <= 820:
                current = candidate
                break
            if current:
                lines.append(current)
                current = ""
            else:
                cut = 1
                while (
                    cut < len(word)
                    and cut < 34
                    and face.getlength(word[: cut + 1]) <= 820
                ):
                    cut += 1
                lines.append(word[:cut])
                word = word[cut:]
    if current:
        lines.append(current)
    return ["\n".join(lines[i : i + 2]) for i in range(0, len(lines), 2)]
