"""Looks (themes): how a frame is dressed, as folders anyone can add. See docs/themes.md.

A look is a folder:
    themes/<id>/theme.json   name, blurb, swatches, fonts, kind (wide, tall or both), what a new frame with
                             this look starts on, and its art palette (how "Match the look" recolors pictures)
    themes/<id>/theme.css    its styles, every rule scoped to body.look-<id>
    themes/<id>/fonts/...    optional font files (or any other file theme.css points at with url(...))

Looks are read from themes/ (they come with Doorpost) and local/themes/ (your own, in a private copy of the
code; a look there with the same id wins). They are found once, when the server starts. The frame gets every
enabled look's CSS in one file, /themes.css, made here.

Picture styles ("Pictures: Original / Match the look", per frame). The drawings never change on the server, so
/art.js stays the same size. On a frame set to Match the look, the frame (web/js/app.js artMatch) writes each
fixed color in a picture's fill, stroke and stop-color as style="fill:var(--art-C9A55A,#C9A55A)", so with no
value set the color is exactly as drawn. /themes.css sets those values for each look: every color found in the
turned-on packs and in the screen time drawing code is put in a family (app/artcolor.py) and moved to the
look's color for that family (theme.json "art" > "palette"), keeping its shade. A look can also add a filter
(dim, brighten) and a frame (border, corners) around pictures. A pack can name the family of its own colors
in pack.json ("palette", docs/art-packs.md).

Look options (theme.json "options"): a few settings a look offers, like how frosted its glass is or its main color.
Each frame saves its own values (look_options: {look id: {name: value}} in its profile, cleaned by option_values()),
and the frame gets them in /api/frame and sets them as CSS variables (--opt-<name>) and body attributes
(data-opt-<name>) so theme.css can use them. A look can also ship themes/<id>/theme.js (all of them are served
together as /themes.js) to work out more variables from the options and to add decorative touches after each screen
is drawn (web/js/looks.js, FrameLooks.register). "background": "photo" puts the slideshow photo behind every screen;
"kids": true marks a look made for kids' frames (Settings lists it first there).
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import threading
from pathlib import Path

from . import artcolor
from typing import Optional

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
BUILTIN_DIR = ROOT / "themes"
LOCAL_DIR = ROOT / "local" / "themes"
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,29}$")
HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
KINDS = ("wide", "tall", "both")
PICTURES = ("original", "match")       # the per-frame setting: "Pictures: Original / Match the look"
FILE_EXT = {".woff2": "font/woff2", ".woff": "font/woff", ".png": "image/png", ".svg": "image/svg+xml", ".jpg": "image/jpeg", ".webp": "image/webp"}

# Where pictures are on the page: the special-day panels, month cells, the countdown ribbons, the kids'
# takeover, the day pop-up and the screen time pictures. A look's filter goes on the drawing, its "frame"
# (border, corners, shadow) on the panel around it.
SVG_PLACES = (".day.sp > svg", ".mcell.sp > svg", ".rb-art > svg", ".krib-art > svg", ".ktake > svg", ".pv-art", ".ks-art",
              ".sp-side > svg", ".pic svg")   # the drawing itself, for a look's filter
FRAME_PLACES = (".day.sp", ".mcell.sp", ".ribbon", ".krib", ".ktake", ".pv", ".kscreen")
FRAME_PROPS = ("border", "border-radius", "box-shadow", "outline", "outline-offset")
SAFE_VALUE = re.compile(r"^[#(),.%\-\w\s/\"']{0,160}$")
FILTER_RE = re.compile(r"^((brightness|contrast|saturate|grayscale|sepia|hue-rotate|opacity)\(\s*-?[\d.]+(%|deg)?\s*\)\s*){0,6}$")
FONT_KEYS = ("serif", "sans", "script")
OPTION_TYPES = ("range", "color", "bool", "choice")
OPTION_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,23}$")
CHOICE_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,29}$")
BACKGROUNDS = ("", "photo")
# theme.json "words": a look's own wording for a few places on the frame. Each key's text as the frame shows it
# without a look's words is in web/js/app.js (WORDS). {name} and {n} are filled in where the key says so.
WORD_KEYS = ("today_title", "tomorrow", "next_prefix", "things_count", "night_title", "night_sub", "pin_title", "pin_sub",
             "kids_grownups", "chores_title", "kids_hi", "tod_morning", "tod_afternoon", "tod_evening")
DATE_STYLES = ("short", "long")
FITS = ("meet", "slice")


class ThemeError(ValueError):
    """Something wrong with a look, in words a person can act on."""


def _check(m: dict, folder: Path) -> dict:
    if not isinstance(m, dict):
        raise ThemeError("theme.json should be a JSON object.")
    tid = str(m.get("id", ""))
    if not ID_RE.match(tid):
        raise ThemeError('theme.json needs an "id": lowercase letters, numbers and dashes.')
    if tid != folder.name:
        raise ThemeError(f'The id "{tid}" should match the folder name "{folder.name}".')
    if not str(m.get("name", "")).strip():
        raise ThemeError('theme.json needs a "name".')
    if m.get("kind", "both") not in KINDS:
        raise ThemeError('"kind" is wide, tall or both.')
    sw = m.get("swatches", [])
    if not isinstance(sw, list) or not all(isinstance(c, str) and HEX_RE.match(c) for c in sw):
        raise ThemeError('"swatches" is a list of colors like "#16324F".')
    fonts = m.get("fonts", {})
    if not isinstance(fonts, dict) or any(k not in FONT_KEYS or not SAFE_VALUE.match(str(v)) for k, v in fonts.items()):
        raise ThemeError('"fonts" can set serif, sans and script, each a CSS font list.')
    art = m.get("art", {})
    if not isinstance(art, dict):
        raise ThemeError('"art" should be an object.')
    pal = art.get("palette", {})
    if not isinstance(pal, dict) or any(k not in artcolor.FAMILIES or not (isinstance(v, str) and HEX_RE.match(v)) for k, v in pal.items()):
        raise ThemeError(f'"art.palette" maps color families ({", ".join(artcolor.FAMILIES)}) to colors like "#16324F".')
    if not FILTER_RE.match(str(art.get("filter", ""))):
        raise ThemeError('"art.filter" is a CSS filter made of brightness(), contrast(), saturate() and the like.')
    fr = art.get("frame", {})
    if not isinstance(fr, dict) or any(k not in FRAME_PROPS or not SAFE_VALUE.match(str(v)) for k, v in fr.items()):
        raise ThemeError(f'"art.frame" can set {", ".join(FRAME_PROPS)}.')
    nf = m.get("new_frame", {})
    if not isinstance(nf, dict):
        raise ThemeError('"new_frame" should be an object.')
    if str(m.get("background", "") or "") not in BACKGROUNDS:
        raise ThemeError('"background" is "photo" or left out.')
    words = m.get("words", {})
    if not isinstance(words, dict) or any(k not in WORD_KEYS or not isinstance(v, str) or len(v) > 60 for k, v in words.items()):
        raise ThemeError(f'"words" maps any of {", ".join(WORD_KEYS)} to a short text (60 letters at most).')
    if m.get("monogram", "image") not in ("image", "initial"):
        raise ThemeError('"monogram" is "image" (the drawn monogram) or "initial" (the family\'s letter, typeset).')
    if m.get("date_style", "short") not in DATE_STYLES:
        raise ThemeError('"date_style" is "short" (Thursday · October 15) or "long" (Thursday, the Fifteenth of October).')
    fit = m.get("picture_fit", {})
    if not isinstance(fit, dict) or any(k not in ("wide", "tall") or v not in FITS for k, v in fit.items()):
        raise ThemeError('"picture_fit" sets "wide" and "tall" to "meet" (the whole picture) or "slice" (fill the panel).')
    check_options(m.get("options", {}))
    return m


def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def check_options(opts) -> dict:
    """theme.json "options", checked. Raises ThemeError with what to fix."""
    if not isinstance(opts, dict):
        raise ThemeError('"options" should be an object: {"name": {"label": ..., "type": ...}}.')
    if len(opts) > 12:
        raise ThemeError('A look can offer up to 12 options.')
    for name, o in opts.items():
        where = f'Option "{name}"'
        if not OPTION_NAME_RE.match(str(name)):
            raise ThemeError(f'{where}: names are lowercase letters, numbers and underscores.')
        if not isinstance(o, dict) or o.get("type") not in OPTION_TYPES:
            raise ThemeError(f'{where}: "type" is {", ".join(OPTION_TYPES)}.')
        t, d = o["type"], o.get("default")
        if o.get("preview", "") not in ("", "readouts"):
            raise ThemeError(f'{where}: "preview" is "readouts" or left out.')
        ro = o.get("readouts", {})
        if not isinstance(ro, dict) or len(ro) > 6 or any(not str(v).startswith("--") for v in ro.values()):
            raise ThemeError(f'{where}: "readouts" maps a label to a CSS variable its theme.js derive returns, like {{"Blur": "--gl-blur"}}.')
        if t == "range":
            lo, hi = o.get("min", 0), o.get("max", 100)
            if not (_num(lo) and _num(hi) and lo < hi):
                raise ThemeError(f'{where}: "min" and "max" are numbers, min below max.')
            if d is not None and not (_num(d) and lo <= d <= hi):
                raise ThemeError(f'{where}: "default" is a number from min to max.')
            if "step" in o and not (_num(o["step"]) and o["step"] > 0):
                raise ThemeError(f'{where}: "step" is a number above 0.')
            pr = o.get("presets", {})
            if not isinstance(pr, dict) or any(not _num(v) or not lo <= v <= hi for v in pr.values()):
                raise ThemeError(f'{where}: "presets" maps a name to a number from min to max.')
        elif t == "color":
            if d is not None and not (isinstance(d, str) and HEX_RE.match(d)):
                raise ThemeError(f'{where}: "default" is a color like "#2F7A68".')
            sw = o.get("swatches", [])
            if not isinstance(sw, list) or not all(isinstance(c, str) and HEX_RE.match(c) for c in sw):
                raise ThemeError(f'{where}: "swatches" is a list of colors like "#2F7A68".')
        elif t == "bool":
            if d is not None and not isinstance(d, bool):
                raise ThemeError(f'{where}: "default" is true or false.')
        else:
            ch = o.get("choices")
            if not isinstance(ch, list) or not ch or not all(isinstance(c, list) and len(c) == 2 and CHOICE_RE.match(str(c[0])) for c in ch):
                raise ThemeError(f'{where}: "choices" is a list of ["value", "Label"] pairs; values are lowercase words.')
            if d is not None and d not in [c[0] for c in ch]:
                raise ThemeError(f'{where}: "default" is one of the choices.')
    return opts


def _option(name: str, o: dict) -> dict:
    """One option, tidied for Settings and the frame (every field present)."""
    t = o["type"]
    out = {"name": name, "type": t, "label": str(o.get("label") or name.replace("_", " ").capitalize())[:40],
           "help": str(o.get("help", ""))[:300], "preview": str(o.get("preview", "")),
           "readouts": [[str(k)[:30], str(v)] for k, v in (o.get("readouts") or {}).items() if str(v).startswith("--")][:6]}
    if t == "range":
        lo, hi = o.get("min", 0), o.get("max", 100)
        out.update(min=lo, max=hi, step=o.get("step", 1), default=o.get("default", lo),
                   presets=[[str(k)[:20], v] for k, v in (o.get("presets") or {}).items()])
    elif t == "color":
        out.update(default=o.get("default") or "#16324F", swatches=list(o.get("swatches") or []))
    elif t == "bool":
        out.update(default=bool(o.get("default", False)))
    else:
        out.update(choices=[[str(c[0]), str(c[1])[:40]] for c in o["choices"]], default=o.get("default") or o["choices"][0][0])
    return out


def option_values(t: Optional[dict], raw) -> dict:
    """A frame's saved values for a look's options: every option present, bad or unknown values back to the default."""
    raw = raw if isinstance(raw, dict) else {}
    out = {}
    for o in (t or {}).get("options", []):
        v, n = raw.get(o["name"], o["default"]), o["name"]
        if o["type"] == "range":
            ok = _num(v) and o["min"] <= v <= o["max"]
        elif o["type"] == "color":
            ok = isinstance(v, str) and bool(HEX_RE.match(v))
            v = v.upper() if ok else v
        elif o["type"] == "bool":
            ok = isinstance(v, bool)
        else:
            ok = v in [c[0] for c in o["choices"]]
        out[n] = v if ok else o["default"]
    return out


def clean_look_options(raw) -> dict:
    """look_options in a frame profile: {look id: values} for the enabled looks that offer options."""
    raw = raw if isinstance(raw, dict) else {}
    out = {}
    for tid, vals in raw.items():
        t = by_id(str(tid))
        if t and t["options"]:
            out[t["id"]] = option_values(t, vals)
    return out


def _read(folder: Path, where: str) -> Optional[dict]:
    try:
        m = _check(json.loads((folder / "theme.json").read_text(encoding="utf-8")), folder)
        css = (folder / "theme.css").read_text(encoding="utf-8") if (folder / "theme.css").is_file() else ""
        js = (folder / "theme.js").read_text(encoding="utf-8") if (folder / "theme.js").is_file() else ""
    except (ThemeError, ValueError, OSError) as exc:
        log.warning("skipping look %s: %s", folder, exc)
        return None
    art = m.get("art", {})
    nf = m.get("new_frame", {})
    return {"id": m["id"], "name": str(m["name"]).strip()[:40], "blurb": str(m.get("blurb", ""))[:80],
            "order": int(m.get("order", 500)), "default": bool(m.get("default")), "enabled": m.get("enabled", True) is not False,
            "kind": m.get("kind", "both"), "swatches": list(m.get("swatches", [])), "fonts": dict(m.get("fonts", {})),
            "palette": dict(art.get("palette", {})), "filter": str(art.get("filter", "")).strip(), "frame": dict(art.get("frame", {})),
            "home": str(nf.get("home") or "today"), "screens": [str(x) for x in (nf.get("screens") or [])],
            "options": [_option(k, v) for k, v in (m.get("options") or {}).items()],
            "background": str(m.get("background") or ""), "kids": bool(m.get("kids")),
            "words": dict(m.get("words") or {}), "date_style": m.get("date_style", "short"), "monogram": m.get("monogram", "image"),
            "picture_fit": dict(m.get("picture_fit") or {}),
            "where": where, "folder": folder, "css": css, "js": js}


def discover(roots: Optional[list] = None) -> list[dict]:
    """Every look found, in picker order (order, then name). A later folder wins on the same id."""
    roots = roots if roots is not None else [(BUILTIN_DIR, "built-in"), (LOCAL_DIR, "local")]
    found: dict[str, dict] = {}
    for root, where in roots:
        root = Path(root)
        if not root.is_dir():
            continue
        for d in sorted(root.iterdir()):
            if d.is_dir() and not d.name.startswith(".") and (d / "theme.json").is_file():
                t = _read(d, where)
                if t:
                    found[t["id"]] = t
    return sorted(found.values(), key=lambda t: (t["order"], t["name"]))


_cache: dict = {"all": None, "key": None, "checked": 0.0, "roots": None}
_lock = threading.Lock()
CHECK_EVERY = 1.0    # seconds between looks at the theme folders' file times


def _stamp(roots: Optional[list] = None) -> str:
    """A key that changes when any look's theme.json, theme.css or theme.js changes, or a look folder comes or goes."""
    roots = roots if roots is not None else [(BUILTIN_DIR, "built-in"), (LOCAL_DIR, "local")]
    parts = []
    for root, _ in roots:
        root = Path(root)
        if not root.is_dir():
            continue
        for d in sorted(root.iterdir()):
            if not d.is_dir():
                continue
            for name in ("theme.json", "theme.css", "theme.js"):
                f = d / name
                try:
                    parts.append(f"{f}:{f.stat().st_mtime_ns}:{f.stat().st_size}")
                except OSError:
                    pass
    return hashlib.sha1("|".join(parts).encode()).hexdigest()


def all_themes() -> list[dict]:
    """Every look found, read again whenever a look's files change (so an edited theme.css shows without a restart)."""
    import time
    with _lock:
        now = time.time()
        if _cache["all"] is None or now - _cache["checked"] > CHECK_EVERY:
            _cache["checked"] = now
            key = _stamp(_cache["roots"])
            if _cache["all"] is None or key != _cache["key"]:
                _cache["all"], _cache["key"] = discover(_cache["roots"]), key
        return _cache["all"]


def reload(roots: Optional[list] = None) -> list[dict]:
    import time
    with _lock:
        _cache["roots"] = roots
        _cache["all"] = discover(roots)
        _cache["key"], _cache["checked"] = _stamp(roots), time.time()
        return _cache["all"]


def enabled() -> list[dict]:
    return [t for t in all_themes() if t["enabled"]]


def by_id(tid: str) -> Optional[dict]:
    return next((t for t in enabled() if t["id"] == tid), None)


def default_id() -> str:
    on = enabled()
    if not on:
        return "navy"
    return next((t["id"] for t in on if t["default"]), on[0]["id"])


def looks() -> dict:
    """{id: (name, blurb)} for every enabled look, in picker order."""
    return {t["id"]: (t["name"], t["blurb"]) for t in enabled()}


def public(t: dict) -> dict:
    """What Settings and the frame's picker need to know about a look."""
    return {"key": t["id"], "name": t["name"], "note": t["blurb"], "kind": t["kind"], "swatches": t["swatches"],
            "home": t["home"], "screens": t["screens"], "options": t["options"], "background": t["background"], "kids": t["kids"]}


def new_frame_defaults(tid: str, screens_all: list, default_screens: list) -> tuple[str, list]:
    """(home, screens) a new frame with this look starts with."""
    t = by_id(tid) or {}
    screens = [s for s in (t.get("screens") or []) if s in screens_all] or list(default_screens)
    return t.get("home") or "today", screens


# ---------------- the CSS ----------------

URL_RE = re.compile(r"url\(\s*(['\"]?)([^'\")]+)\1\s*\)")


def _relink(css: str, tid: str) -> str:
    """url(fonts/x.woff2) in themes/<id>/theme.css -> url(themes/<id>/fonts/x.woff2), served by /themes/<id>/..."""
    def fix(m):
        u = m.group(2).strip()
        if re.match(r"^([a-z]+:|/|#|themes/|\.\./)", u):
            return m.group(0)
        return f'url("themes/{tid}/{u}")'
    return URL_RE.sub(fix, css)


DRAWING_CODE = (ROOT / "web" / "js" / "app.js", ROOT / "web" / "js" / "kids.js")   # the screen time pictures are drawn here
_art_cache: dict = {}


def art_families(packset=None) -> dict:
    """{hex: family} for every color in the turned-on packs' drawings (scenes and Sunday series) and in the
    frame's own drawing code. Cached until the packs change."""
    key = getattr(packset, "signature", "") + ":" + ":".join(str(p.stat().st_mtime_ns) for p in DRAWING_CODE if p.exists())
    if _art_cache.get("key") == key:
        return _art_cache["fam"]
    colors, backs = set(), set()
    texts = [p.read_text(encoding="utf-8") for p in DRAWING_CODE if p.exists()]
    if packset is not None:
        for sc in packset.scenes.values():
            if str(sc.get("path", "")).lower().endswith(".svg"):
                try:
                    texts.append(Path(sc["path"]).read_text(encoding="utf-8"))
                except OSError:
                    pass
        w = getattr(packset, "weekly", None)
        if w:
            for ser in w["data"].get("series", []):
                for it in ser.get("items", []):
                    try:
                        texts.append((w["pack"]["folder"] / str(it.get("file", ""))).read_text(encoding="utf-8"))
                    except OSError:
                        pass
    for t in texts:
        c, b = artcolor.colors_in(t)
        colors |= c
        backs |= b
    fam = artcolor.families(colors, backs, getattr(packset, "palette", None))
    _art_cache.update(key=key, fam=fam)
    return fam


def art_vars(t: dict, fam: dict) -> str:
    """The look's value for every drawn color: --art-C9A55A: <its color in this look>."""
    pal = t["palette"]
    return " ".join(f"--art-{h[1:]}: {artcolor.remap(h, f, pal[f])};" for h, f in sorted(fam.items()) if f in pal)


def theme_css(t: dict, fam: Optional[dict] = None) -> str:
    sel = f"body.look-{t['id']}"
    parts = [f"/* ---- {t['name']} ({t['id']}) ---- */"]
    if t["fonts"]:
        parts.append(f"{sel} {{ " + " ".join(f"--{k}: {v};" for k, v in t["fonts"].items()) + " }")
    if t["palette"] and fam:
        parts.append(f"{sel}.pics-match {{ {art_vars(t, fam)} }}")
    if t["filter"]:
        places = ", ".join(SVG_PLACES)
        parts.append(f"{sel}.pics-match :is({places}) {{ filter: {t['filter']}; }}")
    if t["frame"]:
        parts.append(f"{sel}.pics-match :is({', '.join(FRAME_PLACES)}) {{ " + " ".join(f"{k}: {v};" for k, v in t["frame"].items()) + " }")
    if t["css"].strip():
        parts.append(_relink(t["css"].strip(), t["id"]))
    return "\n".join(parts)


def css(packset=None) -> str:
    """/themes.css: every enabled look's own CSS, with its colors for Match the look."""
    fam = art_families(packset)
    head = ("/* Looks (themes/<id>/theme.css) and picture styles, put together by app/themes.py. See docs/themes.md. */\n"
            "/* The photo behind every screen, for a look with \"background\": \"photo\" (web/js/looks.js). A look sets --look-photo-dim. */\n"
            "#look-bg { position: absolute; inset: 0; z-index: 0; pointer-events: none; display: none; background: #000; overflow: hidden; }\n"
            "#look-bg img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; opacity: 0; transition: opacity 1.2s ease; }\n"
            "#look-bg img.on { opacity: 1; }\n"
            "#look-bg::after { content: ''; position: absolute; inset: 0; background: #000; opacity: var(--look-photo-dim, 0.35); }\n"
            "body.look-photo #look-bg { display: block; }\n"
            "body.look-photo .screen { background: transparent; }\n"
            "/* The screen time cards are painted the color their picture is drawn on; they follow it when it changes. */\n"
            "body.pics-match .kscreen.dark, body.pics-match .pv.dark { background: var(--art-16324F, #16324F); }\n"
            "body.pics-match .kscreen.light { background: var(--art-FFFDF8, #FFFDF8); }")
    return "\n".join([head] + [theme_css(t, fam) for t in enabled()]) + "\n"


def js(packset=None) -> str:
    """/themes.js: every enabled look's theme.js, each in its own wrapper so one broken look can't stop the others.
    It starts with the color family of every drawn color, so a look's derive() can recolor pictures (art families)."""
    fam = art_families(packset)
    parts = ["/* Looks' scripts (themes/<id>/theme.js), put together by app/themes.py. API: web/js/looks.js, docs/themes.md. */",
             "if (window.FrameLooks) FrameLooks.artFamilies = " + json.dumps({h[1:]: f for h, f in sorted(fam.items())}, separators=(",", ":")) + ";",
             "if (window.FrameLooks) FrameLooks.artAnchors = " + json.dumps({f: a[0] for f, a in artcolor.FAMILIES.items()}, separators=(",", ":")) + ";"]
    for t in enabled():
        if t["js"].strip():
            parts.append(f"/* ---- {t['name']} ({t['id']}) ---- */\n(function () {{\ntry {{\n{t['js'].strip()}\n}} catch (e) {{ if (window.console) console.warn('look {t['id']}', e); }}\n}})();")
    return "\n".join(parts) + "\n"


def signature(packset=None) -> str:
    h = hashlib.sha1()
    for t in all_themes():
        for f in sorted(t["folder"].rglob("*")):
            if f.is_file():
                h.update(f"{f}:{f.stat().st_mtime_ns}".encode())
    h.update(getattr(packset, "signature", "").encode())
    for p in (Path(__file__), Path(artcolor.__file__)):
        h.update(p.read_bytes())
    return h.hexdigest()[:10]


def theme_file(tid: str, rel: str) -> Optional[tuple[Path, str]]:
    """A font or picture file inside a look's folder, for /themes/<id>/<path>."""
    t = by_id(tid)
    if not t or Path(rel).suffix.lower() not in FILE_EXT:
        return None
    p = (t["folder"] / rel).resolve()
    if t["folder"].resolve() not in p.parents or not p.is_file():
        return None
    return p, FILE_EXT[p.suffix.lower()]


def unscoped_selectors(css_text: str, tid: str) -> list[str]:
    """Selectors in a theme.css that don't start with body.look-<id> (a look must only change its own frames)."""
    text = re.sub(r"/\*.*?\*/", "", css_text, flags=re.S)
    bad = []
    depth = 0
    buf = ""
    for ch in text:
        if ch == "{":
            sel = buf.strip()
            if depth == 0 and not sel.startswith("@"):
                for s in sel.split(","):
                    if not re.match(rf"^body\.look-{re.escape(tid)}(?![\w-])", s.strip()):
                        bad.append(s.strip())
            depth += 1
            buf = ""
        elif ch == "}":
            depth = max(0, depth - 1)
            buf = ""
        else:
            buf += ch
    return bad
