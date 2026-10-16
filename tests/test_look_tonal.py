"""Tonal View (themes/tonal): the look's files are valid, its script stays Chrome 106 safe, and the scheme its
theme.js builds from the seed keeps text readable (4.5:1) for any seed color.

The scheme math is mirrored here from theme.js (and FrameLooks' HSL helpers in web/js/looks.js), so a change to
one should be made in the other. theme.css carries the default seed's values for the moment before theme.js runs;
the last test checks those match."""
import json
import re
from pathlib import Path

import pytest

from app import artcolor, themes

ROOT = Path(__file__).resolve().parent.parent
LOOK = ROOT / "themes" / "tonal"


# ---------------- a mirror of theme.js scheme() ----------------

def _to_hsl(hexv):
    n = int(hexv[1:], 16)
    r, g, b = ((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255
    mx, mn = max(r, g, b), min(r, g, b)
    l, h, s, d = (mx + mn) / 2, 0.0, 0.0, mx - mn
    if d:
        s = d / (2 - mx - mn) if l > 0.5 else d / (mx + mn)
        if mx == r:
            h = (g - b) / d + (6 if g < b else 0)
        elif mx == g:
            h = (b - r) / d + 2
        else:
            h = (r - g) / d + 4
        h *= 60
    return h, s, l


def _from_hsl(h, s, l):
    h = ((h % 360) + 360) % 360
    s, l = max(0, min(1, s)), max(0, min(1, l))
    q = l * (1 + s) if l < 0.5 else l + s - l * s
    p = 2 * l - q

    def f(t):
        t = (t + 1) % 1
        if t < 1 / 6:
            return p + (q - p) * 6 * t
        if t < 0.5:
            return q
        if t < 2 / 3:
            return p + (q - p) * (2 / 3 - t) * 6
        return p

    def hx(v):
        v = max(0, min(255, int(v + 0.5) if v >= 0 else round(v)))   # Math.round
        return f"{v:02X}"
    return "#" + hx(f(h / 360 + 1 / 3) * 255) + hx(f(h / 360) * 255) + hx(f(h / 360 - 1 / 3) * 255)


def _lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _lum(hexv):
    n = int(hexv[1:], 16)
    return 0.2126 * _lin(((n >> 16) & 255) / 255) + 0.7152 * _lin(((n >> 8) & 255) / 255) + 0.0722 * _lin((n & 255) / 255)


def scheme(seed):
    h, s, _ = _to_hsl(seed if re.match(r"^#[0-9A-Fa-f]{6}$", seed or "") else "#2F7A68")

    def tone(H, S, tn):
        y = ((tn + 16) / 116) ** 3 if tn > 8 else tn / 903.3
        lo, hi = 0.0, 1.0
        for _ in range(22):
            mid = (lo + hi) / 2
            if _lum(_from_hsl(H, S, mid)) < y:
                lo = mid
            else:
                hi = mid
        return _from_hsl(H, S, (lo + hi) / 2)

    def harm(H):
        dd = ((h - H + 540) % 360) - 180
        return (H + dd * 0.1 + 360) % 360

    ps, th = max(0.42, min(0.78, s)), h + 60
    return {
        "pri": tone(h, ps, 40), "priC": tone(h, ps * 0.9, 90), "onPriC": tone(h, ps, 10), "pri80": tone(h, ps * 0.8, 80),
        "pri30": tone(h, ps, 30), "secC": tone(h, 0.34, 88), "onSecC": tone(h, 0.3, 12),
        "ter": tone(th, ps * 0.7, 40), "terC": tone(th, ps * 0.8, 90), "onTerC": tone(th, ps, 12),
        "surf": tone(h, 0.3, 98), "sLow": tone(h, 0.28, 96), "sCont": tone(h, 0.26, 94), "sHigh": tone(h, 0.24, 92),
        "sHighest": tone(h, 0.22, 89), "on": tone(h, 0.15, 10), "onV": tone(h, 0.14, 30), "muted": tone(h, 0.12, 40),
        "outl": tone(h, 0.1, 50), "outlV": tone(h, 0.16, 80),
        "err": tone(4, 0.72, 40), "errC": tone(4, 0.75, 90), "onErrC": tone(4, 0.7, 14),
        "ok": tone(harm(140), 0.45, 34), "okC": tone(harm(140), 0.5, 90), "onOkC": tone(harm(140), 0.5, 14),
        "warnC": tone(40, 0.9, 87), "onWarnC": tone(32, 0.8, 22), "warn": tone(40, 0.9, 70),
        "inv": tone(h, 0.12, 20), "onInv": tone(h, 0.15, 95), "invC": tone(h, 0.14, 28), "onInvV": tone(h, ps * 0.6, 80),
        "nBg": tone(h, 0.3, 3), "nCard": tone(h, 0.28, 8), "nRing": tone(h, ps * 0.6, 22), "nPri": tone(h, ps * 0.6, 62),
        "nOn": tone(h, 0.15, 56), "nOnV": tone(h, 0.12, 42),
    }


def contrast(a, b):
    la, lb = _lum(a), _lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


# text color, background, what it is
PAIRS = [
    ("on", "surf", "body text"), ("on", "sLow", "text on a card"), ("on", "sHighest", "text on a chip"),
    ("onV", "surf", "soft text"), ("onV", "sLow", "soft text on a card"), ("onV", "sCont", "soft text on the nav bar"),
    ("muted", "sLow", "past events"), ("pri", "surf", "accent text"), ("pri", "sLow", "accent text on a card"),
    ("onPriC", "priC", "the clock pill"), ("onSecC", "secC", "an active tab"), ("onTerC", "terC", "the countdown"),
    ("onWarnC", "warnC", "waiting for a parent"), ("ok", "okC", "done chips"), ("onOkC", "okC", "done text"),
    ("ok", "sLow", "minutes earned"), ("err", "sLow", "a warning line"), ("onErrC", "errC", "an error"),
    ("onInv", "inv", "the dark picture panel"), ("onInvV", "inv", "soft text on the dark panel"),
    ("nPri", "nCard", "night clock"), ("nOn", "nBg", "night date"),
]
SEEDS = ["#2F7A68", "#4A63B8", "#B0533A", "#8A4FA8", "#FF0000", "#0000FF", "#C8102E", "#16324F", "#FFD400", "#00FFFF",
         "#777777", "#000000", "#FFFFFF", "nonsense"]


@pytest.mark.parametrize("seed", SEEDS)
def test_text_stays_readable_for_any_seed(seed):
    t = scheme(seed)
    for fg, bg, what in PAIRS:
        need = 4.5 if not fg.startswith("n") or fg in ("nPri",) else 3.0   # the night date is dimmed on purpose
        assert contrast(t[fg], t[bg]) >= need, f"{seed}: {what} ({fg} on {bg}) is {contrast(t[fg], t[bg]):.2f}:1"
    assert contrast("#FFFFFF", t["pri"]) >= 4.5, f"{seed}: white on a filled button"
    assert contrast("#FFFFFF", t["err"]) >= 4.5, f"{seed}: the Lists badge"


def test_surfaces_step_down_in_order():
    for seed in SEEDS:
        t = scheme(seed)
        steps = [_lum(t[k]) for k in ("surf", "sLow", "sCont", "sHigh", "sHighest")]
        assert steps == sorted(steps, reverse=True), seed


# ---------------- the look's files ----------------

def test_look_is_valid_scoped_and_maps_every_family():
    m = json.loads((LOOK / "theme.json").read_text())
    themes._check(m, LOOK)
    assert m["id"] == "tonal" and m["options"]["seed"]["default"] == "#2F7A68"
    assert themes.unscoped_selectors((LOOK / "theme.css").read_text(), "tonal") == []
    assert set(m["art"]["palette"]) == set(artcolor.FAMILIES)


def test_css_and_js_stay_chrome_106_safe():
    css = re.sub(r"/\*.*?\*/", "", (LOOK / "theme.css").read_text(), flags=re.S)
    for bad in ("color-mix(", ":has(", "@container", "&", "oklch(", "@layer"):
        assert bad not in css, bad
    assert not re.search(r"#[0-9A-Fa-f]{8}\b", css), "8-digit hex colors"
    js = (LOOK / "theme.js").read_text()
    for bad in ("=>", "`", "let ", "const ", "?.", "??", "class "):
        assert bad not in js, bad


def test_fonts_are_small_and_licensed():
    fonts = list((LOOK / "fonts").glob("*.woff2"))
    assert fonts and sum(f.stat().st_size for f in fonts) < 60_000
    assert "Open Font License" in (LOOK / "fonts" / "OFL.txt").read_text()


def test_css_defaults_match_the_default_seed():
    """theme.css sets the default seed's tones so the look is right before theme.js runs."""
    css = (LOOK / "theme.css").read_text()
    t = scheme("#2F7A68")
    for key, var in [("pri", "--tv-pri"), ("priC", "--tv-pri-c"), ("surf", "--tv-surf"), ("on", "--tv-on"), ("nCard", "--tv-n-card")]:
        assert re.search(re.escape(var) + r":\s*" + t[key] + ";", css), f"{var} should be {t[key]}"


def test_no_brand_or_os_names_in_visible_text():
    text = (LOOK / "theme.json").read_text() + (LOOK / "theme.css").read_text()
    for word in ("Android", "Material", "Google", "Apple", "iOS", "Pixel"):
        assert word not in text, word
