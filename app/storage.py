"""Storage: how full the server's disk is, what Doorpost keeps on it, and what each frame reports.

Settings > Overview shows the disk that holds the data folder (and the photos folder, when that is a
different disk, as in the Home Assistant add-on: /data and /media). Folder sizes are counted in the
background and kept for a few minutes, so a big photo library isn't walked on every page load.

Frames send a small heartbeat every few minutes (web/js/app.js): screen size, browser, how much the
page itself stores, memory. A web page cannot see the frame's own disk, so that part is only shown
when the kiosk app reports it (the optional `device_storage` field).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from . import config

GB = 1024 ** 3
MB = 1024 ** 2
SIZES_MAX_AGE = 300        # seconds a folder count is reused
WAIT_FOR_COUNT = 3.0       # seconds a request waits for a fresh count before answering "counting"
HEARTBEAT_MAX = 8 * 1024   # bytes; a heartbeat is a few hundred


def level(total: int, free: int) -> str:
    """ok, amber (under 15% or 2 GB free) or red (under 5% or 500 MB free)."""
    if total <= 0:
        return "ok"
    pct = free / total
    if pct < 0.05 or free < 500 * MB:
        return "red"
    if pct < 0.15 or free < 2 * GB:
        return "amber"
    return "ok"


def disk(path: Path) -> Optional[dict]:
    """total, used, free (bytes) of the disk holding this folder."""
    p = Path(path)
    while not p.exists() and p != p.parent:
        p = p.parent
    try:
        u = shutil.disk_usage(p)
    except OSError:
        return None
    return {"path": str(path), "total": u.total, "used": u.used, "free": u.free,
            "free_pct": round(100 * u.free / u.total, 1) if u.total else 0, "level": level(u.total, u.free)}


def _device(path: Path) -> Optional[int]:
    p = Path(path)
    while not p.exists() and p != p.parent:
        p = p.parent
    try:
        return os.stat(p).st_dev
    except OSError:
        return None


def tree_size(path: Path, match: Optional[Callable[[str], bool]] = None, skip: tuple = ()) -> tuple[int, int]:
    """(bytes, files) under a folder, without following links. `skip`: folders not to count."""
    total = files = 0
    stack = [str(path)]
    skip_s = {str(s) for s in skip}
    while stack:
        d = stack.pop()
        try:
            it = os.scandir(d)
        except OSError:
            continue
        with it:
            for e in it:
                try:
                    if e.is_dir(follow_symlinks=False):
                        if e.path not in skip_s:
                            stack.append(e.path)
                    elif e.is_file(follow_symlinks=False) and (match is None or match(e.name)):
                        total += e.stat(follow_symlinks=False).st_size
                        files += 1
                except OSError:
                    continue
    return total, files


def _files_size(paths) -> tuple[int, int]:
    total = files = 0
    for p in paths:
        try:
            total += p.stat().st_size
            files += 1
        except OSError:
            pass
    return total, files


# What each line of the breakdown is, in the order shown.
LABELS = {
    "photos": ("Photos", "The slideshow's own copies: uploads and the Mac's Favorites sync. Albums from Google or iCloud are not stored here."),
    "photo_cache": ("Prepared photos", "Each photo cropped to the frame's size. Safe to clear: the server makes them again when needed."),
    "special": ("Special-day photos", "Pictures uploaded in Settings > Special days."),
    "profile": ("Profile photos", "Kids' faces and birthday portraits."),
    "packs": ("Art packs", "Downloaded special-day picture packs."),
    "database": ("Database and settings", "Chores, screen time, focal points and your settings."),
    "caches": ("Calendar copies and logs", "Recent copies of your calendars, read again every few minutes."),
    "other": ("Everything else", "Anything else in the data folder."),
}


def measure(data_dir: Path, photos_dir: Path, cache_dir: Path) -> dict:
    """Count every part of Doorpost's storage once (can take a while on a big photo folder)."""
    data_dir, photos_dir, cache_dir = Path(data_dir).resolve(), Path(photos_dir).resolve(), Path(cache_dir).resolve()
    parts: dict[str, tuple[int, int]] = {}
    jpg = lambda n: n.endswith(".jpg") or n.endswith(".tmp")   # noqa: E731
    parts["photos"] = tree_size(photos_dir, skip=(cache_dir,)) if photos_dir.exists() else (0, 0)
    parts["photo_cache"] = tree_size(cache_dir, match=jpg) if cache_dir.exists() else (0, 0)
    parts["special"] = tree_size(data_dir / "special-photos")
    k, kf = tree_size(data_dir / "kid-photos")
    p, pf = tree_size(data_dir / "portraits")
    parts["profile"] = (k + p, kf + pf)
    parts["packs"] = tree_size(data_dir / "packs")
    top = [f for f in data_dir.glob("*") if f.is_file()] if data_dir.exists() else []
    parts["database"] = _files_size([f for f in top if re.search(r"\.(db|db-wal|db-shm|json)$", f.name)])
    c1, f1 = _files_size([f for f in top if f.name.endswith(".log")])
    c2, f2 = tree_size(data_dir / "calendar-cache")
    c3, f3 = tree_size(data_dir / "calendar-cache-test")
    c4, f4 = tree_size(data_dir / "logs")
    parts["caches"] = (c1 + c2 + c3 + c4, f1 + f2 + f3 + f4)
    # The rest of the data folder (index files, anything new). The photos folder is skipped when it lives inside it.
    all_bytes, all_files = tree_size(data_dir, skip=(photos_dir,)) if data_dir.exists() else (0, 0)
    counted = [v for key, v in parts.items() if key != "photos"]   # never part of all_bytes
    parts["other"] = (max(0, all_bytes - sum(b for b, _ in counted)), max(0, all_files - sum(n for _, n in counted)))
    items = [{"key": key, "label": LABELS[key][0], "note": LABELS[key][1], "bytes": b, "files": n,
              "clearable": key == "photo_cache"} for key, (b, n) in parts.items()]
    return {"items": items, "total": sum(i["bytes"] for i in items), "at": time.time()}


class SizeCache:
    """Folder sizes, counted in a background thread and reused for SIZES_MAX_AGE seconds."""

    def __init__(self):
        self.lock = threading.Lock()
        self.value: Optional[dict] = None
        self.key: Optional[tuple] = None
        self.thread: Optional[threading.Thread] = None

    def invalidate(self) -> None:
        with self.lock:
            if self.value:
                self.value = dict(self.value, at=0)

    def get(self, data_dir: Path, photos_dir: Path, cache_dir: Path, wait: float = WAIT_FOR_COUNT) -> Optional[dict]:
        key = (str(data_dir), str(photos_dir), str(cache_dir))
        with self.lock:
            fresh = self.value and self.key == key and time.time() - self.value["at"] < SIZES_MAX_AGE
            if fresh:
                return self.value
            if not (self.thread and self.thread.is_alive()):
                self.thread = threading.Thread(target=self._run, args=(key,), daemon=True)
                self.thread.start()
            thread = self.thread
        thread.join(wait)
        with self.lock:
            # A finished count, or the last one we had (marked stale) while a new one runs.
            return self.value if self.value and self.key == key else None

    def _run(self, key: tuple) -> None:
        try:
            v = measure(Path(key[0]), Path(key[1]), Path(key[2]))
        except Exception:  # never let a bad folder break Settings
            return
        with self.lock:
            self.value, self.key = v, key


SIZES = SizeCache()


def server_report(data_dir: Path, photos_dir: Path, cache_dir: Path) -> dict:
    d = disk(data_dir)
    photos_disk = None
    if _device(photos_dir) is not None and _device(photos_dir) != _device(data_dir):
        photos_disk = disk(photos_dir)
    sizes = SIZES.get(data_dir, photos_dir, cache_dir)
    levels = [x["level"] for x in (d, photos_disk) if x]
    worst = "red" if "red" in levels else "amber" if "amber" in levels else "ok"
    return {"disk": d, "photos_disk": photos_disk, "breakdown": sizes, "counting": sizes is None,
            "level": worst, "demo": False}


def clear_photo_cache(cache_dir: Path) -> dict:
    """Remove the prepared (cropped) photos. Regenerable only: the originals, the photo list
    (index.json) and the focal points are never touched. Waits for any photo being made."""
    from .photos import _PREPARE
    freed = count = 0
    cache_dir = Path(cache_dir)
    with _PREPARE:
        if cache_dir.exists():
            for f in cache_dir.iterdir():
                if f.is_file() and f.suffix in (".jpg", ".tmp"):
                    try:
                        size = f.stat().st_size
                        f.unlink()
                        freed += size
                        count += 1
                    except OSError:
                        pass
    SIZES.invalidate()
    return {"freed": freed, "files": count}


# ---------------- frame heartbeats ----------------

class Heartbeats:
    """The latest heartbeat from each frame, kept in memory and in a small JSON file."""

    def __init__(self):
        self.lock = threading.Lock()
        self.data: dict[str, dict] = {}
        self.path: Optional[Path] = None

    def _file(self, demo: bool) -> Path:
        return config.DATA_DIR / ("frame-heartbeats.demo.json" if demo else "frame-heartbeats.json")

    def load(self, demo: bool) -> dict[str, dict]:
        path = self._file(demo)
        with self.lock:
            if self.path != path:
                self.path = path
                try:
                    self.data = json.loads(path.read_text())
                except (OSError, ValueError):
                    self.data = {}
            return dict(self.data)

    def save(self, fid: str, beat: dict, demo: bool) -> None:
        self.load(demo)
        with self.lock:
            self.data[fid] = beat
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                tmp = self.path.with_suffix(".tmp")
                tmp.write_text(json.dumps(self.data))
                tmp.replace(self.path)
            except OSError:
                pass  # the in-memory copy is enough to show it


HEARTBEATS = Heartbeats()


def _num(v: Any, hi: float = 1e15) -> Optional[float]:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f or f < 0 or f > hi:
        return None
    return int(f) if f == int(f) else round(f, 2)


def _str(v: Any, n: int = 200) -> Optional[str]:
    return str(v)[:n] if isinstance(v, str) and v else None


def browser_name(ua: str) -> str:
    """A short name for a user agent: 'Chrome 106 on Android 6.0'."""
    if not ua:
        return ""
    m = re.search(r"(?:Chrome|CriOS)/(\d+)", ua)
    name = f"Chrome {m.group(1)}" if m else ("Safari" if "Safari" in ua else "Browser")
    if "; wv)" in ua or " wv" in ua:
        name += " WebView"
    a = re.search(r"Android ([\d.]+)", ua)
    osn = f"Android {a.group(1)}" if a else "Mac" if "Macintosh" in ua else "Windows" if "Windows" in ua \
        else "iPhone or iPad" if re.search(r"iPhone|iPad", ua) else "Linux" if "Linux" in ua else ""
    return name + (f" on {osn}" if osn else "")


def clean_heartbeat(body: dict, now: float) -> dict:
    """Only known fields, only sane values: anyone on the network can call this."""
    sc = body.get("screen") if isinstance(body.get("screen"), dict) else {}
    stg = body.get("storage") if isinstance(body.get("storage"), dict) else {}
    heap = body.get("heap") if isinstance(body.get("heap"), dict) else {}
    dev = body.get("device_storage") if isinstance(body.get("device_storage"), dict) else {}
    ua = _str(body.get("ua"), 300) or ""
    out = {
        "at": now,
        "screen": {"w": _num(sc.get("w"), 20000), "h": _num(sc.get("h"), 20000), "dpr": _num(sc.get("dpr"), 10),
                   "orientation": _str(sc.get("orientation"), 40)},
        "ua": ua, "browser": browser_name(ua),
        "storage": ({"usage": _num(stg.get("usage")), "quota": _num(stg.get("quota"))} if stg else None),
        "device_memory_gb": _num(body.get("device_memory"), 1024),
        "heap": ({"used": _num(heap.get("used")), "limit": _num(heap.get("limit"))} if heap else None),
        "photo_ms": _num(body.get("photo_ms"), 600000),
        "uptime_s": _num(body.get("uptime_s"), 1e9),
        # For later: the kiosk app may report the frame's own disk (bytes). A web page can't see it.
        "device_storage": ({"total": _num(dev.get("total")), "free": _num(dev.get("free"))} if dev else None),
    }
    if out["device_storage"] and out["device_storage"]["total"] and out["device_storage"]["free"] is not None:
        out["device_storage"]["level"] = level(out["device_storage"]["total"], out["device_storage"]["free"])
    return out


def heartbeat_view(beat: Optional[dict], now: float) -> Optional[dict]:
    if not beat:
        return None
    return dict(beat, ago=max(0, int(now - beat.get("at", now))))


# ---------------- demo ----------------

def demo_report() -> dict:
    """A Raspberry Pi with a 32 GB card, getting full: the warning shows on the Overview page."""
    total = int(29.1 * GB)       # a "32 GB" card after formatting
    free = int(3.6 * GB)
    items = [("photos", int(2.31 * GB), 1184), ("photo_cache", int(412 * MB), 2950), ("special", int(46 * MB), 9),
             ("profile", int(5.8 * MB), 12), ("packs", int(88 * MB), 2), ("database", int(3.4 * MB), 6),
             ("caches", int(1.2 * MB), 7), ("other", int(0.3 * MB), 3)]
    rows = [{"key": k, "label": LABELS[k][0], "note": LABELS[k][1], "bytes": b, "files": n, "clearable": k == "photo_cache"}
            for k, b, n in items]
    d = {"path": "/home/pi/doorpost/data", "total": total, "used": total - free, "free": free,
         "free_pct": round(100 * free / total, 1), "level": level(total, free)}
    return {"disk": d, "photos_disk": None, "counting": False, "level": d["level"], "demo": True,
            "breakdown": {"items": rows, "total": sum(r["bytes"] for r in rows), "at": time.time()}}


DEMO_UA = ("Mozilla/5.0 (Linux; Android 6.0.1; Frame Build/MOB31T; wv) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Version/4.0 Chrome/106.0.5249.126 Safari/537.36")


def demo_heartbeat(now: float) -> dict:
    return clean_heartbeat({"screen": {"w": 1280, "h": 800, "dpr": 1, "orientation": "landscape-primary"},
                            "ua": DEMO_UA, "storage": {"usage": 412000, "quota": 1180000000},
                            "device_memory": 2, "heap": {"used": 19400000, "limit": 268435456},
                            "photo_ms": 640, "uptime_s": 3 * 86400 + 4 * 3600}, now - 95)


# ---------------- routes ----------------

def make_routers(require_admin, svc) -> list[APIRouter]:
    """Built by app.main (which owns the sign-in checks), once per app."""
    from . import frames as frame_profiles

    admin = APIRouter(prefix="/api/admin", dependencies=[Depends(require_admin)])
    public = APIRouter()

    def frame_beats(s) -> dict:
        now = time.time()
        beats = HEARTBEATS.load(s.settings.demo)
        out = {}
        for i, p in enumerate(frame_profiles.profiles(s.settings)):
            b = beats.get(p["id"])
            if not b and s.settings.demo and i == 0:
                b = demo_heartbeat(now)
            out[p["id"]] = heartbeat_view(b, now)
        return out

    @admin.get("/storage")
    def storage(s=Depends(svc)):
        if s.settings.demo:
            rep = demo_report()
        else:
            rep = server_report(config.DATA_DIR, s.photos.folder, s.photos.cache_dir)
        rep["frames"] = frame_beats(s)
        rep["warn_at"] = {"amber": "under 15% or 2 GB free", "red": "under 5% or 500 MB free"}
        return rep

    @admin.post("/storage/clear-photo-cache")
    def clear_cache(s=Depends(svc)):
        if s.settings.demo:
            return {"freed": 0, "files": 0, "demo": True}
        return clear_photo_cache(s.photos.cache_dir)

    @public.post("/api/frame/heartbeat")
    async def heartbeat(request: Request, frame: str = "", s=Depends(svc)):
        raw = await request.body()
        if len(raw) > HEARTBEAT_MAX:
            raise HTTPException(413, "Too big")
        try:
            body = json.loads(raw or b"{}")
        except ValueError:
            raise HTTPException(400, "Not JSON")
        if not isinstance(body, dict):
            raise HTTPException(400, "Not JSON")
        prof = frame_profiles.get(s.settings, frame or _str(body.get("frame"), 40))
        HEARTBEATS.save(prof["id"], clean_heartbeat(body, time.time()), s.settings.demo)
        return {"ok": True}

    return [admin, public]
