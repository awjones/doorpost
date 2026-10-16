"""The Kids home screen (a frame profile with home = "kids", Settings > Frames).

A kids' frame hangs in a playroom, so it gets a narrowed payload:

- `scrub` takes out what is only for parents: event notes and addresses, single-kid
  deductions and the "taken away" line of the screen time total, house status and
  server errors. The frame never receives them, so no screen on it can show them.
- `plan` adds what the kids screen draws: a picture for each chore and each event,
  the "what's next today" strip (ending with bedtime), and the bedtime countdown.
"""
from __future__ import annotations

import copy
import re
from datetime import datetime
from typing import Optional

from .timeutil import fmt_minutes, parse_hhmm

KIDS = "kids"
DEFAULT_BEDTIME = "20:00"
EVENING_MINUTES = 120        # the bedtime countdown shows for the last two hours before bedtime
VIEWS = ("leader", "vault", "rocket", "glass")
DEFAULT_VIEW = "rocket"

# First match wins. Each picture is a simple drawing in web/js/kids.js.
PICTURES = [
    ("bed", r"\bbed(time)?\b|\bnap\b|\bsleep|pajama"),
    ("tooth", r"dentist|teeth|tooth|orthodont"),
    ("doctor", r"doctor|checkup|check-up|pediatric|clinic"),
    ("school", r"school|class\b|teacher|field trip|picture day|homeschool|preschool"),
    ("swim", r"swim|pool|water park|splash"),
    ("music", r"piano|guitar|violin|music|band\b|choir|sing|recital|drum"),
    ("ball", r"soccer|practice|game\b|baseball|basketball|football|t-ball|tball|tennis|gym|karate|hockey|volleyball|dance|sport"),
    ("dishes", r"dish|table\b|kitchen counter"),
    ("dog", r"\bdog\b|\bcat\b|\bpet|feed the|fish\b"),
    ("broom", r"sweep|vacuum|mop|dust"),
    ("shoes", r"shoe"),
    ("laundry", r"laundry|clothes|socks|fold"),
    ("toys", r"\btoys?\b|tidy|clean (up|your)|playroom|your room|pick up"),
    ("trash", r"trash|garbage|recycl|curb"),
    ("plant", r"plant|garden|water the|yard|leaves|rake"),
    ("food", r"supper|dinner|lunch|breakfast|pizza|taco|snack|cook|bake|eat\b|picnic|brunch"),
    ("book", r"library|story|read|homework|book|spelling|math"),
    ("party", r"birthday|party|celebrat"),
    ("tv", r"movie|\btv\b|screen time|show\b"),
    ("people", r"meeting|scout|group|club|visit|grandma|grandpa|friends|playdate|church|service"),
    ("car", r"trip|drive|airport|pick ?up|drop ?off|errand|travel"),
]
_COMPILED = [(name, re.compile(rx, re.I)) for name, rx in PICTURES]


def picture_for(title: str) -> str:
    """A simple picture for a chore or an event, from words in its title."""
    for name, rx in _COMPILED:
        if rx.search(title or ""):
            return name
    return "star"


def is_kids(profile: dict) -> bool:
    return profile.get("home") == KIDS


# ---------------- what a kids' frame must never receive ----------------

def _scrub_event(e: Optional[dict]) -> Optional[dict]:
    if e:
        e["notes"] = ""
        e["where"] = ""
    return e


def _scrub_special(sp: Optional[dict]) -> None:
    if sp and sp.get("kind") == "event":
        sp["lines"] = sp.get("lines", [])[:1]      # the time only: the second line is the address
        sp.pop("notes", None)
        if sp.get("place_from_where"):           # the park sign named the address: use the title instead
            sp["place"] = (sp.get("title") or "")[:28]
            sp["place_from_where"] = False


def _scrub_day(day: dict) -> None:
    for e in day.get("events", []):
        _scrub_event(e)
    _scrub_special(day.get("special"))


def scrub_calendar_view(view: dict) -> dict:
    """One calendar page (week, rolling or month), with notes and addresses taken out."""
    view = copy.deepcopy(view)   # the shared payload's days stay as they were for the parents' frames
    for day in [d for wk in view["weeks"] for d in wk] if "weeks" in view else view.get("days", []):
        _scrub_day(day)
    return view


def scrub(p: dict) -> dict:
    """The payload for a kids' frame: nothing that is only for parents."""
    p = dict(p)
    cal = dict(p["calendar"])
    cal["today"] = [_scrub_event(dict(e)) for e in cal["today"]]
    cal["tomorrow_first"] = _scrub_event(dict(cal["tomorrow_first"])) if cal.get("tomorrow_first") else None
    if cal.get("upcoming"):
        cal["upcoming"] = copy.deepcopy(cal["upcoming"])
        _scrub_special(cal["upcoming"])
    for v in ("week", "rolling", "month"):
        cal[v] = scrub_calendar_view(cal[v])
    p["calendar"] = cal

    sc = dict(p["screen"])
    sc.pop("log", None)
    sc["feed"] = [e for e in sc.get("feed", []) if e["minutes"] >= 0]       # no deductions on the playroom wall
    sc["parts"] = [x for x in sc.get("parts", []) if x["minutes"] >= 0]
    sc["kid_bonus"] = {k: max(0, v) for k, v in (sc.get("kid_bonus") or {}).items()}
    sc["new_week_due"] = False
    p["screen"] = sc
    p["kids"] = [dict(k, bonus=max(0, k.get("bonus", 0))) for k in p["kids"]]

    p["home"] = []                     # garage and door status stay on the parents' frames
    p["status"] = {}                   # calendar and server errors are for Settings, not the playroom
    return p


# ---------------- what the kids screen draws ----------------

def _hhmm_label(hhmm: str) -> str:
    t = parse_hhmm(hhmm)
    return f"{(t.hour % 12) or 12}:{t.minute:02d} {'AM' if t.hour < 12 else 'PM'}"


def _label_minutes(label: str) -> Optional[int]:
    m = re.match(r"\s*(\d{1,2}):(\d\d)\s*([AP])M", label or "", re.I)
    if not m:
        return None
    return (int(m.group(1)) % 12) * 60 + int(m.group(2)) + (720 if m.group(3).upper() == "P" else 0)


def _kids_in(who: str, kids: list[dict]) -> list[str]:
    who = (who or "").lower()
    if who == "everyone":
        return [k["id"] for k in kids]
    return [k["id"] for k in kids if k["name"].lower() in who]


def bedtime_info(bedtime: str, now: datetime) -> dict:
    t = parse_hhmm(bedtime)
    mins = (t.hour * 60 + t.minute) - (now.hour * 60 + now.minute)
    return {"at": bedtime, "label": _hhmm_label(bedtime), "minutes": mins,
            "evening": 0 <= mins <= EVENING_MINUTES, "past": mins < 0,
            "in": "now" if mins <= 0 else fmt_minutes(mins)}


def next_today(events: list[dict], kids: list[dict], now: datetime, bedtime: Optional[str], room: int = 6) -> list[dict]:
    """Today's timed events that haven't ended yet, as pictures, with bedtime last."""
    nowm = now.hour * 60 + now.minute
    out = []
    for e in events:
        if e.get("all_day") or not e.get("sort"):
            continue
        start = _label_minutes(e.get("time", ""))
        end = _label_minutes(e.get("end_time", "")) or (start + 30 if start is not None else None)
        if start is None or end <= nowm:
            continue
        out.append({"title": e["title"], "time": e["time"], "sort": e["sort"], "picture": picture_for(e["title"]),
                    "kids": _kids_in(e.get("who", ""), kids), "now": start <= nowm < end, "next": False})
    if bedtime:
        b = bedtime_info(bedtime, now)
        if not b["past"]:
            out = [x for x in out if x["sort"] < bedtime]
            out.append({"title": "Bedtime", "time": b["label"], "sort": bedtime, "picture": "bed",
                        "kids": [k["id"] for k in kids], "now": False, "next": False, "bedtime": True})
    out.sort(key=lambda x: x["sort"])
    first = next((x for x in out if not x["now"]), None)
    if first:
        first["next"] = True
    return out[:room]


def plan(p: dict, profile: dict, now: datetime) -> dict:
    """Add the kids screen's own data to a (scrubbed) payload."""
    bedtime = profile.get("bedtime") or DEFAULT_BEDTIME
    p["kids"] = [dict(k, chores=[dict(c, picture=picture_for(c["title"])) for c in k["chores"]]) for k in p["kids"]]
    view = profile.get("screen_view") if profile.get("screen_view") in VIEWS else DEFAULT_VIEW
    p["kidsview"] = {
        "next": next_today(p["calendar"]["today"], p["kids"], now, bedtime),
        "bedtime": bedtime_info(bedtime, now),
        "view": view,
    }
    return p
