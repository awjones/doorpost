"""Cruise ship tracker: follow a family member's cruise ship on a map for the days of a trip
(Settings > Cruise ship tracker). The map covers the Caribbean, the Gulf of Mexico and the Bahamas.

The module is on only for an occasion: Settings > Modules turns it on, and the trip's own dates
(`show_from`..`show_until`) decide when the frame shows it. Outside those dates nothing shows and
no position is fetched.

Where the ship is comes from AIS, the position radio every big ship sends. The main source is the
ship's public page on CruiseMapper.com (`page_url`), which carries the latest position and how old
it is; robots.txt allows those pages. It's read about once an hour, day and night (the ship sails
overnight and the whole route is kept), at a different minute each time (up to 15 minutes either side of the hour). If that fails and an
AISStream.io key is saved, AISStream is tried as a backup (a WebSocket stream filtered to the
ship's MMSI; its land receivers often miss the ship, even in Miami). When the last real position is
old, the frame shows an estimate from the itinerary and says so.

Saved:
  store["trip"]                       the trip (name, ship, dates, ports)
  store["secrets"]["aisstream_key"]   the AISStream key (never sent back to the browser)
  data/trip-track.json                every position heard, with its time (and `since` when the ship sat in one
                                      spot over several checks), kept for the line and for replaying the week
  data/trip-track-<mmsi>.json         an earlier ship's line, set aside when the ship is changed
"""
from __future__ import annotations

import base64
import json
import logging
import math
import os
import random
import re
import socket
import ssl
import struct
import threading
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
import urllib.error
import urllib.request

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from . import searoute
from .config import DATA_DIR, read_store, write_store

log = logging.getLogger("family_frame.trip")

AIS_URL = "wss://stream.aisstream.io/v0/stream"
LIVE_HOURS = 3          # a position newer than this is "live"; older ones get an estimate beside them
IN_PORT_KM = 6          # stopped this close to a known port = in port
TRACK_MAX = 2000
CM_PREFIX = "https://www.cruisemapper.com/ships/"
CM_AGENT = "Doorpost/2.0 (home photo frame; one ship, hourly)"
WINDOW = None           # (6, 21) would check only 6 AM to 9 PM frame time; None = round the clock
JITTER_MIN = 15         # ...at up to 15 minutes either side of the hour

# The map (web/img/caribbean.svg, scripts/make-caribbean-map.py): x=(lon-LON0)*K*S, y=(LAT1-lat)*S
MAP = {"lon0": -98.0, "lon1": -58.0, "lat0": 8.0, "lat1": 33.0, "k": math.cos(math.radians(22)), "s": 30.0}

# Cruise ports in the Caribbean, the Bahamas, the Gulf and Florida: (key, name, place, lat, lon)
PORTS = [
    ("miami", "Miami", "Florida", 25.774, -80.170),
    ("fort-lauderdale", "Fort Lauderdale", "Florida", 26.093, -80.117),
    ("port-canaveral", "Port Canaveral", "Florida", 28.408, -80.623),
    ("tampa", "Tampa", "Florida", 27.940, -82.445),
    ("key-west", "Key West", "Florida", 24.556, -81.808),
    ("galveston", "Galveston", "Texas", 29.310, -94.793),
    ("new-orleans", "New Orleans", "Louisiana", 29.940, -90.060),
    ("cococay", "Perfect Day at CocoCay", "The Bahamas", 25.818, -77.941),
    ("nassau", "Nassau", "The Bahamas", 25.081, -77.344),
    ("freeport", "Freeport", "The Bahamas", 26.517, -78.770),
    ("bimini", "Bimini", "The Bahamas", 25.700, -79.297),
    ("half-moon-cay", "Half Moon Cay", "The Bahamas", 24.578, -75.952),
    ("grand-turk", "Grand Turk", "Turks and Caicos", 21.433, -71.153),
    ("cozumel", "Cozumel", "Mexico", 20.497, -86.965),
    ("costa-maya", "Costa Maya", "Mexico", 18.715, -87.708),
    ("progreso", "Progreso", "Mexico", 21.330, -89.670),
    ("roatan", "Roatán", "Honduras", 16.370, -86.420),
    ("belize-city", "Belize City", "Belize", 17.490, -88.185),
    ("grand-cayman", "George Town", "Grand Cayman", 19.294, -81.385),
    ("montego-bay", "Montego Bay", "Jamaica", 18.475, -77.928),
    ("falmouth", "Falmouth", "Jamaica", 18.494, -77.655),
    ("ocho-rios", "Ocho Rios", "Jamaica", 18.410, -77.105),
    ("labadee", "Labadee", "Haiti", 19.786, -72.244),
    ("amber-cove", "Amber Cove", "Dominican Republic", 19.858, -70.713),
    ("puerto-plata", "Puerto Plata", "Dominican Republic", 19.803, -70.694),
    ("san-juan", "San Juan", "Puerto Rico", 18.461, -66.110),
    ("st-thomas", "St. Thomas", "U.S. Virgin Islands", 18.335, -64.925),
    ("st-maarten", "Philipsburg", "St. Maarten", 18.017, -63.045),
    ("st-kitts", "Basseterre", "St. Kitts", 17.295, -62.720),
    ("antigua", "St. John’s", "Antigua", 17.124, -61.849),
    ("st-lucia", "Castries", "St. Lucia", 14.015, -60.995),
    ("barbados", "Bridgetown", "Barbados", 13.106, -59.630),
    ("aruba", "Oranjestad", "Aruba", 12.519, -70.039),
    ("curacao", "Willemstad", "Curaçao", 12.106, -68.934),
    ("bonaire", "Kralendijk", "Bonaire", 12.150, -68.277),
    ("cartagena", "Cartagena", "Colombia", 10.407, -75.535),
    ("havana", "Havana", "Cuba", 23.141, -82.351),
]
PORT_BY_KEY = {p[0]: p for p in PORTS}

DEFAULTS = {
    "name": "Where’s the ship?",
    "traveler": "Traveler",   # who's on board, as the map labels them
    "ship": "",
    "mmsi": "",         # the ship's 9-digit AIS number (only the AISStream backup needs it)
    "page_url": "",     # the ship's CruiseMapper page, https://www.cruisemapper.com/ships/<Ship-Name>-<id>
    "show_from": "",    # nothing shows until the trip's dates are set
    "show_until": "",
    "check_minutes": 10,
    "ports": [],   # one row per stop: {"day", "port" (a PORTS key), "arrive", "depart", "note"}; days without a row are at sea
}


# ---------------- settings ----------------

def config(store: dict) -> dict:
    raw = store.get("trip") or {}
    out = {k: raw.get(k, v) for k, v in DEFAULTS.items()}
    out["ports"] = [_clean_row(r) for r in (raw.get("ports") if "ports" in raw else DEFAULTS["ports"]) or []]
    out["ports"].sort(key=lambda r: (r["day"], r["arrive"] or r["depart"] or ""))
    return out


def _clean_row(r: dict) -> dict:
    return {"day": str(r.get("day") or "")[:10], "port": str(r.get("port") or ""), "arrive": str(r.get("arrive") or "")[:5],
            "depart": str(r.get("depart") or "")[:5], "note": str(r.get("note") or "")[:60]}


def api_key(store: dict) -> str:
    return (store.get("secrets") or {}).get("aisstream_key") or os.environ.get("AISSTREAM_KEY", "")


def showing(cfg: dict, today: date) -> bool:
    try:
        return date.fromisoformat(cfg["show_from"]) <= today <= date.fromisoformat(cfg["show_until"])
    except (TypeError, ValueError):
        return False


# ---------------- the track (positions heard) ----------------

def _track_path(demo: bool) -> Path:
    return DATA_DIR / ("trip-track.demo.json" if demo else "trip-track.json")


def read_track(demo: bool) -> dict:
    try:
        return json.loads(_track_path(demo).read_text())
    except (OSError, ValueError):
        return {"mmsi": "", "fixes": [], "last_try": None, "last_error": None, "destination": ""}


def _write_track(demo: bool, t: dict) -> None:
    p = _track_path(demo)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(t))
    tmp.replace(p)


# ---------------- AISStream (a tiny WebSocket client, so the Pi needs no new package) ----------------

class AisError(Exception):
    pass


def _ws_open(url: str, timeout: float) -> ssl.SSLSocket:
    u = urlparse(url)
    log.info("trip check: looking up %s", u.hostname)
    addrs = socket.getaddrinfo(u.hostname, u.port or 443, socket.AF_INET, socket.SOCK_STREAM)   # IPv4: the Pi has no IPv6 route
    log.info("trip check: connecting to %s", addrs[0][4][0])
    raw = socket.create_connection(addrs[0][4][:2], timeout=timeout)
    sock = ssl.create_default_context().wrap_socket(raw, server_hostname=u.hostname)
    log.info("trip check: connected")
    key = base64.b64encode(os.urandom(16)).decode()
    sock.sendall((f"GET {u.path or '/'} HTTP/1.1\r\nHost: {u.hostname}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                  f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\nUser-Agent: doorpost-frame\r\n\r\n").encode())
    head = b""
    while b"\r\n\r\n" not in head:
        chunk = sock.recv(1024)
        if not chunk:
            raise AisError("AISStream closed the connection")
        head += chunk
        if len(head) > 16384:
            raise AisError("AISStream sent an unexpected answer")
    status = head.split(b"\r\n", 1)[0].decode(errors="replace")
    if " 101 " not in status + " ":
        raise AisError(f"AISStream answered {status}")
    sock._ws_extra = head.split(b"\r\n\r\n", 1)[1]   # type: ignore[attr-defined]
    return sock


def _ws_send(sock, text: str, opcode: int = 1) -> None:
    data = text.encode()
    mask = os.urandom(4)
    n = len(data)
    head = bytes([0x80 | opcode]) + (bytes([0x80 | n]) if n < 126 else bytes([0x80 | 126]) + struct.pack(">H", n) if n < 65536
                                     else bytes([0x80 | 127]) + struct.pack(">Q", n))
    sock.sendall(head + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))


class _Reader:
    def __init__(self, sock, deadline: float):
        self.sock, self.buf, self.deadline = sock, getattr(sock, "_ws_extra", b""), deadline

    def _need(self, n: int) -> bytes:
        while len(self.buf) < n:
            left = self.deadline - time.time()   # the server's pings must not keep a check open past its time
            if left <= 0:
                raise TimeoutError("trip check: time is up")
            self.sock.settimeout(max(0.5, left))
            chunk = self.sock.recv(65536)
            if not chunk:
                raise AisError("AISStream closed the stream")
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def message(self) -> tuple[int, bytes]:
        parts, first_op = [], None
        while True:
            b1, b2 = self._need(2)
            fin, op, n = b1 & 0x80, b1 & 0x0F, b2 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._need(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._need(8))[0]
            mask = self._need(4) if b2 & 0x80 else None
            data = self._need(n)
            if mask:
                data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
            if op == 9:      # ping
                _ws_send(self.sock, data.decode(errors="replace"), opcode=10)
                self.pings = getattr(self, "pings", 0) + 1
                continue
            if op == 10:
                continue
            if op == 8:
                reason = data[2:].decode(errors="replace") if len(data) > 2 else ""
                raise AisError("AISStream closed the stream" + (f": {reason}" if reason else ""))
            if op != 0:
                first_op = op
            parts.append(data)
            if fin:
                return first_op or 1, b"".join(parts)


def _ais_time(meta: dict) -> str:
    t = str(meta.get("time_utc") or "")
    try:   # "2027-03-04 19:20:01.123456789 +0000 UTC"
        d = datetime.strptime(t[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        d = datetime.now(timezone.utc)
    return d.isoformat(timespec="seconds")


def fetch_position(key: str, mmsi: str, wait_seconds: float = 215) -> tuple[Optional[dict], str]:
    """One position (and the ship's AIS destination if heard), or None when nothing came in time."""
    if not key:
        raise AisError("No AISStream key yet. Add one in Settings > Cruise ship tracker.")
    sock = _ws_open(AIS_URL, timeout=45)   # AISStream sometimes takes 20+ s to answer the connection
    dest = ""
    try:
        _ws_send(sock, json.dumps({"APIKey": key, "BoundingBoxes": [[[-90, -180], [90, 180]]],
                                   "FiltersShipMMSI": [str(mmsi)],
                                   "FilterMessageTypes": ["PositionReport", "ShipStaticData"]}))
        log.info("trip check: listening for MMSI %s for up to %d s", mmsi, wait_seconds)
        end = time.time() + wait_seconds
        r = _Reader(sock, end)
        heard = 0
        while time.time() < end:
            try:
                _op, data = r.message()
            except (socket.timeout, TimeoutError):
                break
            except AisError as exc:
                if not heard and "closed" in str(exc):
                    raise AisError("AISStream closed the stream right away. Check the AISStream key in Settings > Cruise ship tracker.")
                raise
            heard += 1
            try:
                m = json.loads(data)
            except ValueError:
                continue
            if m.get("error"):
                raise AisError(f"AISStream: {m['error']}")
            kind, meta, body = m.get("MessageType"), m.get("MetaData") or {}, (m.get("Message") or {})
            log.info("trip check: heard %s", kind)
            if kind == "ShipStaticData":
                dest = str((body.get("ShipStaticData") or {}).get("Destination") or "").strip()
                continue
            if kind == "PositionReport":
                pr = body.get("PositionReport") or {}
                lat, lon = pr.get("Latitude", meta.get("latitude")), pr.get("Longitude", meta.get("longitude"))
                if lat is None or lon is None or abs(lat) > 90 or abs(lon) > 180:
                    continue
                sog = pr.get("Sog")
                return ({"lat": round(float(lat), 5), "lon": round(float(lon), 5),
                         "sog": None if sog is None or sog >= 102.3 else round(float(sog), 1),
                         "cog": pr.get("Cog"), "nav": pr.get("NavigationalStatus"), "at": _ais_time(meta)}, dest)
        log.info("trip check: nothing from the ship in %d s (%d messages, %d pings)", wait_seconds, heard, getattr(r, "pings", 0))
        return None, dest
    finally:
        try:
            _ws_send(sock, "", opcode=8)
            sock.close()
        except OSError:
            pass


def feed_test(key: str, seconds: float = 25, box=((24.0, -81.5), (27.0, -78.5)), mmsi: Optional[list] = None) -> dict:
    """Is the feed working at all? Every ship's position near Miami for a few seconds, no ship filter."""
    if not key:
        raise AisError("No AISStream key yet.")
    sock = _ws_open(AIS_URL, timeout=45)
    out = {"messages": 0, "positions": 0, "ships": {}, "seconds": seconds, "error": None, "first": None}
    try:
        sub = {"APIKey": key, "BoundingBoxes": [[list(box[0]), list(box[1])]], "FilterMessageTypes": ["PositionReport"]}
        if mmsi:
            sub["FiltersShipMMSI"] = [str(x) for x in mmsi]
            sub["BoundingBoxes"] = [[[-90, -180], [90, 180]]]
        _ws_send(sock, json.dumps(sub))
        end = time.time() + seconds
        r = _Reader(sock, end)
        while time.time() < end:
            try:
                _op, data = r.message()
            except (socket.timeout, TimeoutError):
                break
            out["messages"] += 1
            try:
                m = json.loads(data)
            except ValueError:
                continue
            if out["first"] is None:
                out["first"] = m.get("MessageType") or m.get("error")
            if m.get("error"):
                out["error"] = m["error"]
                break
            if m.get("MessageType") == "PositionReport":
                out["positions"] += 1
                meta = m.get("MetaData") or {}
                if len(out["ships"]) < 40:
                    out["ships"][str(meta.get("MMSI"))] = str(meta.get("ShipName") or "").strip()
    except AisError as exc:
        out["error"] = str(exc)
    finally:
        try:
            _ws_send(sock, "", opcode=8)
            sock.close()
        except OSError:
            pass
    log.info("trip feed test: %d messages, %d positions, %d ships, error %s", out["messages"], out["positions"], len(out["ships"]), out["error"])
    return out


# ---------------- CruiseMapper (the ship's public page) ----------------

class PageError(Exception):
    pass


_CM_POS = re.compile(r'"shipCurrentPositionMap"\s*:\s*\{\s*"lat"\s*:\s*(-?\d+(?:\.\d+)?)\s*,\s*"lon"\s*:\s*(-?\d+(?:\.\d+)?)')
_CM_AGE = re.compile(r"last reported\s+(an?|\d+)\s+(minute|hour|day)s?\s+ago", re.I)
_CM_DEST = re.compile(r"en route to\s+([A-Z][A-Z ]{1,24}?)\s*\.")


def parse_cruisemapper(html: str, now_utc: datetime) -> tuple[dict, str]:
    """The position on a CruiseMapper ship page, dated from its 'last reported N minutes ago'."""
    m = _CM_POS.search(html)
    if not m:
        raise PageError("CruiseMapper's page had no position on it (the page may have changed).")
    lat, lon = float(m.group(1)), float(m.group(2))
    if abs(lat) > 90 or abs(lon) > 180 or (lat == 0 and lon == 0):
        raise PageError("CruiseMapper's page had a position that doesn't make sense.")
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
    a = _CM_AGE.search(text)
    mins = 0
    if a:
        n = 1 if a.group(1).lower() in ("a", "an") else int(a.group(1))
        mins = n * {"minute": 1, "hour": 60, "day": 1440}[a.group(2).lower()]
    when = (now_utc - timedelta(minutes=mins)).replace(second=0, microsecond=0)
    d = _CM_DEST.search(text)
    return ({"lat": round(lat, 5), "lon": round(lon, 5), "sog": None, "cog": None, "nav": None,
             "at": when.isoformat(timespec="seconds"), "src": "cruisemapper"}, d.group(1).strip() if d else "")


def fetch_cruisemapper(url: str) -> tuple[dict, str]:
    if not url.startswith(CM_PREFIX):
        raise PageError("The ship's page has to be a CruiseMapper ship page.")
    log.info("trip check: reading %s", url)
    req = urllib.request.Request(url, headers={"User-Agent": CM_AGENT, "Accept": "text/html"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            html = r.read(1_500_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        raise PageError(f"CruiseMapper answered {exc.code}.")
    except (urllib.error.URLError, OSError) as exc:
        raise PageError(f"Couldn't reach CruiseMapper ({getattr(exc, 'reason', exc)}).")
    return parse_cruisemapper(html, datetime.now(timezone.utc))


def _keep(t: dict, fix: dict) -> None:
    """Add a position to the line. Same spot as last time: just move its time on. Speed from the last
    position when the page doesn't give one."""
    fixes = t.setdefault("fixes", [])
    prev = fixes[-1] if fixes else None
    if prev and prev["at"] == fix["at"]:
        return
    if prev and fix.get("sog") is None:
        try:
            hrs = (datetime.fromisoformat(fix["at"]) - datetime.fromisoformat(prev["at"])).total_seconds() / 3600
        except ValueError:
            hrs = 0
        if 0.1 <= hrs <= LIVE_HOURS:
            fix["sog"] = round(km((prev["lat"], prev["lon"]), (fix["lat"], fix["lon"])) / 1.852 / hrs, 1)
    if prev and km((prev["lat"], prev["lon"]), (fix["lat"], fix["lon"])) < 0.1:   # still there: keep when it got there
        prev.setdefault("since", prev["at"])
        prev.update(at=fix["at"], sog=fix["sog"] if fix.get("sog") is not None else prev.get("sog"))
        return
    fixes.append(fix)
    del fixes[:-TRACK_MAX]


def check_now(demo: bool, wait_seconds: float = 215) -> dict:   # a docked ship reports every 3 minutes
    """Read the ship's CruiseMapper page (AISStream as the backup) and keep what it says. Returns the saved track."""
    store = read_store(demo)
    cfg = config(store)
    t = read_track(demo)
    if t.get("mmsi") != cfg["mmsi"]:   # a different ship: put the old line aside (never thrown away) and start fresh
        if t.get("fixes") and t.get("mmsi"):
            _track_path(demo).with_name(f"trip-track-{t['mmsi']}.json").write_text(json.dumps(t))
        t = {"mmsi": cfg["mmsi"], "fixes": [], "destination": ""}
    t["last_try"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    problems, fix, dest = [], None, ""
    if cfg.get("page_url"):
        try:
            fix, dest = fetch_cruisemapper(cfg["page_url"])
        except PageError as exc:
            problems.append(str(exc))
            log.warning("trip tracker: %s", exc)
    if fix is None and api_key(store) and cfg["mmsi"]:   # the backup needs the ship's MMSI
        try:
            fix, dest = fetch_position(api_key(store), cfg["mmsi"], wait_seconds)
            if fix:
                fix["src"] = "aisstream"
            else:
                problems.append("AISStream heard nothing from the ship.")
        except (AisError, OSError, ssl.SSLError) as exc:
            problems.append(str(exc))
            log.warning("trip tracker: %s", exc)
    if fix is None and not problems:
        problems.append("Add the ship's CruiseMapper page first.")
    t["last_error"] = None if fix else " ".join(problems)
    t["last_source"] = fix.get("src") if fix else None
    if dest:
        t["destination"] = dest
    if fix:
        _keep(t, fix)
    _write_track(demo, t)
    log.info("trip check: done (%s)", "position heard" if not t.get("last_error") else t["last_error"])
    return t


def in_window(now: datetime) -> bool:
    if WINDOW is None:
        return True
    return now.replace(hour=WINDOW[0], minute=0, second=0, microsecond=0) <= now <= now.replace(hour=WINDOW[1], minute=0, second=0, microsecond=0)


def next_check(now: datetime, rng=random) -> datetime:
    """The next check: about an hour on, up to 15 minutes either side of the hour, at least half an hour
    after `now`, and inside WINDOW when there is one."""
    base = now.replace(minute=0, second=0, microsecond=0)
    for i in range(1, 48):
        h = base + timedelta(hours=i)
        if WINDOW and not (WINDOW[0] <= h.hour <= WINDOW[1]):
            continue
        t = h + timedelta(minutes=rng.uniform(-JITTER_MIN, JITTER_MIN))
        if WINDOW:
            t = min(max(t, h.replace(hour=WINDOW[0])), h.replace(hour=WINDOW[1]))
        if t - now >= timedelta(minutes=30):
            return t.replace(microsecond=0)
    return base + timedelta(days=1)


class Checker:
    """Checks about once an hour, day and night, while the trip shows, in its own thread (never two at once)."""
    def __init__(self):
        self.running = False
        self.last = 0.0
        self.started = 0.0
        self.next_at: Optional[datetime] = None

    def busy(self) -> bool:
        """A check that has run over 6 minutes is stuck: let the next one start."""
        if self.running and time.time() - self.started > 360:
            log.warning("trip check: the last check never finished; starting over")
            self.running = False
        return self.running

    def tick(self, services) -> None:
        if self.busy():
            return
        store = read_store(services.settings.demo)
        cfg = config(store)
        now = services.now()
        if not showing(cfg, now.date()) or not (cfg.get("page_url") or api_key(store)):
            self.next_at = None
            return
        if self.next_at is None:   # just started: check now (with a WINDOW, wait for morning)
            self.next_at = now if in_window(now) else next_check(now)
        if now < self.next_at:
            return
        self.next_at = next_check(now)
        log.info("trip check: next one at %s", self.next_at.strftime("%-I:%M %p"))
        self.kick(services.settings.demo)

    def kick(self, demo: bool) -> None:
        if self.busy():
            return
        self.running, self.last, self.started = True, time.time(), time.time()

        def run():
            try:
                check_now(demo)
            except Exception:
                log.exception("trip tracker check failed")
            finally:
                self.running = False
        threading.Thread(target=run, daemon=True, name="trip-check").start()


CHECKER = Checker()


# ---------------- where the ship is, in words ----------------

def km(a: tuple, b: tuple) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(min(1, math.sqrt(h)))


def nearest_port(lat: float, lon: float) -> tuple[Optional[tuple], float]:
    best, bd = None, 1e9
    for p in PORTS:
        d = km((lat, lon), (p[3], p[4]))
        if d < bd:
            best, bd = p, d
    return best, bd


def xy(lat: float, lon: float) -> list:
    return [round((lon - MAP["lon0"]) * MAP["k"] * MAP["s"], 1), round((MAP["lat1"] - lat) * MAP["s"], 1)]


def _port_view(key: str) -> Optional[dict]:
    p = PORT_BY_KEY.get(key)
    return {"key": p[0], "name": p[1], "place": p[2], "lat": p[3], "lon": p[4], "xy": xy(p[3], p[4])} if p else None


def _dt(day: str, hhmm: str, tz) -> Optional[datetime]:
    if not day or not hhmm:
        return None
    try:
        return datetime.fromisoformat(f"{day}T{hhmm}").replace(tzinfo=tz)
    except ValueError:
        return None


def _clock(hhmm: str) -> str:
    try:
        h, m = map(int, hhmm.split(":"))
    except ValueError:
        return hhmm
    return f"{h % 12 or 12}{':%02d' % m if m else ''} {'AM' if h < 12 else 'PM'}"


DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DOW_LONG = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _days(cfg: dict) -> list[dict]:
    """The itinerary as one row per day from the first port day to the last (missing days = at sea)."""
    rows = [r for r in cfg["ports"] if r["day"]]
    if not rows:
        return []
    try:
        first, last = date.fromisoformat(rows[0]["day"]), date.fromisoformat(rows[-1]["day"])
    except ValueError:
        return []
    by_day: dict = {}
    for r in rows:
        by_day.setdefault(r["day"], []).append(r)
    out, d = [], first
    while d <= last and len(out) < 40:
        for r in by_day.get(d.isoformat()) or [{"day": d.isoformat(), "port": "", "arrive": "", "depart": "", "note": ""}]:
            out.append(dict(r, dow=DOW[d.weekday()], date_label=f"{DOW[d.weekday()]} {MONTHS[d.month - 1]} {d.day}",
                            port_view=_port_view(r["port"]) if r["port"] else None))
        d += timedelta(days=1)
    return out


def estimate(days: list[dict], now: datetime) -> Optional[dict]:
    """Where the itinerary says the ship is now: in a port, or between two ports (along the likely sea route, by time)."""
    stops = []
    for r in days:
        pv = r["port_view"]
        if not pv:
            continue
        a = _dt(r["day"], r["arrive"] or "07:00", now.tzinfo) if r["arrive"] or r["depart"] else None
        dep = _dt(r["day"], r["depart"] or "17:00", now.tzinfo) if r["arrive"] or r["depart"] else None
        if r["arrive"] and not r["depart"]:
            dep = None
        if r["depart"] and not r["arrive"]:
            a = None
        stops.append((pv, a, dep))
    if not stops:
        return None
    for i, (pv, a, dep) in enumerate(stops):
        if (a is None or a <= now) and (dep is None or now <= dep) and (a or dep):
            if (a is None and now.date() != dep.date()) or (dep is None and now.date() != a.date()):
                continue   # the first port counts from that morning, the last one until that night
            return {"lat": pv["lat"], "lon": pv["lon"], "in_port": pv}
        if i + 1 < len(stops) and dep and stops[i + 1][1] and dep < now < stops[i + 1][1]:
            nxt, arr = stops[i + 1][0], stops[i + 1][1]
            f = (now - dep) / (arr - dep)   # along the likely way by sea, not straight across the land
            path = searoute.route(tuple(pv["xy"]), tuple(nxt["xy"]), searoute.PORT_TRIM, searoute.PORT_TRIM)
            la, lo = searoute.latlon(searoute.along(path, f))
            return {"lat": round(la, 4), "lon": round(lo, 4), "in_port": None}
    return None


def _ago(minutes: float) -> str:
    if minutes < 2:
        return "just now"
    if minutes < 60:
        return f"{int(minutes)} min ago"
    h = minutes / 60
    if h < 24:
        return f"{int(h)} hr ago" if h >= 1.5 else "an hour ago"
    return f"{int(h // 24)} day{'s' if h >= 48 else ''} ago"


def view(cfg: dict, track: dict, now: datetime, demo: bool = False, house: Optional[tuple] = None) -> dict:
    """What the frame draws: the ship, the line sailed, the ports, and a sentence or two.
    house: (lat, lon) of the house (the weather location), for "How far is Mom?"."""
    days = _days(cfg)
    today = now.date().isoformat()
    fixes = track.get("fixes") or []
    last = fixes[-1] if fixes else None
    age_min = None
    if last:
        try:
            age_min = (now - datetime.fromisoformat(last["at"])).total_seconds() / 60
        except ValueError:
            age_min = None
    live = last is not None and age_min is not None and age_min <= LIVE_HOURS * 60
    plan = estimate(days, now)   # where the itinerary says the ship is
    planned = plan if live else None
    # Not live, but heard in the last day and the itinerary doesn't put the ship in a port: show where it was
    # last heard (not a guess across the map). In port by the itinerary: show the port.
    recent = last is not None and age_min is not None and age_min <= 24 * 60 and not (plan and plan["in_port"])
    est = None if live or recent else plan

    ship = None
    in_port = None
    if live:
        p, d = nearest_port(last["lat"], last["lon"])
        stopped = (last.get("sog") is not None and last["sog"] < 1.5) or last.get("nav") in (1, 5) \
            or (last.get("sog") is None and planned is not None and planned["in_port"] is not None
                and planned["in_port"]["key"] == p[0])   # no speed given: in port if the itinerary agrees
        if p and d <= IN_PORT_KM and stopped:
            in_port = _port_view(p[0])
        ship = {"lat": last["lat"], "lon": last["lon"], "xy": xy(last["lat"], last["lon"]), "estimated": False,
                "sog": last.get("sog"), "cog": last.get("cog"), "heard": _ago(age_min), "at": last["at"]}
    elif recent:
        ship = {"lat": last["lat"], "lon": last["lon"], "xy": xy(last["lat"], last["lon"]), "estimated": False, "stale": True,
                "sog": last.get("sog"), "cog": last.get("cog"), "heard": _ago(age_min), "at": last["at"]}
    elif est:
        in_port = est["in_port"]
        ship = {"lat": est["lat"], "lon": est["lon"], "xy": xy(est["lat"], est["lon"]), "estimated": True,
                "heard": _ago(age_min) if age_min is not None else None, "at": last["at"] if last else None}
    elif last:   # an old position and nothing to estimate from: show it as it was
        ship = {"lat": last["lat"], "lon": last["lon"], "xy": xy(last["lat"], last["lon"]), "estimated": True,
                "heard": _ago(age_min) if age_min is not None else None, "at": last["at"]}

    # which day of the trip, and what's next
    first_day = days[0]["day"] if days else cfg["show_from"]
    last_day = days[-1]["day"] if days else cfg["show_until"]
    before = today < first_day
    after = today > last_day
    nxt = None
    for r in days:
        if r["port_view"] and (r["day"] > today or (r["day"] == today and r["arrive"] and now.strftime("%H:%M") < r["arrive"])):
            nxt = r
            break
    today_row = next((r for r in days if r["day"] == today), None)

    if in_port:
        headline = f"In port · {in_port['name']}"
        sub = in_port["place"]
        if today_row and today_row["port"] == in_port["key"] and today_row["depart"]:
            sub += f" · sails {_clock(today_row['depart'])}"
    elif ship:
        headline = "At sea"
        sub = f"on the way to {nxt['port_view']['name']}" if nxt else (f"heading for {track['destination'].title()}" if track.get("destination") else "")
    else:
        headline = "Waiting for the ship’s position"
        sub = "Add the AISStream key in Settings" if not track.get("last_try") else "No position heard yet"
    if before and not in_port:
        boards = days[0] if days else None
        headline = f"Sails {DOW_LONG[date.fromisoformat(first_day).weekday()]}" if days else headline
        if boards and boards["port_view"]:
            sub = f"from {boards['port_view']['name']}" + (f" at {_clock(boards['depart'])}" if boards["depart"] else "")

    try:
        home_day = date.fromisoformat(last_day)
        left = (home_day - now.date()).days
        home = "Home today" if left == 0 else "Home tomorrow" if left == 1 else f"Home in {left} days" if left > 1 else "Home"
    except ValueError:
        home = ""

    return {
        "name": cfg["name"], "traveler": cfg["traveler"], "ship_name": cfg["ship"],
        "map": {"w": round((MAP["lon1"] - MAP["lon0"]) * MAP["k"] * MAP["s"], 1), "h": round((MAP["lat1"] - MAP["lat0"]) * MAP["s"], 1)},
        "ship": ship, "in_port": in_port, "headline": headline, "sub": sub, "home": home,
        "before": before, "after": after,
        "track": [xy(f["lat"], f["lon"]) for f in fixes[-600:]],
        "moves": [{"xy": xy(f["lat"], f["lon"]), "at": f["at"], "since": f.get("since", f["at"])} for f in fixes[-600:]],   # for replaying the trip
        "ahead": [[round(a, 1), round(b, 1)] for a, b in searoute.route(tuple(ship["xy"]), tuple(nxt["port_view"]["xy"]))]
        if ship and nxt and not in_port else None,   # the likely way to the next port, by sea
        "next": {"name": nxt["port_view"]["name"], "xy": nxt["port_view"]["xy"], "date_label": nxt["date_label"],
                 "arrive": _clock(nxt["arrive"]) if nxt["arrive"] else ""} if nxt else None,
        "days": [{"day": r["day"], "date_label": r["date_label"], "dow": r["dow"], "today": r["day"] == today, "past": r["day"] < today,
                  "port": r["port_view"]["name"] if r["port_view"] else (r["port"] if r["port"] and r["port"] not in PORT_BY_KEY else "At sea"),
                  "place": r["port_view"]["place"] if r["port_view"] else "",
                  "xy": r["port_view"]["xy"] if r["port_view"] else None,
                  "hours": " – ".join(x for x in (_clock(r["arrive"]) if r["arrive"] else "", _clock(r["depart"]) if r["depart"] else "") if x)
                  if r["arrive"] and r["depart"] else (f"sails {_clock(r['depart'])}" if r["depart"] else f"arrives {_clock(r['arrive'])}" if r["arrive"] else ""),
                  "note": r["note"]} for r in days],
        "heard": ship.get("heard") if ship else None,
        "estimated": bool(ship and ship["estimated"]),
        "far": far_from_home(house, ship),
    }


def far_from_home(house: Optional[tuple], ship: Optional[dict]) -> Optional[dict]:
    """The house on the map and how far the ship is from it, in miles as the crow flies (nearest 10)."""
    if not ship or not house or house[0] is None or house[1] is None:
        return None
    miles = km(house, (ship["lat"], ship["lon"])) * 0.621371
    return {"xy": xy(house[0], house[1]), "miles": int(round(miles, -1)) if miles >= 20 else int(round(miles))}


def frame_view(services) -> Optional[dict]:
    """The trip for /api/frame, or None when it isn't showing today."""
    demo = services.settings.demo
    cfg = config(read_store(demo))
    now = services.now()
    if not showing(cfg, now.date()):
        return None
    return view(cfg, read_track(demo), now, demo, (services.settings.latitude, services.settings.longitude))


# ---------------- Settings > Cruise ship tracker ----------------

def export(cfg: dict, track: dict) -> dict:
    """The whole route as GeoJSON: one line, every position (with its time and since when the ship sat
    there), and the ports of call. For drawing the trip later."""
    fixes = track.get("fixes") or []
    feats = [{"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[f["lon"], f["lat"]] for f in fixes]},
              "properties": {"kind": "route", "ship": cfg["ship"], "mmsi": cfg["mmsi"], "traveler": cfg["traveler"],
                             "from": fixes[0].get("since", fixes[0]["at"]) if fixes else None, "to": fixes[-1]["at"] if fixes else None}}]
    for f in fixes:
        feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [f["lon"], f["lat"]]},
                      "properties": {"kind": "position", "at": f["at"], "since": f.get("since", f["at"]), "knots": f.get("sog"),
                                     "course": f.get("cog"), "source": f.get("src") or "aisstream"}})
    for r in cfg["ports"]:
        p = PORT_BY_KEY.get(r["port"])
        if p:
            feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [p[4], p[3]]},
                          "properties": {"kind": "port", "name": p[1], "place": p[2], "day": r["day"], "arrive": r["arrive"],
                                         "depart": r["depart"], "note": r["note"]}})
    return {"type": "FeatureCollection", "name": cfg["name"], "features": feats}


def export_csv(track: dict) -> str:
    rows = ["at_utc,since_utc,lat,lon,knots,course,source"]
    for f in track.get("fixes") or []:
        rows.append(",".join("" if v is None else str(v) for v in (f["at"], f.get("since", f["at"]), f["lat"], f["lon"],
                                                                      f.get("sog"), f.get("cog"), f.get("src") or "aisstream")))
    return "\n".join(rows) + "\n"


def _export_name(cfg: dict) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", f"{cfg['traveler']} {cfg['ship']} {cfg['show_from']}").strip("-")


def make_routers(require_admin, svc):
    admin = APIRouter(prefix="/api/admin/trip", dependencies=[Depends(require_admin)])

    def settings_view(s) -> dict:
        demo = s.settings.demo
        store = read_store(demo)
        cfg = config(store)
        t = read_track(demo)
        fixes = t.get("fixes") or []
        now = s.now()
        last = fixes[-1] if fixes else None
        return {**cfg, "key_set": bool(api_key(store)), "showing": showing(cfg, now.date()),
                "ports_list": [{"key": p[0], "name": p[1], "place": p[2]} for p in PORTS],
                "last_fix": last, "last_try": t.get("last_try"), "last_error": t.get("last_error"),
                "destination": t.get("destination") or "", "fixes": len(fixes), "checking": CHECKER.busy(),
                "last_source": t.get("last_source"),
                "next_check": CHECKER.next_at.isoformat() if CHECKER.next_at else None,
                "preview": view(cfg, t, now, demo)}

    @admin.get("")
    def get_trip(s=Depends(svc)):
        return settings_view(s)

    @admin.put("")
    def put_trip(body: dict, request: Request, s=Depends(svc)):
        demo = s.settings.demo
        store = read_store(demo)
        cur = config(store)
        new = dict(cur)
        for k in ("name", "traveler", "ship"):
            if k in body:
                v = str(body[k] or "").strip()[:60]
                if not v:
                    raise HTTPException(400, f"The {'trip name' if k == 'name' else k} can't be empty.")
                new[k] = v
        if "mmsi" in body:
            v = str(body["mmsi"] or "").strip()
            if v and not (v.isdigit() and len(v) == 9):
                raise HTTPException(400, "The ship’s MMSI is 9 digits. It’s on the ship’s page on CruiseMapper or VesselFinder.")
            new["mmsi"] = v
        if "page_url" in body:
            v = str(body["page_url"] or "").strip()
            if v and not (v.startswith(CM_PREFIX) and len(v) < 200):
                raise HTTPException(400, "The ship’s page is its CruiseMapper page, starting " + CM_PREFIX)
            new["page_url"] = v
        for k in ("show_from", "show_until"):
            if k in body:
                try:
                    new[k] = date.fromisoformat(str(body[k])).isoformat()
                except ValueError:
                    raise HTTPException(400, "Pick the dates the frame shows the trip.")
        if new["show_from"] > new["show_until"]:
            raise HTTPException(400, "The trip can’t stop showing before it starts.")
        if "check_minutes" in body:
            try:
                new["check_minutes"] = max(5, min(60, int(body["check_minutes"])))
            except (TypeError, ValueError):
                raise HTTPException(400, "Check every: a number of minutes.")
        if "ports" in body:
            rows = []
            for r in body["ports"] or []:
                r = _clean_row(r)
                try:
                    date.fromisoformat(r["day"])
                except ValueError:
                    raise HTTPException(400, "Each port of call needs a date.")
                for t in ("arrive", "depart"):
                    if r[t] and not (len(r[t]) == 5 and r[t][2] == ":" and r[t].replace(":", "").isdigit()):
                        raise HTTPException(400, f"{r['day']}: times look like 07:00.")
                rows.append(r)
            new["ports"] = sorted(rows, key=lambda r: (r["day"], r["arrive"] or r["depart"] or ""))
        store["trip"] = new
        if "aisstream_key" in body:
            k = str(body["aisstream_key"] or "").strip()
            sec = store.setdefault("secrets", {})
            if k:
                sec["aisstream_key"] = k
            elif body.get("clear_key"):
                sec.pop("aisstream_key", None)
        write_store(store, demo)
        from .main import _payload_cache
        _payload_cache["at"] = 0.0   # the frame sees the change on its next poll
        if showing(new, s.now().date()) and (new.get("page_url") or api_key(store)):
            CHECKER.kick(demo)
        return settings_view(s)

    @admin.get("/export.geojson")
    def get_export(s=Depends(svc)):
        demo = s.settings.demo
        cfg = config(read_store(demo))
        return Response(json.dumps(export(cfg, read_track(demo)), indent=1), media_type="application/geo+json",
                        headers={"Content-Disposition": f'attachment; filename="{_export_name(cfg)}.geojson"'})

    @admin.get("/export.csv")
    def get_export_csv(s=Depends(svc)):
        demo = s.settings.demo
        cfg = config(read_store(demo))
        return Response(export_csv(read_track(demo)), media_type="text/csv",
                        headers={"Content-Disposition": f'attachment; filename="{_export_name(cfg)}.csv"'})

    @admin.post("/feed-test")
    def post_feed_test(body: Optional[dict] = None, s=Depends(svc)):
        """Settings: does the key get anything at all? (every ship near Miami for 25 s, no ship filter;
        or {"mmsi": [...], "seconds": n} to try the ship filter on ships we know are on the air)"""
        body = body or {}
        mm = [str(x) for x in (body.get("mmsi") or []) if str(x).isdigit()][:10] or None
        secs = max(5, min(240, float(body.get("seconds") or 25)))
        try:
            return feed_test(api_key(read_store(s.settings.demo)), secs, mmsi=mm)
        except (AisError, OSError, ssl.SSLError) as exc:
            raise HTTPException(502, str(exc))

    @admin.post("/check")
    def post_check(s=Depends(svc)):
        demo = s.settings.demo
        store = read_store(demo)
        if not (config(store).get("page_url") or api_key(store)):
            raise HTTPException(400, "Add the ship’s CruiseMapper page first.")
        CHECKER.kick(demo)
        return settings_view(s)

    return admin
