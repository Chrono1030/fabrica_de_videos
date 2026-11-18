"""Captions aligned to measured phrase WAVs, without inferred word alignment."""

from .subtitle_style import SubtitleStyle


def stamp(seconds, ass=False):
    units = round(seconds * (100 if ass else 1000))
    rate = 100 if ass else 1000
    h, rest = divmod(units, 3600 * rate)
    m, rest = divmod(rest, 60 * rate)
    s, fraction = divmod(rest, rate)
    return (
        f"{h}:{m:02}:{s:02}.{fraction:02}"
        if ass
        else f"{h:02}:{m:02}:{s:02},{fraction:03}"
    )


def write_subtitles(timeline, board, config, job, save):
    from .cards import font

    style = SubtitleStyle(
        size=config.subtitle_size,
        margin=config.subtitle_margin,
        color="F6EEDB",
        outline=3,
    )
    safe = board.safe_area
    # ASS uses a fixed logical canvas, matching the existing visual components.
    bottom = 1920 - style.margin
    if (
        bottom > (board.height - safe.bottom) * 1920 / board.height
        or bottom - 2 * style.size * 1.4 < safe.top * 1920 / board.height
    ):
        raise ValueError("Captions outside the storyboard safe zone")
    face = font(style.size)
    srt, dialogue = [], []
    previous = 0
    for i, segment in enumerate(timeline.segments, 1):
        text = segment.subtitle_text
        lines = text.splitlines()
        if (
            not (0 <= previous <= segment.start < segment.end <= timeline.duration)
            or len(lines) > 2
        ):
            raise ValueError("Invalid caption interval or line count")
        if any(len(line) > 34 or face.getlength(line) > 820 for line in lines):
            raise ValueError("Caption exceeds safe width")
        if any(c in text for c in "{}\\"):
            raise ValueError("Caption contains unsupported ASS control characters")
        srt.append(f"{i}\n{stamp(segment.start)} --> {stamp(segment.end)}\n{text}\n")
        escaped = text.replace("\n", r"\N")
        dialogue.append(
            f"Dialogue: 0,{stamp(segment.start, True)},{stamp(segment.end, True)},Default,,0,0,0,,{escaped}"
        )
        previous = segment.end
    (job / "subtitles.srt").write_text("\n".join(srt), encoding="utf-8")
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style.font},{style.size},&H00DBEEF6,&H00DBEEF6,&H00351A0B,&H80000000,0,0,0,0,100,100,0,0,1,3,0,2,110,110,{style.margin},1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    (job / "subtitles.ass").write_text(
        header + "\n".join(dialogue) + "\n", encoding="utf-8"
    )
    save(
        job / "subtitle_validation.json",
        dict(
            valid=True,
            cues=len(srt),
            alignment=timeline.alignment,
            phonetic_alignment=False,
            style=style.config(),
            safe_bottom=bottom,
        ),
    )
