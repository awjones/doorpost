#!/usr/bin/env python3
"""Cruise ship tracker: pass on positions texted home from a phone on board.

A Shortcut on the traveler's phone sends an iMessage like "Ship spot: 22.68123, -74.48012" (see
docs/cruise-tracker.md, "A phone on board"). This reads the new ones from Messages on this Mac and posts
each to the frame's /api/trip/fix with the upload key. Nothing else in Messages is read or kept.

Needs Full Disk Access for whatever runs it (Messages' database is protected). cron usually has it.
Run every few minutes, e.g. crontab:
  */5 * * * * /usr/bin/python3 ~/doorpost/mac/trip-phone-relay.py >> ~/Library/Logs/doorpost-trip-relay.log 2>&1

Settings: ~/Library/Application Support/Doorpost/trip-relay.json (keep it chmod 600: it holds the upload key)
  {"frame_url": "http://doorpost.local:8090",
   "upload_token": "<Settings > Photos > upload key>",
   "from": ["+15555550123", "traveler@example.com"],     # the phone's iMessage addresses
   "only_host": "My-Mac"}                                 # optional: run on this Mac only (scutil --get LocalHostName)
"""
from __future__ import annotations

import json
import re
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

HOME = Path.home()
CONFIG = HOME / "Library/Application Support/Doorpost/trip-relay.json"
STATE = HOME / "Library/Application Support/Doorpost/trip-relay-state.json"
CHAT_DB = HOME / "Library/Messages/chat.db"
APPLE_EPOCH = datetime(2001, 1, 1, tzinfo=timezone.utc)
SPOT = re.compile(r"ship\s*spot\s*:?\s*(-?\d{1,2}(?:\.\d+)?)\s*,\s*(-?\d{1,3}(?:\.\d+)?)", re.I)
FIRST_LOOK_DAYS = 2   # the first run looks this far back


def log(msg: str) -> None:
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)


def spot(text: str):
    """(lat, lon) from a "Ship spot: lat, lon" message, or None."""
    m = SPOT.search(text or "")
    if not m:
        return None
    lat, lon = float(m.group(1)), float(m.group(2))
    return (lat, lon) if -90 <= lat <= 90 and -180 <= lon <= 180 and (lat, lon) != (0, 0) else None


def message_text(text, body) -> str:
    """Newer Messages keep some texts only in attributedBody (an archived NSAttributedString); the words are
    in it as plain UTF-8, which is all the pattern needs."""
    if text:
        return text
    return bytes(body).decode("utf-8", "ignore") if body else ""


def when(apple_date) -> datetime:
    d = int(apple_date or 0)
    return APPLE_EPOCH + (timedelta(microseconds=d / 1000) if d > 10**12 else timedelta(seconds=d))   # nanoseconds since 2001 (older: seconds)


def new_spots(db: Path, handles: list[str], after_rowid: int, since: datetime):
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        q = ",".join("?" * len(handles))
        rows = conn.execute(
            f"""SELECT m.ROWID, m.text, m.attributedBody, m.date FROM message m JOIN handle h ON m.handle_id = h.ROWID
                WHERE m.ROWID > ? AND m.is_from_me = 0 AND h.id IN ({q}) ORDER BY m.ROWID""",
            [after_rowid, *handles]).fetchall()
    finally:
        conn.close()
    out, last = [], after_rowid
    for rowid, text, body, date in rows:
        last = max(last, rowid)
        at = when(date)
        p = spot(message_text(text, body))
        if p and at >= since:
            out.append((rowid, p, at))
    return out, last


def post(cfg: dict, lat: float, lon: float, at: datetime) -> None:
    req = urllib.request.Request(cfg["frame_url"].rstrip("/") + "/api/trip/fix",
                                 data=json.dumps({"lat": lat, "lon": lon, "at": at.isoformat(timespec="seconds")}).encode(),
                                 headers={"Content-Type": "application/json", "X-Upload-Token": cfg["upload_token"]})
    urllib.request.urlopen(req, timeout=20).read()


def main() -> int:
    try:
        cfg = json.loads(CONFIG.read_text())
    except (OSError, ValueError) as exc:
        log(f"no settings at {CONFIG} ({exc})")
        return 1
    host = cfg.get("only_host")
    if host:
        here = subprocess.run(["/usr/sbin/scutil", "--get", "LocalHostName"], capture_output=True, text=True).stdout.strip()
        if here != host:
            return 0
    try:
        state = json.loads(STATE.read_text())
    except (OSError, ValueError):
        state = {}
    since = datetime.now(timezone.utc) - timedelta(days=FIRST_LOOK_DAYS)
    try:
        spots, last = new_spots(CHAT_DB, [str(h) for h in cfg.get("from") or []], int(state.get("last_rowid", 0)), since)
    except sqlite3.DatabaseError as exc:
        log(f"can't read Messages ({exc}); give whatever runs this Full Disk Access")
        return 1
    for rowid, (lat, lon), at in spots:
        try:
            post(cfg, lat, lon, at)
            log(f"passed on the position sent {at.astimezone():%a %-I:%M %p}")
        except urllib.error.HTTPError as exc:
            log(f"the frame said {exc.code} to the position sent {at.astimezone():%a %-I:%M %p}; skipping it")
        except (urllib.error.URLError, OSError) as exc:
            log(f"couldn't reach the frame ({exc}); will try again next run")
            last = rowid - 1   # come back to this one
            break
    if last != state.get("last_rowid"):
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps({"last_rowid": last, "updated": datetime.now().isoformat(timespec="seconds")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
