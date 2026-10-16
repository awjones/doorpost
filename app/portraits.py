"""Profile photos: one picture of each person, cropped square around their face (shown as a circle): their avatar on
the frame and the photo on their birthday card. Picked by hand in Settings > Family (Photos, Google Photos or a file),
or "use the initial" instead.

Where they come from:
- Apple Photos (the Mac's Favorites sync, scripts/apple-portraits.py): Photos already knows who is who, so the
  Mac picks the newest photo where that person is the only face and sends it with where the face is.
- Google Photos (app/google_photos.py): Google doesn't let apps see its face groups, so a parent picks a few
  recent photos of the person; the frame keeps the newest one with a single face in it.
- Settings: upload any photo by hand.

Each portrait is kept as <slug>.jpg (4:5, about 640x800) in DATA_DIR/portraits, with index.json saying where it
came from and when it was taken. A portrait chosen by hand or from Google isn't replaced by the Mac's automatic one.
"""
from __future__ import annotations

import io
import json
import logging
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from PIL import Image, ImageOps

log = logging.getLogger(__name__)

OUT_W, OUT_H = 720, 720          # square: shown as a circle (avatars, the birthday picture's round window)
FACE_SHARE = 0.42                # the face is about this much of the portrait's height
FACE_AT = 0.45                   # ...with its middle this far down
MAX_UPLOAD = 40 * 1024 * 1024
SOURCES = ("apple", "google", "upload")


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")[:40]


def people_of(settings) -> list[dict]:
    """Everyone who can have a birthday card: Settings' people (with nicknames) and the kids, once each."""
    out: dict[str, dict] = {}
    for p in settings.people or []:
        name = p if isinstance(p, str) else str(p.get("name", ""))
        aliases = [] if isinstance(p, str) else [str(a) for a in p.get("aliases", []) if a]
        bday = "" if isinstance(p, str) else str(p.get("birthday") or "")
        initial = False if isinstance(p, str) else bool(p.get("use_initial"))
        if name.strip():
            out.setdefault(slug(name), {"slug": slug(name), "name": name.strip(), "aliases": aliases, "kid": None, "birthday": bday,
                                        "use_initial": initial})
    for k in settings.kids:
        key = slug(k.name)
        if key in out:
            out[key]["kid"] = k.id
        else:
            out[key] = {"slug": key, "name": k.name, "aliases": [], "kid": k.id, "birthday": "", "use_initial": False}
    return list(out.values())


def match_person(text: str, people: list[dict]) -> Optional[dict]:
    """Which person a birthday title is about ("Child 1's 10th Birthday", "Birthday – Buddy", "🎂 Child 2 turns 8")."""
    t = (text or "").replace("’", "'").lower()
    best = None
    for p in people:
        for n in [p["name"]] + p["aliases"]:
            n = n.replace("’", "'").lower().strip()
            if n and re.search(r"(?<![a-z])" + re.escape(n) + r"(?![a-z])", t):
                if best is None or len(n) > best[0]:
                    best = (len(n), p)
    return best[1] if best else None


def is_family_birthday(title: str, people: list[dict]) -> Optional[dict]:
    """Whose birthday it is, when the title says it's one of ours ("Child 1's birthday", "Child 1 Example’s Birthday",
    "Birthday: Child 2", "Happy birthday, Buddy", "Buddy turns 6"); None for "Birthday party (Buddy)" or a friend's."""
    t = (title or "").replace("’", "'")
    for p in people:
        for n in [p["name"]] + p["aliases"]:
            n = re.escape(n.strip())
            if n and any(re.search(pat, t, re.I) for pat in (
                    rf"(?<![a-z]){n}(?:\s+[a-z]+)?'s\s+(?:\d+\w*\s+)?(?:birthday|bday|b-day)",
                    rf"(?:birthday|bday|b-day)\s*[:\-–—]\s*{n}(?![a-z])",
                    rf"happy\s+(?:birthday|bday),?\s+{n}(?![a-z])",
                    rf"(?<![a-z]){n}\s+turns\s+\d+")):
                return p
    return None


BIRTHDAY_WORDS = re.compile(r"(?i)\b(happy|birthday|bday|b-day|party|turns?|is|the|big|celebration|day)\b|\b\d+(st|nd|rd|th)?\b|['’]s\b|[^\w\s&'’-]")


def birthday_name(title: str, people: list[dict]) -> str:
    """The name for the birthday banner: the person it matches, else what's left of the title (e.g. "Grandma")."""
    p = match_person(title, people)
    if p:
        return p["name"]
    left = re.sub(r"\s+", " ", BIRTHDAY_WORDS.sub(" ", title or "")).strip(" -–—:")
    return left[:18]


# ---------------- faces ----------------

def detect_faces(im: Image.Image) -> list[tuple[float, float, float]]:
    """Faces as (x, y, size) fractions of the picture (middle of the face; size = face height / picture height).
    Uses OpenCV's frontal-face finder when it's installed; otherwise finds none."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        return []
    small = im.copy()
    small.thumbnail((900, 900))
    gray = cv2.cvtColor(np.asarray(small.convert("RGB")), cv2.COLOR_RGB2GRAY)
    finder = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    w, h = small.size
    found = finder.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=6, minSize=(max(24, w // 30), max(24, w // 30)))
    return [((x + fw / 2) / w, (y + fh / 2) / h, fh / h) for (x, y, fw, fh) in found]


def reconcile_face(im: Image.Image, given: Optional[tuple]) -> Optional[tuple]:
    """Fine-tune a face position (from Apple Photos) with the frame's own face finder: a face found right at Apple's
    spot gives an exact center and size. With no spot (uploads, Google), the biggest face found."""
    found = [f for f in detect_faces(im) if f[2] >= 0.04]
    if not found:
        return given
    if given:   # Apple knows whose face it is: only fine-tune to a face right there, never swap people
        near = min(found, key=lambda f: (f[0] - given[0]) ** 2 + (f[1] - given[1]) ** 2)
        return near if ((near[0] - given[0]) ** 2 + (near[1] - given[1]) ** 2) ** 0.5 < 0.12 else given
    return max(found, key=lambda f: f[2])


def portrait_crop(size: tuple[int, int], face: Optional[tuple[float, float, float]]) -> tuple[int, int, int, int]:
    """The square box (left, top, right, bottom) with the face at a pleasant size; the upper middle when there's no face."""
    W, H = size
    if face:
        fx, fy, fs = face
        ch = min(H, max(fs * H / FACE_SHARE, 0.25 * H))
        cx, cy = fx * W, fy * H + (0.5 - FACE_AT) * ch
    else:
        ch, cx, cy = H, W / 2, H / 2
    cw = ch * OUT_W / OUT_H
    if cw > W:
        cw, ch = W, W * OUT_H / OUT_W
    left = min(max(cx - cw / 2, 0), W - cw)
    top = min(max(cy - ch / 2, 0), H - ch)
    if not face:
        top = min(max(H * 0.38 - ch / 2, 0), H - ch)   # no face found: people's heads are usually in the upper part
    return round(left), round(top), round(left + cw), round(top + ch)


def open_image(data: bytes) -> Image.Image:
    try:   # iPhone photos often arrive as HEIC
        from pillow_heif import register_heif_opener
        register_heif_opener()
    except ImportError:
        pass
    if len(data) > MAX_UPLOAD:
        raise ValueError("That picture is over 40 MB.")
    try:
        return ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    except Exception:
        raise ValueError("That isn't a picture this frame can read (JPEG, PNG, HEIC or WebP).")


def best_portrait(candidates: list[tuple[Image.Image, str]]) -> Optional[tuple[Image.Image, str, Optional[tuple]]]:
    """From (picture, taken ISO time) pairs: the newest with exactly one good-sized face; else the newest with a
    face; else the newest. Returns (picture, taken, face)."""
    if not candidates:
        return None
    ranked = sorted(candidates, key=lambda c: c[1] or "", reverse=True)
    some_face = None
    for im, taken in ranked:
        faces = [f for f in detect_faces(im) if f[2] >= 0.06]
        if len(faces) == 1:
            return im, taken, faces[0]
        if faces and some_face is None:
            some_face = (im, taken, max(faces, key=lambda f: f[2]))
    return some_face or (ranked[0][0], ranked[0][1], None)


# ---------------- the store ----------------

class Portraits:
    def __init__(self, folder: Path):
        self.folder = folder
        self._lock = threading.Lock()

    @property
    def _index_path(self) -> Path:
        return self.folder / "index.json"

    def index(self) -> dict:
        try:
            return json.loads(self._index_path.read_text())
        except (OSError, ValueError):
            return {}

    def _write(self, idx: dict) -> None:
        self.folder.mkdir(parents=True, exist_ok=True)
        tmp = self._index_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(idx, indent=1))
        tmp.replace(self._index_path)

    def path(self, key: str) -> Optional[Path]:
        p = self.folder / f"{slug(key)}.jpg"
        return p if slug(key) and p.exists() else None

    def url(self, key: str) -> Optional[str]:
        info = self.index().get(slug(key))
        return f"portraits/{slug(key)}.jpg?v={info.get('v', 0)}" if info and self.path(key) else None

    def save(self, key: str, im: Image.Image, source: str, taken: str = "", face: Optional[tuple] = None,
             ref: str = "", auto: bool = False, extra: Optional[dict] = None) -> dict:
        """Crop around the face and keep it. auto=True (the Mac's sync) never replaces a hand-picked portrait."""
        key = slug(key)
        if not key or source not in SOURCES:
            raise ValueError("Unknown person or source.")
        with self._lock:
            idx = self.index()
            old = idx.get(key)
            if auto and old and old.get("source") != "apple":
                return {"ok": True, "kept": old.get("source")}
            face = reconcile_face(im, face)
            src = im.copy()
            src.thumbnail((1600, 1600))
            box = portrait_crop(im.size, face)
            out = im.crop(box).resize((OUT_W, OUT_H), Image.LANCZOS)
            self.folder.mkdir(parents=True, exist_ok=True)
            out.save(self.folder / f"{key}.jpg", "JPEG", quality=88)
            src.save(self.folder / f"{key}-src.jpg", "JPEG", quality=88)   # the whole photo, to crop again later
            info = {"source": source, "taken": taken or "", "ref": ref or "", "face": bool(face), "src": True,
                    "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "v": int((old or {}).get("v", 0)) + 1, **(extra or {})}
            idx[key] = info
            self._write(idx)
            return {"ok": True, **info}

    def rename(self, old: str, new: str) -> None:
        """Someone's name changed in Settings: their portrait follows them."""
        old, new = slug(old), slug(new)
        if not old or not new or old == new:
            return
        with self._lock:
            idx = self.index()
            src = self.folder / f"{old}.jpg"
            if src.exists() and not (self.folder / f"{new}.jpg").exists():
                src.replace(self.folder / f"{new}.jpg")
                if (self.folder / f"{old}-src.jpg").exists():
                    (self.folder / f"{old}-src.jpg").replace(self.folder / f"{new}-src.jpg")
                if old in idx:
                    idx[new] = idx.pop(old)
                self._write(idx)

    def remove(self, key: str) -> bool:
        key = slug(key)
        with self._lock:
            idx = self.index()
            p = self.folder / f"{key}.jpg"
            had = p.exists()
            if had:
                p.unlink()
            if (self.folder / f"{key}-src.jpg").exists():
                (self.folder / f"{key}-src.jpg").unlink()
            idx.pop(key, None)
            self._write(idx)
            return had
