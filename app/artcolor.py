"""Color families for "Pictures: Match the look" (app/themes.py, docs/themes.md).

Every color in the drawings belongs to one family: background, ink blue, deep shadow, gold, cream, red, orange,
brown, green, blue or pink. A look gives one color per family (theme.json "art" > "palette"). Each drawn color
then moves to its look's family color but keeps its place in the family (lighter stays lighter, darker stays
darker), worked out in OKLCH so shades look even. A family left out of a look keeps its colors as drawn.
"""
from __future__ import annotations

import math
import re

# family: (the color the family is measured from, its name in docs and Settings)
FAMILIES = {
    "night": ("#16324F", "Background (the dark sky or wall behind a picture)"),
    "navy": ("#2E4A7A", "Ink blue (dark blue things drawn on top)"),
    "deep": ("#0F1F38", "Deep shadow"),
    "gold": ("#C9A55A", "Gold"),
    "paper": ("#F3EBDA", "Cream and light"),
    "red": ("#C8102E", "Red"),
    "warm": ("#D9822B", "Orange"),
    "brown": ("#6B4E2E", "Brown and wood"),
    "green": ("#4E8A4A", "Green"),
    "sky": ("#5E86B0", "Blue"),
    "pink": ("#E8A3B5", "Pink"),
}
# Dark blues that are things in a picture (a book, a coat), not the sky behind it.
INK = {"#2E4A7A", "#10263D"}
HEX6 = re.compile(r"^#[0-9A-F]{6}$")
_BG_RECT = re.compile(r'<rect width="100%" height="100%" fill="(#[0-9A-Fa-f]{6})"')


def norm(h: str) -> str:
    h = h.strip().upper().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return "#" + h


def _rgb(h):
    h = norm(h)[1:]
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _gam(c):
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def oklch(h: str) -> tuple[float, float, float]:
    r, g, b = (_lin(c) for c in _rgb(h))
    l_ = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m_ = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s_ = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    b2 = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    return L, math.hypot(a, b2), math.degrees(math.atan2(b2, a)) % 360


def from_oklch(L: float, C: float, H: float) -> str:
    L, C = max(0.0, min(1.0, L)), max(0.0, C)
    for _ in range(40):   # pull the chroma in until the color fits in sRGB
        a, b = C * math.cos(math.radians(H)), C * math.sin(math.radians(H))
        l_, m_, s_ = L + 0.3963377774 * a + 0.2158037573 * b, L - 0.1055613458 * a - 0.0638541728 * b, L - 0.0894841775 * a - 1.2914855480 * b
        l_, m_, s_ = l_ ** 3, m_ ** 3, s_ ** 3
        rgb = (4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_, -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
               -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_)
        if all(-1e-4 <= x <= 1 + 1e-4 for x in rgb):
            break
        C *= 0.92
    return "#" + "".join("%02X" % max(0, min(255, round(_gam(max(0.0, min(1.0, x))) * 255))) for x in rgb)


def family(h: str) -> str:
    """The family a color belongs to, from its lightness, chroma and hue. Dark blues are ink blue here;
    background() decides which of them are backgrounds."""
    L, C, H = oklch(h)
    if C < 0.02:
        return "paper" if L > 0.8 else ("deep" if L < 0.4 else "brown")
    if L > 0.88 and C < 0.09:
        return "pink" if (H < 20 or H > 330) else "paper"
    if 180 <= H <= 280:
        if L < 0.42:
            return "navy" if L > 0.25 else "deep"
        return "sky"
    if 110 <= H < 180:
        return "green"
    if H >= 330 or H < 35:
        return "pink" if L > 0.75 else "red"
    if 35 <= H < 75:
        if L < 0.5:
            return "deep" if L < 0.3 else "brown"
        return "warm" if L < 0.72 and C > 0.1 else ("brown" if C < 0.1 and L < 0.7 else "gold")
    if 75 <= H < 110:
        if L < 0.5:
            return "brown" if L > 0.3 else "deep"
        return "gold" if L < 0.93 else "paper"
    return "brown"


def colors_in(svg: str) -> tuple[set, set]:
    """(every fill/stroke/stop-color hex in a drawing, the ones painted as its full background)."""
    found = {norm(m) for m in re.findall(r'(?:fill|stroke|stop-color)="(#[0-9A-Fa-f]{6}|#[0-9A-Fa-f]{3})"', svg)}
    found |= {norm(m) for m in re.findall(r"""['"](#[0-9A-Fa-f]{6})['"]""", svg)}   # colors in the screen time drawing code
    return found, {norm(m) for m in _BG_RECT.findall(svg)}


def families(colors: set, backgrounds: set, override: dict | None = None) -> dict:
    """{hex: family}. A dark color painted as a full background (in any drawing) is the background family."""
    out = {}
    for h in colors:
        f = family(h)
        if h in backgrounds and oklch(h)[0] < 0.45 and h not in INK:
            f = "night"
        out[h] = f
    for h, f in (override or {}).items():
        h = norm(h)
        if HEX6.match(h) and f in FAMILIES:
            out[h] = f
    return out


def remap(h: str, fam: str, target: str) -> str:
    """A drawn color moved to its look's family color, keeping its shade within the family."""
    anchor = FAMILIES[fam][0]
    if norm(h) == anchor:
        return norm(target)
    L, C, _H = oklch(h)
    La, Ca, _ = oklch(anchor)
    Lt, Ct, Ht = oklch(target)
    nL = Lt + (L - La) * 0.7
    nC = Ct * max(0.55, min(1.4, (C / Ca) if Ca > 0.01 else 1.0))
    if fam == "paper" and L > 0.99:
        nL = max(nL, min(1.0, Lt + 0.03))
    return from_oklch(nL, nC, Ht)
