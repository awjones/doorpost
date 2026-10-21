"""Modules: the parts of the frame a family can turn on and off (Settings > Modules).

Core is always on: the frame shell, the clock, night mode, Settings, parent PINs, the family
list and the calendar. Everything else is a module with a small manifest below.

Saved in the settings store as `modules: {id: bool}`. A module that is off:
  - its addresses answer 404 (`ROUTES` below, checked by `guard` for every request),
  - its frame screens, Today pieces and phone-page tabs disappear (`narrow` and `fit_profile`;
    the frame page reads the list of modules that are on from /api/frame),
  - its Settings page leaves the menu, its background jobs stop, and Settings > Overview
    stops asking about it.
Turning a module off never deletes anything. Turning it back on brings it all back.
"""
from __future__ import annotations

from typing import Callable, Optional

# needs badges: what a module asks of the family's setup (shown as small labels in Settings > Modules)
NEEDS = {
    "internet": "Internet",
    "mac": "A Mac",
    "google": "Google",
    "apple": "Apple",
    "home_assistant": "Home Assistant",
    "art_pack": "An art pack",
    "domain": "Your own web address",
    "frame": "Another frame",
    "nothing": "Nothing extra",
    "email": "An email account",
}

MODULES: list[dict] = [
    {"id": "calendar", "name": "Calendar", "icon": "calendar", "always_on": True,
     "description": "Today, the week, the month and the next 7 days from your shared calendars.",
     "needs": ["internet"], "needs_text": "A private calendar address (Google, Apple or Outlook)",
     "screens": ["calendar"], "admin_pages": ["calendars"], "routes": [], "jobs": ["read the calendars every few minutes"]},
    {"id": "weather", "name": "Weather", "icon": "partly", "default_on": True,
     "description": "Now, today and the next 3 days on the Today screen.",
     "needs": ["internet"], "needs_text": "Your town or ZIP code; no account",
     "today": ["weather"], "routes": [], "jobs": ["read the forecast"]},
    {"id": "chores", "name": "Chores", "icon": "chores", "default_on": True,
     "description": "Kids tap “I did it”; a parent approves on the frame or a phone.",
     "needs": ["nothing"], "needs_text": "Nothing extra",
     "screens": ["chores"], "today": ["chores"], "admin_pages": ["chores"],
     "routes": ["/api/chores", "/api/parent/chores", "/api/admin/chores", "/admin/chores"]},
    {"id": "screen_time", "name": "Screen time", "icon": "hourglass", "default_on": True, "requires": ["chores"],
     "description": "Chores fill a weekend pool of minutes; the frame shows who filled it.",
     "needs": ["nothing"], "needs_text": "Chores turned on",
     "screens": ["screen"], "today": ["screen"], "admin_pages": ["screen-time"],
     "routes": ["/api/parent/screen", "/api/admin/screen_time", "/admin/screen-time"]},
    {"id": "email_updates", "name": "Email updates", "icon": "mail", "default_on": True, "requires": ["chores"],
     "description": "A daily chore recap with quick approve buttons, and the weekend’s screen time for setting each device.",
     "needs": ["email"], "needs_text": "An email account to send from (Gmail works, with an app password)",
     "admin_pages": ["email-updates"],
     "routes": ["/e", "/api/email", "/api/admin/email-updates", "/admin/email-updates"],
     "jobs": ["send the chore and screen time emails at their times"]},
    {"id": "photos", "name": "Photos", "icon": "photos", "default_on": True,
     "description": "A slideshow when the frame sits idle, with the clock and next event.",
     "needs": ["nothing"], "needs_text": "Photos you upload, a shared album, or a photos folder on the home server",
     "screens": ["photos"], "admin_pages": ["photos"],
     "routes": ["/api/photos", "/photos", "/api/admin/photos", "/admin/photos"],
     "jobs": ["look for new photos", "download shared albums", "the Mac's Favorites sync"]},
    {"id": "portraits", "name": "Profile photos", "icon": "face", "default_on": True,
     "description": "Faces on the chore buttons and birthday cards, instead of a colored initial.",
     "needs": ["nothing"], "needs_text": "A photo of each person, or a Mac or Google Photos to find them",
     "routes": ["/portraits", "/api/portraits", "/api/admin/portraits", "/kids/*", "/api/admin/kids/*/photo"],
     "jobs": ["the Mac's portrait sync"]},
    {"id": "lists", "name": "Lists", "icon": "list", "default_on": False,
     "description": "Groceries and to-dos you can check off or add to on the frame.",
     "needs": ["mac", "google"], "needs_text": "A Mac at home for Apple Reminders, or Google Tasks",
     "screens": ["lists"], "today": ["groceries"], "admin_pages": ["lists"],
     "routes": ["/api/lists", "/api/admin/lists", "/admin/lists"], "jobs": ["sync Google Tasks", "the Mac's Reminders sync"]},
    {"id": "house", "name": "Home Assistant", "icon": "home", "default_on": False,
     "description": "Garage, doors and locks in the line at the bottom of the frame.",
     "needs": ["home_assistant"], "needs_text": "Home Assistant on your home network",
     "today": ["homebar"], "admin_pages": ["house"],
     "routes": ["/api/admin/home_assistant", "/api/admin/ha", "/admin/house"], "jobs": ["read the doors and locks"]},
    {"id": "special_days", "name": "Special days", "icon": "star", "default_on": True,
     "description": "Holidays and your starred events take over their day with a picture and a countdown.",
     "needs": ["art_pack"], "needs_text": "An art pack for pictures (Holidays comes installed)",
     "today": ["countdown"], "admin_pages": ["special-days"],
     "routes": ["/special", "/api/admin/special", "/admin/special-days"], "jobs": ["read the holiday calendar once a day"]},
    {"id": "lords_day", "name": "Lord’s Day pictures", "icon": "sun", "default_on": True, "requires": ["special_days"],
     "pack": "weekly",   # only offered when an installed art pack has a weekly Sunday series (the Faith pack)
     "description": "A picture, a verse and a short note every Sunday, from the Faith art pack’s series.",
     "needs": ["art_pack"], "needs_text": "The Faith art pack and Special days turned on", "routes": []},
    {"id": "remote_access", "name": "Sign in from anywhere", "icon": "globe", "default_on": False,
     "description": "Open the parent page and Settings away from home through Cloudflare Access.",
     "needs": ["internet", "domain"], "needs_text": "A Cloudflare account and your own web address", "routes": []},
    {"id": "multi_frame", "name": "Multiple frames", "icon": "frames", "default_on": False,
     "description": "Give each screen in the house its own size, look and screens.",
     "needs": ["frame"], "needs_text": "A second frame on the same network",
     "routes": ["/api/parent/frames"]},
    {"id": "kids_view", "name": "Kids view", "icon": "people", "default_on": False,
     "description": "A picture-first home screen for a playroom frame, for kids who can’t read yet.",
     "needs": ["nothing"], "needs_text": "Nothing extra (best on its own frame)",
     "screens": ["kids"], "routes": []},
]
BY_ID = {m["id"]: m for m in MODULES}
IDS = [m["id"] for m in MODULES]

# Frame screens that belong to a module (Settings > Frames lists only the ones that are on).
SCREEN_MODULE = {s: m["id"] for m in MODULES if not m.get("always_on") for s in m.get("screens", [])}
# Settings pages that belong to a module (they leave the menu when it is off).
PAGE_MODULE = {p: m["id"] for m in MODULES if not m.get("always_on") for p in m.get("admin_pages", [])}


# ---------------- which modules are on ----------------

def _configured(mid: str, cfg: dict) -> bool:
    """For a setup saved before modules existed: on when it's already being used."""
    if mid == "lists":
        lc = cfg.get("lists") or {}
        return bool(lc.get("shown") or lc.get("google"))
    if mid == "house":
        return bool((cfg.get("home_assistant") or {}).get("enabled"))
    if mid == "remote_access":
        ca = cfg.get("cloudflare_access") or {}
        return bool(ca.get("team_domain") and ca.get("aud"))
    if mid == "multi_frame":
        return len(cfg.get("frames") or []) > 1
    if mid == "kids_view":
        return any((f or {}).get("home") == "kids" for f in cfg.get("frames") or [])
    return bool(BY_ID[mid].get("default_on"))


def available(mid: str, packs=None) -> bool:
    """A module that needs something installed (the Faith pack's Sunday series) is offered only when it is."""
    m = BY_ID[mid]
    if m.get("pack") and packs is not None:
        return bool(getattr(packs, m["pack"], None))
    return True


def chosen(cfg: dict, demo: bool) -> dict:
    """What the family picked (or the default for each), before `requires` is applied."""
    saved = cfg.get("modules") or {}
    out = {}
    for m in MODULES:
        mid = m["id"]
        if m.get("always_on"):
            out[mid] = True
        elif mid in saved:
            out[mid] = bool(saved[mid])
        else:
            out[mid] = True if demo else _configured(mid, cfg)
    return out


def resolve(cfg: dict, demo: bool, packs=None) -> frozenset:
    """The modules that are on: chosen, available, and with every module they need on too."""
    pick = chosen(cfg, demo)
    on = {mid for mid, v in pick.items() if v and available(mid, packs)}
    changed = True
    while changed:   # screen time needs chores; Lord's Day pictures need special days
        changed = False
        for mid in list(on):
            if any(r not in on for r in BY_ID[mid].get("requires", [])):
                on.discard(mid)
                changed = True
    return frozenset(on)


def on_set(settings) -> frozenset:
    got = getattr(settings, "modules_on", None)
    return frozenset(IDS) if got is None else got


def is_on(settings, mid: str) -> bool:
    return mid in on_set(settings)


def apply_choice(current: dict, changes: dict, packs=None) -> tuple[dict, list[str]]:
    """Settings > Modules save: the new {id: bool} map and plain notes about what else changed.
    Turning screen time on turns chores on too. Turning chores off leaves screen time chosen but
    resting (`resolve` keeps it off), so turning chores back on brings screen time back as it was."""
    new = dict(current)
    notes: list[str] = []
    for mid, v in changes.items():
        if mid not in BY_ID or BY_ID[mid].get("always_on"):
            continue
        if v and not available(mid, packs):
            raise ValueError(f"{BY_ID[mid]['name']} needs the Faith art pack. Install it in Settings > Art packs first.")
        new[mid] = bool(v)
    changed = True
    while changed:
        changed = False
        for m in MODULES:
            if not new.get(m["id"]) or not available(m["id"], packs):
                continue
            for r in m.get("requires", []):
                if new.get(r):
                    continue
                if changes.get(m["id"]) is True and changes.get(r) is False:
                    raise ValueError(f"{m['name']} needs {BY_ID[r]['name']}. Leave {BY_ID[r]['name']} on to use it.")
                if changes.get(m["id"]) is True:
                    new[r] = True   # just turned on: bring what it needs
                    notes.append(f"{BY_ID[r]['name']} was turned on too, because {m['name']} needs it.")
                    changed = True
                elif changes.get(r) is False:
                    notes.append(f"{m['name']} is off too while {BY_ID[r]['name']} is off. It comes back when you turn {BY_ID[r]['name']} on.")
    return new, notes


# ---------------- addresses ----------------

def _match(path: str, pattern: str) -> bool:
    if "*" in pattern:
        a, b = pattern.strip("/").split("/"), path.strip("/").split("/")
        if pattern.endswith("/*"):
            return len(b) >= len(a) and all(x == "*" or x == y for x, y in zip(a, b))
        return len(a) == len(b) and all(x == "*" or x == y for x, y in zip(a, b))
    return path == pattern or path.startswith(pattern + "/")


ROUTES = [(p, m["id"]) for m in MODULES for p in m.get("routes", [])]


def owner(path: str) -> Optional[str]:
    """The module an address belongs to, or None for core addresses."""
    for p, mid in ROUTES:
        if _match(path, p):
            return mid
    return None


def guard(path: str, settings) -> Optional[str]:
    """The module that is off and owns this address (so it answers 404), else None."""
    mid = owner(path)
    return mid if mid and not is_on(settings, mid) else None


def enabled(mid: str) -> Callable:
    """A FastAPI dependency for new routes: 404 when the module is off, e.g. Depends(enabled("chores"))."""
    from fastapi import HTTPException, Request

    def dep(request: Request) -> None:
        if not is_on(request.app.state.services.settings, mid):
            raise HTTPException(404, f"{BY_ID[mid]['name']} is turned off in Settings > Modules.")
    return dep


# ---------------- frames ----------------

def fit_profile(profile: dict, settings) -> dict:
    """A frame profile with the screens of modules that are off taken out (stored settings keep them)."""
    on = on_set(settings)
    p = dict(profile)
    p["screens"] = [s for s in p["screens"] if SCREEN_MODULE.get(s, "calendar") in on]
    if SCREEN_MODULE.get(p["home"], "calendar") not in on:
        p["home"] = "today"
    if p["home"] not in p["screens"]:
        p["screens"] = [p["home"]] + p["screens"]
    return p


def live_profiles(profiles: list[dict], settings) -> list[dict]:
    """The frames in use: just the first one when Multiple frames is off."""
    if not is_on(settings, "multi_frame"):
        profiles = profiles[:1]
    return [fit_profile(p, settings) for p in profiles]


def keep_hidden(cleaned: list[dict], stored: list[dict], settings) -> list[dict]:
    """Settings > Frames save while modules are off: keep what Settings couldn't show
    (the other frames, and screens of modules that are off), so turning them back on brings them back."""
    on = on_set(settings)
    old = {p.get("id"): p for p in stored}
    out = []
    for p in cleaned:
        prev = old.get(p["id"]) or {}
        hidden = [s for s in prev.get("screens") or [] if SCREEN_MODULE.get(s, "calendar") not in on and s not in p["screens"]]
        p = dict(p, screens=p["screens"] + hidden)
        if SCREEN_MODULE.get(prev.get("home"), "calendar") not in on and p["home"] == "today":
            p["home"] = prev["home"]
        out.append(p)
    if not is_on(settings, "multi_frame"):
        ids = {p["id"] for p in out}
        out = out[:1] + [dict(p) for p in stored[1:] if p.get("id") not in ids]
    return out


# ---------------- the frame's data ----------------

EMPTY_LISTS = {"lists": [], "home": None, "can_add": False, "can_check": False}


def narrow(payload: dict, settings) -> dict:
    """/api/frame without what belongs to modules that are off. Never changes the shared payload."""
    on = on_set(settings)
    p = dict(payload)
    p["modules"] = sorted(on)
    if "weather" not in on:
        p["weather"] = None
    if "house" not in on:
        p["home"] = []
    if "lists" not in on:
        p["lists"] = dict(EMPTY_LISTS)
    if "photos" not in on:
        p["photos_count"], p["photos_version"] = 0, ""
    if "screen_time" not in on:
        p["screen"] = None
    if "chores" not in on or "portraits" not in on:
        kids = []
        for k in p.get("kids") or []:
            k = dict(k)
            if "chores" not in on:
                k.update(chores=[], done=0, total=0, waiting_count=0, waiting_minutes=0)
            if "portraits" not in on:
                k["photo"] = None
            kids.append(k)
        p["kids"] = kids
    if "special_days" not in on and p.get("calendar"):
        cal = dict(p["calendar"])
        cal["upcoming"] = None
        p["calendar"] = cal
    status = dict(p.get("status") or {})
    for key, mid in (("weather_error", "weather"), ("home_error", "house"), ("screen_time_error", "screen_time")):
        if mid not in on:
            status.pop(key, None)
    p["status"] = status
    return p


class NoSpecialDays:
    """Stands in for app/special.py's SpecialDays when Special days is off: no day is special."""
    countdown_days = -1
    church_defaults: dict = {}

    def for_day(self, d, events, today):
        return None, []


# ---------------- Settings > Modules ----------------

def _status(text: str) -> dict:
    text = text or ""
    return {"status": text.lstrip("!"), "status_tone": "warn" if text.startswith("!") else "ok"}


def rows(settings, cfg: dict, packs, status: Callable[[str], str]) -> list[dict]:
    """One row per module for the Settings page (modules that need a missing pack are left out)."""
    pick = chosen(cfg, settings.demo)
    on = on_set(settings)
    out = []
    for m in MODULES:
        mid = m["id"]
        if not available(mid, packs):
            continue
        blocked = [BY_ID[r]["name"] for r in m.get("requires", []) if r not in on]
        out.append({"id": mid, "name": m["name"], "icon": m["icon"], "description": m["description"],
                    "needs": [{"key": n, "label": NEEDS[n]} for n in m.get("needs", [])], "needs_text": m.get("needs_text", ""),
                    "always_on": bool(m.get("always_on")), "chosen": bool(pick[mid]), "on": mid in on,
                    "requires": [BY_ID[r]["name"] for r in m.get("requires", [])],
                    "blocked_by": blocked if pick[mid] and mid not in on else [],
                    "pages": m.get("admin_pages", []), **_status(status(mid))})
    return out
