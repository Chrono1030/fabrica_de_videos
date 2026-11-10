"""Contrato tipado entre el generador de guiones y el renderizador."""
from enum import Enum
from pydantic import BaseModel, ConfigDict, model_validator


class VisualType(str, Enum):
    concept = "concept"
    big_number = "big_number"
    comparison = "comparison"
    bar_chart = "bar_chart"


class Scene(BaseModel):
    model_config = ConfigDict(extra="forbid")
    narration: str
    visual_type: VisualType
    headline: str
    visual_label: str
    visual_data: list[str]

    @model_validator(mode="after")
    def valid_scene(self):
        if not self.narration.strip() or not self.headline.strip():
            raise ValueError("La narración y el título de escena son obligatorios")
        if len(self.headline) > 95:
            raise ValueError("Texto de escena demasiado largo")
        if len(self.visual_data) > 8:
            raise ValueError("Demasiados elementos visuales")
        return self


class VideoScript(BaseModel):
    model_config = ConfigDict(extra="forbid")
    topic: str
    title: str
    description: str
    language: str
    hook: str
    scenes: list[Scene]
    disclaimer: str
    references: list[str]

    @model_validator(mode="after")
    def validate_script(self):
        if self.language != "es-419":
            raise ValueError("Solo español latinoamericano (es-419)")
        if not 2 <= len(self.scenes) <= 12:
            raise ValueError("El guion requiere entre 2 y 12 escenas")
        if len(self.title) > 100:
            raise ValueError("El título excede el límite de 100 caracteres")
        return self
