"""Shared contract primitives; each adapter owns its layout and animation."""

import base64
import html
import json
import math
import shutil
from pathlib import Path

from PIL import Image, ImageDraw

from fabrica.cards import font

ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "experiments/renderer_ab"


def text(d, value, box, size, color):
    x, y, w, h = box
    f = font(size)
    lines = []
    for para in value.split("\n"):
        line = ""
        for word in para.split():
            trial = (line + " " + word).strip()
            if d.textlength(trial, font=f) > w and line:
                lines.append(line)
                line = word
            else:
                line = trial
        lines.append(line)
    assert len(lines) * (size + 12) <= h, (value, box)
    for line in lines:
        d.text((x + w / 2, y), line, font=f, fill=color, anchor="mt")
        y += size + 12


def pillow_frame(fixture, settings, t):
    c = settings["colors"]
    image = Image.new("RGB", (1080, 1920), c["background"])
    d = ImageDraw.Draw(image)
    i = next(i for i, b in enumerate(fixture["beats"]) if b["start"] <= t < b["end"])
    b = fixture["beats"][i]
    local = t - b["start"]
    gold, ink = c["gold"], c["ivory"]
    text(d, b["heading"], (80, 180, 920, 240), 54, gold)
    d.line((80, 440, 1000, 440), fill=gold, width=3)

    def clock(cx, cy, r):
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=gold, width=10)
        a = local * 0.8 - math.pi / 2
        d.line(
            (cx, cy, cx + math.cos(a) * r * 0.7, cy + math.sin(a) * r * 0.7),
            fill=ink,
            width=8,
        )
        d.line((cx, cy, cx - r * 0.4, cy - r * 0.2), fill=ink, width=10)

    def book(cx, cy):
        d.line(
            (
                cx - 85,
                cy + 50,
                cx - 85,
                cy - 65,
                cx,
                cy - 45,
                cx + 85,
                cy - 65,
                cx + 85,
                cy + 50,
                cx,
                cy + 70,
                cx - 85,
                cy + 50,
            ),
            fill=gold,
            width=8,
        )
        d.line((cx, cy - 45, cx, cy + 70), fill=gold, width=6)

    def friends(cx, cy):
        for off in [-52, 52]:
            d.ellipse(
                (cx + off - 26, cy - 65, cx + off + 26, cy - 13), outline=gold, width=7
            )
            d.arc(
                (cx + off - 48, cy - 5, cx + off + 48, cy + 100),
                180,
                360,
                fill=gold,
                width=8,
            )

    if i == 0:
        clock(540, 710, 150)
        d.line((540, 900, 540, 950, 300, 1070), fill=gold, width=8)
        d.line((540, 950, 780, 1070), fill=gold, width=8)
        book(300, 1180)
        friends(780, 1180)
    elif i in [1, 2]:
        for j, cx in enumerate([310, 770]):
            border = gold if i == 1 or j == 0 else c["muted"]
            d.rounded_rectangle(
                (cx - 210, 650, cx + 210, 1150),
                radius=30,
                fill=c["surface"],
                outline=border,
                width=7,
            )
            (book if j == 0 else friends)(cx, 840)
            text(
                d, fixture["beats"][1]["labels"][j], (cx - 195, 1000, 390, 90), 42, ink
            )
        if i == 2:
            p = min(1, local / 1.3)
            d.line((610, 690, 610 + 320 * p, 690 + 410 * p), fill=c["muted"], width=10)
            d.line((145, 1200, 205, 1260, 430, 1190), fill=gold, width=10)
    else:
        clock(540, 700, 115)
        friends(300, 1040)
        d.line((690, 1090, 820, 960, 820, 1020), fill=gold, width=10)
        text(d, fixture["claims"][0], (100, 1220, 880, 190), 39, ink)
    text(d, b["narrative"], (100, 1430, 880, 200), 36, ink)
    d.rounded_rectangle((80, 1680, 1000, 1840), radius=20, fill=c["surface"])
    text(d, b["caption"], (105, 1710, 870, 120), 35, ink)
    d.rectangle((80, 1650, 80 + 920 * t / 20, 1655), fill=gold)
    return image


def svg(kind):
    paths = {
        "clock": '<circle cx="120" cy="120" r="95"/><path class="hand" d="M120 120 L120 45 M120 120 L175 145"/>',
        "book": '<path d="M20 50 L120 70 L220 50 L220 190 L120 210 L20 190 Z M120 70 V210"/>',
        "friends": '<circle cx="65" cy="75" r="30"/><circle cx="175" cy="75" r="30"/><path d="M15 195 Q15 115 65 115 Q115 115 115 195 M125 195 Q125 115 175 115 Q225 115 225 195"/>',
        "future": '<path d="M25 200 L200 35 M130 35 H200 V105"/>',
        "fork": '<path d="M120 15 V100 L25 215 M120 100 L215 215"/>',
    }
    return '<svg viewBox="0 0 240 240" aria-hidden="true">' + paths[kind] + "</svg>"


def build_html(engine, fixture, settings, target):
    """Distinct native timelines: GSAP/HyperFrames and sequence/gm.onFrame."""
    target.mkdir(parents=True, exist_ok=True)
    fontdata = base64.b64encode(
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf").read_bytes()
    ).decode()
    c = settings["colors"]
    css = f"""@font-face{{font-family:Contract;src:url(data:font/ttf;base64,{fontdata})}}*{{box-sizing:border-box}}html,body{{margin:0;width:1080px;height:1920px;background:{c["background"]};color:{c["ivory"]};font-family:Contract;overflow:hidden}}section{{position:absolute;inset:0;padding:170px 80px 260px}}h1{{font-size:54px;line-height:1.25;text-align:center;color:{c["gold"]};height:240px;margin:0;border-bottom:3px solid {c["gold"]}}}svg{{width:240px;height:240px;fill:none;stroke:{c["gold"]};stroke-width:8;stroke-linecap:round;stroke-linejoin:round}}.stage{{position:absolute;top:570px;left:80px;width:920px;height:740px;display:flex;align-items:center;justify-content:center;gap:40px}}.card{{width:440px;height:520px;background:{c["surface"]};border:5px solid {c["gold"]};border-radius:30px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:50px;position:relative}}.label{{font-size:42px;text-align:center}}.narrative{{position:absolute;top:1420px;left:100px;width:880px;font-size:36px;line-height:1.45;text-align:center;margin:0}}.caption{{position:absolute;left:80px;top:1680px;width:920px;height:160px;padding:25px;background:{c["surface"]};border-radius:20px;font-size:35px;line-height:1.4;display:flex;align-items:center;justify-content:center;text-align:center}}.opening{{flex-direction:column;gap:10px}}.opening>svg{{width:290px;height:290px}}.paths{{display:flex;gap:220px}}.paths svg{{width:200px;height:200px}}.fork{{height:140px!important}}.slash{{position:absolute;inset:30px;width:370px;height:450px}}.claim{{position:absolute;top:1220px;left:100px;width:880px;font-size:39px;text-align:center;line-height:1.4}}.summary{{flex-wrap:wrap;height:590px;gap:100px}}.summary svg:first-child{{margin:0 300px}}.hand{{transform-box:view-box;transform-origin:120px 120px}}"""
    sections = []
    for i, b in enumerate(fixture["beats"]):
        esc = html.escape
        if i == 0:
            stage = (
                '<div class="stage opening">'
                + svg("clock")
                + svg("fork").replace("<svg", '<svg class="fork"')
                + '<div class="paths">'
                + svg("book")
                + svg("friends")
                + "</div></div>"
            )
        elif i in [1, 2]:
            stage = '<div class="stage">'
            for j, k in enumerate(["book", "friends"]):
                stage += f'<article class="card option{j}">{svg(k)}<div class="label">{esc(fixture["beats"][1]["labels"][j])}</div>'
                if i == 2 and j == 1:
                    stage += '<svg class="slash" viewBox="0 0 370 450"><path d="M0 0 L370 450"/></svg>'
                stage += "</article>"
            stage += "</div>"
        else:
            stage = (
                '<div class="stage summary">'
                + svg("clock")
                + svg("friends")
                + svg("future")
                + '</div><div class="claim">'
                + esc(fixture["claims"][0])
                + "</div>"
            )
        attrs = f'data-start="{b["start"]}" data-duration="{b["end"] - b["start"]}"'
        sections.append(
            f'<section id="s{i}" class="scene clip" {attrs}><h1>{esc(b["heading"])}</h1>{stage}<p class="narrative">{esc(b["narrative"])}</p><div class="caption">{esc(b["caption"])}</div></section>'
        )
    if engine == "hyperframes":
        shutil.copy(
            EXP / "engines/hyperframes/node_modules/gsap/dist/gsap.min.js",
            target / "gsap.min.js",
        )
        # Native sub-compositions own their local scene time and visibility.
        comps = target / "compositions"
        comps.mkdir(exist_ok=True)
        mounts = []
        for i, b in enumerate(fixture["beats"]):
            duration = b["end"] - b["start"]
            scene = (
                sections[i]
                .replace('class="scene clip"', 'class="scene"')
                .replace(f'data-start="{b["start"]}"', 'data-start="0"')
            )
            scene = scene.replace('data-start="0"', "").replace(
                f'data-duration="{duration}"', ""
            )
            animation = f'const tl=gsap.timeline({{paused:true}});tl.fromTo("#s{i} .stage",{{y:35}},{{y:0,duration:0.8,ease:"power2.out"}},0);'
            if i == 0:
                animation += 'tl.to("#s0 .hand",{rotation:180,svgOrigin:"120 120",duration:4,ease:"none"},0);'
            if i == 2:
                animation += 'tl.fromTo("#s2 .slash",{opacity:0},{opacity:1,duration:1.3},0);tl.to("#s2 .option1",{opacity:0.75,duration:1.3},0);'
            if i == 3:
                animation += 'tl.fromTo("#s3 .summary svg",{scale:0.8},{scale:1,duration:1,stagger:0.5},0);'
            animation += f"tl.to({{}},{{duration:{duration}}},0);window.__timelines=window.__timelines||{{}};window.__timelines.scene{i}=tl;"
            (comps / f"s{i}.html").write_text(
                f'<template><div id="scene{i}" data-composition-id="scene{i}" data-width="1080" data-height="1920" data-duration="{duration}">{scene}</div><style>{css}</style><script>{animation}</script></template>'
            )
            mounts.append(
                f'<div id="mount{i}" data-composition-id="scene{i}" data-composition-src="compositions/s{i}.html" data-start="{b["start"]}" data-duration="{duration}" data-track-index="{i}" style="position:absolute;inset:0"></div>'
            )
        script = "window.__timelines=window.__timelines||{};const tl=gsap.timeline({paused:true});tl.to({},{duration:20});window.__timelines.main=tl;"
        body = (
            '<main data-composition-id="main" data-start="0" data-duration="20" data-width="1080" data-height="1920" data-fps="24">'
            + "".join(mounts)
            + "</main>"
        )
        head = '<script src="gsap.min.js"></script>'
    else:
        body = (
            "<main data-sequence>"
            + "".join(
                section.replace(f'data-start="{b["start"]}"', 'data-start="0"')
                for section, b in zip(sections, fixture["beats"])
            )
            + "</main>"
        )
        script = ""
        for i in range(4):
            script += f"""gm.onFrame('#s{i}',t=>{{const p=Math.min(1,t/0.8);document.querySelector('#s{i} .stage').style.transform=`translateY(${{35*(1-p)**3}}px)`;"""
            if i == 0:
                script += 'document.querySelector("#s0 .hand").style.transform=`rotate(${t*45}deg)`;'
            if i == 2:
                script += 'document.querySelector("#s2 .slash").style.opacity=Math.min(1,t/1.3);document.querySelector("#s2 .option1").style.opacity=1-Math.min(1,t/1.3)*0.25;'
            if i == 3:
                script += 'document.querySelectorAll("#s3 .summary svg").forEach((e,j)=>e.style.transform=`scale(${0.8+0.2*Math.min(1,Math.max(0,t-j*0.5))})`);'
            script += "});"
        head = ""
    (target / "index.html").write_text(
        f'<!doctype html><html lang="es" data-width="1080" data-height="1920" data-fps="24"><head><meta charset="utf-8">{head}<style>{css}</style></head><body>{body}<script>{script}</script></body></html>'
    )
    (target / "input.json").write_text(
        json.dumps(fixture, ensure_ascii=False, indent=2)
    )
