"""Photo slideshow: a local folder plus live shared-album feeds.

Local: everything in the photos folder (subfolders are fine). Admin-panel
uploads land in photos/uploads/, the Mac's Apple Favorites sync in
photos/apple-favorites/. Shared albums (Google, iCloud) are re-read every six
hours; their photos are downloaded only when first shown.

Every photo is turned upright from its EXIF tag, cropped to fill the frame (1280x800 wide,
800x1280 tall), saved as a small JPEG in the cache and served from there. Each photo can
have a focal point (Settings > Photos; the faces Apple Photos found are the starting point):
both crops center on it, either crop can be nudged on its own, and either can instead show
the whole photo on a soft blurred background. See FocusStore.
Optional captions: photos/captions.yaml mapping "file name" -> "caption".
"""
from __future__ import annotations

import hashlib
import io
import logging
import random
import re
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock, Semaphore
from typing import Optional

import httpx
import yaml
import json
from PIL import Image, ImageFilter, ImageOps

from .photo_sources import FETCHERS, UA

log = logging.getLogger(__name__)
SIZE = (1280, 800)
SHAPES = {"wide": (1280, 800), "tall": (800, 1280),
          "wide-hd": (1920, 1080), "tall-hd": (1080, 1920)}   # full-HD frames (15.6", 21.5"): sharper, 16:9
BASE = {"wide": "wide", "tall": "tall", "wide-hd": "wide", "tall-hd": "tall"}  # which crop choices a shape follows
THUMB = (320, 200)
EDIT = 1200          # the whole photo, for the focal-point editor
DEFAULT_CENTER = (0.5, 0.4)  # a little above the middle: heads, not feet
# The Pi can only afford one photo resize at a time: a settings page asking for hundreds
# at once used to swamp it (and Home Assistant with it). Others wait their turn.
_PREPARE = Semaphore(1)
EXTS = {".jpg", ".jpeg", ".png", ".webp"}
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]
REMOTE_REFRESH = timedelta(hours=6)
MAX_UPLOAD = 40 * 1024 * 1024


def crop_rect(w: int, h: int, shape: str, cx: float, cy: float) -> tuple[float, float, float, float]:
    """The part of a w x h photo a frame of this shape shows when centered on (cx, cy), as fractions
    (left, top, width, height), pushed back inside the photo at the edges."""
    fw, fh = SHAPES[shape]
    if w / h > fw / fh:          # photo wider than the frame: crop the sides
        cw, ch = (fw / fh) / (w / h), 1.0
    else:                        # taller: crop top and bottom
        cw, ch = 1.0, (w / h) / (fw / fh)
    left = min(max(cx - cw / 2, 0.0), 1.0 - cw)
    top = min(max(cy - ch / 2, 0.0), 1.0 - ch)
    return left, top, cw, ch


FOCUS_SCHEMA = """
CREATE TABLE IF NOT EXISTS photo_focus (
    name     TEXT PRIMARY KEY,   -- the photo's path inside the photos folder
    point    TEXT,               -- [x, y] set by hand (fractions across and down), or NULL
    faces    TEXT,               -- [x, y] from the faces Apple Photos found, or NULL
    wide     TEXT,               -- [x, y] the wide crop moved on its own, or NULL (follows the point)
    tall     TEXT,               -- the same for the tall crop
    wide_fit INTEGER NOT NULL DEFAULT 0,   -- 1: wide frames show the whole photo, no crop
    tall_fit INTEGER NOT NULL DEFAULT 0,
    updated  TEXT
);
"""
FOCUS_FIELDS = ("point", "faces", "wide", "tall", "wide_fit", "tall_fit")


class FocusStore:
    """Focal points and crop choices, one row per photo (kept in the frame's database)."""

    def __init__(self, db):
        self.db = db
        with db.connect() as conn:
            conn.executescript(FOCUS_SCHEMA)
        self._all: Optional[dict[str, dict]] = None

    def all(self) -> dict[str, dict]:
        if self._all is None:
            out = {}
            with self.db.connect() as conn:
                for r in conn.execute("SELECT * FROM photo_focus").fetchall():
                    out[r["name"]] = {"point": _pt(r["point"]), "faces": _pt(r["faces"]), "wide": _pt(r["wide"]), "tall": _pt(r["tall"]),
                                      "wide_fit": bool(r["wide_fit"]), "tall_fit": bool(r["tall_fit"])}
            self._all = out
        return self._all

    def get(self, name: str) -> dict:
        return self.all().get(name) or {"point": None, "faces": None, "wide": None, "tall": None, "wide_fit": False, "tall_fit": False}

    def stamp(self) -> str:
        return hashlib.sha1(json.dumps(self.all(), sort_keys=True).encode()).hexdigest()[:8]

    def set(self, name: str, **fields) -> dict:
        cur = dict(self.get(name))
        for k, v in fields.items():
            if k in ("wide_fit", "tall_fit"):
                cur[k] = bool(v)
            elif k in FOCUS_FIELDS:
                cur[k] = _clean_pt(v)
        with self.db.connect() as conn:
            conn.execute("INSERT INTO photo_focus (name, point, faces, wide, tall, wide_fit, tall_fit, updated) VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
                         "ON CONFLICT(name) DO UPDATE SET point = excluded.point, faces = excluded.faces, wide = excluded.wide, tall = excluded.tall, "
                         "wide_fit = excluded.wide_fit, tall_fit = excluded.tall_fit, updated = excluded.updated",
                         (name, _js(cur["point"]), _js(cur["faces"]), _js(cur["wide"]), _js(cur["tall"]),
                          int(cur["wide_fit"]), int(cur["tall_fit"]), datetime.now().isoformat(timespec="seconds")))
        self._all = None
        return cur

    @staticmethod
    def center(f: dict, shape: str) -> tuple[float, float]:
        """Where a crop of this shape centers: moved by hand, else the focal point, else the faces, else a bit above the middle."""
        return tuple(f.get(BASE.get(shape, shape)) or f.get("point") or f.get("faces") or DEFAULT_CENTER)

    @staticmethod
    def version(f: dict) -> str:
        """Short tag that changes whenever anything that affects the crops changes ('' = nothing set)."""
        if not f or not any(f.get(k) for k in FOCUS_FIELDS):
            return ""
        return hashlib.sha1(json.dumps([f.get(k) for k in FOCUS_FIELDS]).encode()).hexdigest()[:8]


def _pt(v):
    return json.loads(v) if v else None


def _js(v):
    return json.dumps(v) if v else None


def _clean_pt(v):
    if not v:
        return None
    x, y = float(v[0]), float(v[1])
    return [round(min(max(x, 0.0), 1.0), 4), round(min(max(y, 0.0), 1.0), 4)]


class PhotoLibrary:
    def __init__(self, folder: Path, cache_dir: Path, sources: Optional[list[dict]] = None,
                 http: Optional[httpx.Client] = None, focus: Optional[FocusStore] = None):
        self.folder = folder
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.sources = sources or []
        self.http = http or httpx.Client(timeout=60, follow_redirects=True, headers={"User-Agent": UA})
        self._local: dict[str, dict] = {}
        self._remote: dict[str, dict] = {}       # source id -> {"items": [...], "at": dt, "error": str}
        self._scanned_at: Optional[datetime] = None
        self._lock = Lock()
        self.focus = focus
        self.shapes = {"wide"}   # frame shapes seen; the background loop prepares photos for each

    # ---------- local folder ----------

    def adopt(self, old: "PhotoLibrary") -> None:
        """Settings were saved: carry over what the old library already knows instead of scanning again."""
        self._remote, self.shapes = old._remote, old.shapes
        if old.folder == self.folder:
            self._local, self._scanned_at = old._local, old._scanned_at

    def _load_info(self) -> dict:
        """Captions and sizes read before (kept in the cache folder, so a restart doesn't re-open every photo)."""
        try:
            return json.loads((self.cache_dir / "index.json").read_text())
        except (OSError, ValueError):
            return {}

    def _save_info(self, index: dict) -> None:
        try:
            tmp = self.cache_dir / "index.json.tmp"
            tmp.write_text(json.dumps({pid: {"caption": p["auto_caption"], "w": p["w"], "h": p["h"]} for pid, p in index.items()}))
            tmp.replace(self.cache_dir / "index.json")
        except OSError as exc:
            log.warning("couldn't save the photo index: %s", exc)

    def scan(self) -> list[dict]:
        with self._lock:
            captions = {}
            cap_file = self.folder / "captions.yaml"
            if cap_file.exists():
                captions = yaml.safe_load(cap_file.read_text()) or {}
            index = {}
            known = self._local or self._load_info()  # same file, same id: no need to open it again
            new = 0
            if self.folder.exists():
                for path in sorted(self.folder.rglob("*")):
                    if path.suffix.lower() not in EXTS or path.name.startswith("."):
                        continue
                    stat = path.stat()
                    pid = hashlib.sha1(f"{path}:{stat.st_mtime_ns}".encode()).hexdigest()[:16]
                    rel = path.relative_to(self.folder)
                    k = known.get(pid)
                    if k:
                        cap, w, h = k.get("auto_caption", k.get("caption", "")), k.get("w"), k.get("h")
                    else:
                        cap, w, h = self._exif_info(path)
                        new += 1
                    index[pid] = {"id": pid, "path": path, "source": rel.parts[0] if len(rel.parts) > 1 else "folder",
                                  "name": str(rel), "caption": captions.get(path.name) or cap, "auto_caption": cap, "w": w, "h": h}
            self._local = index
            self._scanned_at = datetime.now()
            if new or len(index) != len(known):
                self._save_info(index)
        self.refresh_remote()
        return self.listing()

    def maybe_rescan(self, minutes: int = 10) -> None:
        if not self._scanned_at or (datetime.now() - self._scanned_at).total_seconds() > minutes * 60:
            self.scan()

    # ---------- shared-album feeds ----------

    def refresh_remote(self, force: bool = False) -> None:
        now = datetime.now()
        for src in self.sources:
            sid = src["id"]
            state = self._remote.get(sid, {})
            if not force and state.get("at") and now - state["at"] < REMOTE_REFRESH:
                continue
            fetch = FETCHERS.get(src.get("kind"))
            if not fetch:
                continue
            try:
                items = fetch(src["url"])
                self._remote[sid] = {"items": items, "at": now, "error": None}
            except Exception as exc:
                log.warning("photo source %s failed: %s", src.get("label") or sid, exc)
                self._remote[sid] = {"items": state.get("items", []), "at": now, "error": str(exc)[:200]}
        live = {s["id"] for s in self.sources}
        for sid in list(self._remote):
            if sid not in live:
                del self._remote[sid]

    def source_status(self) -> list[dict]:
        out = []
        for src in self.sources:
            st = self._remote.get(src["id"], {})
            out.append({"id": src["id"], "count": len(st.get("items", [])), "error": st.get("error"),
                        "checked": st["at"].isoformat(timespec="minutes") if st.get("at") else None})
        return out

    def _remote_index(self) -> dict[str, dict]:
        out = {}
        labels = {s["id"]: s.get("label", "") for s in self.sources}
        for sid, st in self._remote.items():
            for it in st.get("items", []):
                pid = hashlib.sha1(it["key"].encode()).hexdigest()[:16]
                out[pid] = {"id": pid, "url": it["url"], "source": sid, "caption": labels.get(sid, "")}
        return out

    # ---------- listing + files ----------

    def focus_of(self, pid: str) -> dict:
        item = self._local.get(pid)
        return self.focus.get(item["name"]) if (self.focus and item) else {}

    def listing(self) -> list[dict]:
        """The slideshow: each photo's id and caption, plus "v" when it has a focal point or crop choices
        (the frame adds it to the address, so a changed crop is fetched fresh)."""
        focus = self.focus.all() if self.focus else {}
        items = []
        for p in {**self._local, **self._remote_index()}.values():
            it = {"id": p["id"], "caption": p["caption"]}
            v = FocusStore.version(focus.get(p.get("name"), {}))
            if v:
                it["v"] = v
            items.append(it)
        random.Random(datetime.now().strftime("%Y%m%d")).shuffle(items)  # new order each day
        return items

    def version(self) -> str:
        """Changes when the set of photos (or today's order, or a crop) changes, so the frame refetches the list."""
        ids = sorted({**self._local, **self._remote_index()})
        stamp = self.focus.stamp() if self.focus else ""
        return hashlib.sha1((datetime.now().strftime("%Y%m%d") + stamp + "|".join(ids)).encode()).hexdigest()[:12]

    def prepare_some(self, limit: int = 15) -> int:
        """Make screen-size copies ahead of time (in slideshow order, a few at a time) so the frame never waits."""
        made = 0
        for p in self.listing():
            for shape in sorted(self.shapes):
                if made >= limit:
                    return made
                if not self._cache_path(p["id"], shape).exists() and self.file_for(p["id"], shape=shape):
                    made += 1
        return made

    def admin_listing(self) -> list[dict]:
        """Newest first (file names start with the date taken), with each photo's size and focal point."""
        focus = self.focus.all() if self.focus else {}
        out = []
        for p in sorted(self._local.values(), key=lambda p: p["name"].rsplit("/", 1)[-1], reverse=True):
            f = focus.get(p["name"]) or {}
            out.append({"id": p["id"], "source": p["source"], "name": p["name"], "caption": p["caption"],
                        "w": p.get("w"), "h": p.get("h"), "focus": f or None, "v": FocusStore.version(f)})
        return out

    def _cache_path(self, pid: str, shape: str) -> Path:
        v = FocusStore.version(self.focus_of(pid))
        tag = {"wide": "", "tall": "-h", "wide-hd": "-x", "tall-hd": "-y", "thumb": "-t", "edit": "-e"}[shape]
        if v and shape != "edit":
            tag += f"-{v}" if shape != "wide" else f"-w-{v}"
        return self.cache_dir / f"{pid}{tag}.jpg"

    def drop_variants(self, pid: str) -> None:
        """A crop changed: forget the old copies (the plain wide one stays, it's the no-focal-point default)."""
        for pat in (f"{pid}-w-*.jpg", f"{pid}-h*.jpg", f"{pid}-x*.jpg", f"{pid}-y*.jpg", f"{pid}-t*.jpg"):
            for f in self.cache_dir.glob(pat):
                f.unlink(missing_ok=True)

    def file_for(self, pid: str, thumb: bool = False, shape: str = "wide") -> Optional[Path]:
        """The photo cropped to fill a wide or tall frame (or a small thumbnail, or the whole photo for
        the focal-point editor), made once and cached."""
        shape = "thumb" if thumb else shape
        item = self._local.get(pid) or self._remote_index().get(pid)
        if not item or shape not in ("thumb", "edit", *SHAPES):
            return None
        if shape in SHAPES:
            self.shapes.add(shape)
        out = self._cache_path(pid, shape)
        if out.exists():
            return out
        with _PREPARE:
            if out.exists():  # made while we waited
                return out
            try:
                if "path" in item:
                    im = Image.open(item["path"])
                else:
                    r = self.http.get(item["url"])
                    r.raise_for_status()
                    im = Image.open(io.BytesIO(r.content))
                with im:
                    # JPEGs decode at reduced size: far less memory and time. Big enough for either shape.
                    big = max(SHAPES[shape]) if shape in SHAPES else EDIT
                    im.draft("RGB", (big, big))
                    im = ImageOps.exif_transpose(im).convert("RGB")
                    f = self.focus_of(pid)
                    if shape == "edit":
                        im.thumbnail((EDIT, EDIT), Image.LANCZOS)
                    elif shape == "thumb":
                        im = render(im, "wide", f).resize(THUMB, Image.LANCZOS)
                    else:
                        im = render(im, shape, f)
                    tmp = out.with_suffix(".tmp")
                    small = shape in ("thumb", "edit")
                    im.save(tmp, "JPEG", quality=80 if small else 84, optimize=not small, progressive=not small)
                    tmp.replace(out)
            except Exception as exc:
                log.warning("couldn't prepare photo %s: %s", pid, exc)
                return None
        return out

    # ---------- uploads (admin panel, Mac favorites sync) ----------

    def save_upload(self, filename: str, data: bytes, sub: str = "uploads") -> str:
        if len(data) > MAX_UPLOAD:
            raise ValueError("That photo is over 40 MB.")
        try:
            with Image.open(io.BytesIO(data)) as im:
                im.verify()
        except Exception:
            raise ValueError(f"{filename} isn't a photo this frame can read (JPEG, PNG or WebP).")
        dest_dir = self.folder / _safe_sub(sub)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / stored_name(filename)
        dest.write_bytes(data)
        self._scanned_at = None
        return dest.name

    def remove(self, pid: str) -> bool:
        """Remove one photo from the frame's own folder (never from Google or iCloud)."""
        item = self._local.get(pid)
        if not item:
            return False
        item["path"].unlink(missing_ok=True)
        for f in self.cache_dir.glob(f"{pid}*.jpg"):
            f.unlink(missing_ok=True)
        self._scanned_at = None
        return True

    def prune(self, sub: str, keep: set[str]) -> int:
        """Mac sync: drop photos in photos/<sub>/ that are no longer favorites."""
        folder = self.folder / _safe_sub(sub)
        keep = {stored_name(k) for k in keep}  # same spelling the upload saved them under
        removed = 0
        if folder.exists():
            for p in folder.iterdir():
                if p.is_file() and p.suffix.lower() in EXTS and p.name not in keep:
                    p.unlink()
                    removed += 1
        self._scanned_at = None
        return removed

    @staticmethod
    def _exif_info(path: Path) -> tuple[str, Optional[int], Optional[int]]:
        """Caption ("October 2026" from the date taken) and the upright width and height. Reads only the header."""
        cap, w, h = "", None, None
        try:
            with Image.open(path) as im:
                w, h = im.size
                exif = im.getexif()
                if exif.get(274) in (5, 6, 7, 8):  # stored on its side
                    w, h = h, w
                raw = exif.get_ifd(0x8769).get(36867) or exif.get(306)  # DateTimeOriginal / DateTime
            if raw:
                y, m = int(raw[:4]), int(raw[5:7])
                cap = f"{MONTHS[m - 1]} {y}"
        except Exception:
            pass
        return cap, w, h


def render(im: Image.Image, shape: str, f: dict) -> Image.Image:
    """One frame's picture: cropped to fill around the focal point, or (if chosen for this shape)
    the whole photo on a soft, darkened, blurred copy of itself."""
    fw, fh = SHAPES[shape]
    w, h = im.size
    if f and f.get(f"{BASE[shape]}_fit") and abs(w / h - fw / fh) > 0.02:
        bg = ImageOps.fit(im, (fw // 20, fh // 20), Image.BILINEAR)          # tiny copy: blurring it costs nothing
        bg = bg.filter(ImageFilter.GaussianBlur(1.2)).resize((fw, fh), Image.BICUBIC)
        bg = Image.eval(bg, lambda v: int(v * 0.55))
        fg = im.copy()
        fg.thumbnail((fw, fh), Image.LANCZOS)
        bg.paste(fg, ((fw - fg.width) // 2, (fh - fg.height) // 2))
        return bg
    cx, cy = FocusStore.center(f or {}, shape)
    left, top, cw, ch = crop_rect(w, h, shape, cx, cy)
    box = (round(left * w), round(top * h), round((left + cw) * w), round((top + ch) * h))
    return im.crop(box).resize((fw, fh), Image.LANCZOS)


def stored_name(filename: str) -> str:
    """How an uploaded file is named on disk: safe characters, lower-case extension."""
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", Path(filename).stem).strip("-")[:80] or "photo"
    ext = Path(filename).suffix.lower()
    return stem + (ext if ext in EXTS else ".jpg")


def _safe_sub(sub: str) -> str:
    s = re.sub(r"[^a-z0-9-]+", "-", (sub or "uploads").lower()).strip("-")
    return s or "uploads"


def save_kid_photo(folder: Path, kid_id: str, data: bytes) -> str:
    """Square face photo for a kid's avatar. Returns a version stamp for cache-busting."""
    if len(data) > MAX_UPLOAD:
        raise ValueError("That photo is over 40 MB.")
    try:
        im = Image.open(io.BytesIO(data))
        im = ImageOps.exif_transpose(im).convert("RGB")
    except Exception:
        raise ValueError("That isn't a photo this frame can read (JPEG, PNG or WebP).")
    im = ImageOps.fit(im, (320, 320), Image.LANCZOS, centering=(0.5, 0.35))
    folder.mkdir(parents=True, exist_ok=True)
    im.save(folder / f"{_safe_sub(kid_id)}.jpg", "JPEG", quality=88)
    return hashlib.sha1(data).hexdigest()[:8]
