"""Renderer-independent visual planning; no browser or engine dependencies."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


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


class VisualElement(StrictModel):
    """Semantic component inputs, never executable HTML or engine instructions."""

    id: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]*$")
    label: str = Field(min_length=1, max_length=80)
    value: float | str | None = None
    data_key: str | None = None
    narration_anchor: str | None = None
    initial_value: float | None = None
    initial_key: str | None = None
    format: Literal["number", "currency", "percent", "text"] = "number"
    unit: str = Field(default="", max_length=20)
    color_role: Literal["gold", "ivory", "muted"] = "gold"

    @model_validator(mode="after")
    def single_source(self):
        if self.value is not None and self.data_key is not None:
            raise ValueError("Element must have a single value source")
        if self.initial_value is not None and self.initial_key is not None:
            raise ValueError("Element must have a single initial value source")
        return self


class NarrativeAnchor(StrictModel):
    id: str
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    text: str


class VisualEvent(StrictModel):
    id: str
    at: float = Field(ge=0)
    duration: float = Field(gt=0)
    intent: str
    elements: list[str]
    action: Literal[
        "reveal", "grow", "count", "transfer", "compare", "highlight", "transition"
    ] = "reveal"
    from_id: str | None = None
    to_id: str | None = None
    amount: float | None = Field(default=None, ge=0)
    amount_key: str | None = None


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
    title: str = ""
    caption: str = ""
    layout: Literal[
        "cards", "bars", "flow", "counter", "distribution", "comparison", "transfer"
    ] = "cards"
    elements: list[VisualElement] = Field(default_factory=list, max_length=6)
    anchors: list[NarrativeAnchor] = Field(default_factory=list)
    transition: Literal["cut", "settle"] = "settle"

    @model_validator(mode="after")
    def event_bounds(self):
        if self.end <= self.start or any(
            e.at + e.duration > self.end - self.start for e in self.events
        ):
            raise ValueError("Invalid scene/event timing")
        return self


class DataTotal(StrictModel):
    total_key: str
    parts: list[str] = Field(min_length=1)


class VisualStoryboard(StrictModel):
    schema_version: Literal[1, 2] = 1
    job_id: str | None = None
    video_id: str
    title: str
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    fps: int = Field(gt=0)
    duration: float = Field(gt=0)
    language: str
    audio: Literal["none", "external"]
    palette: dict[str, str]
    typography: dict[str, str | int]
    safe_area: SafeArea
    budgets: dict[str, Budget] = Field(default_factory=dict)
    data: dict[str, JsonValue] = Field(default_factory=dict)
    totals: list[DataTotal] = Field(default_factory=list)
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
        if self.schema_version == 2:
            self.validate_visual_plan()
        return self

    def value_of(self, element, initial=False):
        key = element.initial_key if initial else element.data_key
        value = element.initial_value if initial else element.value
        if key is not None:
            if (
                key not in self.data
                or not isinstance(self.data[key], (int, float, str))
                or isinstance(self.data[key], bool)
            ):
                raise ValueError(f"Missing or nonscalar data: {key}")
            return self.data[key]
        return value

    def validate_visual_plan(self):
        import math
        import re

        if self.language != "es-419" or self.width % 2 or self.height % 2:
            raise ValueError("Require es-419 and even dimensions")
        for role in ("background", "surface", "gold", "ivory", "muted"):
            if not re.fullmatch(r"#[0-9A-Fa-f]{6}", self.palette.get(role, "")):
                raise ValueError("Palette must provide five hex colors")
        if self.typography.get("family") != "DejaVu Sans":
            raise ValueError("Use the currently verified project typeface DejaVu Sans")
        from decimal import Decimal

        for constraint in self.totals:
            keys = [constraint.total_key, *constraint.parts]
            if len(constraint.parts) != len(set(constraint.parts)) or any(
                not isinstance(self.data.get(k), (int, float))
                or isinstance(self.data.get(k), bool)
                or not math.isfinite(self.data[k])
                for k in keys
            ):
                raise ValueError("Invalid quantitative total references")
            if sum(Decimal(str(self.data[k])) for k in constraint.parts) != Decimal(
                str(self.data[constraint.total_key])
            ):
                raise ValueError("Quantitative parts must sum exactly to total")
        anchor_ids = []
        for scene in self.scenes:
            if not scene.title.strip() or not scene.elements or not scene.anchors:
                raise ValueError(
                    "V2 scene requires title, elements and narrative anchors"
                )
            if (
                abs(scene.start * self.fps - round(scene.start * self.fps)) > 1e-6
                or abs(scene.end * self.fps - round(scene.end * self.fps)) > 1e-6
            ):
                raise ValueError("Scene boundaries must align to frames")
            if scene.layout == "counter" and len(scene.elements) > 2:
                raise ValueError("Counter layout supports one or two primary numbers")
            anchor_set = {a.id for a in scene.anchors}
            if any(
                e.narration_anchor and e.narration_anchor not in anchor_set
                for e in scene.elements
            ):
                raise ValueError(
                    "Visual element references an unknown narration anchor"
                )
            ids = {e.id for e in scene.elements}
            if len(ids) != len(scene.elements):
                raise ValueError("Duplicate visual element ID")
            values = {e.id: self.value_of(e) for e in scene.elements}
            for element in scene.elements:
                for value in (
                    self.value_of(element),
                    self.value_of(element, initial=True),
                ):
                    if isinstance(value, (int, float)) and not math.isfinite(value):
                        raise ValueError("Visual data must be finite")
                if scene.layout in ("bars", "distribution", "transfer") and (
                    not isinstance(values[element.id], (int, float))
                    or values[element.id] < 0
                ):
                    raise ValueError("Quantitative layout requires nonnegative values")
            if (
                scene.layout in ("distribution", "transfer")
                and sum(values.values()) <= 0
            ):
                raise ValueError("Distribution needs a positive total")
            for event in scene.events:
                if not set(event.elements) <= ids:
                    raise ValueError("Event references unknown elements")
                if event.action == "transfer":
                    amount = (
                        self.data.get(event.amount_key)
                        if event.amount_key
                        else event.amount
                    )
                    if (
                        event.from_id not in ids
                        or event.to_id not in ids
                        or event.from_id == event.to_id
                    ):
                        raise ValueError(
                            "Transfer requires distinct existing categories"
                        )
                    if (
                        not isinstance(amount, (float, int))
                        or isinstance(amount, bool)
                        or not math.isfinite(amount)
                        or amount < 0
                        or amount > values[event.from_id]
                    ):
                        raise ValueError("Transfer amount is invalid")
            if not any(
                a.id == scene.narrative_segment_id and a.text == scene.narrative
                for a in scene.anchors
            ):
                raise ValueError("Narrative segment must have a matching text anchor")
            for anchor in scene.anchors:
                if not scene.start <= anchor.start < anchor.end <= scene.end:
                    raise ValueError("Narrative anchor outside scene")
                anchor_ids.append(anchor.id)
        if len(anchor_ids) != len(set(anchor_ids)):
            raise ValueError("Narrative anchors must be unique")
