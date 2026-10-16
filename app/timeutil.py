from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo


def now_in(tz: str) -> datetime:
    return datetime.now(ZoneInfo(tz))


def parse_hhmm(value: str) -> time:
    h, m = value.split(":")
    return time(int(h), int(m))


def is_night(now: datetime, start: str, end: str) -> bool:
    """True when `now` falls in the night window. Handles windows that cross midnight."""
    s, e, t = parse_hhmm(start), parse_hhmm(end), now.time()
    if s == e:
        return False
    if s < e:
        return s <= t < e
    return t >= s or t < e


def fmt_minutes(m: int) -> str:
    m = int(m)
    h, r = divmod(abs(m), 60)
    sign = "-" if m < 0 else ""
    if not h:
        return f"{sign}{r} min"
    return f"{sign}{h} hr" + (f" {r} min" if r else "")


def fmt_clock(dt: datetime) -> str:
    """'4:12 PM' style, no leading zero."""
    hour = dt.hour % 12 or 12
    return f"{hour}:{dt.minute:02d} {'AM' if dt.hour < 12 else 'PM'}"
