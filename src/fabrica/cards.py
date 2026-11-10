"""Tarjetas visuales verticales, sin descargar ni incluir activos externos."""
from pathlib import Path
import textwrap
from PIL import Image, ImageDraw, ImageFont
from .models import VideoScript, VisualType

W, H = 1080, 1920
NAVY = (18, 33, 53)
GOLD = (231, 181, 89)
IVORY = (244, 238, 221)
MUTED = (161, 180, 198)


def font(size: int, specified: str | None = None):
    candidates = [specified, "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf"]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def wrap(text: str, width: int = 24) -> list[str]:
    lines = []
    for paragraph in text.splitlines():
        lines.extend(textwrap.wrap(paragraph, width=width, break_long_words=False) or [""])
    return lines


def draw_centered(d, words: str, y: int, f, fill, spacing: int = 25):
    lines = wrap(words)
    for line in lines[:5]:
        box = d.textbbox((0, 0), line, font=f)
        x = (W - (box[2] - box[0])) // 2
        d.text((x, y), line, font=f, fill=fill)
        y += (box[3] - box[1]) + spacing + 15
    return y


def make_card(scene, index: int, total: int, target: Path, font_path: str | None = None):
    image = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(image)
    d.rounded_rectangle((62, 60, W - 62, H - 60), radius=34, outline=(55, 74, 95), width=4)
    d.text((95, 105), f"ECONOMÍA  ·  {index:02d}/{total:02d}", font=font(42, font_path), fill=GOLD)
    y = draw_centered(d, scene.headline.upper(), 280, font(77, font_path), IVORY)
    d.line((200, y + 50, W - 200, y + 50), fill=GOLD, width=6)
    cy = max(y + 160, 900)
    if scene.visual_type == VisualType.bar_chart:
        items = scene.visual_data[:4]
        for i, item in enumerate(items):
            x = 160 + i * 205
            bar_height = 160 + 100 * (i + 1)
            d.rounded_rectangle((x, cy + 220 - bar_height, x + 120, cy + 220), radius=15, fill=GOLD)
            d.text((x - 20, cy + 245), item[:13], font=font(27, font_path), fill=IVORY)
    elif scene.visual_type == VisualType.comparison:
        d.rounded_rectangle((100, cy - 100, 520, cy + 260), radius=30, outline=GOLD, width=5)
        d.rounded_rectangle((560, cy - 100, 980, cy + 260), radius=30, outline=GOLD, width=5)
        for i, label in enumerate(scene.visual_data[:2]):
            draw = label[:22]
            d.text((130 + i * 460, cy + 35), draw, font=font(42, font_path), fill=IVORY)
    else:
        d.ellipse((370, cy - 160, 710, cy + 180), fill=(31, 58, 84), outline=GOLD, width=8)
        d.text((425, cy - 15), "$  %", font=font(74, font_path), fill=GOLD)
    draw_centered(d, scene.visual_label, 1410, font(51, font_path), MUTED)
    d.text((95, 1740), "CONTENIDO EDUCATIVO", font=font(35, font_path), fill=MUTED)
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target)
    return target


def create_cards(script: VideoScript, outdir: Path, font_path: str | None = None) -> list[Path]:
    return [make_card(scene, i, len(script.scenes), outdir / f"scene_{i:02d}.png", font_path)
            for i, scene in enumerate(script.scenes, start=1)]
