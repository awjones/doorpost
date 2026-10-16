"""Admin panel API: everything the family edits without touching files.

Saved to the settings store (data/settings.json, or /data/settings.json in the
Home Assistant add-on). Secrets (calendar addresses, logins) are never sent
back to the browser in full: the panel shows only that one is saved.
"""
from __future__ import annotations

import copy
import re
import secrets
from datetime import timedelta
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile

from . import photo_sources
from .auth import check_pin_hash, hash_pin
from .calendar_feed import CalendarService
from .config import DATA_DIR, effective_config, load_settings, read_store, write_store
from .main import KID_PHOTOS, SPECIAL_PHOTOS, Services, reload_services, require_admin, svc
from . import special as sp
from . import themes
from .photos import save_kid_photo
from .screentime import DAY_KEYS as ST_DAYS, VIEWS, ScreenTimeSettings

router = APIRouter(prefix="/api/admin", dependencies=[Depends(require_admin)])

HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
DAYS = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]  # Sunday first, always


def _hint(url: str | None) -> str:
    return ("…" + url[-6:]) if url else ""


@router.get("/settings")
def get_settings(s: Services = Depends(svc)):
    demo = s.settings.demo
    cfg = effective_config(demo)
    sec = read_store(demo).get("secrets", {})
    cals = []
    for c in cfg.get("calendars", []):
        f = c.get("filter") or {}
        url = c.get("ics_url") or ""
        cals.append({
            "key": c["key"], "label": c["label"], "color": c["color"], "who_default": c.get("who_default", ""),
            "has_url": bool(url) or bool(c.get("ics_file") and demo), "url_hint": _hint(url),
            "public": "/public/basic.ics" in url,  # anyone can read a public address; the secret one is private
            **_caldav_view(c, url, demo),
            "filter_mode": c.get("filter_mode") or ("family" if f.get("require_attendee_any") or f.get("include_titles_matching") else "all"),
            "filter_emails": c.get("filter_emails") or ", ".join(f.get("require_attendee_any", [])),
        })
    st = ScreenTimeSettings.from_store(cfg.get("screen_time", {}) or {})
    ha = cfg.get("home_assistant", {}) or {}
    return {
        "mode": {"demo": demo, "addon": s.settings.addon, "ha_available": bool(s.settings.ha_token)},
        "modules": sorted(mods_on(s)),   # Settings shows the pages of modules that are on
        "page_modules": page_modules(),
        "display": {
            "family_name": cfg.get("family_name", ""), "family_initial": cfg.get("family_initial", ""), "timezone": s.settings.timezone,
            "frame_url": cfg.get("frame_url") or "https://frame.example.com",
            "lan_url": cfg.get("lan_url") or "http://doorpost.local:8090",
            "latitude": (cfg.get("location") or {}).get("latitude"), "longitude": (cfg.get("location") or {}).get("longitude"),
            "night_start": (cfg.get("night") or {}).get("start", "22:00"), "night_end": (cfg.get("night") or {}).get("end", "06:00"),
            "idle_minutes_to_photos": cfg.get("idle_minutes_to_photos", 5),
            "return_to_today_minutes": cfg.get("return_to_today_minutes", 2),
            "photo_seconds": cfg.get("photo_seconds", 20),
            "weather_source": (cfg.get("weather") or {}).get("source") or "auto",
            "weather_temp": (cfg.get("weather") or {}).get("temp") or "auto",
            "weather_wind": (cfg.get("weather") or {}).get("wind") or "auto",
            "weather_show_wind": (cfg.get("weather") or {}).get("show_wind") or "panel",
            "weather_unit_letter": (cfg.get("weather") or {}).get("unit_letter") or "no",
            "weather_auto_units": "F, mph" if s.weather.is_us() else "C, km/h",
        },
        "calendars": cals,
        "merge_shared_events": bool(cfg.get("merge_shared_events", True)),
        "kids": [{**{k: v for k, v in kid.items() if k in ("id", "name", "initial", "color", "screen_time_nickname")},
                  "photo": f"kids/{kid['id']}.jpg?v={kid['photo']}" if kid.get("photo") else None}
                 for kid in cfg.get("kids", [])],
        "chores": [{**c, "days": _days_list(c.get("days"))} for c in cfg.get("chores", [])],
        "screen_time": st.to_store(),
        "home_assistant": {"enabled": bool(ha.get("enabled")), "entities": ha.get("entities", [])},
        "photos": {"sources": (cfg.get("photos") or {}).get("sources", []), "status": s.photos.source_status(),
                   "upload_token": s.settings.upload_token},
        "security": {"pin_set": bool(sec.get("pin_hash") or s.settings.pin_hash),
                     "parents": [p["name"] for p in sec.get("parent_pins", []) if p.get("name")],
                     "demo_pins": bool(demo and not sec.get("parent_pins") and not sec.get("pin_hash"))},
    }


def _provider_of(url: str) -> str:
    u = url.lower()
    for word, name in (("google.com", "google"), ("icloud.com", "icloud"), ("outlook", "outlook"), ("office365", "outlook")):
        if word in u:
            return name
    return "other" if url else "google"


def _caldav_view(c: dict, url: str, demo: bool) -> dict:
    """What Settings may show about where a calendar comes from. Never the password."""
    kind = c.get("kind") or "ics"
    out = {"kind": kind, "provider": c.get("provider") or ("icloud" if kind == "caldav" else _provider_of(url))}
    if kind == "caldav":
        out.update({"caldav_server": c.get("caldav_server") or "", "caldav_user": c.get("caldav_user") or "",
                    "caldav_calendar": c.get("caldav_calendar") or "",
                    "caldav_calendar_name": c.get("caldav_calendar_name") or "",
                    "has_password": bool(c.get("caldav_password"))})
        out["has_url"] = bool(out["caldav_calendar"] and out["has_password"]) or bool(c.get("ics_file") and demo)
    return out


def _days_list(days) -> list[str]:
    from .config import _expand_days
    try:
        return _expand_days(days)
    except ValueError:
        return []


def _save(request: Request, s: Services, mutate) -> dict:
    """Apply a change to the store, check the whole config still loads, then reload."""
    demo = s.settings.demo
    store = read_store(demo)
    before = copy.deepcopy(store)
    mutate(store, effective_config(demo))
    write_store(store, demo)
    try:
        load_settings()
    except Exception as exc:
        write_store(before, demo)
        raise HTTPException(400, f"Not saved: {exc}")
    reload_services(request.app)
    return {"ok": True}


@router.put("/display")
def put_display(body: dict, request: Request, s: Services = Depends(svc)):
    def m(store, cfg):
        store["family_name"] = str(body.get("family_name") or "Our Family")[:60]
        ini = str(body.get("family_initial") or "").strip()[:1].upper()   # empty: from the family name (app/frame.py)
        if ini and not ini.isalpha():
            raise HTTPException(400, "The family initial is one letter, or leave it empty.")
        store["family_initial"] = ini
        url = str(body.get("frame_url") or "").strip().rstrip("/")
        if url and not re.match(r"^https?://[\w.-]+(:\d+)?$", url):
            raise HTTPException(400, "The frame's address looks like http://frame.example.com:8090")
        store["frame_url"] = url
        lan = str(body.get("lan_url") or "").strip().rstrip("/")
        if lan and not re.match(r"^https?://[\w.-]+(:\d+)?$", lan):
            raise HTTPException(400, "The home-network address looks like http://doorpost.local:8090")
        store["lan_url"] = lan
        store["timezone"] = str(body.get("timezone") or s.settings.timezone)
        lat, lon = body.get("latitude"), body.get("longitude")
        store["location"] = {"latitude": float(lat) if lat not in (None, "") else None,
                             "longitude": float(lon) if lon not in (None, "") else None}
        store["night"] = {"start": _hhmm(body.get("night_start", "22:00")), "end": _hhmm(body.get("night_end", "06:00"))}
        store["idle_minutes_to_photos"] = max(1.0, float(body.get("idle_minutes_to_photos", 5)))
        store["return_to_today_minutes"] = max(0.5, float(body.get("return_to_today_minutes", 2)))
        store["photo_seconds"] = max(5, int(body.get("photo_seconds", 20)))
        store["weather"] = _weather_choices(body, cfg.get("weather") or {})
    return _save(request, s, m)


def _weather_choices(body: dict, old: dict) -> dict:
    from .weather import SHOW_WIND, SOURCES, TEMP_UNITS, UNIT_LETTER, WIND_UNITS
    out = {}
    for key, allowed in (("source", SOURCES), ("temp", TEMP_UNITS), ("wind", WIND_UNITS),
                         ("show_wind", SHOW_WIND), ("unit_letter", UNIT_LETTER)):
        v = body.get("weather_" + key, old.get(key) or allowed[0])
        if v not in allowed:
            raise HTTPException(400, f"Weather {key} is one of {', '.join(allowed)}")
        out[key] = v
    return out


def _hhmm(v: str) -> str:
    if not re.match(r"^\d{1,2}:\d{2}$", str(v)):
        raise HTTPException(400, f"Times look like 22:00, not '{v}'")
    return str(v)


@router.put("/calendars")
def put_calendars(body: list[dict], request: Request, s: Services = Depends(svc)):
    def m(store, cfg):
        old = {c["key"]: c for c in cfg.get("calendars", [])}
        out, keys = [], set()
        for c in body:
            label = str(c.get("label", "")).strip()
            if not label:
                raise HTTPException(400, "Every calendar needs a name.")
            key = c.get("key") or re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-") or "cal"
            while key in keys:
                key += "-2"
            keys.add(key)
            if not HEX.match(c.get("color", "")):
                raise HTTPException(400, f"Pick a color for {label}.")
            prev = old.get(key, {})
            entry = {"key": key, "label": label, "color": c["color"], "who_default": str(c.get("who_default", "")),
                     "filter_mode": c.get("filter_mode", "all"), "filter_emails": str(c.get("filter_emails", "")),
                     "provider": str(c.get("provider") or prev.get("provider") or "")[:20]}
            if prev.get("filter"):
                entry["filter"] = prev["filter"]
            if (c.get("kind") or "ics") == "caldav":
                out.append(_caldav_entry(c, prev, entry, label, s.settings.demo))
                continue
            new_url = str(c.get("ics_url") or "").strip()
            if new_url and not re.match(r"^(https?|webcals?)://", new_url):
                raise HTTPException(400, f"The address for {label} should start with https://")
            url = _https(new_url) if new_url else (prev.get("ics_url") if (prev.get("kind") or "ics") == "ics" else None)
            if url:
                entry["ics_url"] = url
            elif s.settings.demo and prev.get("ics_file"):
                entry["ics_file"] = prev["ics_file"]
            out.append(entry)
        store["calendars"] = out
    return _save(request, s, m)


def _https(url: str) -> str:
    """webcal:// and webcals:// are just https:// for calendar apps."""
    return re.sub(r"^webcals?://", "https://", url.strip())


def _caldav_entry(c: dict, prev: dict, entry: dict, label: str, demo: bool) -> dict:
    """A private CalDAV calendar. A blank password keeps the saved one (it is never sent back)."""
    from .caldav import ICLOUD_SERVER, normalize_server
    server = ICLOUD_SERVER if entry["provider"] == "icloud" else str(c.get("caldav_server") or "").strip()
    if not server:
        raise HTTPException(400, f"Type the CalDAV server address for {label}.")
    if not re.match(r"^(https?|webcals?)://[\w.-]+(:\d+)?(/.*)?$", _https(server)):
        raise HTTPException(400, f"The server for {label} should look like https://caldav.example.com")
    user = str(c.get("caldav_user") or "").strip()
    same_account = prev.get("kind") == "caldav" and prev.get("caldav_user") == user
    password = str(c.get("caldav_password") or "").strip() or (prev.get("caldav_password") if same_account else "")
    cal_url = str(c.get("caldav_calendar") or "").strip()
    entry.update({"kind": "caldav", "caldav_server": normalize_server(_https(server)).rstrip("/"), "caldav_user": user,
                  "caldav_calendar": cal_url,
                  "caldav_calendar_name": str(c.get("caldav_calendar_name") or (prev.get("caldav_calendar_name") if cal_url == prev.get("caldav_calendar") else "") or "")[:80]})
    if password:
        entry["caldav_password"] = password
    if demo and prev.get("ics_file"):
        entry["ics_file"] = prev["ics_file"]  # demo sample data until a real login is saved
    return entry


@router.put("/calendar_options")
def put_calendar_options(body: dict, request: Request, s: Services = Depends(svc)):
    def m(store, cfg):
        store["merge_shared_events"] = bool(body.get("merge_shared_events", True))
    return _save(request, s, m)


@router.put("/kids")
def put_kids(body: list[dict], request: Request, s: Services = Depends(svc)):
    def m(store, cfg):
        old = {k["id"]: k for k in cfg.get("kids", [])}
        out, ids = [], set()
        for k in body:
            name = str(k.get("name", "")).strip()
            if not name:
                raise HTTPException(400, "Every kid needs a name.")
            kid_id = k.get("id") or re.sub(r"[^a-z0-9]+", "", name.lower()) or "kid"
            if kid_id in ids:
                raise HTTPException(400, f"Two kids share the id '{kid_id}'.")
            ids.add(kid_id)
            if not HEX.match(k.get("color", "")):
                raise HTTPException(400, f"Pick a color for {name}.")
            out.append({"id": kid_id, "name": name[:20], "initial": (str(k.get("initial") or name[0]).strip())[:2],
                        "color": k["color"], "screen_time_nickname": str(k.get("screen_time_nickname") or name),
                        "photo": old.get(kid_id, {}).get("photo")})
        store["kids"] = out
        if "chores" not in store:
            store["chores"] = cfg.get("chores", [])
        store["chores"] = [c for c in store["chores"] if c["kid"] in ids]  # a removed kid's chores go too
    return _save(request, s, m)


@router.put("/chores")
def put_chores(body: list[dict], request: Request, s: Services = Depends(svc)):
    def m(store, cfg):
        kid_ids = {k["id"] for k in cfg.get("kids", [])}
        out = []
        for c in body:
            title = str(c.get("title", "")).strip()
            if not title:
                continue
            if c.get("kid") not in kid_ids:
                raise HTTPException(400, f"'{title}' isn't assigned to a kid.")
            days = [d for d in c.get("days", []) if d in DAYS]
            if not days:
                raise HTTPException(400, f"Pick at least one day for '{title}'.")
            try:
                minutes = int(c.get("minutes", 5))
            except (TypeError, ValueError):
                raise HTTPException(400, f"Enter the minutes for '{title}' as a number.")
            if not 1 <= minutes <= 240:
                raise HTTPException(400, f"'{title}' can be worth 1 to 240 minutes.")
            entry = {"kid": c["kid"], "title": title[:60], "minutes": minutes, "days": days}
            if c.get("id"):
                entry["id"] = c["id"]
            out.append(entry)
        store["chores"] = out
    return _save(request, s, m)


@router.put("/screen_time")
def put_screen_time(body: dict, request: Request, s: Services = Depends(svc)):
    def num(key, lo, hi, label):
        try:
            v = int(body.get(key))
        except (TypeError, ValueError):
            raise HTTPException(400, f"{label}: enter a number of minutes.")
        if not lo <= v <= hi:
            raise HTTPException(400, f"{label}: between {lo} and {hi} minutes.")
        return v
    cfg = ScreenTimeSettings(
        base_saturday_minutes=num("base_saturday_minutes", 0, 600, "Saturday to start"),
        base_sunday_minutes=num("base_sunday_minutes", 0, 600, "Sunday to start"),
        good_day_minutes=num("good_day_minutes", 5, 120, "A good day"),
        full_minutes=num("full_minutes", 60, 1440, "Full mark"),
        new_week_day=body.get("new_week_day") if body.get("new_week_day") in ST_DAYS else "sun",
        new_week_time=_hhmm(body.get("new_week_time") or "21:00"),
        views=[v for v in body.get("views", []) if v in VIEWS] or list(VIEWS),
    )
    def m(store, _cfg):
        store["screen_time"] = cfg.to_store()
    return _save(request, s, m)


@router.put("/home_assistant")
def put_ha(body: dict, request: Request, s: Services = Depends(svc)):
    def m(store, cfg):
        ents = []
        for e in body.get("entities", []):
            ent = str(e.get("entity", "")).strip()
            if not re.match(r"^[a-z_]+\.[a-z0-9_]+$", ent):
                continue
            name = str(e.get("name") or ent.split(".")[1].replace("_", " ").title())
            domain = ent.split(".")[0]
            if domain == "lock":
                states, alert, icon = {"locked": f"{name} locked", "unlocked": f"{name} unlocked"}, ["unlocked"], "lock"
            elif domain == "cover":
                states = {"closed": f"{name} closed", "open": f"{name} open", "opening": f"{name} opening",
                          "closing": f"{name} closing"}
                alert, icon = ["open", "opening"], "garage"
            else:
                states, alert, icon = {"on": f"{name} open", "off": f"{name} closed"}, ["on"], "home"
            ents.append({"entity": ent, "name": name, "icon": icon, "states": states, "alert_when": alert})
        store["home_assistant"] = {"enabled": bool(body.get("enabled")), "entities": ents,
                                   "url": (cfg.get("home_assistant") or {}).get("url")}
    return _save(request, s, m)


@router.put("/photos")
def put_photos(body: dict, request: Request, s: Services = Depends(svc)):
    def m(store, cfg):
        out = []
        for src in body.get("sources", []):
            kind, url = src.get("kind"), str(src.get("url", "")).strip()
            if kind not in photo_sources.FETCHERS or not url:
                continue
            out.append({"id": src.get("id") or secrets.token_hex(4), "kind": kind, "url": url,
                        "label": str(src.get("label") or "")[:40], "enabled": bool(src.get("enabled", True))})
        photos = dict(cfg.get("photos") or {})
        photos["sources"] = out
        store["photos"] = photos
    return _save(request, s, m)


@router.post("/pin")
def set_pin(body: dict, request: Request, s: Services = Depends(svc)):
    """A parent's own PIN (body has "name"), or the shared PIN (no name)."""
    pin = str(body.get("pin", ""))
    name = str(body.get("name") or "").strip()[:20]
    try:
        h = hash_pin(pin)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    def m(store, cfg):
        sec = store.setdefault("secrets", {})
        others = [p for p in sec.get("parent_pins", []) if p["name"].lower() != name.lower()]
        taken = [p["hash"] for p in others] + ([sec["pin_hash"]] if name and sec.get("pin_hash") else [])
        if any(check_pin_hash(pin, t) for t in taken):
            raise HTTPException(400, "Someone else already uses that PIN. Pick a different one so the log knows who's who.")
        if name:
            sec["parent_pins"] = others + [{"name": name, "hash": h}]
        else:
            sec["pin_hash"] = h
    return _save(request, s, m)


@router.delete("/pin")
def remove_pin(name: str = "", request: Request = None, s: Services = Depends(svc)):
    """Turn off one parent's PIN, or the shared PIN (no name)."""
    def m(store, cfg):
        sec = store.setdefault("secrets", {})
        if name:
            sec["parent_pins"] = [p for p in sec.get("parent_pins", []) if p["name"].lower() != name.lower()]
        else:
            if not sec.get("parent_pins"):
                raise HTTPException(400, "Set a parent's own PIN first, so the frame still has one.")
            sec.pop("pin_hash", None)
    return _save(request, s, m)


@router.post("/upload-token/rotate")
def rotate_token(request: Request, s: Services = Depends(svc)):
    def m(store, cfg):
        store.setdefault("secrets", {})["upload_token"] = secrets.token_urlsafe(24)
    return _save(request, s, m)


# ---------------- special days ----------------

@router.get("/special")
def get_special(s: Services = Depends(svc)):
    return s.special.settings_view(s.now().date())


@router.put("/special")
def put_special(body: dict, request: Request, s: Services = Depends(svc)):
    def m(store, cfg):
        cur = dict(cfg.get("special_days") or {})
        if "holiday_modes" in body:
            modes = {sp.norm(k): v for k, v in (body["holiday_modes"] or {}).items() if v in sp.MODES}
            cur["holiday_modes"] = dict(cur.get("holiday_modes") or {}, **modes)
        if "church" in body:
            known = s.special.church_defaults   # the church-year days the turned-on art packs have
            cur["church"] = dict(cur.get("church") or {}, **{k: bool(v) for k, v in (body["church"] or {}).items() if k in known})
        if "words" in body:
            words = []
            for w in body["words"] or []:
                word = str(w.get("word", "")).strip()[:40]
                if word:
                    words.append({"word": word, "look": sp.slug(str(w.get("look") or "")),
                                  **({"picture_only": True} if w.get("picture_only") else {})})
            cur["words"] = words
        if "sundays" in body:
            cur["sundays"] = bool(body["sundays"])
        if "seasons" in body:
            cur["seasons"] = bool(body["seasons"])
        if "countdown_days" in body:
            try:
                cur["countdown_days"] = max(0, min(60, int(body["countdown_days"])))
            except (TypeError, ValueError):
                raise HTTPException(400, "Countdown: enter a number of days.")
        if "holiday_url" in body and not s.settings.demo:  # demo mode always reads its saved sample file
            url = str(body.get("holiday_url") or "").strip().replace("webcal://", "https://")
            if url and not url.startswith("https://"):
                raise HTTPException(400, "The holiday calendar address should start with https://")
            cur["holiday_url"] = url
        store["special_days"] = cur
    return _save(request, s, m)


@router.get("/frames")
def get_frames(s: Services = Depends(svc)):
    from . import frames as fp
    from . import modules as mods
    on = mods.on_set(s.settings)   # screens of modules that are off aren't offered (and are kept as they were)
    return {"frames": [dict(p, seen=fp.seen_view(p["id"])) for p in fp.live(s.settings)],
            "looks": [themes.public(t) for t in themes.enabled()],
            "screens": [{"key": k, "name": fp.SCREEN_NAMES[k]} for k in fp.SCREENS if mods.SCREEN_MODULE.get(k, "calendar") in on],
            "homes": [h for h in fp.HOMES if mods.SCREEN_MODULE.get(h, "calendar") in on],
            "multi": "multi_frame" in on,
            "lan_url": effective_config(s.settings.demo).get("lan_url") or "http://doorpost.local:8090"}


@router.put("/frames")
def put_frames(body: list[dict], request: Request, s: Services = Depends(svc)):
    from . import frames as fp
    if not body:
        raise HTTPException(400, "Keep at least one frame.")
    kid_ids, cal_keys = {k.id for k in s.settings.kids}, {c.key for c in s.settings.calendars}
    cleaned = [fp.clean(p, kid_ids, cal_keys) for p in body]
    if len({p["id"] for p in cleaned}) != len(cleaned):
        raise HTTPException(400, "Two frames have the same name. Give each its own.")
    from .modules import keep_hidden
    def m(store, cfg):
        store["frames"] = keep_hidden(cleaned, list(cfg.get("frames") or s.settings.frames or []), s.settings)
    return _save(request, s, m)


@router.get("/lists")
def get_lists(s: Services = Depends(svc)):
    L = s.lists
    synced = L.synced_at()
    now = s.now().replace(tzinfo=None)
    from .admin_providers import lists_sources
    return {"available": L.available(), "shown": L.shown(), "home": L.home(),
            "sections": [a["id"] for a in L.available() if L.sections_on(a["id"])],
            "anyone_add": L.can_add, "anyone_check": L.can_check,
            "synced": synced.isoformat() if synced else None,
            "synced_ago": int((now - synced).total_seconds()) if synced else None,
            "upload_token": s.settings.upload_token, "lan_url": effective_config(s.settings.demo).get("lan_url") or "http://doorpost.local:8090",
            **lists_sources(s)}


@router.put("/lists")
def put_lists(body: dict, request: Request, s: Services = Depends(svc)):
    known = {a["id"] for a in s.lists.available()}
    def m(store, cfg):
        cur = dict(cfg.get("lists") or {})
        if "shown" in body:
            cur["shown"] = [str(x) for x in body["shown"] or [] if str(x) in known]
        if "sections" in body:
            cur["sections"] = [str(x) for x in body["sections"] or [] if str(x) in known]
        if "home" in body:
            cur["home"] = str(body["home"] or "")
        for k in ("anyone_add", "anyone_check", "google"):
            if k in body:
                cur[k] = bool(body[k])
        store["lists"] = cur
    return _save(request, s, m)


@router.post("/special/check")
def check_special(s: Services = Depends(svc)):
    s.holidays.refresh(force=True)
    if s.holidays.error:
        return {"ok": False, "message": s.holidays.error}
    today = s.now().date()
    n = len([h for h in s.holidays.days if today <= h["date"] <= today + timedelta(days=366)])
    return {"ok": True, "message": f"Connected: {n} holidays in the next 12 months."}


@router.post("/special/pictures")
async def upload_special_picture(file: UploadFile, name: str = Form(""), s: Services = Depends(svc)):
    try:
        key = sp.save_picture(SPECIAL_PHOTOS, name or (file.filename or "").rsplit(".", 1)[0], await file.read())
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"ok": True, "name": key}


@router.delete("/special/pictures/{name}")
def delete_special_picture(name: str):
    path = SPECIAL_PHOTOS / f"{sp.slug(name)}.jpg"
    if not sp.slug(name) or not path.exists():
        raise HTTPException(404, "No picture by that name.")
    path.unlink()
    return {"ok": True}


# ---------------- tests ("Check" buttons) ----------------

def _caldav_login(body: dict, src) -> tuple[str, str, str]:
    """Server, user and password for a Check: typed values, or the saved password
    when the typed sign-in name matches the saved calendar's."""
    from .caldav import ICLOUD_SERVER
    provider = body.get("provider") or (src.provider if src else "")
    server = ICLOUD_SERVER if provider == "icloud" else _https(str(body.get("caldav_server") or (src.caldav_server if src else "") or ""))
    user = str(body.get("caldav_user") or "").strip() or (src.caldav_user if src else "")
    password = str(body.get("caldav_password") or "").strip()
    if not password and src is not None and src.kind == "caldav" and src.caldav_user == user:
        password = src.caldav_password
    if not server:
        raise HTTPException(400, "Type the CalDAV server address first.")
    return server, user, password


@router.post("/test/caldav")
def find_caldav_calendars(body: dict, s: Services = Depends(svc)):
    """List the calendars on a CalDAV account so the parent can pick one."""
    from . import caldav
    src = next((c for c in s.settings.calendars if c.key == body.get("key")), None)
    server, user, password = _caldav_login(body, src)
    try:
        cals = caldav.CalDAVClient(server, user, password, http=caldav.make_http()).calendars()
    except caldav.CalDAVError as exc:
        return {"ok": False, "message": str(exc), "calendars": []}
    except httpx.HTTPError as exc:
        return {"ok": False, "message": f"Could not reach the server ({exc.__class__.__name__}).", "calendars": []}
    if not cals:
        return {"ok": False, "message": "Signed in, but this account has no calendars.", "calendars": []}
    return {"ok": True, "message": f"Found {len(cals)} calendar{'' if len(cals) == 1 else 's'}. Pick one, then press Check.",
            "calendars": cals}


@router.post("/test/calendar")
def test_calendar(body: dict, s: Services = Depends(svc)):
    from copy import copy as shallow
    from . import caldav
    from .config import CalendarSource
    key, url = body.get("key"), _https(str(body.get("ics_url") or ""))
    kind = body.get("kind") or "ics"
    src = next((c for c in s.settings.calendars if c.key == key), None)
    test_src = shallow(src) if src else CalendarSource(key="test", label="Test", color="#000000", tint="#FFFFFF")
    if kind == "caldav":
        server, user, password = _caldav_login(body, src)
        cal_url = str(body.get("caldav_calendar") or "").strip() or (src.caldav_calendar if src else "")
        test_src.kind, test_src.caldav_server, test_src.caldav_user = "caldav", server, user
        test_src.caldav_password, test_src.caldav_calendar = password, cal_url
        if password:
            test_src.ics_file = None  # a real login: don't fall back to demo data
    else:
        if not url and (src is None or src.kind != "ics"):
            raise HTTPException(400, "Paste the calendar's address first.")
        test_src.kind = "ics"
        if url:
            test_src.ics_url, test_src.ics_file = url, None
    tmp = shallow(s.settings)
    tmp.calendars = [test_src]
    cal = CalendarService(tmp, DATA_DIR / "calendar-cache-test", http=caldav.make_http())
    cal.refresh()
    if cal.errors:
        return {"ok": False, "message": next(iter(cal.errors.values()))}
    today = s.now().date()
    evs = cal.events_between(today, today + timedelta(days=14))
    name = str(cal.calendars[test_src.key].get("X-WR-CALNAME", "")) if test_src.key in cal.calendars else ""
    return {"ok": True, "message": f"Connected{' to “' + name + '”' if name else ''}: {len(evs)} events in the next two weeks.",
            "sample": [f"{e['day']} {e['time']} {e['title']}" for e in evs[:5]]}


@router.post("/test/photos")
def test_photos(body: dict):
    fetch = photo_sources.FETCHERS.get(body.get("kind"))
    if not fetch:
        raise HTTPException(400, "Unknown album type.")
    try:
        items = fetch(str(body.get("url", "")).strip())
    except Exception as exc:
        return {"ok": False, "message": str(exc)}
    return {"ok": True, "message": f"Found {len(items)} photos."}


@router.get("/ha/entities")
def ha_entities(s: Services = Depends(svc)):
    if not s.settings.ha_token or not s.settings.ha_url:
        return {"available": False, "entities": []}
    try:
        r = httpx.get(f"{s.settings.ha_url.rstrip('/')}/api/states",
                      headers={"Authorization": f"Bearer {s.settings.ha_token}"}, timeout=10)
        r.raise_for_status()
    except Exception as exc:
        return {"available": False, "entities": [], "message": str(exc)[:200]}
    out = []
    for st in r.json():
        eid = st["entity_id"]
        dom = eid.split(".")[0]
        dc = st.get("attributes", {}).get("device_class", "")
        if dom in ("lock", "cover") or (dom == "binary_sensor" and dc in ("door", "garage_door", "window", "opening")):
            out.append({"entity": eid, "name": st.get("attributes", {}).get("friendly_name", eid), "state": st["state"]})
    return {"available": True, "entities": sorted(out, key=lambda e: e["name"])}


# ---------------- photos + kid faces ----------------

@router.get("/photos")
def list_photos(s: Services = Depends(svc)):
    s.photos.maybe_rescan()  # picks up anything uploaded since the last scan
    return {"photos": s.photos.admin_listing(), "sources": s.photos.source_status()}


@router.put("/photos/{pid}/focus")
def put_photo_focus(pid: str, body: dict, s: Services = Depends(svc)):
    """Settings > Photos focal point editor. Send any of: point, wide, tall ([x, y] or null) and wide_fit, tall_fit."""
    item = s.photos._local.get(pid)
    if not item:
        raise HTTPException(404, "That photo is gone (the list may be out of date: reload the page).")
    fields = {k: body[k] for k in ("point", "wide", "tall", "wide_fit", "tall_fit") if k in body}
    f = s.photos.focus.set(item["name"], **fields)
    s.photos.drop_variants(pid)
    from .main import _payload_cache
    _payload_cache["at"] = 0
    from .photos import FocusStore
    return {"ok": True, "focus": f, "v": FocusStore.version(f)}


@router.post("/photos")
async def upload_photos(files: list[UploadFile], s: Services = Depends(svc)):
    saved, errors = [], []
    for f in files:
        try:
            saved.append(s.photos.save_upload(f.filename or "photo.jpg", await f.read()))
        except ValueError as exc:
            errors.append(str(exc))
    s.photos.scan()
    return {"saved": saved, "errors": errors}


@router.delete("/photos/{pid}")
def delete_photo(pid: str, s: Services = Depends(svc)):
    if not s.photos.remove(pid):
        raise HTTPException(404, "That photo isn't in the frame's folder.")
    s.photos.scan()
    return {"ok": True}


@router.post("/kids/{kid_id}/photo")
async def upload_kid_photo(kid_id: str, file: UploadFile, request: Request, s: Services = Depends(svc)):
    if kid_id not in {k.id for k in s.settings.kids}:
        raise HTTPException(404, "No such kid.")
    try:
        version = save_kid_photo(KID_PHOTOS, kid_id, await file.read())
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    def m(store, cfg):
        store["kids"] = [dict(k, photo=version if k["id"] == kid_id else k.get("photo")) for k in cfg.get("kids", [])]
    return _save(request, s, m)


@router.delete("/kids/{kid_id}/photo")
def remove_kid_photo(kid_id: str, request: Request, s: Services = Depends(svc)):
    (KID_PHOTOS / f"{kid_id}.jpg").unlink(missing_ok=True)
    def m(store, cfg):
        store["kids"] = [dict(k, photo=None if k["id"] == kid_id else k.get("photo")) for k in cfg.get("kids", [])]
    return _save(request, s, m)


@router.get("/status")
def status(s: Services = Depends(svc)):
    screen = s.screen()
    on = s.on   # Needs attention only asks about modules that are on (Settings > Modules)
    return {
        "calendar_errors": s.calendar.errors,
        "calendar_refreshed": s.calendar.last_refresh.isoformat(timespec="minutes") if s.calendar.last_refresh else None,
        "weather_error": s.weather.error if on("weather") else None,
        "weather_source": s.weather.label() if on("weather") else "",
        "home_error": s.home.error if on("house") else None,
        "screen_total": screen["total_label"], "screen_headline": screen["headline"],
        "screen_new_week_due": screen["new_week_due"] and on("screen_time"),
        "photos": len(s.photos.listing()) if on("photos") else 0,
        "photo_sources": s.photos.source_status() if on("photos") else [],
        "modules": sorted(mods_on(s)),
    }


def page_modules() -> dict:
    from .modules import PAGE_MODULE
    return PAGE_MODULE


def mods_on(s: Services):
    from .modules import on_set
    return on_set(s.settings)


# ---------------- birthday portraits (Settings > Special days) ----------------

def _portraits_view(s: Services) -> dict:
    from .portraits import people_of
    idx = s.portraits.index()
    names = (s.settings.special or {}).get("portrait_names") or {}
    from .admin_providers import google_view
    people = []
    for p in people_of(s.settings):
        info = idx.get(p["slug"]) or {}
        people.append({**p, "photos_name": names.get(p["slug"], ""), "portrait": s.portrait_url({**p, "use_initial": False}),
                       "source": info.get("source") or ("kid photo" if s.portrait_url(p) else ""), "taken": info.get("taken", "")})
    return {"people": people, "google": google_view(s)}


@router.get("/portraits")
def get_portraits(s: Services = Depends(svc)):
    return _portraits_view(s)


@router.put("/portraits/names")
def put_portrait_names(body: dict, request: Request, s: Services = Depends(svc)):
    """What Apple Photos calls each person, when it isn't their name here (e.g. "Sam Example" for Child 3)."""
    def m(store, cfg):
        cur = dict(cfg.get("special_days") or {})
        cur["portrait_names"] = {sp.slug(k): str(v).strip()[:60] for k, v in (body or {}).items() if str(v).strip()}
        store["special_days"] = cur
    return _save(request, s, m)


@router.post("/portraits/{key}")
async def upload_portrait(key: str, file: UploadFile, s: Services = Depends(svc)):
    from .portraits import open_image, people_of, slug as pslug
    if pslug(key) not in {p["slug"] for p in people_of(s.settings)}:
        raise HTTPException(404, "No one by that name.")
    try:
        im = open_image(await file.read())
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return s.portraits.save(key, im, "upload")


@router.delete("/portraits/{key}")
def remove_portrait(key: str, s: Services = Depends(svc)):
    """Take the portrait off (the next Mac sync can bring a new one from Apple Photos)."""
    return {"ok": s.portraits.remove(key)}


@router.put("/google")
def put_google(body: dict, request: Request, s: Services = Depends(svc)):
    cid = str(body.get("client_id") or "").strip()
    if cid and not cid.endswith(".apps.googleusercontent.com"):
        raise HTTPException(400, "The client ID ends in .apps.googleusercontent.com")
    def m(store, cfg):
        store["google"] = dict(cfg.get("google") or {}, client_id=cid)
        sd = dict(store.get("special_days") or {})
        if sd.pop("google_photos", None) is not None:   # where older versions kept it
            store["special_days"] = sd
        if body.get("client_secret"):
            store.setdefault("secrets", {})["google_client_secret"] = str(body["client_secret"]).strip()
    return _save(request, s, m)


@router.get("/google/connect")
def google_connect(features: str = "photos,tasks", s: Services = Depends(svc)):
    """Google's sign-in page for these features (comma separated: photos, tasks), added to what's allowed already."""
    from .google_photos import GoogleError
    try:
        return {"url": s.google().auth_url([f.strip() for f in features.split(",")])}
    except GoogleError as exc:
        raise HTTPException(400, str(exc))


@router.post("/google/disconnect")
def google_disconnect(s: Services = Depends(svc)):
    s.google().disconnect()
    return {"ok": True}


@router.post("/portraits/{key}/google")
def google_pick_start(key: str, s: Services = Depends(svc)):
    """Open a Google Photos picking session; the parent picks a few recent photos of this person."""
    from .google_photos import GoogleError
    try:
        sess = s.google_photos().new_session()
    except GoogleError as exc:
        raise HTTPException(400, str(exc))
    return sess


@router.get("/portraits/{key}/google/{sid}")
def google_pick_poll(key: str, sid: str, s: Services = Depends(svc)):
    """Once the parent taps Done: download what they picked (newest first) and keep the newest one with a single face."""
    from .google_photos import MAX_PICKED, GoogleError
    from .portraits import best_portrait, open_image
    g = s.google_photos()
    try:
        if not g.session_done(sid):
            return {"done": False}
        items = sorted(g.picked(sid), key=lambda i: i.get("createTime", ""), reverse=True)[:MAX_PICKED]
        if not items:
            return {"done": True, "ok": False, "message": "Nothing was picked."}
        cands = []
        for it in items:
            try:
                cands.append((open_image(g.download(it)), it.get("createTime", "")))
            except (GoogleError, ValueError):
                continue
            if len(cands) >= 12:   # plenty to find one good face; keeps it quick
                break
        best = best_portrait(cands)
        if not best:
            return {"done": True, "ok": False, "message": "Couldn't download the picked photos."}
        im, taken, face = best
        info = s.portraits.save(key, im, "google", taken=taken, face=face)
        g.end_session(sid)
        return {"done": True, "ok": True, "face": bool(face), "picked": len(items), **info}
    except GoogleError as exc:
        raise HTTPException(400, str(exc))


# ---------------- Settings > Family: everyone in one place ----------------
# One list for parents and kids: names and nicknames (who an event is about), birthdays (the birthday card comes up
# by itself), the name Apple Photos knows them by, one photo (chore avatar and birthday card), and, for kids,
# the initial, color and screen-time name.

DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@router.get("/family")
def get_family(s: Services = Depends(svc)):
    view = _portraits_view(s)
    kids = {k.id: k for k in s.settings.kids}
    members = []
    for p in view["people"]:
        k = kids.get(p.get("kid"))
        members.append({"key": p["slug"], "name": p["name"], "aliases": p["aliases"], "birthday": p.get("birthday", ""),
                        "use_initial": bool(p.get("use_initial")),
                        "photos_name": p["photos_name"], "photo": p["portrait"], "source": p["source"], "taken": p["taken"],
                        "kid": {"id": k.id, "initial": k.initial, "color": k.color, "screen_time_nickname": k.screen_time_nickname or ""} if k else None})
    return {"members": members, "google": view["google"]}


@router.put("/family")
def put_family(body: dict, request: Request, s: Services = Depends(svc)):
    from .portraits import slug as pslug
    members = body.get("members") or []
    seen, people, kid_rows, names, renames = set(), [], [], {}, []
    for m in members:
        name = str(m.get("name") or "").strip()[:30]
        if not name:
            raise HTTPException(400, "Everyone needs a name.")
        key = pslug(name)
        if key in seen:
            raise HTTPException(400, f"Two people are named {name}.")
        seen.add(key)
        aliases = m.get("aliases") or []
        if isinstance(aliases, str):
            aliases = aliases.split(",")
        aliases = [a.strip()[:30] for a in aliases if a and a.strip()]
        bday = str(m.get("birthday") or "").strip()
        if bday and not DATE.match(bday):
            raise HTTPException(400, f"{name}'s birthday: pick a date.")
        people.append({"name": name, **({"aliases": aliases} if aliases else {}), **({"birthday": bday} if bday else {}),
                       **({"use_initial": True} if m.get("use_initial") else {})})
        if str(m.get("photos_name") or "").strip():
            names[key] = str(m["photos_name"]).strip()[:120]
        if m.get("key") and pslug(m["key"]) != key:
            renames.append((m["key"], key))
        k = m.get("kid")
        if k:
            kid_rows.append({**k, "name": name})

    def mut(store, cfg):
        store["people"] = people
        old = {k["id"]: k for k in cfg.get("kids", [])}
        out, ids = [], set()
        for k in kid_rows:
            kid_id = k.get("id") or re.sub(r"[^a-z0-9]+", "", k["name"].lower()) or "kid"
            if kid_id in ids:
                raise HTTPException(400, f"Two kids share the id '{kid_id}'.")
            ids.add(kid_id)
            color = k.get("color") or old.get(kid_id, {}).get("color") or "#1F7576"
            if not HEX.match(color):
                raise HTTPException(400, f"Pick a color for {k['name']}.")
            out.append({"id": kid_id, "name": k["name"][:20], "initial": (str(k.get("initial") or k["name"][0]).strip())[:2],
                        "color": color, "screen_time_nickname": str(k.get("screen_time_nickname") or k["name"]),
                        "photo": old.get(kid_id, {}).get("photo")})
        store["kids"] = out
        if "chores" not in store:
            store["chores"] = cfg.get("chores", [])
        store["chores"] = [c for c in store["chores"] if c["kid"] in ids]  # someone no longer a kid: their chores go
        sd = dict(cfg.get("special_days") or {})
        sd["portrait_names"] = names
        store["special_days"] = sd

    for a, b in renames:
        s.portraits.rename(a, b)
    return _save(request, s, mut)
