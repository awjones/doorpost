"""Builds the one JSON payload the frame page polls (GET /api/frame)."""
from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timedelta
import re
from typing import Optional

from . import chores as chore_logic
from .config import DAY_KEYS
from .timeutil import fmt_minutes, is_night

DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DOW_LONG = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]
SHORT_MONTHS = [m[:3] for m in MONTHS]


def _sunday_on_or_before(d: date) -> date:
    return d - timedelta(days=(d.weekday() + 1) % 7)


def _day_entry(d: date, today: date, events: list[dict], special_days=None) -> dict:
    entry = {
        "date": d.isoformat(), "dow": DOW[d.weekday()], "dow_long": DOW_LONG[d.weekday()],
        "num": d.day, "month": SHORT_MONTHS[d.month - 1], "today": d == today,
        "past": d < today, "events": events, "special": None, "holidays": [],
    }
    if special_days is not None:  # a flagged event, a chosen holiday or the church year (app/special.py)
        entry["special"], entry["holidays"] = special_days.for_day(d, events, today)
    return entry


def _mark_past_and_next(events: list[dict], now: datetime) -> None:
    hhmm = now.strftime("%H:%M")
    next_found = False
    for e in events:
        e["past"] = bool(e["sort"]) and e["sort"] < hhmm
        e["next"] = False
        if not next_found and e["sort"] and e["sort"] >= hhmm:
            e["next"] = True
            h, m = map(int, e["sort"].split(":"))
            mins = (h * 60 + m) - (now.hour * 60 + now.minute)
            e["in"] = "now" if mins <= 0 else fmt_minutes(mins)
            next_found = True



def add_months(d: date, n: int) -> date:
    idx = d.year * 12 + (d.month - 1) + n
    return date(idx // 12, idx % 12 + 1, 1)


def _by_day(cal, start: date, end: date) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for e in cal.events_between(start, end):
        out.setdefault(e["day"], []).append(e)
    return out


def _span_label(days: list[dict]) -> str:
    a, b = days[0], days[-1]
    return f"{a['dow_long']}, {a['month']} {a['num']} – {b['dow_long']}, {b['month']} {b['num']}"


def _run_of_days(services, start: date, today: date, now: datetime) -> list[dict]:
    by_day = _by_day(services.calendar, start, start + timedelta(days=7))
    if today.isoformat() in by_day:
        _mark_past_and_next(by_day[today.isoformat()], now)
    sp = services.special
    return [_day_entry(start + timedelta(days=i), today, by_day.get((start + timedelta(days=i)).isoformat(), []), sp)
            for i in range(7)]


def calendar_view(services, view: str, offset: int, today: date, now: datetime) -> dict:
    """One calendar view, `offset` weeks (week, rolling) or months (month) from now."""
    cal = services.calendar
    if view == "week":
        start = _sunday_on_or_before(today) + timedelta(weeks=offset)
        days = _run_of_days(services, start, today, now)
        title = {0: "This Week", 1: "Next Week", -1: "Last Week"}.get(offset, f"Week of {days[0]['month']} {days[0]['num']}")
        return {"view": view, "offset": offset, "days": days, "label": _span_label(days), "title": title}
    if view == "rolling":
        days = _run_of_days(services, today + timedelta(weeks=offset), today, now)
        title = "The Next Seven Days" if offset == 0 else "Seven Days Ahead" if offset > 0 else "Seven Days Back"
        return {"view": view, "offset": offset, "days": days, "label": _span_label(days), "title": title}
    if view == "month":
        first = add_months(today.replace(day=1), offset)
        grid_start = _sunday_on_or_before(first)
        last = first.replace(day=monthrange(first.year, first.month)[1])
        grid_end = last + timedelta(days=6 - (last.weekday() + 1) % 7) + timedelta(days=1)
        by_day = _by_day(cal, grid_start, grid_end)
        if today.isoformat() in by_day:
            _mark_past_and_next(by_day[today.isoformat()], now)
        weeks, d, sp = [], grid_start, services.special
        while d < grid_end:
            row = []
            for _ in range(7):
                entry = _day_entry(d, today, by_day.get(d.isoformat(), []), sp)
                entry["in_month"] = d.month == first.month
                row.append(entry)
                d += timedelta(days=1)
            weeks.append(row)
        label = f"{MONTHS[first.month - 1]} {first.year}"
        return {"view": view, "offset": offset, "weeks": weeks, "label": label, "title": label}
    raise ValueError(f"unknown calendar view '{view}'")


def build_calendar(services, today: date, now: datetime) -> dict:
    cal = services.calendar
    near = _by_day(cal, today, today + timedelta(days=2))
    todays = near.get(today.isoformat(), [])
    _mark_past_and_next(todays, now)
    tomorrow = near.get((today + timedelta(days=1)).isoformat(), [])
    tomorrow_first = next((e for e in tomorrow if not e["all_day"]), tomorrow[0] if tomorrow else None)
    return {
        "today": todays,
        "tomorrow_first": tomorrow_first,
        "upcoming": upcoming_special(services, today),
        "week": calendar_view(services, "week", 0, today, now),
        "rolling": calendar_view(services, "rolling", 0, today, now),
        "month": calendar_view(services, "month", 0, today, now),
        "sources": [{"key": c.key, "label": c.label, "color": c.color, "tint": c.tint}
                    for c in services.settings.calendars],
    }


def upcoming_special(services, today: date) -> Optional[dict]:
    """The next special day within the countdown window, for the ribbon on the Today screen."""
    sp = services.special
    if sp.countdown_days < 0:
        return None
    by_day = _by_day(services.calendar, today, today + timedelta(days=sp.countdown_days + 1))
    for i in range(sp.countdown_days + 1):
        d = today + timedelta(days=i)
        special, _ = sp.for_day(d, by_day.get(d.isoformat(), []), today)
        if special and special["span"][0] == 0 and special["kind"] != "sunday":  # the weekly picture gets no countdown
            return dict(special, date=d.isoformat(), dow_long=DOW_LONG[d.weekday()], month=MONTHS[d.month - 1], num=d.day)
    return None


ORDINALS = ["First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh", "Eighth", "Ninth", "Tenth", "Eleventh",
            "Twelfth", "Thirteenth", "Fourteenth", "Fifteenth", "Sixteenth", "Seventeenth", "Eighteenth", "Nineteenth",
            "Twentieth", "Twenty-first", "Twenty-second", "Twenty-third", "Twenty-fourth", "Twenty-fifth", "Twenty-sixth",
            "Twenty-seventh", "Twenty-eighth", "Twenty-ninth", "Thirtieth", "Thirty-first"]


def long_date(d: date) -> str:
    """'Thursday, the Fifteenth of October': for a look with "date_style": "long" (docs/themes.md)."""
    return f"{DOW_LONG[d.weekday()]}, the {ORDINALS[d.day - 1]} of {MONTHS[d.month - 1]}"


def family_initial(name: str, chosen: str = "") -> str:
    """The family's letter: the one picked in Settings > General, else the first letter of the family name's last word
    ("The Example Family" -> E, skipping "Family" and "The")."""
    if chosen and chosen[:1].isalpha():
        return chosen[:1].upper()
    words = [w for w in re.findall(r"[^\W\d_]+", name or "") if w.lower() not in ("the", "family", "families", "household", "home", "our")]
    return (words[-1][0].upper() if words else "F")


def kid_photo(services, k):
    """The kid's photo from Settings > Family (the same one their birthday card uses); else an older face photo."""
    from .portraits import people_of, slug
    me = next((p for p in people_of(services.settings) if p["slug"] == slug(k.name)), None)
    if me and me.get("use_initial"):
        return None
    url = services.portraits.url(slug(k.name)) if getattr(services, "portraits", None) else None
    return url or (f"kids/{k.id}.jpg?v={k.photo}" if k.photo else None)


def build_kids(services, today: date, now: datetime) -> tuple[list[dict], dict]:
    s = services.settings
    db = services.db
    screen = services.screen()
    kids = []
    for k in s.kids:
        todays = chore_logic.chores_for(db, s, today, k.id)
        local_days = chore_logic.local_week_minutes(db, k.id, today)
        earned = screen["kid_minutes"].get(k.id, 0)
        waiting = sum(c["minutes"] for c in todays if c["status"] == "waiting")
        kids.append({
            "id": k.id, "name": k.name, "initial": k.initial, "color": k.color, "tint": k.tint,
            "photo": kid_photo(services, k),
            "chores": todays,
            "done": sum(1 for c in todays if c["status"] == "done"),
            "total": len(todays),
            "waiting_count": sum(1 for c in todays if c["status"] == "waiting"),
            "waiting_minutes": waiting,
            "earned": earned, "earned_label": fmt_minutes(earned) if earned else "none yet",
            "bonus": screen["kid_bonus"].get(k.id, 0),
            "days": [local_days[d] for d in DAY_KEYS[:5]],
        })

    max_earned = max([k["earned"] for k in kids] + [60])
    for k in kids:
        k["bar"] = round(100 * k["earned"] / max_earned)
    screen["waiting_minutes"] = sum(k["waiting_minutes"] for k in kids)
    screen.pop("log", None)  # the full log is for parents only
    return kids, screen


def build_payload(services) -> dict:
    s = services.settings
    now = services.now()
    today = now.date()
    services.photos.maybe_rescan()
    payload = {
        "now": now.isoformat(),
        "epoch_ms": int(now.timestamp() * 1000),
        "tz_offset_min": int(now.utcoffset().total_seconds() // 60),
        "is_night": is_night(now, s.night_start, s.night_end),
        "family_name": s.family_name,
        "initial": family_initial(s.family_name, getattr(s, "family_initial", "")),   # the monogram's letter, for looks
        "date_label": f"{DOW_LONG[today.weekday()]} · {MONTHS[today.month - 1]} {today.day}",
        "date_long": long_date(today),
        "settings": {
            "idle_minutes_to_photos": s.idle_minutes_to_photos,
            "return_to_today_minutes": s.return_to_today_minutes,
            "photo_seconds": s.photo_seconds,
        },
        "weather": services.weather_now(now),
        "home": services.home_status(now),
        "lists": services.lists.frame_view(now),
        "calendar": build_calendar(services, today, now),
        "pin_configured": services.pin.configured,
        # The list itself (1,000+ entries) is fetched from /api/photos only when this version changes.
        "photos_count": len(services.photos.listing()),
        "photos_version": services.photos.version(),
        "demo": s.demo,
    }
    payload["kids"], payload["screen"] = build_kids(services, today, now)
    payload["status"] = {
        "calendar_errors": services.calendar.errors,
        "weather_error": getattr(services.weather, "error", None),
        "screen_time_error": payload["screen"]["error"],
        "home_error": getattr(services.home, "error", None),
    }
    return payload
