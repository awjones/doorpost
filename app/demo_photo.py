"""Demo mode's sample photo: a drawn landscape (hills, a lake, pine trees; no people), made once when the demo
starts with an empty photos folder, so the Photos screen and a look's photo background have something to show."""
from __future__ import annotations

import math
import random
from pathlib import Path

NAME = "sample-landscape.jpg"
IMAGE_EXT = (".jpg", ".jpeg", ".png", ".heic", ".webp")


def _mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def draw(w: int = 2400, h: int = 1500):
    from PIL import Image, ImageDraw, ImageFilter
    rnd = random.Random(7)
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    top, low = (86, 132, 186), (246, 200, 150)   # an early evening sky
    horizon = int(h * 0.62)
    for y in range(horizon):
        d.line([(0, y), (w, y)], fill=_mix(top, low, (y / horizon) ** 1.4))
    sun = (int(w * 0.68), int(h * 0.44))
    glow = Image.new("L", (w, h), 0)
    ImageDraw.Draw(glow).ellipse([sun[0] - 260, sun[1] - 260, sun[0] + 260, sun[1] + 260], fill=120)
    img.paste((255, 226, 170), (0, 0), glow.filter(ImageFilter.GaussianBlur(120)))
    d.ellipse([sun[0] - 70, sun[1] - 70, sun[0] + 70, sun[1] + 70], fill=(255, 238, 200))

    def ridge(base, amp, color, seed, step=8):
        r = random.Random(seed)
        ph = [r.uniform(0, 6.28) for _ in range(3)]
        pts = [(0, h)]
        for x in range(0, w + step, step):
            y = base - amp * (0.55 * math.sin(x / w * 3.1 + ph[0]) + 0.3 * math.sin(x / w * 7.3 + ph[1]) + 0.15 * math.sin(x / w * 17 + ph[2]))
            pts.append((x, y))
        pts.append((w, h))
        d.polygon(pts, fill=color)

    ridge(h * 0.52, 120, (132, 140, 172), 1)
    ridge(h * 0.58, 90, (98, 116, 140), 2)
    ridge(h * 0.63, 60, (64, 96, 92), 3)
    lake_top = int(h * 0.66)   # the lake, with the sky in it
    for y in range(lake_top, h):
        t = (y - lake_top) / (h - lake_top)
        d.line([(0, y), (w, y)], fill=_mix((214, 184, 160), (46, 74, 92), t ** 0.7))
    for _ in range(140):   # ripples
        x, y = rnd.randint(0, w), rnd.randint(lake_top + 10, h)
        ln = rnd.randint(30, 160)
        d.line([(x, y), (x + ln, y)], fill=(236, 214, 186) if y < lake_top + 160 else (90, 118, 132), width=2)
    ridge(h * 0.86, 26, (44, 70, 52), 4)   # the near shore, then pines on it
    for i in range(46):
        x = rnd.randint(-40, w + 40)
        if w * 0.3 < x < w * 0.62:
            continue
        base = h * 0.88 + rnd.randint(-10, 40)
        th = rnd.randint(160, 360)
        tw = th * 0.32
        col = _mix((30, 58, 42), (52, 84, 58), rnd.random())
        for k in range(4):
            yk = base - th * (0.25 + k * 0.22)
            d.polygon([(x, yk - th * 0.3), (x - tw * (1 - k * 0.18), yk + th * 0.12), (x + tw * (1 - k * 0.18), yk + th * 0.12)], fill=col)
        d.rectangle([x - 6, base - th * 0.2, x + 6, base], fill=(70, 50, 36))
    ridge(h * 0.94, 24, (38, 56, 40), 5)
    return img.filter(ImageFilter.SMOOTH)


def ensure(folder: Path) -> bool:
    """Make the sample photo if the demo's photos folder has no pictures. True when one was made."""
    folder = Path(folder)
    if folder.is_dir() and any(p.suffix.lower() in IMAGE_EXT for p in folder.rglob("*") if p.is_file()):
        return False
    try:
        folder.mkdir(parents=True, exist_ok=True)
        draw().save(folder / NAME, "JPEG", quality=86)
    except Exception:  # noqa: BLE001  (a missing sample photo never stops the demo)
        return False
    return True
