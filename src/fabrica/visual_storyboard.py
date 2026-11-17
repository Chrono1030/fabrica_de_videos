"""Renderer-independent visual planning; no browser or engine dependencies."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SafeArea(StrictModel):
    top: int = Field(ge=0)
    bottom: int = Field(ge=0)
    left: int = Field(ge=0)
    right: int = Field(ge=0)


class Budget(StrictModel):
    income: int = Field(gt=0)
    fixed: int = Field(ge=0)
    variable: int = Field(ge=0)
    savings: int = Field(ge=0)

    @model_validator(mode="after")
    def balanced(self):
        if self.fixed + self.variable + self.savings != self.income:
            raise ValueError("Budget must sum exactly to income")
        return self


class VisualEvent(StrictModel):
    id: str
    at: float = Field(ge=0)
    duration: float = Field(gt=0)
    intent: str
    elements: list[str]


class VisualScene(StrictModel):
    id: str
    narrative_segment_id: str
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    narrative: str
    visual_intent: str
    semantic_elements: list[str]
    quantitative_data: dict[str, int]
    events: list[VisualEvent]

    @model_validator(mode="after")
    def event_bounds(self):
        if self.end <= self.start or any(
            e.at + e.duration > self.end - self.start for e in self.events
        ):
            raise ValueError("Invalid scene/event timing")
        return self


class VisualStoryboard(StrictModel):
    schema_version: Literal[1] = 1
    video_id: str
    title: str
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    fps: int = Field(gt=0)
    duration: float = Field(gt=0)
    language: str
    audio: Literal["none"]
    palette: dict[str, str]
    typography: dict[str, str | int]
    safe_area: SafeArea
    budgets: dict[str, Budget]
    scenes: list[VisualScene]
    source_metadata: dict[str, str]

    @model_validator(mode="after")
    def continuity(self):
        if not self.scenes or self.scenes[0].start != 0:
            raise ValueError("Storyboard must start at zero")
        if any(a.end != b.start for a, b in zip(self.scenes, self.scenes[1:])):
            raise ValueError("Scenes must be contiguous")
        if self.scenes[-1].end != self.duration:
            raise ValueError("Scenes must cover duration")
        for key in ("id", "narrative_segment_id"):
            values = [getattr(s, key) for s in self.scenes]
            if len(values) != len(set(values)):
                raise ValueError("Scene and narrative IDs must be unique")
        if self.safe_area.left + self.safe_area.right >= self.width:
            raise ValueError("Empty horizontal safe area")
        if self.safe_area.top + self.safe_area.bottom >= self.height:
            raise ValueError("Empty vertical safe area")
        return self
