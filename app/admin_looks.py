"""Settings look: Settings (/admin) and the phone page (/parent) dressed in one of the frame looks. See docs/themes.md.

Safe by design:
- A look only gives a small set of admin design tokens (theme.json "admin": {"tokens": {...}}): colors, two fonts,
  a corner radius and a shadow. web/css/admin-look.css turns them into the whole page, so every look styles the
  same controls in the same places.
- The server works the tokens out itself (from the look's own frame colors and the chosen frame's look options,
  with the same color math as web/js/looks.js), then checks them: body text and button text 4.5:1, small labels
  and the focus ring 3:1. A look whose tokens fail is not used: the page gets Navy and the log says why.
- A look may add decorative CSS in themes/<id>/admin.css, scoped to body.admin-look-<id>. It is cleaned on the
  way in: only decorative properties are kept (borders, shadows, background pictures, fonts and letter shapes,
  token text colors), so no look can hide, move or cover a control.
- ?look=plain on /admin or /parent always gives the plain Navy style. A look that is removed or turned off, or a
  matched frame that is gone, falls back to Navy too.
"""
from __future__ import annotations

import html as _html
import logging
import re
from pathlib import Path
from typing import Optional

from . import themes

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
FRAME_CSS = ROOT / "web" / "css" / "frame.css"
PLAIN = "navy"     # the safe look: always there, written into this file, not read from themes/navy

# ---------------- the tokens ----------------

REQUIRED = ("paper", "card", "ink", "soft", "line", "accent", "accent_ink", "danger", "ok",
            "head_bg", "head_ink", "font_display", "font_body", "radius", "shadow")
# Optional tokens and how each is made when a look leaves it out (expressions, below).
DERIVED = {
    "tile": "mix(@card, @paper, 0.5)",
    "line_soft": "mix(@line, @card, 0.5)",
    "muted": "@soft",
    "label": "@soft",                       # small labels and hints (kickers, notes under names)
    "note": "@soft",                        # "Needs ..." lines on Modules
    "rule": "@accent",                      # decorative lines and rings (gold on Navy)
    "head_soft": "@head_ink",               # the kicker under the name in the header
    "head_rule": "@rule",                   # the line under the header
    "field": "@card",                       # inputs and drop-downs
    "field_ink": "@ink",
    "link": "readable(@accent, @card)",
    "track": "mix(@line, @soft, 0.3)",      # an off switch
    "warn": "readable(#7D5210, @card)",
    "warn_bg": "mix(#F6E7C8, @card, 0.2)",
    "ok_bg": "mix(@ok, @card, 0.86)",
    "danger_bg": "mix(@danger, @card, 0.86)",
    "danger_ink": "best(@danger, #FFFFFF, @ink)",
    "focus": "@accent",
    "font_script": "@font_display",
    "pill": "999px",
}
TOKENS = REQUIRED + tuple(DERIVED)
FONT_TOKENS = ("font_display", "font_body", "font_script")
SIZE_TOKENS = ("radius", "pill")
TEXT_COLOR_TOKENS = ("ink", "soft", "link", "accent", "danger", "ok", "muted")   # admin.css may set color to these

# Navy & gilt: the live look, and the plain style. Exactly the colors Settings had before looks (web/css/frame.css).
NAVY = {
    "paper": "#F6F1E7", "card": "#FFFDF8", "ink": "#1F1B16", "soft": "#5E5547", "line": "#E2D8C3",
    "accent": "#16324F", "accent_ink": "#C9A55A", "danger": "#C8102E", "ok": "#2F5E36",
    "head_bg": "#16324F", "head_ink": "#C9A55A",
    "font_display": '"Playfair Display", Georgia, "Times New Roman", serif',
    "font_body": '"Libre Franklin", "Helvetica Neue", Arial, sans-serif',
    "radius": "14px", "shadow": "none",
    "tile": "#FAF5EA", "line_soft": "#EEE6D6", "muted": "#6E6556", "label": "#8C7A4E", "note": "#7A6A2F",
    "rule": "#C9A55A", "head_soft": "#B9A06E", "head_rule": "#C9A55A", "field": "#FFFFFF", "field_ink": "#1F1B16",
    "link": "#16324F", "track": "#CFC6B4", "warn": "#7D5210", "warn_bg": "#F6E7C8", "ok_bg": "#E2EEDD",
    "danger_bg": "#F8DDDD", "danger_ink": "#FFFFFF", "focus": "#16324F",
    "font_script": '"Pinyon Script", "Snell Roundhand", cursive', "pill": "999px",
}

# The readability check: (text, background, least contrast). A background that is see-through is laid over paper.
PAIRS = [
    ("ink", "paper", 4.5), ("ink", "card", 4.5), ("ink", "tile", 4.5), ("field_ink", "field", 4.5),
    ("soft", "paper", 4.5), ("soft", "card", 4.5), ("soft", "tile", 4.5), ("muted", "card", 4.5),
    ("accent_ink", "accent", 4.5), ("head_ink", "head_bg", 4.5), ("head_soft", "head_bg", 4.5),
    ("link", "card", 4.5), ("accent", "card", 4.5), ("danger", "card", 4.5), ("danger_ink", "danger", 4.5),
    ("ok", "card", 4.5), ("ok", "ok_bg", 4.5), ("warn", "warn_bg", 4.5), ("danger", "danger_bg", 4.5),
    ("note", "card", 4.5),
    ("label", "card", 3.0), ("label", "tile", 3.0),          # small decorative labels: 3:1 (Navy's gold is 4.1)
    ("focus", "paper", 3.0), ("focus", "card", 3.0),          # the focus ring has to show
]


class LookError(ValueError):
    pass


# ---------------- colors (the same math as web/js/looks.js) ----------------

HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
RGBA = re.compile(r"^rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*(?:,\s*([\d.]+)\s*)?\)$")


def rgba(c: str) -> tuple[float, float, float, float]:
    c = str(c).strip()
    if HEX.match(c):
        n = int(c[1:], 16)
        return (n >> 16) & 255, (n >> 8) & 255, n & 255, 1.0
    m = RGBA.match(c)
    if m:
        a = float(m.group(4)) if m.group(4) is not None else 1.0
        return float(m.group(1)), float(m.group(2)), float(m.group(3)), max(0.0, min(1.0, a))
    raise LookError(f'"{c}" is not a color like #16324F or rgba(255, 255, 255, 0.8)')


def to_hex(r, g, b) -> str:
    return "#" + "".join(f"{max(0, min(255, round(v))):02X}" for v in (r, g, b))


def over(top: str, under: str) -> str:
    """A see-through color laid over a solid one."""
    r, g, b, a = rgba(top)
    R, G, B, _ = rgba(under)
    return to_hex(r * a + R * (1 - a), g * a + G * (1 - a), b * a + B * (1 - a))


def _lin(c):
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(c: str) -> float:
    r, g, b, _ = rgba(c)
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast(a: str, b: str) -> float:
    x, y = sorted((luminance(a), luminance(b)))
    return (y + 0.05) / (x + 0.05)


def to_hsl(c: str):
    r, g, b, _ = rgba(c)
    r, g, b = r / 255, g / 255, b / 255
    mx, mn = max(r, g, b), min(r, g, b)
    l, d, h, s = (mx + mn) / 2, mx - mn, 0.0, 0.0
    if d:
        s = d / (2 - mx - mn) if l > 0.5 else d / (mx + mn)
        h = ((g - b) / d + (6 if g < b else 0)) if mx == r else ((b - r) / d + 2) if mx == g else ((r - g) / d + 4)
        h *= 60
    return h, s, l


def from_hsl(h, s, l) -> str:
    h = ((h % 360) + 360) % 360
    s, l = max(0.0, min(1.0, s)), max(0.0, min(1.0, l))
    q = l * (1 + s) if l < 0.5 else l + s - l * s
    p = 2 * l - q

    def f(t):
        t = (t + 1) % 1
        return p + (q - p) * 6 * t if t < 1 / 6 else q if t < 0.5 else p + (q - p) * (2 / 3 - t) * 6 if t < 2 / 3 else p
    return to_hex(f(h / 360 + 1 / 3) * 255, f(h / 360) * 255, f(h / 360 - 1 / 3) * 255)


def mix(a: str, b: str, w: float) -> str:
    x, y = rgba(a), rgba(b)
    return to_hex(*(x[i] + (y[i] - x[i]) * w for i in range(3)))


def shift(c: str, dh=0.0, ds=0.0, dl=0.0) -> str:
    h, s, l = to_hsl(c)
    return from_hsl(h + dh, s + ds, l + dl)


def tones(c: str) -> dict:
    """FrameLooks.tones(): a scale of one color, 0 black to 100 white."""
    h, s, _ = to_hsl(c)
    out = {}
    for t in (0, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 98, 99, 100):
        out[t] = from_hsl(h, s * (0.6 if t > 90 else 0.8 if t < 10 else 1), t / 100)
    return out


def lstar(c: str, sat, tone_: float) -> str:
    """The Tonal View scheme's tone(): the seed's hue at a lightness the eye sees as tone_ (CIE L*, 0 to 100).
    sat "auto" is the scheme's primary saturation (the seed's, kept between 0.42 and 0.78)."""
    h, s, _ = to_hsl(c)
    sat = max(0.42, min(0.78, s)) if sat == "auto" else float(sat)
    y = ((tone_ + 16) / 116) ** 3 if tone_ > 8 else tone_ / 903.3
    lo, hi = 0.0, 1.0
    for _ in range(22):
        mid = (lo + hi) / 2
        if luminance(from_hsl(h, sat, mid)) < y:
            lo = mid
        else:
            hi = mid
    return from_hsl(h, sat, (lo + hi) / 2)


def readable(c: str, bg: str, ratio: float = 4.6) -> str:
    """c, darkened (on a light background) or lightened (on a dark one) until it reads on bg."""
    bg = over(bg, "#FFFFFF") if rgba(bg)[3] < 1 else bg
    step = -0.03 if luminance(bg) > 0.18 else 0.03
    n = 0
    while contrast(c, bg) < ratio and n < 34:
        c = shift(c, 0, 0, step)
        n += 1
    return c


# ---------------- token expressions ----------------
#   "#16324F", "rgba(...)", "14px", a font list    as written
#   "$accent"                                       the look's option (the chosen frame's value, else the default)
#   "@card"                                         another admin token
#   "var(--paper)"                                  the look's own frame color (theme.css body.look-<id>, else frame.css)
#   numbers: 0.8, "$frost" (an option), lerp($frost, 0.6, 0.9) (an option from 0 to 100, mapped)
#   mix(a, b, w)  tone(a, 40)  lstar(a, auto, 40)  shift(a, dh, ds, dl)  readable(a, bg)  alpha(a, 0.8)  best(bg, a, b)

FUNCS = ("mix", "tone", "lstar", "shift", "readable", "alpha", "best")
SAFE = re.compile(r"^[#(),.%\-\w\s/\"']{0,200}$")


def _split(args: str) -> list[str]:
    out, depth, buf = [], 0, ""
    for ch in args:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(buf.strip())
            buf = ""
        else:
            buf += ch
    out.append(buf.strip())
    return out


class _Ctx:
    def __init__(self, raw: dict, options: dict, frame_vars: dict):
        self.raw, self.options, self.frame_vars = raw, options, frame_vars
        self.done: dict[str, str] = {}
        self.busy: set = set()

    def token(self, name: str) -> str:
        if name in self.done:
            return self.done[name]
        if name in self.busy:
            raise LookError(f'token "{name}" refers to itself')
        if name not in TOKENS:
            raise LookError(f'"@{name}" is not an admin token')
        self.busy.add(name)
        expr = self.raw.get(name, DERIVED.get(name))
        if expr is None:
            raise LookError(f'"{name}" is missing')
        val = self.eval(str(expr))
        self.busy.discard(name)
        self.done[name] = val
        return val

    def num(self, e: str) -> float:
        """A number argument: 0.8, an option ("$frost"; on/off is 1 or 0), or lerp($frost, 0.6, 0.9) (0 to 100 mapped)."""
        e = e.strip()
        if e.startswith("$"):
            v = self.options.get(e[1:])
            if isinstance(v, bool):
                return 1.0 if v else 0.0
            if isinstance(v, (int, float)):
                return float(v)
            raise LookError(f'the look has no number option "{e[1:]}"')
        m = re.match(r"^lerp\((.*)\)$", e)
        if m:
            a = _split(m.group(1))
            x = max(0.0, min(100.0, self.num(a[0])))
            return self.num(a[1]) + (self.num(a[2]) - self.num(a[1])) * x / 100
        return float(e)

    def eval(self, e: str) -> str:
        e = e.strip()
        if e.startswith("@"):
            return self.token(e[1:])
        if e.startswith("$"):
            v = self.options.get(e[1:])
            if v is None:
                raise LookError(f'the look has no option "{e[1:]}"')
            return str(v)
        m = re.match(r"^var\(\s*(--[\w-]+)\s*\)$", e)
        if m:
            v = self.frame_vars.get(m.group(1))
            if v is None:
                raise LookError(f"the look's frame colors have no {m.group(1)}")
            return self.eval(v)
        m = re.match(r"^(\w+)\((.*)\)$", e, re.S)
        if m and m.group(1) in FUNCS:
            fn, a = m.group(1), _split(m.group(2))
            col = lambda i: self.eval(a[i])   # noqa: E731
            if fn == "mix":
                return mix(col(0), col(1), self.num(a[2]))
            if fn == "tone":
                return tones(col(0))[int(a[1])]
            if fn == "lstar":
                return lstar(col(0), a[1] if a[1] == "auto" else self.num(a[1]), self.num(a[2]))
            if fn == "shift":
                return shift(col(0), self.num(a[1]), self.num(a[2]), self.num(a[3]))
            if fn == "readable":
                return readable(col(0), col(1), self.num(a[2]) if len(a) > 2 else 4.6)
            if fn == "alpha":
                r, g, b, _ = rgba(col(0))
                return f"rgba({int(r)}, {int(g)}, {int(b)}, {round(self.num(a[1]), 3)})"
            if fn == "best":
                bg = col(0)
                return max((col(1), col(2)), key=lambda c: contrast(c, over(bg, "#FFFFFF")))
        if not SAFE.match(e) or re.search(r"url|expression|javascript|[;{}]", e, re.I):
            raise LookError(f'"{e}" is not allowed in a token')
        return e


_frame_root: dict = {}


def frame_vars(t: Optional[dict]) -> dict:
    """The CSS variables a look's frame sets on body.look-<id> (theme.css), over frame.css's :root."""
    if not _frame_root:
        root = re.search(r":root\s*\{([^}]*)\}", FRAME_CSS.read_text(encoding="utf-8"))
        _frame_root.update(re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", root.group(1) if root else ""))
    out = dict(_frame_root)
    if t:
        out.update({f"--{k}": v for k, v in t.get("fonts", {}).items()})   # theme.json "fonts" (app/themes.py theme_css)
        css = re.sub(r"/\*.*?\*/", "", t.get("css", ""), flags=re.S)
        for m in re.finditer(r"(?:^|\})\s*body\.look-" + re.escape(t["id"]) + r"\s*\{([^}]*)\}", css):
            out.update({k: v.strip() for k, v in re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", m.group(1))})
    return out


def admin_block(t: Optional[dict]) -> dict:
    """theme.json "admin" ({"tokens": {...}, "photo": true}), read straight from the look's folder."""
    if not t:
        return {}
    import json
    try:
        m = json.loads((t["folder"] / "theme.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    a = m.get("admin")
    return a if isinstance(a, dict) else {}


def resolve(t: Optional[dict], options: Optional[dict] = None) -> dict:
    """All admin tokens for a look and option values. Raises LookError when the look gives none or one is wrong."""
    if t is None:
        return dict(NAVY)
    block = admin_block(t)
    raw = block.get("tokens")
    if not isinstance(raw, dict) or not raw:
        raise LookError(f'{t["name"]} has no "admin" tokens in theme.json')
    missing = [k for k in REQUIRED if k not in raw]
    if missing:
        raise LookError(f'{t["name"]} is missing admin tokens: {", ".join(missing)}')
    unknown = [k for k in raw if k not in TOKENS]
    if unknown:
        raise LookError(f'{t["name"]} has unknown admin tokens: {", ".join(unknown)}')
    opts = themes.option_values(t, options or {})
    ctx = _Ctx(raw, opts, frame_vars(t))
    out = {k: ctx.token(k) for k in TOKENS}
    for k in TOKENS:
        if k in FONT_TOKENS or k in SIZE_TOKENS or k == "shadow":
            if not SAFE.match(out[k]) or re.search(r"url|expression|[;{}]", out[k], re.I):
                raise LookError(f'{t["name"]}: "{k}" is not allowed')
        else:
            rgba(out[k])   # every other token is a color
    for k in ("paper", "head_bg", "accent"):
        if rgba(out[k])[3] < 1:
            raise LookError(f'{t["name"]}: "{k}" has to be a solid color')
    return out


def check(tok: dict, photo_wash: Optional[str] = None) -> list[str]:
    """What fails the readability check, in words ([] when all is well)."""
    bad = []
    solid = {}
    for k, v in tok.items():
        if k in FONT_TOKENS or k in SIZE_TOKENS or k == "shadow":
            continue
        solid[k] = over(v, over(tok["paper"], "#FFFFFF")) if rgba(v)[3] < 1 else v
    # see-through cards also sit on the photo or the page behind; check them over black and white as well
    for text, bg, least in PAIRS:
        c = contrast(solid[text], solid[bg])
        if c < least:
            bad.append(f"{text} on {bg} is {c:.2f}:1, needs {least}:1")
    if photo_wash:
        for under in ("#000000", "#FFFFFF"):
            page = over(photo_wash, under)
            for text in ("ink",):   # only the side menu and the footer sit on the page itself, in ink
                c = contrast(solid[text], page)
                if c < 4.5:
                    bad.append(f"{text} on the photo behind the page is {c:.2f}:1, needs 4.5:1")
            for k in ("card", "tile"):
                if rgba(tok[k])[3] < 1:
                    c = contrast(solid["ink"], over(tok[k], page))
                    if c < 4.5:
                        bad.append(f"ink on {k} over the photo is {c:.2f}:1, needs 4.5:1")
    return bad


# ---------------- admin.css: decoration only ----------------

ALLOWED = {
    "border", "border-top", "border-bottom", "border-left", "border-right", "border-color", "border-style", "border-width",
    "border-top-color", "border-bottom-color", "border-left-color", "border-right-color", "border-radius",
    "border-top-left-radius", "border-top-right-radius", "border-bottom-left-radius", "border-bottom-right-radius",
    "box-shadow", "text-shadow", "background-image", "background-size", "background-position", "background-repeat",
    "background-attachment", "font-family", "font-style", "font-weight", "letter-spacing", "text-transform",
    "text-decoration", "text-decoration-color", "text-decoration-thickness", "text-underline-offset", "font-variant",
    "font-variant-caps", "font-variant-numeric", "font-feature-settings", "backdrop-filter", "-webkit-backdrop-filter",
    "color", "font-size",
}
PSEUDO_ONLY = {"content", "display", "width", "height", "margin", "margin-top", "margin-bottom", "margin-left", "margin-right",
               "background-color"}
HEADING = re.compile(r"(h1|h2|h3|\.script|\.kicker|summary)(::first-letter)?$")
FORBIDDEN = [   # also checked on the files by a test (tests/test_admin_looks.py)
    (re.compile(r"display\s*:\s*none", re.I), "display: none"),
    (re.compile(r"(?<![\w-])visibility\s*:", re.I), "visibility"),
    (re.compile(r"(?<![\w-])position\s*:", re.I), "position"),
    (re.compile(r"(?<![\w-])opacity\s*:", re.I), "opacity"),
    (re.compile(r"pointer-events", re.I), "pointer-events"),
    (re.compile(r"z-index", re.I), "z-index"),
    (re.compile(r"(?<![\w-])transform", re.I), "transform"),
    (re.compile(r"!important", re.I), "!important"),
    (re.compile(r"@import", re.I), "@import"),
    (re.compile(r"expression\s*\(|javascript:", re.I), "script"),
    (re.compile(r"(?<![\w-])clip", re.I), "clip"),
    (re.compile(r"\border\s*:|\bfloat\s*:|\binset\s*:", re.I), "order, float or inset"),
]


def _decl_ok(prop: str, val: str, sel: str, tid: str) -> Optional[str]:
    pseudo = "::before" in sel or "::after" in sel
    if prop in PSEUDO_ONLY:
        if not pseudo:
            return f"{prop} only on ::before or ::after"
        if prop == "display" and val not in ("block", "inline-block"):
            return "display is block or inline-block"
        if prop == "content" and not re.match(r"^(\"[^\"]{0,4}\"|'[^']{0,4}')$", val):
            return "content is a short ornament in quotes"
        return None
    if prop not in ALLOWED:
        return f"{prop} is not a decorative property"
    if prop == "color" and not re.match(r"^var\(--a-(" + "|".join(t.replace("_", "-") for t in TEXT_COLOR_TOKENS) + r")\)$", val):
        return "color is one of the text tokens, like var(--a-accent)"
    if prop == "font-size":
        last = sel.split()[-1] if sel.split() else ""
        m = re.match(r"^(\d+(\.\d+)?)px$", val)
        if not HEADING.search(last) or not m or not 12 <= float(m.group(1)) <= 44:
            return "font-size only on headings, 12px to 44px"
    if prop in ("backdrop-filter", "-webkit-backdrop-filter") and val != "none" and (
            not re.match(r"^(blur|saturate|brightness)\(", val) or set(re.findall(r"([a-z-]+)\(", val)) - {"blur", "saturate", "brightness", "calc", "var"}):
        return "backdrop-filter is none, or blur(), saturate() and brightness()"
    for u in re.findall(r"url\(\s*['\"]?([^'\")]+)", val):
        if re.match(r"^([a-z]+:|/|\.\.)", u.strip()):
            return "url() only for files in the look's own folder"
    return None


def clean_admin_css(text: str, tid: str) -> tuple[str, list[str]]:
    """A look's admin.css with everything that isn't decoration taken out, and what was taken out."""
    text = re.sub(r"/\*.*?\*/", "", text or "", flags=re.S)
    problems: list[str] = []
    for rx, what in FORBIDDEN:
        if rx.search(text):
            problems.append(f"{what} is not allowed")
    text = re.sub(r"@(import|charset|namespace)[^;{}]*;", "", text, flags=re.I)
    out = []
    scope = re.compile(rf"^body\.admin-look-{re.escape(tid)}(?![\w-])")
    pos = 0
    rule = re.compile(r"([^{}]+)\{([^{}]*)\}")
    media = re.compile(r"@media\s*([^{]+)\{((?:[^{}]*\{[^{}]*\})*)\s*\}")
    chunks = []
    for m in media.finditer(text):
        chunks.append((text[pos:m.start()], None))
        chunks.append((m.group(2), m.group(1).strip()))
        pos = m.end()
    chunks.append((text[pos:], None))
    for body, cond in chunks:
        if cond is not None and not re.match(r"^\((max|min)-width:\s*\d+px\)$", cond):
            problems.append(f"@media {cond} is not allowed (only max-width or min-width)")
            continue
        rules = []
        for m in rule.finditer(body):
            sels = [s.strip() for s in m.group(1).split(",") if s.strip()]
            if any(s.startswith("@") for s in sels):
                problems.append(f"{m.group(1).strip()} is not allowed")
                continue
            bad_sel = [s for s in sels if not scope.match(s)]
            if bad_sel:
                problems.append(f"selector not scoped to body.admin-look-{tid}: {', '.join(bad_sel)}")
                continue
            keep = []
            for d in m.group(2).split(";"):
                if ":" not in d:
                    continue
                prop, val = d.split(":", 1)
                prop, val = prop.strip().lower(), val.strip()
                why = None
                if any(rx.search(prop + ":" + val) for rx, _ in FORBIDDEN):
                    why = "forbidden"
                else:
                    for s in sels:
                        why = why or _decl_ok(prop, val, s, tid)
                if why:
                    problems.append(f"{', '.join(sels)} {{ {prop}: {val} }}: {why}")
                else:
                    keep.append(f"{prop}: {val};")
            if keep:
                rules.append(f"{', '.join(sels)} {{ {' '.join(keep)} }}")
        if rules:
            out.append(f"@media {cond} {{\n" + "\n".join(rules) + "\n}" if cond else "\n".join(rules))
    if len("\n".join(out)) > 12000:
        problems.append("admin.css is over 12 KB; only the first part is used")
    css = themes._relink("\n".join(out)[:12000], tid)
    return css, problems


def admin_css(t: dict) -> tuple[str, list[str]]:
    f = t["folder"] / "admin.css"
    if not f.is_file():
        return "", []
    try:
        return clean_admin_css(f.read_text(encoding="utf-8"), t["id"])
    except OSError as exc:
        return "", [str(exc)]


def font_faces(t: dict) -> str:
    """The @font-face rules from a look's theme.css, so Settings can use the look's own fonts."""
    css = re.sub(r"/\*.*?\*/", "", t.get("css", ""), flags=re.S)
    return themes._relink("\n".join(re.findall(r"@font-face\s*\{[^}]*\}", css)), t["id"])


# ---------------- the setting ----------------

def setting(cfg: dict) -> dict:
    """settings_look in the store: {"look": a look id or "frame", "frame": a frame id, "phone": true}."""
    raw = cfg.get("settings_look") if isinstance(cfg.get("settings_look"), dict) else {}
    return {"look": str(raw.get("look") or PLAIN), "frame": str(raw.get("frame") or ""), "phone": raw.get("phone", True) is not False}


def validate(body: dict, frame_ids: list[str]) -> dict:
    """What PUT /api/admin/settings-look may save. Raises LookError with what to fix."""
    if not isinstance(body, dict):
        raise LookError("Send the Settings look as an object.")
    look = str(body.get("look") or "")
    frame = str(body.get("frame") or "")
    if look == "frame":
        if frame not in frame_ids:
            raise LookError("Pick which frame Settings should match.")
    elif not themes.by_id(look):
        raise LookError("That look isn't available. Pick one from the list.")
    else:
        frame = ""
    return {"look": look, "frame": frame, "phone": body.get("phone", True) is not False}


def choose(cfg: dict, profiles: list[dict], page: str, query_look: str = "") -> dict:
    """Which look a page wears: {"id", "name", "options", "plain", "reason", "match"}. reason says why Navy is used."""
    s = setting(cfg)
    out = {"id": PLAIN, "name": "Navy & gilt", "options": {}, "plain": False, "reason": "", "match": ""}
    navy = themes.by_id(PLAIN)
    if navy:
        out["name"] = navy["name"]
    if query_look == "plain":
        out["plain"] = True
        return out
    if page == "parent" and not s["phone"]:
        return out
    look, opts = s["look"], {}
    if look == "frame":
        p = next((p for p in profiles if p["id"] == s["frame"]), None)
        if not p:
            out["reason"] = "the matched frame is gone"
            return out
        look, opts = p["look"], (p.get("look_options") or {}).get(p["look"], {})
        out["match"] = p["name"]
    t = themes.by_id(look)
    if not t:
        out["reason"] = f'the look "{look}" is removed or turned off'
        return out
    out.update(id=t["id"], name=t["name"], options=themes.option_values(t, opts))
    return out


_warned: set = set()


def page_style(choice: dict, photo_url: str = "") -> tuple[str, str, list[str], dict, str]:
    """(the <style> text, the body classes, problems, the tokens used, body attributes). A look that fails any check gives Navy's style."""
    t = None if choice["plain"] or choice["id"] == PLAIN else themes.by_id(choice["id"])
    problems: list[str] = []
    extra_css, faces, photo = "", "", False
    tok = dict(NAVY)
    if t:
        try:
            tok = resolve(t, choice["options"])
            block = admin_block(t)
            photo = bool(block.get("photo")) and bool(photo_url)
            wash = str(block.get("photo_wash") or "rgba(236, 241, 248, 0.7)")
            problems = check(tok, wash if photo else None)
            if photo:
                tok["photo_wash"] = wash
        except (LookError, ValueError, KeyError, IndexError) as exc:
            problems = [str(exc)]
        if not problems:
            extra_css, css_problems = admin_css(t)
            faces = font_faces(t)
            for p in css_problems:   # taken out, the rest is used
                _warn(t["id"], f"admin.css: {p}")
        else:
            _warn(t["id"], "; ".join(problems))
            tok, t, photo = dict(NAVY), None, False
    lid = t["id"] if t else PLAIN
    lines = [f"--a-{k.replace('_', '-')}: {v};" for k, v in tok.items()]
    if luminance(tok["paper"]) < 0.18:
        lines.append("color-scheme: dark;")   # a dark look: the browser draws its own bits (pickers, scroll bars) dark too
    for k, v in (choice["options"] if t else {}).items():
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            lines.append(f"--opt-{k.replace('_', '-')}: {v};")
        elif isinstance(v, str) and HEX.match(v):
            lines.append(f"--opt-{k.replace('_', '-')}: {v};")
    # the photo is set here, in the page, so its address is read from the page (a url() in a variable used by
    # web/css/admin-look.css would be read from that file's folder)
    pic = f'body.admin-look-photo::before {{ background-image: url("{_html.escape(photo_url)}"); }}' if photo else ""
    css = "\n".join(x for x in (faces, ":root { " + " ".join(lines) + " }", pic, extra_css) if x)
    classes = f"admin-look admin-look-{lid}" + (" admin-look-photo" if photo else "")
    attrs = ""   # on/off and choice options as body attributes, like the frame (data-opt-reduce-effects="1")
    for k, v in (choice["options"] if t else {}).items():
        if isinstance(v, bool):
            attrs += f' data-opt-{k.replace("_", "-")}="{1 if v else 0}"'
        elif isinstance(v, str) and not HEX.match(v):
            attrs += f' data-opt-{k.replace("_", "-")}="{_html.escape(v)}"'
    return css, classes, problems, tok, attrs


def _warn(tid: str, why: str) -> None:
    key = f"{tid}:{why}"
    if key not in _warned:
        _warned.add(key)
        log.warning("Settings look %s not used, Navy instead: %s" if "admin.css" not in why else "Settings look %s: %s", tid, why)


def dress(html: str, choice: dict, page: str, photo_url: str = "", here: str = "") -> str:
    """Put the chosen look's tokens and decoration into /admin or /parent."""
    css, classes, problems, tok, attrs = page_style(choice, photo_url)
    used = "plain" if choice["plain"] else (choice["id"] if not problems else PLAIN)
    html = html.replace("</head>", f'<style id="admin-look">\n{css}\n</style>\n</head>', 1)
    html = html.replace("<body>", f'<body class="{classes}" data-admin-look="{used}"{attrs}>', 1)
    html = re.sub(r'<meta name="theme-color" content="[^"]*">', f'<meta name="theme-color" content="{tok["head_bg"]}">', html, count=1)
    here = _html.escape(here or ("admin" if page == "admin" else "parent"))
    name = _html.escape(choice["name"] + (f' (matching {choice["match"]})' if choice.get("match") else ""))
    if choice["plain"]:
        foot = f'Plain style. <a href="{here}">Use the Settings look</a>'
    elif problems:
        foot = f"Settings look: {name} couldn't be used safely here, so this page uses the plain style."
    elif used == PLAIN:
        foot = f"Settings look: {name}."
    else:
        foot = f'Settings look: {name}. <a href="{here}?look=plain">Use plain</a>'
    return html.replace("<!--admin-look-foot-->", f'<footer class="alook-foot">{foot}</footer>', 1)


def presets(t: dict) -> list[dict]:
    """Option values to check a look with: the defaults, every range preset, every color swatch, both on/off and
    every choice, one option at a time."""
    base = themes.option_values(t, {})
    out = [dict(base)]
    for o in t["options"]:
        vals = []
        if o["type"] == "range":
            vals = [v for _, v in o.get("presets", [])] + [o["min"], o["max"]]
        elif o["type"] == "color":
            vals = list(o.get("swatches", []))
        elif o["type"] == "bool":
            vals = [True, False]
        else:
            vals = [c[0] for c in o["choices"]]
        for v in vals:
            out.append({**base, o["name"]: v})
    return out


def list_public() -> list[dict]:
    """Every enabled look for the picker, with whether its Settings look passes the check with its defaults."""
    out = []
    for t in themes.enabled():
        ok = True
        if t["id"] != PLAIN:
            try:
                ok = not check(resolve(t, {}))
            except (LookError, ValueError):
                ok = False
        out.append({"key": t["id"], "name": t["name"], "swatches": t["swatches"], "ready": ok})
    return out
