"""Load frame settings from config/frame.yaml, chores from config/chores.yaml,
and secrets from the environment (.env).

Secrets never live in the YAML files: calendar iCal addresses, the Home
Assistant token and the parent PIN hashes come from env vars or the settings
store (data/settings.json).
"""
from __future__ import annotations

import json
import os
import re
import secrets
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

from .screentime import ScreenTimeSettings

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = Path(os.environ.get("FRAME_CONFIG_DIR", ROOT / "config"))
DATA_DIR = Path(os.environ.get("FRAME_DATA_DIR", ROOT / "data"))
WEB_DIR = ROOT / "web"


def load_dotenv(path: Path = ROOT / ".env") -> None:
    """Tiny .env reader so we don't need python-dotenv. Existing env wins."""
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), value)


@dataclass
class Kid:
    id: str
    name: str
    initial: str
    color: str
    tint: str
    screen_time_nickname: Optional[str] = None
    photo: Optional[str] = None  # version stamp of an uploaded face photo, if any


@dataclass
class CalendarSource:
    key: str
    label: str
    color: str
    tint: str
    ics_url: Optional[str] = None
    ics_file: Optional[str] = None
    who_default: str = ""
    filter: dict = field(default_factory=dict)
    # Where it comes from. kind "ics" is any iCal/webcal address (Google, Outlook,
    # iCloud public link); "caldav" is a private account (iCloud with an app-specific
    # password, Fastmail, Nextcloud). provider is only a label for Settings.
    kind: str = "ics"
    provider: str = ""
    caldav_server: str = ""
    caldav_user: str = ""
    caldav_password: str = ""
    caldav_calendar: str = ""   # the calendar's own address on the CalDAV server


@dataclass
class ChoreDef:
    id: str
    kid: str
    title: str
    minutes: int
    days: list[str]


@dataclass
class HAEntity:
    entity: str
    icon: str
    states: dict[str, str]
    alert_when: list[str]


@dataclass
class Settings:
    timezone: str
    latitude: Optional[float]
    longitude: Optional[float]
    family_name: str
    family_initial: str
    idle_minutes_to_photos: float
    return_to_today_minutes: float
    photo_seconds: int
    night_start: str
    night_end: str
    kids: list[Kid]
    people: list[str]
    calendars: list[CalendarSource]
    calendar_refresh_minutes: int
    chores: list[ChoreDef]
    screen_time: ScreenTimeSettings
    ha_enabled: bool
    ha_url: Optional[str]
    ha_token: Optional[str]
    ha_entities: list[HAEntity]
    photos_folder: Path
    photo_sources: list[dict]
    pin_hash: Optional[str]                      # the shared PIN (logs as "Parent")
    parent_pins: list[tuple[str, str]]           # (name, hash): a PIN each, so the log says who
    secret: str
    upload_token: str
    demo: bool
    addon: bool
    weather_user_agent: str
    merge_shared_events: bool = True
    special: dict = field(default_factory=dict)  # Settings > Special days (see app/special.py)
    lists: dict = field(default_factory=dict)    # Settings > Lists (see app/lists.py)
    frames: list = field(default_factory=list)   # Settings > Frames (see app/frames.py)
    weather: dict = field(default_factory=dict)  # Settings > General: source and units (see app/weather.py)
    access_team_domain: Optional[str] = None
    access_aud: Optional[str] = None
    modules_on: Optional[frozenset] = None       # Settings > Modules: the ones that are on (see app/modules.py)


DAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DAY_GROUPS = {
    "weekdays": ["mon", "tue", "wed", "thu", "fri"],
    "weekend": ["sat", "sun"],
    "daily": DAY_KEYS,
}


def _expand_days(days: Any) -> list[str]:
    if days is None:
        return DAY_GROUPS["daily"]
    if isinstance(days, str):
        days = [days]
    out: list[str] = []
    for d in days:
        d = str(d).lower()[:3] if str(d).lower() not in DAY_GROUPS else str(d).lower()
        out.extend(DAY_GROUPS.get(d, [d]))
    bad = [d for d in out if d not in DAY_KEYS]
    if bad:
        raise ValueError(f"Unknown day name(s) in chores config: {bad}")
    return out


def tint_of(color: str, amount: float = 0.84) -> str:
    """A pale version of a kid's color for backgrounds: mix with white."""
    c = color.lstrip("#")
    r, g, b = (int(c[i:i + 2], 16) for i in (0, 2, 4))
    mix = lambda v: round(v + (255 - v) * amount)
    return f"#{mix(r):02X}{mix(g):02X}{mix(b):02X}"


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-")


def _read_yaml(name: str, demo: bool) -> dict:
    """local/config/<name>.yaml (the private overlay, app/overlay.py), then config/<name>.yaml, then the example.
    Demo mode always reads the example, so the sample family never mixes with a real one."""
    from . import overlay
    real = CONFIG_DIR / f"{name}.yaml"
    example = CONFIG_DIR / f"{name}.example.yaml"
    path = example if demo else overlay.config_file(name) or (real if real.exists() else example)
    if not path.exists():
        raise FileNotFoundError(f"Missing {real} (copy {example.name} to {real.name})")
    return yaml.safe_load(path.read_text()) or {}


def load_settings() -> Settings:
    from . import overlay
    load_dotenv(overlay.env_file())   # the private overlay's secrets first (existing env still wins)
    load_dotenv()
    demo = os.environ.get("FRAME_DEMO", "").lower() in ("1", "true", "yes")
    cfg = effective_config(demo)
    chores_cfg = {"chores": cfg["chores"]}
    store = read_store(demo)

    kids = []
    for k in cfg.get("kids", []):
        k = {f: k.get(f) for f in ("id", "name", "initial", "color", "tint", "screen_time_nickname", "photo")}
        k["initial"] = (k["initial"] or k["name"][:1]).strip()[:2]
        k["tint"] = k["tint"] or tint_of(k["color"])
        kids.append(Kid(**k))
    kid_ids = {k.id for k in kids}

    calendars = []
    for c in cfg.get("calendars", []):
        c = dict(c)
        c.pop("url_hint", None)
        mode = c.pop("filter_mode", None)
        emails = [e.strip().lower() for e in str(c.pop("filter_emails", "") or "").split(",") if e.strip()]
        if mode == "family":
            # Only events that involve one of these people, or name a family member in the title.
            names = [p if isinstance(p, str) else p["name"] for p in cfg.get("people", [])]
            names += [a for p in cfg.get("people", []) if isinstance(p, dict) for a in p.get("aliases", [])]
            pat = "(?i)\\b(" + "|".join(re.escape(n) for n in names + ["kids", "family"]) + ")\\b"
            keep = {k: v for k, v in (c.get("filter") or {}).items() if k in ("skip_declined_by", "exclude_titles_matching")}
            c["filter"] = {**keep, "require_attendee_any": emails, "include_titles_matching": [pat]}
        elif mode == "all":
            c["filter"] = {k: v for k, v in (c.get("filter") or {}).items() if k in ("skip_declined_by",)}
        pw_env = c.pop("caldav_password_env", None)
        if pw_env:
            c["caldav_password"] = os.environ.get(pw_env, "")
        env_name = c.pop("ics_url_env", None)
        url = os.environ.get(env_name) if env_name else c.pop("ics_url", None)
        c.pop("ics_url", None)
        if c.get("kind") == "caldav" and not demo:
            c.pop("ics_file", None)  # sample data never stands in for a private calendar
        if demo and c.get("ics_file"):
            url = None
        elif env_name:
            # Live mode with an env var: the demo file must never stand in for a
            # missing secret address. A missing address shows as a calendar error.
            c.pop("ics_file", None)
        c["tint"] = c.get("tint") or tint_of(c["color"], 0.88)
        if url and url.startswith(("webcal://", "webcals://")):
            url = "https://" + url.split("://", 1)[1]
        allowed = ("key", "label", "color", "tint", "ics_file", "who_default", "filter", "kind", "provider",
                   "caldav_server", "caldav_user", "caldav_password", "caldav_calendar")
        calendars.append(CalendarSource(ics_url=url or None, **{k: v for k, v in c.items() if k in allowed}))

    chores = []
    seen: set[str] = set()
    for ch in chores_cfg.get("chores", []):
        if ch["kid"] not in kid_ids:
            raise ValueError(f"Chore '{ch['title']}' names unknown kid '{ch['kid']}'")
        minutes = int(ch["minutes"])
        if not 1 <= minutes <= 240:
            raise ValueError(f"Chore '{ch['title']}' must be worth 1 to 240 minutes")
        cid = ch.get("id") or f"{ch['kid']}-{_slug(ch['title'])}"
        if cid in seen:
            raise ValueError(f"Duplicate chore id '{cid}'")
        seen.add(cid)
        chores.append(ChoreDef(id=cid, kid=ch["kid"], title=ch["title"], minutes=minutes,
                               days=_expand_days(ch.get("days"))))

    loc = cfg.get("location", {}) or {}
    night = cfg.get("night", {}) or {}
    st = cfg.get("screen_time", {}) or {}
    ha = cfg.get("home_assistant", {}) or {}
    photos = cfg.get("photos", {}) or {}
    photos_folder = Path(os.environ.get("FRAME_PHOTOS_DIR") or photos.get("folder", "photos"))
    if not photos_folder.is_absolute():
        photos_folder = ROOT / photos_folder

    # Secrets set from the admin panel live in the store and win over .env.
    sec = store.get("secrets", {})
    if not sec.get("secret") or not sec.get("upload_token"):
        sec.setdefault("secret", os.environ.get("FRAME_SECRET") or secrets.token_urlsafe(32))
        sec.setdefault("upload_token", secrets.token_urlsafe(24))
        store["secrets"] = sec
        write_store(store, demo)
    supervisor_token = os.environ.get("SUPERVISOR_TOKEN")

    from . import modules as _mods
    from . import packs as _packs
    modules_on = _mods.resolve(cfg, demo, _packs.load(demo))

    return Settings(
        modules_on=modules_on,
        timezone=cfg.get("timezone") or os.environ.get("TZ") or "America/New_York",
        latitude=loc.get("latitude"),
        longitude=loc.get("longitude"),
        family_name=cfg.get("family_name", "Our Family"),
        family_initial=str(cfg.get("family_initial") or "")[:1].upper(),
        idle_minutes_to_photos=float(cfg.get("idle_minutes_to_photos", 5)),
        return_to_today_minutes=float(cfg.get("return_to_today_minutes", 2)),
        photo_seconds=int(cfg.get("photo_seconds", 20)),
        night_start=str(night.get("start", "22:00")),
        night_end=str(night.get("end", "06:00")),
        kids=kids,
        people=cfg.get("people", []),
        calendars=calendars,
        calendar_refresh_minutes=int(cfg.get("calendar_refresh_minutes", 5)),
        chores=chores,
        screen_time=ScreenTimeSettings.from_store(st),
        ha_enabled=bool(ha.get("enabled", False)),
        # As a Home Assistant add-on, talk to HA through the Supervisor with its own token.
        ha_url="http://supervisor/core" if supervisor_token else ha.get("url"),
        ha_token=supervisor_token or sec.get("ha_token") or os.environ.get("HA_TOKEN"),
        ha_entities=[HAEntity(entity=e["entity"], icon=e.get("icon", "home"),
                              states=e.get("states", {}), alert_when=e.get("alert_when", []))
                     for e in ha.get("entities", [])],
        photos_folder=photos_folder,
        photo_sources=[s for s in photos.get("sources", []) if s.get("enabled", True)],
        pin_hash=sec.get("pin_hash") or os.environ.get("FRAME_PIN_HASH") or None,
        parent_pins=[(p["name"], p["hash"]) for p in sec.get("parent_pins", []) if p.get("name") and p.get("hash")],
        secret=sec["secret"],
        upload_token=sec["upload_token"],
        demo=demo,
        addon=bool(supervisor_token) or os.environ.get("FRAME_ADDON") == "1",
        merge_shared_events=bool(cfg.get("merge_shared_events", True)),
        special=_special_cfg(cfg.get("special_days") or {}, demo),
        lists=dict(cfg.get("lists") or {}),
        frames=list(cfg.get("frames") or (_demo_frames() if demo else [])),
        weather=dict(cfg.get("weather") or {}),
        access_team_domain=(cfg.get("cloudflare_access") or {}).get("team_domain"),
        access_aud=(cfg.get("cloudflare_access") or {}).get("aud"),
        weather_user_agent=os.environ.get(
            "WEATHER_USER_AGENT", "doorpost (home dashboard; contact via config)"),
    )


def _demo_frames() -> list:
    from .frames import DEMO_FRAMES  # the kitchen, plus a tall playroom frame on the Kids screen
    return [dict(f) for f in DEMO_FRAMES]


def _special_cfg(sd: dict, demo: bool) -> dict:
    from .special import US_HOLIDAYS_URL
    sd = dict(sd)
    sd.setdefault("holiday_url", US_HOLIDAYS_URL)
    if demo:  # sample data: a saved copy of Google's U.S. holidays, no network
        sd["holiday_url"] = str(CONFIG_DIR / "demo-holidays.ics")
    return sd


# ---------- the admin panel's settings store ----------

STORE_KEYS = ("merge_shared_events", "special_days", "frame_url", "lan_url", "cloudflare_access", "timezone", "location", "family_name", "family_initial", "idle_minutes_to_photos", "return_to_today_minutes",
              "photo_seconds", "night", "kids", "people", "calendars", "calendar_refresh_minutes",
              "screen_time", "home_assistant", "photos", "lists", "frames", "google", "weather", "modules", "settings_look")


def store_path(demo: bool) -> Path:
    return DATA_DIR / ("settings.demo.json" if demo else "settings.json")


def read_store(demo: bool) -> dict:
    p = store_path(demo)
    if not p.exists():
        return {}
    return json.loads(p.read_text() or "{}")


def write_store(data: dict, demo: bool) -> None:
    p = store_path(demo)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    os.chmod(tmp, 0o600)  # holds calendar addresses and logins
    tmp.replace(p)


def effective_config(demo: bool) -> dict:
    """Everything the admin panel edits: YAML defaults with the store laid over them."""
    cfg = _read_yaml("frame", demo)
    chores_cfg = _read_yaml("chores", demo)
    store = read_store(demo)
    for k in STORE_KEYS:
        if k in store:
            cfg[k] = store[k]
    cfg["chores"] = store["chores"] if "chores" in store else chores_cfg.get("chores", [])
    return cfg
