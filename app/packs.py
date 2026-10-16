"""Art packs: the special-day pictures and the rules that bring them up, as folders the family can add or remove.

A pack is a folder (or a zip of one):
    <id>/pack.json        name, version, priority, scenes, groups and rules (docs/art-packs.md)
    <id>/scenes/*.svg     the drawings (png and jpg work too)
    <id>/series.json      optional: pictures that take turns every week (the faith pack's Sunday series)

Packs are read from three places, later ones winning on a clash of the same pack id:
    packs/                 built in (comes with Doorpost, can be turned off but not removed)
    local/packs/           your own, in a private copy of the code (app/overlay.py; FRAME_LOCAL_DIR moves it)
    DATA_DIR/packs/        installed from Settings > Art packs (DATA_DIR/packs-demo/ in demo mode)
FRAME_EXTRA_PACKS (folders separated by ':') adds more places to read; the tests use it.

Two scenes with the same id: the pack with the higher "priority" wins. Only turned-on packs count, and the
frame only ever gets drawings from turned-on packs (/art.js). Every SVG is cleaned before it reaches the frame
(no scripts, event handlers, foreignObject or outside links), because the frame puts drawings on the page as HTML.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import secrets
import shutil
import threading
import xml.etree.ElementTree as ET
import zipfile
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from . import config as _cfg

ROOT = Path(__file__).resolve().parent.parent
BUILTIN_DIR = ROOT / "packs"
INDEX_FILE = BUILTIN_DIR / "index.json"
DIST_DIR = ROOT / "dist" / "packs"
MAX_ZIP = 20 * 1024 * 1024          # a pack zip, and everything in it once unzipped
MAX_FILES = 3000
ALLOWED_EXT = {".svg", ".png", ".jpg", ".jpeg", ".json"}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
WHERE_LABEL = {"built-in": "Built in", "local": "Your own (local/packs)", "installed": "Installed", "extra": "Extra folder"}


class PackError(ValueError):
    """Something wrong with a pack, in words a person can act on."""


# ---------------- cleaning SVG ----------------

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
XML_NS = "http://www.w3.org/XML/1998/namespace"
ALLOWED_TAGS = {
    "svg", "g", "defs", "symbol", "use", "title", "desc", "path", "rect", "circle", "ellipse", "line", "polyline",
    "polygon", "text", "tspan", "textPath", "linearGradient", "radialGradient", "stop", "clipPath", "mask", "pattern",
    "marker", "filter", "feGaussianBlur", "feOffset", "feBlend", "feColorMatrix", "feComposite", "feFlood", "feMerge",
    "feMergeNode", "feDropShadow", "feMorphology", "feComponentTransfer", "feFuncR", "feFuncG", "feFuncB", "feFuncA",
}
BAD_VALUE = re.compile(r"(?i)(java|vb)script\s*:|data\s*:|@import|expression\s*\(|behavior\s*:")
OUTSIDE_URL = re.compile(r"(?i)url\(\s*['\"]?\s*(?!#)")
LOOSE_AMP = re.compile(r"&(?!(?:#\d+|#x[0-9a-fA-F]+|amp|lt|gt|quot|apos);)")
ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", XLINK_NS)


def _split(tag: str) -> tuple[str, str]:
    if tag.startswith("{"):
        ns, _, local = tag[1:].partition("}")
        return ns, local
    return "", tag


OWN_FILE = re.compile(r"^(?!/)(?!.*\.\.)[A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:png|jpe?g)$", re.I)


def _own_image(el, own_file) -> bool:
    """An <image> whose href is a png or jpg in the drawing's own pack: point it at that file's address."""
    hrefs = [k for k in el.attrib if _split(k)[1] == "href"]
    v = el.attrib.get(hrefs[0], "").strip() if len(hrefs) == 1 else ""
    url = own_file(v) if OWN_FILE.match(v) else None
    if not url:
        return False
    del el.attrib[hrefs[0]]
    el.set("href", url)
    el.set("data-own", "1")
    return True


def sanitize_svg(text: str, own_file=None) -> str:
    """The drawing with anything that could run code or reach outside removed. A clean drawing comes back as it was.

    own_file(rel) -> address or None: lets an <image> show a png or jpg from the drawing's own pack
    (href="images/logo.png"); the address it gives (art/packs/<id>/...) is put in its place."""
    text = text.lstrip("﻿")
    if re.search(r"(?i)<!DOCTYPE|<!ENTITY", text):
        raise PackError("A drawing in this pack uses a DOCTYPE or ENTITY, which isn't allowed.")
    text = re.sub(r"^\s*<\?xml[^>]*\?>\s*", "", text)
    text = LOOSE_AMP.sub("&amp;", text)
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise PackError(f"A drawing in this pack isn't valid SVG ({exc}).")
    if _split(root.tag)[1] != "svg":
        raise PackError("A drawing in this pack isn't an SVG.")
    changed = bool(re.search(r"<[!?]", text))   # comments, CDATA, processing instructions: write it out fresh
    for parent in root.iter():
        for child in list(parent):
            if not isinstance(child.tag, str):
                continue
            ns, local = _split(child.tag)
            if ns in ("", SVG_NS) and local == "image" and own_file and _own_image(child, own_file):
                changed = True   # a png or jpg from the drawing's own pack, now pointing at its address
                continue
            if ns not in ("", SVG_NS) or local not in ALLOWED_TAGS:
                parent.remove(child)
                changed = True
    for el in root.iter():
        for name in list(el.attrib):
            ns, local = _split(name)
            v = el.attrib[name]
            low = local.lower()
            if low == "href" and _split(el.tag)[1] == "image" and el.get("data-own") == "1":
                continue   # checked by _own_image
            bad = (ns not in ("", XLINK_NS, XML_NS) or low.startswith("on") or
                   (low == "href" and not v.strip().startswith("#")) or BAD_VALUE.search(v) or OUTSIDE_URL.search(v))
            if bad:
                del el.attrib[name]
                changed = True
    for el in root.iter():
        el.attrib.pop("data-own", None)
    if not changed:
        return text
    return ET.tostring(root, encoding="unicode", short_empty_elements=False)


# ---------------- reading packs ----------------

def installed_dir(demo: bool) -> Path:
    return _cfg.DATA_DIR / ("packs-demo" if demo else "packs")


def _roots(demo: bool) -> list[tuple[Path, str]]:
    from . import overlay
    roots = [(BUILTIN_DIR, "built-in"), (overlay.packs_dir(), "local"), (installed_dir(demo), "installed")]
    for p in (os.environ.get("FRAME_EXTRA_PACKS") or "").split(os.pathsep):
        if p.strip():
            roots.append((Path(p.strip()), "extra"))
    return roots


def _pack_dirs(demo: bool) -> list[tuple[Path, str]]:
    out = []
    for root, where in _roots(demo):
        if not root.is_dir():
            continue
        for d in sorted(root.iterdir()):
            if d.is_dir() and not d.name.startswith(".") and (d / "pack.json").is_file():
                out.append((d, where))
    return out


def _folder_size(folder: Path) -> int:
    return sum(p.stat().st_size for p in folder.rglob("*") if p.is_file())


def check_manifest(m: dict, folder: Optional[Path] = None) -> dict:
    """pack.json is sane: an id, a name, scenes with files that exist. Returns it."""
    if not isinstance(m, dict):
        raise PackError("pack.json should be a JSON object.")
    pid = str(m.get("id", ""))
    if not ID_RE.match(pid):
        raise PackError("pack.json needs an \"id\": lowercase letters, numbers and dashes, like my-pack.")
    if not str(m.get("name", "")).strip():
        raise PackError("pack.json needs a \"name\".")
    scenes = m.get("scenes") or {}
    if not isinstance(scenes, dict) or not isinstance(m.get("rules", []), list) or not isinstance(m.get("groups", []), list):
        raise PackError("In pack.json, \"scenes\" should be an object and \"rules\" and \"groups\" lists.")
    pal = m.get("palette", {})
    if not isinstance(pal, dict) or not all(re.match(r"^#[0-9A-Fa-f]{6}$", str(k)) and isinstance(v, str) for k, v in pal.items()):
        raise PackError("In pack.json, \"palette\" maps colors like \"#AA3322\" to art roles like \"gold\" (docs/art-packs.md).")
    try:
        int(m.get("priority", 50))
    except (TypeError, ValueError):
        raise PackError("In pack.json, \"priority\" should be a number.")
    for sid, sc in scenes.items():
        if not ID_RE.match(str(sid)) or not isinstance(sc, dict) or not isinstance(sc.get("file"), str):
            raise PackError(f"Scene {sid!r}: scene names are lowercase letters, numbers and dashes, each with a \"file\".")
        if folder is not None and not _inside(folder, sc["file"]).is_file():
            raise PackError(f"Scene {sid!r}: the file {sc['file']} isn't in the pack.")
    if folder is not None:
        for r in m.get("rules", []):
            if isinstance(r, dict) and r.get("series"):
                p = _inside(folder, str(r["series"]))
                if not p.is_file():
                    raise PackError(f"The series file {r['series']} isn't in the pack.")
                data = json.loads(p.read_text(encoding="utf-8"))
                for s in data.get("series", []):
                    for it in s.get("items", []):
                        if not _inside(folder, str(it.get("file", ""))).is_file():
                            raise PackError(f"Series picture {it.get('file')} isn't in the pack.")
    return m


def _inside(folder: Path, rel: str) -> Path:
    p = (folder / rel).resolve()
    if folder.resolve() not in p.parents:
        raise PackError(f"{rel} points outside the pack.")
    return p


def _read(folder: Path, where: str) -> Optional[dict]:
    try:
        m = check_manifest(json.loads((folder / "pack.json").read_text(encoding="utf-8")))
    except (PackError, ValueError, OSError) as exc:
        import logging
        logging.getLogger(__name__).warning("skipping art pack %s: %s", folder, exc)
        return None
    pictures = len(m.get("scenes") or {})
    series = None
    for r in m.get("rules", []):
        if isinstance(r, dict) and r.get("series") and (folder / str(r["series"])).is_file():
            try:
                series = json.loads((folder / str(r["series"])).read_text(encoding="utf-8"))
                pictures += sum(len(s.get("items", [])) for s in series.get("series", []))
            except ValueError:
                series = None
    return {"id": m["id"], "name": str(m["name"]), "version": str(m.get("version", "")), "priority": int(m.get("priority", 50)),
            "description": str(m.get("description", "")), "license": str(m.get("license", "")), "where": where,
            "folder": folder, "manifest": m, "series": series, "pictures": pictures, "size": _folder_size(folder),
            "preview": m.get("preview") or next((sc["file"] for sc in (m.get("scenes") or {}).values()), None)}


class PackSet:
    """Every pack found, and the merged pictures and rules of the ones turned on."""

    def __init__(self, found: list[dict], off: set, signature: str = ""):
        self.signature = signature
        order = {"built-in": 0, "local": 1, "extra": 2, "installed": 3}
        self.all = sorted(found, key=lambda p: (order.get(p["where"], 9), p["id"]))
        for p in self.all:
            p["on"] = p["id"] not in off
        self.on = sorted([p for p in self.all if p["on"]], key=lambda p: (p["priority"], order.get(p["where"], 9), p["id"]))
        self.scenes: dict[str, dict] = {}
        self.holiday_rules: dict[str, dict] = {}
        self.church: dict[str, dict] = {}
        self.seasons: dict[str, dict] = {}
        self.weekly: Optional[dict] = None
        self._clock: list = []     # [(["text", "ref"], passage or None)] for the bedtime clock
        self.demo = False          # set by load(); which Bible settings to read (app/bible.py)
        self.palette: dict[str, str] = {}   # a pack's own colors -> art roles, for "Match the look" (app/themes.py)
        groups: dict[str, dict] = {}
        words = []
        for n, p in enumerate(self.on):
            m = p["manifest"]
            for hexv, role in (m.get("palette") or {}).items():
                if re.match(r"^#[0-9A-Fa-f]{6}$", str(hexv)) and isinstance(role, str):
                    self.palette[str(hexv).upper()] = role
            for sid, sc in (m.get("scenes") or {}).items():
                self.scenes[sid] = {**sc, "pack": p["id"], "path": p["folder"] / sc["file"]}
            for g in m.get("groups") or []:
                if isinstance(g, dict) and g.get("name"):
                    cur = groups.setdefault(g["name"], {"name": g["name"], "order": g.get("order", 500), "scenes": []})
                    cur["scenes"] += [s for s in g.get("scenes", []) if s not in cur["scenes"]]
            for i, r in enumerate(m.get("rules") or []):
                if not isinstance(r, dict):
                    continue
                if r.get("holiday"):
                    from .special import norm
                    key = norm(str(r["holiday"]))
                    self.holiday_rules[key] = {**self.holiday_rules.get(key, {}), **{k: v for k, v in r.items() if k != "holiday"}}
                elif r.get("church"):
                    self.church[str(r["church"])] = {**r, "pack": p["id"]}
                elif r.get("season"):
                    self.seasons[str(r["season"])] = r
                elif r.get("weekly") == "sunday" and p["series"]:
                    self.weekly = {**r, "pack": p, "data": p["series"]}
                elif r.get("clock_verses"):
                    ps = r.get("passages") if isinstance(r.get("passages"), list) else []
                    self._clock = [([str(v[0]), str(v[1])], ps[i] if i < len(ps) and isinstance(ps[i], dict) else None)
                                   for i, v in enumerate(r["clock_verses"]) if isinstance(v, (list, tuple)) and len(v) == 2]
                elif r.get("keyword"):
                    w = {"word": str(r["keyword"])[:40], "look": str(r.get("scene") or "")}
                    if r.get("picture_only"):
                        w["picture_only"] = True
                    words.append((r.get("order", 500), n, i, w))
        self.words = [w for *_k, w in sorted(words, key=lambda x: (x[0], x[1], x[2]))]
        self.groups = sorted(groups.values(), key=lambda g: (g["order"], g["name"]))
        self._svg: dict[str, str] = {}
        self._art: Optional[str] = None
        self._lock = threading.Lock()

    # ----- the pictures -----

    def scene_svg(self, sid: str) -> str:
        if sid not in self._svg:
            sc = self.scenes[sid]
            path = sc["path"]
            if path.suffix.lower() == ".svg":
                pack = next(p for p in self.on if p["id"] == sc["pack"])
                svg = sanitize_svg(path.read_text(encoding="utf-8"), own_file=lambda rel, pack=pack: _own_url(pack, rel))
            else:   # a photo-style picture: shown through a small SVG wrapper, served by /art/packs/...
                rel = path.relative_to(next(p["folder"] for p in self.on if p["id"] == sc["pack"])).as_posix()
                svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 600" preserveAspectRatio="xMidYMax slice" '
                       'style="position: absolute; inset: 0; width: 100%; height: 100%" aria-hidden="true">'
                       f'<image href="art/packs/{sc["pack"]}/{rel}" width="300" height="600" preserveAspectRatio="xMidYMid slice"></image></svg>')
            self._svg[sid] = svg
        return self._svg[sid]

    def art_js(self) -> str:
        """window.THEMES for the frame and Settings: every drawing of every turned-on pack."""
        with self._lock:
            if self._art is None:
                art = {}
                for sid in self.scenes:
                    try:
                        art[sid] = self.scene_svg(sid)
                    except (OSError, PackError, UnicodeDecodeError):
                        continue
                self._art = ("/* Drawings from the turned-on art packs (app/packs.py). */\nwindow.THEMES = " +
                             json.dumps(art, ensure_ascii=False).replace("</", "<\\/") + ";\n")
            return self._art

    def variant(self, sid: str, d: Optional[date]) -> str:
        """The scene to show on day d: a scene can name another one for part of the year
        ("variants": [{"scene": "fair-autumn", "from": "09-12", "to": "11-03"}])."""
        if d is None:
            return sid
        for v in self.scenes.get(sid, {}).get("variants") or []:
            try:
                lo = tuple(int(x) for x in str(v["from"]).split("-"))
                hi = tuple(int(x) for x in str(v["to"]).split("-"))
            except (KeyError, ValueError, TypeError):
                continue
            md = (d.month, d.day)
            inside = lo <= md <= hi if lo <= hi else (md >= lo or md <= hi)   # a range can wrap past New Year
            if inside and v.get("scene") in self.scenes:
                return v["scene"]
        return sid

    def visible_scenes(self) -> set:
        return {k for k, v in self.scenes.items() if not v.get("hidden")}

    def title(self, sid: str) -> str:
        return str(self.scenes.get(sid, {}).get("title") or sid)

    def script(self, sid: str) -> Optional[str]:
        return self.scenes.get(sid, {}).get("script")

    # ----- Bible verses, in the family's chosen translation (app/bible.py) -----

    def bible(self):
        from . import bible
        return bible.current(self.demo)

    def verse_line(self, passage, fallback: str = "") -> str:
        """'“Text.” Psalm 23:1 (KJV)' for a pack's verse; the pack's own line when it has no passage."""
        return self.bible().line(passage if isinstance(passage, dict) else None, fallback)

    @property
    def clock_verses(self) -> list:
        """The bedtime clock's verses: [["text", "citation"], ...], one per weekday."""
        b = self.bible()
        out = []
        for pair, p in self._clock:
            if p and (p.get("text") or p.get("verses")):
                text, cite, _code = b.show(p)
                out.append([text, cite])
            else:
                out.append(pair)
        return out

    def passages(self) -> list:
        """Every passage in the turned-on packs (what a Bible download needs to cover)."""
        out = [p for _pair, p in self._clock if p]
        out += [r["passage"] for r in self.church.values() if isinstance(r.get("passage"), dict)]
        out += [r["passage"] for r in self.holiday_rules.values() if isinstance(r.get("passage"), dict)]
        if self.weekly:
            out += [it["passage"] for s in self.weekly["data"].get("series", []) for it in s.get("items", [])
                    if isinstance(it.get("passage"), dict)]
        return out

    # ----- the rules -----

    def holiday_looks(self) -> dict:
        """normalized holiday name: (scene, script, solemn, verse), like special.HOLIDAY_LOOKS."""
        return {k: (r["scene"], r.get("script", "Special day"), bool(r.get("solemn")), self.verse_line(r.get("passage"), r.get("verse", "")))
                for k, r in self.holiday_rules.items() if r.get("scene")}

    def holiday_modes(self) -> dict:
        return {k: r["mode"] for k, r in self.holiday_rules.items() if r.get("mode") in ("hide", "show", "special")}

    def church_days(self, year: int) -> list[dict]:
        from .special import easter
        e = easter(year)
        out = []
        for key, r in self.church.items():
            try:
                if "easter" in r:
                    d = e + timedelta(days=int(r["easter"]))
                else:
                    mm, dd = (int(x) for x in str(r["date"]).split("-"))
                    d = date(year, mm, dd)
            except (KeyError, ValueError, TypeError):
                continue
            out.append({"key": key, "name": str(r.get("name") or key), "date": d, "look": str(r.get("scene") or "pattern"),
                        "script": str(r.get("script") or r.get("name") or ""), "verse": self.verse_line(r.get("passage"), str(r.get("verse") or "")),
                        "solemn": bool(r.get("solemn")), "icon": "cross"})
        return out

    def church_defaults(self) -> dict:
        return {k: bool(r.get("default_on", True)) for k, r in self.church.items()}

    def replaced_holidays(self) -> dict:
        """Google holiday names a church-year day shows instead ("easter sunday" -> "easter")."""
        from .special import norm
        return {norm(str(n)): k for k, r in self.church.items() for n in (r.get("replaces") or [])}

    def sunday(self, d: date, paused=None) -> Optional[dict]:
        """This Sunday's picture from the weekly series (the faith pack), or None without one."""
        w = self.weekly
        if not w:
            return None
        from .lordsday import pick
        series = [s for s in w["data"].get("series", []) if s.get("items")]
        if not series:
            return None
        try:
            start = date.fromisoformat(str(w["data"].get("start") or w.get("start") or "2027-01-03"))
        except ValueError:
            start = date(2027, 1, 3)
        s, i = pick([len(x["items"]) for x in series], start, d, paused)
        it = series[s]["items"][i]
        key = f"series:{series[s].get('key')}:{i}"
        if key not in self._svg:
            self._svg[key] = sanitize_svg(_inside(w["pack"]["folder"], str(it["file"])).read_text(encoding="utf-8"))
        return {"series": str(series[s].get("name", "")), "series_key": series[s].get("key"), "n": i + 1, "count": len(series[s]["items"]),
                "title": str(it.get("title", "")),
                "verse": self.verse_line(it.get("passage"), f"“{it.get('verse', '')}.” {it.get('ref', '')}" if it.get("verse") else ""),
                "about": str(it.get("about", "")), "svg": self._svg[key], "script": str(w.get("script") or "Sunday")}

    def view(self) -> list[dict]:
        """What Settings > Art packs lists."""
        return [{"id": p["id"], "name": p["name"], "version": p["version"], "description": p["description"], "license": p["license"],
                 "where": p["where"], "where_label": WHERE_LABEL.get(p["where"], p["where"]), "on": p["on"],
                 "removable": p["where"] == "installed", "pictures": p["pictures"], "size": p["size"],
                 "preview": f"art/preview/{p['id']}.svg" if p["preview"] else None} for p in self.all]


_cache: dict = {"key": None, "set": None, "demo": False}
_cache_lock = threading.Lock()


def _signature(demo: bool) -> tuple:
    dirs = _pack_dirs(demo)
    parts = [(str(d), w, (d / "pack.json").stat().st_mtime_ns) for d, w in dirs]
    store = _cfg.store_path(demo)
    return (demo, tuple(parts), store.stat().st_mtime_ns if store.exists() else 0, os.environ.get("FRAME_EXTRA_PACKS", ""))


def off_ids(demo: bool) -> set:
    return set((_cfg.read_store(demo).get("art_packs") or {}).get("off") or [])


def load(demo: bool) -> PackSet:
    """Every pack from the three places, with the ones turned off in Settings marked. Cached until something changes."""
    with _cache_lock:
        key = _signature(demo)
        if _cache["key"] != key:
            found: dict[str, dict] = {}
            for d, where in _pack_dirs(demo):
                p = _read(d, where)
                if p:
                    found[p["id"]] = p   # a later place wins (installed over local over built in)
            _cache["set"] = PackSet(list(found.values()), off_ids(demo), hashlib.sha1(repr(key).encode()).hexdigest()[:10])
            _cache["set"].demo = demo
            _cache["key"] = key
        _cache["demo"] = demo
        return _cache["set"]


def current() -> PackSet:
    """The packs the running server uses (the last load), for code that has no Services at hand."""
    return load(_cache["demo"])


# ---------------- installing ----------------

def read_index() -> list[dict]:
    """packs/index.json: the packs you can install from Settings."""
    try:
        data = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    out = []
    for e in data.get("packs", []):
        if isinstance(e, dict) and ID_RE.match(str(e.get("id", ""))) and e.get("url") and re.match(r"^[0-9a-f]{64}$", str(e.get("sha256", ""))):
            out.append(e)
    return out


def index_view(ps: PackSet) -> list[dict]:
    have = {p["id"]: p for p in ps.all}
    out = []
    for e in read_index():
        p = have.get(e["id"])
        out.append({"id": e["id"], "name": e.get("name", e["id"]), "description": e.get("description", ""), "version": e.get("version", ""),
                    "size": e.get("size"), "pictures": e.get("pictures"), "license": e.get("license", ""),
                    "preview": f"art/preview/{e['id']}.svg", "installed": bool(p), "default": bool(e.get("default")),
                    "update": bool(p and p["where"] == "installed" and _newer(str(e.get("version", "")), p["version"]))})
    return out


def _newer(a: str, b: str) -> bool:
    def parts(v):
        return tuple(int(x) if x.isdigit() else 0 for x in re.split(r"[.-]", v or "0"))
    return parts(a) > parts(b)


def _download(entry: dict) -> bytes:
    url = str(entry["url"])
    if url.startswith("https://"):
        import httpx
        with httpx.stream("GET", url, timeout=60, follow_redirects=True) as r:
            r.raise_for_status()
            buf = bytearray()
            for chunk in r.iter_bytes():
                buf += chunk
                if len(buf) > MAX_ZIP:
                    raise PackError("That download is over 20 MB.")
            return bytes(buf)
    if re.match(r"^[a-z]+://", url):
        raise PackError("Packs download over https only.")
    path = (ROOT / url).resolve()
    if DIST_DIR.resolve() not in path.parents:
        raise PackError("The packs list points outside dist/packs.")
    if path.is_file():
        return path.read_bytes()
    # Not built yet (a fresh copy of the code): make it from the drawing code, the same bytes the list expects.
    from . import pack_build as pb
    if entry["id"] in pb.INFO and str(entry.get("version")) == pb.version_of(entry["id"]):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            z, _sha = pb.build_zip(entry["id"], Path(tmp), Path(tmp))
            return z.read_bytes()
    raise PackError(f"{path.name} isn't here. Run: python3 scripts/build-pack.py {entry['id']}")


def seed_defaults(demo: bool) -> list[str]:
    """Install the packs that come on by default ("default": true in packs/index.json, the Faith pack) the first
    time the server starts. Each is done once: a family that removes it (or turns it off) keeps it that way.
    A pack already found somewhere (local/packs, an extra folder) is left alone. Returns the ids installed."""
    store = _cfg.read_store(demo)
    ap = dict(store.get("art_packs") or {})
    seeded = set(ap.get("seeded") or [])
    todo = [e for e in read_index() if e.get("default") and e["id"] not in seeded]
    if not todo:
        return []
    have = {d.name for d, _w in _pack_dirs(demo)}
    done, installed = [], []
    for e in todo:
        if e["id"] not in have:
            try:
                install_from_index(e["id"], demo)
                installed.append(e["id"])
            except Exception as exc:  # noqa: BLE001  (offline with a https:// link, say: try again next start)
                import logging
                logging.getLogger(__name__).warning("couldn't install the %s art pack: %s", e["id"], exc)
                continue
        done.append(e["id"])
    if done:
        ap["seeded"] = sorted(seeded | set(done))
        store["art_packs"] = ap
        _cfg.write_store(store, demo)
    return installed


def install_from_index(pid: str, demo: bool) -> dict:
    entry = next((e for e in read_index() if e["id"] == pid), None)
    if not entry:
        raise PackError("That pack isn't in the list.")
    return install_zip(_download(entry), demo, expect_sha=entry["sha256"])


def _safe_names(z: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    infos = [i for i in z.infolist() if not i.is_dir()]
    if len(infos) > MAX_FILES:
        raise PackError(f"That zip has more than {MAX_FILES} files.")
    if sum(i.file_size for i in infos) > MAX_ZIP:
        raise PackError("Unzipped, that pack is over 20 MB.")
    for i in infos:
        n = i.filename
        parts = n.split("/")
        if n.startswith("/") or "\\" in n or ":" in n or any(p in ("", ".", "..") for p in parts):
            raise PackError(f"The zip has a file with an unsafe name: {n}")
        if (i.external_attr >> 16) & 0o170000 == 0o120000:
            raise PackError(f"The zip has a link instead of a file: {n}")
        if parts[-1].startswith("."):
            continue   # .DS_Store and friends: skipped
        if Path(n).suffix.lower() not in ALLOWED_EXT:
            raise PackError(f"Packs hold only .svg, .png, .jpg and .json files, not {parts[-1]}.")
    return [i for i in infos if not i.filename.split("/")[-1].startswith(".")]


def install_zip(data: bytes, demo: bool, expect_sha: Optional[str] = None, dest_root: Optional[Path] = None) -> dict:
    """Check, unzip, clean and install a pack zip into DATA_DIR/packs/<id>/ (replacing an older copy). Returns its pack.json."""
    if len(data) > MAX_ZIP:
        raise PackError("That file is over 20 MB.")
    if expect_sha and hashlib.sha256(data).hexdigest() != expect_sha:
        raise PackError("The download doesn't match the packs list (sha256), so it wasn't installed.")
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise PackError("That isn't a zip file.")
    infos = _safe_names(z)
    names = {i.filename for i in infos}
    if "pack.json" in names:
        prefix = ""
    else:
        tops = {n.split("/")[0] for n in names}
        prefix = f"{tops.pop()}/" if len(tops) == 1 else ""
        if f"{prefix}pack.json" not in names:
            raise PackError("There's no pack.json in that zip.")
    try:
        manifest = check_manifest(json.loads(z.read(f"{prefix}pack.json").decode("utf-8")))
    except (ValueError, UnicodeDecodeError) as exc:
        if isinstance(exc, PackError):
            raise
        raise PackError(f"pack.json isn't valid JSON ({exc}).")
    pid = manifest["id"]
    if (BUILTIN_DIR / pid / "pack.json").exists():
        raise PackError(f"“{pid}” is the name of a built-in pack. Give yours another id.")
    dest_root = Path(dest_root) if dest_root else installed_dir(demo)
    dest_root.mkdir(parents=True, exist_ok=True)
    tmp = dest_root / f".tmp-{secrets.token_hex(4)}"
    try:
        total = 0
        for i in infos:
            if prefix and not i.filename.startswith(prefix):
                continue
            rel = i.filename[len(prefix):]
            with z.open(i) as f:
                body = f.read(MAX_ZIP + 1)
            total += len(body)
            if total > MAX_ZIP:
                raise PackError("Unzipped, that pack is over 20 MB.")
            ext = Path(rel).suffix.lower()
            if ext == ".svg":
                try:
                    body = sanitize_svg(body.decode("utf-8")).encode("utf-8")
                except UnicodeDecodeError:
                    raise PackError(f"{rel} isn't UTF-8 text.")
            elif ext == ".json":
                try:
                    json.loads(body.decode("utf-8"))
                except (ValueError, UnicodeDecodeError):
                    raise PackError(f"{rel} isn't valid JSON.")
            else:
                from PIL import Image
                try:
                    Image.open(io.BytesIO(body)).verify()
                except Exception:
                    raise PackError(f"{rel} isn't a picture this frame can read.")
            out = tmp / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(body)
        check_manifest(manifest, tmp)
        final = dest_root / pid
        old = None
        if final.exists():
            old = dest_root / f".old-{secrets.token_hex(4)}"
            final.rename(old)
        tmp.rename(final)
        if old:
            shutil.rmtree(old, ignore_errors=True)
    finally:
        if tmp.exists():
            shutil.rmtree(tmp, ignore_errors=True)
    return manifest


def remove(pid: str, demo: bool) -> None:
    """Remove an installed pack (built-in and local ones can only be turned off)."""
    if not ID_RE.match(pid):
        raise PackError("No such pack.")
    folder = installed_dir(demo) / pid
    if not (folder / "pack.json").exists():
        raise PackError("Only installed packs can be removed. Built-in packs can be turned off instead.")
    shutil.rmtree(folder)


def _own_url(pack: dict, rel: str) -> Optional[str]:
    """art/packs/<id>/<rel> for a png or jpg that really is in this pack, else None."""
    try:
        path = _inside(pack["folder"], rel)
    except PackError:
        return None
    if path.suffix.lower() not in {".png", ".jpg", ".jpeg"} or not path.is_file():
        return None
    return f"art/packs/{pack['id']}/{path.relative_to(pack['folder'].resolve()).as_posix()}"


def file_in_pack(ps: PackSet, pid: str, rel: str) -> Optional[Path]:
    """A picture file of a turned-on pack, for /art/packs/<id>/<path> (png and jpg pictures)."""
    p = next((x for x in ps.on if x["id"] == pid), None)
    if not p or Path(rel).suffix.lower() not in {".png", ".jpg", ".jpeg"}:
        return None
    try:
        path = _inside(p["folder"], rel)
    except PackError:
        return None
    return path if path.is_file() else None


def preview_svg(ps: PackSet, pid: str) -> Optional[str]:
    """A pack's preview drawing (installed or in the packs list), cleaned."""
    p = next((x for x in ps.all if x["id"] == pid), None)
    path = None
    if p and p["preview"]:
        try:
            path = _inside(p["folder"], str(p["preview"]))
        except PackError:
            path = None
    if (path is None or not path.is_file()) and ID_RE.match(pid):
        path = BUILTIN_DIR / "previews" / f"{pid}.svg"
    if path is None or not path.is_file() or path.suffix.lower() != ".svg":
        return None
    try:
        svg = sanitize_svg(path.read_text(encoding="utf-8"))
    except (PackError, OSError, UnicodeDecodeError):
        return None
    for a, b in (("{{PLACE_SIZE}}", "22"), ("{{PLACE}}", "Fun Park"), ("{{NAME_SIZE}}", "22"), ("{{NAME}}", "Birthday"), ("{{PORTRAIT}}", "")):
        svg = svg.replace(a, b)
    if "xmlns=" not in svg[:300]:
        svg = svg.replace("<svg ", f'<svg xmlns="{SVG_NS}" ', 1)
    return svg
