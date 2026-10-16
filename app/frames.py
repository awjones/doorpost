"""Several frames in the house, one Doorpost.

Each frame has a profile (Settings > Frames): its name, look, home screen, which screens,
calendars and kids it shows, whether parents can approve on it, and its own night hours.
Calendars, chores, screen time and photos stay shared, so a chore approved on one frame
shows done on all of them. A frame remembers which profile it is (picked once on the frame,
behind the parent PIN, or opened at /frame/<id>).
"""
from __future__ import annotations

import copy
import re
import time
from typing import Optional

from . import kidsview
from . import themes
from .timeutil import is_night

SCREENS = ["today", "kids", "clock", "calendar", "chores", "screen", "lists", "photos"]
SCREEN_NAMES = {"today": "Today", "kids": "Kids", "clock": "Clock & today", "calendar": "Calendar", "chores": "Chores",
                "screen": "Screen Time", "lists": "Lists", "photos": "Photos"}
HOMES = ("today", "kids", "clock", "chores")
LOOKS = themes.looks()   # {id: (name, blurb)}: the looks in themes/ (app/themes.py), found when the server starts
PICTURES = themes.PICTURES  # "original": pictures as drawn; "match": recolored and framed to fit the look
DEFAULT = {"id": "kitchen", "name": "Kitchen", "look": themes.default_id(), "home": "today",
           "screens": ["today", "calendar", "chores", "screen", "lists", "photos"],
           "calendars": [], "kids": [], "approvals": True, "night": None,
           "bedtime": None, "screen_view": None,   # these two: the Kids home screen (app/kidsview.py)
           "pictures": "original",
           "look_options": {}}   # {look id: {option: value}}: theme.json "options", per frame (app/themes.py)

# Demo mode (FRAME_DEMO=1) starts with two frames: the kitchen and a tall playroom frame on the Kids screen.
DEMO_FRAMES = [dict(DEFAULT),
               {"id": "playroom", "name": "Playroom", "look": "kids", "home": "kids",
                "screens": ["kids", "chores", "screen", "photos"], "calendars": [], "kids": [], "approvals": True,
                "night": {"start": "20:30", "end": "07:00"}, "bedtime": "20:00", "screen_view": "rocket"}]

# Frames check in with every poll: when, and how big their screen is (for Settings > Frames).
SEEN: dict[str, dict] = {}


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")[:30]


def clean(p: dict, kid_ids: set[str], cal_keys: set[str]) -> dict:
    """One profile with every field present and only known values."""
    out = dict(DEFAULT)
    out.update({k: p[k] for k in DEFAULT if k in p})
    out["id"] = slug(out["id"] or out["name"]) or "frame"
    out["name"] = str(out["name"] or "Frame").strip()[:40]
    out["look"] = out["look"] if out["look"] in LOOKS else DEFAULT["look"]
    out["pictures"] = out["pictures"] if out.get("pictures") in PICTURES else "original"
    out["look_options"] = themes.clean_look_options(out.get("look_options"))
    out["screens"] = [s for s in SCREENS if s in (out["screens"] or [])] or list(DEFAULT["screens"])
    out["home"] = out["home"] if out["home"] in HOMES else "today"
    if out["home"] not in out["screens"]:
        out["screens"] = [out["home"]] + out["screens"]
    out["calendars"] = [c for c in (out["calendars"] or []) if c in cal_keys]
    out["kids"] = [k for k in (out["kids"] or []) if k in kid_ids]
    out["approvals"] = bool(out["approvals"])
    n = out.get("night") or None
    if n and (not re.match(r"^\d\d:\d\d$", str(n.get("start", ""))) or not re.match(r"^\d\d:\d\d$", str(n.get("end", "")))):
        n = None
    out["night"] = {"start": n["start"], "end": n["end"]} if n else None
    b = out.get("bedtime")
    out["bedtime"] = b if b and re.match(r"^([01]\d|2[0-3]):[0-5]\d$", str(b)) else (kidsview.DEFAULT_BEDTIME if out["home"] == "kids" else None)
    out["screen_view"] = out["screen_view"] if out.get("screen_view") in kidsview.VIEWS else None
    return out


def profiles(settings) -> list[dict]:
    kid_ids = {k.id for k in settings.kids}
    cal_keys = {c.key for c in settings.calendars}
    raw = settings.frames or [DEFAULT]
    out, seen = [], set()
    for p in raw:
        c = clean(p, kid_ids, cal_keys)
        while c["id"] in seen:
            c["id"] += "-2"
        seen.add(c["id"])
        out.append(c)
    return out


def live(settings) -> list[dict]:
    """The frames in use, without the screens of modules that are off (app/modules.py)."""
    from .modules import live_profiles
    return live_profiles(profiles(settings), settings)


def get(settings, fid: Optional[str]) -> dict:
    ps = live(settings)
    return next((p for p in ps if p["id"] == fid), ps[0])


def note_seen(fid: str, w: Optional[int], h: Optional[int]) -> None:
    if fid:
        SEEN[fid] = {"at": time.time(), "w": w, "h": h}


def seen_view(fid: str) -> dict:
    s = SEEN.get(fid)
    if not s:
        return {"online": False, "ago": None, "w": None, "h": None}
    ago = int(time.time() - s["at"])
    return {"online": ago < 120, "ago": ago, "w": s["w"], "h": s["h"]}


def _keep(e: dict, cals: set[str]) -> bool:
    return e.get("cal") in cals


def _filter_days(days: list[dict], cals: set[str]) -> None:
    for d in days:
        d["events"] = [e for e in d["events"] if _keep(e, cals)]


def filter_calendar_view(view: dict, cals: set[str]) -> dict:
    if not cals:
        return view
    view = copy.deepcopy(view)
    if "weeks" in view:
        for wk in view["weeks"]:
            _filter_days(wk, cals)
    else:
        _filter_days(view["days"], cals)
    return view


def apply(payload: dict, profile: dict, settings, now) -> dict:
    """The shared payload, narrowed to what this frame shows."""
    p = dict(payload)
    p["frame"] = {k: profile[k] for k in ("id", "name", "look", "home", "screens", "approvals", "bedtime", "screen_view", "pictures")}
    look = themes.by_id(profile["look"]) or {}   # its options, and whether it shows the photo behind every screen
    p["frame"]["look_options"] = themes.option_values(look, (profile.get("look_options") or {}).get(profile["look"]))
    p["frame"]["look_background"] = look.get("background", "")
    p["frame"]["look_kids"] = bool(look.get("kids"))
    p["frame"]["look_words"] = dict(look.get("words") or {})              # theme.json "words" (docs/themes.md)
    p["frame"]["look_date_style"] = look.get("date_style", "short")
    p["frame"]["look_monogram"] = look.get("monogram", "image")
    p["frame"]["look_picture_fit"] = dict(look.get("picture_fit") or {})
    if profile["night"]:
        p["is_night"] = is_night(now, profile["night"]["start"], profile["night"]["end"])
    if profile["kids"]:
        p["kids"] = [k for k in payload["kids"] if k["id"] in profile["kids"]]
    cals = set(profile["calendars"])
    if cals:
        cal = dict(payload["calendar"])
        cal["sources"] = [s for s in cal["sources"] if s["key"] in cals]
        cal["today"] = [e for e in cal["today"] if _keep(e, cals)]
        tf = cal.get("tomorrow_first")
        cal["tomorrow_first"] = tf if tf and _keep(tf, cals) else None
        for v in ("week", "rolling", "month"):
            cal[v] = filter_calendar_view(cal[v], cals)
        p["calendar"] = cal
    if for_kids(profile):  # a playroom frame or a kids' look: nothing only for parents
        p = kidsview.scrub(p)
    if kidsview.is_kids(profile) or "kids" in profile["screens"]:   # the Kids screen's own pictures
        p = kidsview.plan(p, profile, now)
    return p


def for_kids(profile: dict) -> bool:
    """A frame kids look at on their own: its home is the Kids screen, or its look is made for kids
    (theme.json "kids": true). Such a frame never receives what is only for parents (app/kidsview.py scrub)."""
    return kidsview.is_kids(profile) or bool((themes.by_id(profile.get("look", "")) or {}).get("kids"))


def for_calendar_page(view: dict, profile: dict) -> dict:
    """GET /api/calendar for this frame: its calendars, and no notes on a kids' frame."""
    view = filter_calendar_view(view, set(profile["calendars"]))
    return kidsview.scrub_calendar_view(view) if for_kids(profile) else view
