"""Editorial planning shared by every renderer; no engine APIs or templates."""

from .models import VideoScript
from .visual_storyboard import VisualStoryboard

PALETTE = dict(
    background="#112037",
    surface="#182B40",
    gold="#E6B864",
    ivory="#F6EEDB",
    muted="#9CB0C4",
)
LAYOUTS = {
    "concept": "cards",
    "icon": "cards",
    "comparison": "comparison",
    "diagram": "flow",
    "big_number": "counter",
    "bar_chart": "bars",
    "line_chart": "bars",
}


def plan_script(
    script: VideoScript, job_id, *, width=1080, height=1920, fps=24, scene_seconds=8
):
    scenes, data = [], {}
    step = round(scene_seconds * fps) / fps
    if step <= 0:
        raise ValueError("Scene duration must contain at least one frame")
    for i, source in enumerate(script.scenes):
        sid, segment = f"scene-{i + 1:02}", f"segment-{i + 1:02}"
        elements = []
        for j, item in enumerate(
            source.visual_data or [source.visual_label or source.headline]
        ):
            label, separator, numeric = item.rpartition(":")
            value = None
            if separator:
                value = float(numeric)
            elif source.visual_type == "big_number":
                try:
                    value = float(item)
                except ValueError:
                    value = item
                label = source.visual_label or source.headline
            else:
                label = item
            key = f"{sid}.value-{j}"
            if value is not None:
                data[key] = value
            elements.append(
                dict(
                    id=f"item-{j + 1}",
                    label=label,
                    data_key=key if value is not None else None,
                    color_role=["gold", "ivory", "muted"][j % 3],
                    format="text" if isinstance(value, str) else "number",
                )
            )
        layout = LAYOUTS[source.visual_type]
        duration = step
        scenes.append(
            dict(
                id=sid,
                narrative_segment_id=segment,
                start=i * step,
                end=(i + 1) * step,
                narrative=source.narration,
                visual_intent=source.visual_label or source.headline,
                semantic_elements=[e["id"] for e in elements],
                quantitative_data={},
                title=source.headline,
                caption=source.visual_label,
                layout=layout,
                elements=elements,
                events=[
                    dict(
                        id=f"{sid}-build",
                        at=0,
                        duration=min(duration, max(0.25, duration * 0.4)),
                        intent=source.visual_label or source.headline,
                        elements=[e["id"] for e in elements],
                        action={
                            "counter": "count",
                            "bars": "grow",
                            "comparison": "compare",
                        }.get(layout, "reveal"),
                    )
                ],
                anchors=[
                    dict(
                        id=segment,
                        start=i * step,
                        end=(i + 1) * step,
                        text=source.narration,
                    )
                ],
            )
        )
    return VisualStoryboard.model_validate(
        dict(
            schema_version=2,
            job_id=job_id,
            video_id=job_id,
            title=script.title,
            width=width,
            height=height,
            fps=fps,
            duration=len(scenes) * step,
            language=script.language,
            audio="none",
            palette=PALETTE,
            typography=dict(family="DejaVu Sans", heading_px=68, body_px=40),
            safe_area=dict(
                top=round(height * 160 / 1920),
                bottom=round(height * 260 / 1920),
                left=round(width * 80 / 1080),
                right=round(width * 80 / 1080),
            ),
            data=data,
            scenes=scenes,
            source_metadata=dict(
                brand="Mente y Capital",
                origin="Factory VideoScript; deterministic visual planner v2",
                disclaimer=script.disclaimer,
                tts_status="pending; narrative anchors are planned, not phonetic alignment",
            ),
        )
    )


def validate_correspondence(script, storyboard):
    if len(script.scenes) != len(storyboard.scenes) or script.title != storyboard.title:
        raise ValueError("Storyboard does not correspond to script")
    if any(
        a.narration != b.narrative for a, b in zip(script.scenes, storyboard.scenes)
    ):
        raise ValueError("Storyboard narrative differs from script")
