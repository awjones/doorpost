"""Opening data saved by an older version (before art packs and the one Google sign-in), without losing anything.

The server calls upgrade() once at start, before it reads the settings. It only acts on a settings file that an
older version wrote (no "data_version" in it); a new install is stamped at once and never upgraded. What it does:

1. Keeps a copy of the old settings file next to it (settings.before-upgrade.json), once.
2. Google sign-in: google-photos.json is copied to google.json (the old file stays, so going back to the older
   version needs no change), and the client ID is copied from special_days.google_photos to google.
3. Art packs: older versions had every picture built in. The optional packs from the packs list (packs/index.json)
   that aren't here yet are installed, so the frame keeps showing the church days, the Sunday pictures, parks,
   trains, sports and the rest. They can be turned off or removed in Settings > Art packs afterwards.
4. Stamps the file with data_version, so this runs once.

Everything else an older version saved (settings keys, the database tables, photo folders, special-day pictures,
profile photos, frame profiles, the screen time log) is read as it is; tests/test_compat.py checks that with data
made by the old code.

`python -m app.compat <data folder>` reports what upgrade() would do, and which saved title words point at a
picture no pack has, without changing anything. Run it on a copy of a backup before updating.
"""
from __future__ import annotations

import json
import logging
import shutil
import sys
from pathlib import Path
from typing import Callable, Optional

log = logging.getLogger(__name__)

DATA_VERSION = 2
BACKUP_NAME = "settings.before-upgrade.json"


def _read(p: Path) -> dict:
    try:
        return json.loads(p.read_text() or "{}")
    except (OSError, ValueError):
        return {}


def is_old(store: dict) -> bool:
    """Written by a version before data_version existed (it always has the secrets it made on its first start)."""
    return bool(store) and "data_version" not in store


def _lists_in_use(data_dir: Path) -> bool:
    """The Mac's Reminders helper has sent lists. Older versions showed the Groceries list without a saved choice,
    so a setup like that has no 'lists' settings and would otherwise lose its Lists screen."""
    import sqlite3
    db = data_dir / "frame.db"
    if not db.exists():
        return False
    try:
        with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as conn:
            return bool(conn.execute("SELECT 1 FROM list_meta WHERE key IN ('available', 'synced_at') LIMIT 1").fetchone())
    except sqlite3.Error:
        return False


def plan(data_dir: Path, store: dict) -> list[str]:
    """What upgrade() would do, in plain words (nothing is changed)."""
    from . import pack_build, packs as P
    out = []
    if not is_old(store):
        return out
    out.append(f"Keep a copy of the settings as {BACKUP_NAME}.")
    if (data_dir / "google-photos.json").exists() and not (data_dir / "google.json").exists():
        out.append("Copy the Google sign-in google-photos.json to google.json (the old file stays).")
    cid = ((store.get("special_days") or {}).get("google_photos") or {}).get("client_id")
    if cid and not (store.get("google") or {}).get("client_id"):
        out.append("Copy the Google client ID to its new place in the settings.")
    if "lists" not in (store.get("modules") or {}) and _lists_in_use(data_dir):
        out.append("Turn on the Lists module (the Mac's Reminders helper is sending lists).")
    have = {p["id"] for p in P.load(False).all}
    for e in P.read_index():
        if e["id"] in pack_build.OPTIONAL and e["id"] not in have:
            out.append(f"Install the {e.get('name', e['id'])} art pack (older versions had its pictures built in).")
    return out


def upgrade(data_dir: Path, demo: bool, install: Optional[Callable[[str], dict]] = None) -> list[str]:
    """Bring an older version's data up to date (see the module notes). Returns what was done."""
    from . import config, pack_build, packs as P
    if demo:
        return []
    path = config.store_path(False)
    store = _read(path)
    if not path.exists():
        config.write_store({"data_version": DATA_VERSION}, False)   # a new install: nothing to upgrade, ever
        return []
    if not is_old(store):
        return []
    done = []
    backup = data_dir / BACKUP_NAME
    if not backup.exists():
        shutil.copy2(path, backup)
        done.append(f"Kept a copy of the old settings as {BACKUP_NAME}.")
    old_g, new_g = data_dir / "google-photos.json", data_dir / "google.json"
    if old_g.exists() and not new_g.exists():
        shutil.copy2(old_g, new_g)   # copy, not move: the older version still finds its file if you go back
        done.append("Copied the Google sign-in to google.json.")
    cid = ((store.get("special_days") or {}).get("google_photos") or {}).get("client_id")
    if cid and not (store.get("google") or {}).get("client_id"):
        store["google"] = dict(store.get("google") or {}, client_id=cid)
        done.append("Copied the Google client ID to settings 'google'.")
    if "lists" not in (store.get("modules") or {}) and _lists_in_use(data_dir):
        store["modules"] = dict(store.get("modules") or {}, lists=True)
        done.append("Turned on the Lists module (the Mac's Reminders helper is sending lists).")
    have = {p["id"] for p in P.load(False).all}
    installed = []
    for e in P.read_index():
        if e["id"] not in pack_build.OPTIONAL or e["id"] in have:
            continue
        try:
            (install or (lambda pid: P.install_from_index(pid, False)))(e["id"])
            installed.append(e["id"])
            done.append(f"Installed the {e.get('name', e['id'])} art pack.")
        except Exception as exc:  # noqa: BLE001  (never stop the frame from starting)
            log.warning("upgrade: could not install art pack %s: %s", e["id"], exc)
            done.append(f"Could not install the {e.get('name', e['id'])} art pack ({exc}); install it in Settings > Art packs.")
    if installed:
        ap = dict(store.get("art_packs") or {})
        ap["installed_on_upgrade"] = installed
        store["art_packs"] = ap
    store["data_version"] = DATA_VERSION
    config.write_store(store, False)
    for line in done:
        log.info("upgrade: %s", line)
    return done


def missing_pictures(store: dict) -> list[str]:
    """Saved title words whose picture no turned-on pack has (they would show the gold pattern)."""
    from . import packs as P
    from .special import slug
    scenes = P.load(False).scenes
    out = []
    for w in (store.get("special_days") or {}).get("words") or []:
        look = slug(str(w.get("look") or ""))
        if look and look not in scenes and look.replace("-", "") not in scenes:
            out.append(f"{w.get('word')} -> {look}")
    return out


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: python -m app.compat <data folder>   (reports only; changes nothing)")
        return 2
    import os
    data_dir = Path(argv[0]).resolve()
    os.environ["FRAME_DATA_DIR"] = str(data_dir)
    import importlib
    from . import config
    importlib.reload(config)
    from . import overlay
    store = _read(config.store_path(False))
    print(f"Data folder: {data_dir}")
    print(f"Settings written by: {'an older version' if is_old(store) else 'this version' if store else 'nothing yet'}")
    ov = overlay.summary()
    print(f"Private overlay: {ov['folder']}" + ("" if ov["present"] else " (none)"))
    if ov["present"]:
        print(f"  config: {', '.join(ov['config']) or 'none'}; packs: {', '.join(ov['packs']) or 'none'}; "
              f"web files: {len(ov['web'])}")
    steps = plan(data_dir, store)
    print("On the next start it will:" if steps else "Nothing to upgrade.")
    for s in steps:
        print(f"  - {s}")
    miss = missing_pictures(store)
    if miss:
        print("Title words whose picture no pack has here (they would show the gold pattern):")
        for m in miss:
            print(f"  - {m}")
        print("  (Packs this check can't see yet, like the optional ones above, are installed on the first start.)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
