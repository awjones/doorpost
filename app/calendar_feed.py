"""Read-only family calendars from iCal (.ics) addresses or private CalDAV accounts.

Two kinds of source (see docs/calendars.md):
- "ics": any iCal/webcal address (Google's secret address, an Outlook published
  calendar, an iCloud public link).
- "caldav": a private account such as Apple iCloud with an app-specific password
  (app/caldav.py). Its events come back as iCalendar text too, so both kinds go
  through the same parser.
Addresses and passwords live only on the server. The frame never sees them; it
only gets the finished event list.
Recurring events are expanded with recurring-ical-events. The last good copy of
each feed is cached on disk so a network blip or reboot doesn't blank the frame.
"""
from __future__ import annotations

import logging
import re
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import httpx
import icalendar
import recurring_ical_events

from . import caldav
from .config import CalendarSource, Settings
from .special import default_words, flag_event
from .timeutil import fmt_clock

log = logging.getLogger(__name__)


class CalendarService:
    def __init__(self, settings: Settings, cache_dir: Path, http: Optional[httpx.Client] = None):
        self.settings = settings
        self.tz = ZoneInfo(settings.timezone)
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.http = http or caldav.make_http()
        self.calendars: dict[str, icalendar.Calendar] = {}
        self.errors: dict[str, str] = {}
        self.last_refresh: Optional[datetime] = None
        self._memo: dict[tuple, list[dict]] = {}  # expanded ranges, cleared on each refresh
        self._people = self._compile_people(settings.people)
        from .portraits import people_of
        self._birthday_people = people_of(settings)

    # ---------- loading ----------

    def refresh(self) -> None:
        for src in self.settings.calendars:
            try:
                raw = self._fetch(src)
                self.calendars[src.key] = trim_history(icalendar.Calendar.from_ical(raw), self.tz)
                self.errors.pop(src.key, None)
            except Exception as exc:  # keep the last good copy on any failure
                log.warning("calendar %s refresh failed: %s", src.key, exc)
                self.errors[src.key] = str(exc)[:200]
                if src.key not in self.calendars:
                    cached = self.cache_dir / f"{src.key}.ics"
                    if cached.exists():
                        self.calendars[src.key] = trim_history(icalendar.Calendar.from_ical(cached.read_bytes()), self.tz)
        self.last_refresh = datetime.now(self.tz)
        self._memo.clear()

    def _fetch(self, src: CalendarSource) -> bytes:
        if src.kind == "caldav":
            return self._fetch_caldav(src)
        if src.ics_url:
            resp = self.http.get(src.ics_url)
            resp.raise_for_status()
            data = resp.content
            if b"BEGIN:VCALENDAR" not in data[:200]:
                raise ValueError("response was not an iCal feed (is the secret address right?)")
            (self.cache_dir / f"{src.key}.ics").write_bytes(data)
            return data
        if src.ics_file:
            path = Path(src.ics_file)
            if not path.is_absolute():
                path = Path(__file__).resolve().parent.parent / path
            return path.read_bytes()
        raise ValueError("no address yet: paste its secret iCal address in Settings > Calendars")

    # CalDAV asks for a window of dates; this covers what the frame's views can show.
    CALDAV_BACK_DAYS = 62
    CALDAV_AHEAD_DAYS = 400

    def _fetch_caldav(self, src: CalendarSource) -> bytes:
        if src.ics_file and not src.caldav_password:  # demo sample data stands in
            return Path(src.ics_file if Path(src.ics_file).is_absolute()
                        else Path(__file__).resolve().parent.parent / src.ics_file).read_bytes()
        if not src.caldav_calendar:
            raise ValueError("no calendar picked yet: press Find my calendars in Settings > Calendars")
        client = caldav.CalDAVClient(src.caldav_server, src.caldav_user, src.caldav_password, http=self.http)
        today = datetime.now(self.tz).date()
        lo = datetime.combine(today - timedelta(days=self.CALDAV_BACK_DAYS), time.min, self.tz)
        hi = datetime.combine(today + timedelta(days=self.CALDAV_AHEAD_DAYS), time.min, self.tz)
        data = client.fetch(src.caldav_calendar, lo, hi)
        (self.cache_dir / f"{src.key}.ics").write_bytes(data)
        return data

    # ---------- querying ----------

    def events_between(self, start: date, end: date) -> list[dict]:
        """All events touching [start, end) as dicts, sorted. Multi-day events repeat per day.
        Results are kept until the next refresh, so the frame's polling stays cheap."""
        key = (start, end, self.settings.merge_shared_events)
        if key not in self._memo:
            if len(self._memo) > 64:
                self._memo.clear()
            self._memo[key] = self._events_between(start, end)
        return [dict(e, also=list(e.get("also", []))) for e in self._memo[key]]  # callers may mark them up

    def _events_between(self, start: date, end: date) -> list[dict]:
        lo = datetime.combine(start, time.min, self.tz)
        hi = datetime.combine(end, time.min, self.tz)
        out: list[dict] = []
        for src in self.settings.calendars:
            cal = self.calendars.get(src.key)
            if cal is None:
                continue
            for ev in recurring_ical_events.of(cal).between(lo, hi):
                if not self._keep(src, ev):
                    continue
                out.extend(self._to_dicts(src, ev, start, end))
        if self.settings.merge_shared_events:
            out = self._merge_shared(out)
        out.sort(key=lambda e: (e["day"], not e["all_day"], e["sort"], e["title"]))
        return out

    def _merge_shared(self, events: list[dict]) -> list[dict]:
        """Show an event once when it's on more than one calendar (an invite between Dad and
        Mom, or the same thing added to two calendars). Google gives every copy of an invite
        the same UID; copies made by hand match on day, start time and title instead.
        The copy from the calendar listed first in Settings wins (its color shows); the
        "who" names are combined, and `also` lists the other calendars."""
        order = {c.key: i for i, c in enumerate(self.settings.calendars)}
        labels = {c.key: c.label for c in self.settings.calendars}
        kept: list[dict] = []
        index: dict[tuple, dict] = {}
        for e in sorted(events, key=lambda e: order.get(e["cal"], 99)):
            title_key = re.sub(r"\W+", " ", e["title"]).strip().lower()
            keys = [("t", e["day"], e["all_day"], e["sort"], title_key)]
            if e.get("uid"):
                keys.insert(0, ("u", e["day"], e["uid"], e["sort"]))
            first = next((index[k] for k in keys if k in index), None)
            if first is None or first["cal"] == e["cal"]:
                e["also"] = []
                kept.append(e)
                for k in keys:
                    index.setdefault(k, e)
                continue
            if first.get("look") is None and e.get("look") is not None:  # flagged on either copy
                first["look"], first["notes"] = e["look"], first.get("notes") or e.get("notes", "")
            first["where"] = first.get("where") or e.get("where", "")
            label = labels.get(e["cal"], e["cal"])
            if label not in first["also"]:
                first["also"].append(label)
            first["who"] = self._combine_who(first["who"], e["who"])
        return kept

    def _combine_who(self, a: str, b: str) -> str:
        if not b or a == b:
            return a
        if not a:
            return b
        if "everyone" in (a, b):
            return "everyone"
        names = [n.strip() for n in re.split(r",|&", a + "," + b) if n.strip()]
        rank = {name: i for i, (name, _) in enumerate(self._people)}
        uniq = sorted(dict.fromkeys(names), key=lambda n: rank.get(n, 99))
        return _join(uniq)

    def _keep(self, src: CalendarSource, ev) -> bool:
        status = str(ev.get("STATUS", "")).upper()
        if status == "CANCELLED":
            return False
        f = src.filter or {}
        title = str(ev.get("SUMMARY", ""))
        for pat in f.get("exclude_titles_matching", []):
            if re.search(pat, title):
                return False
        attendees = ev.get("ATTENDEE") or []
        if not isinstance(attendees, list):
            attendees = [attendees]
        declined_by = [e.lower() for e in f.get("skip_declined_by", [])]
        for a in attendees:
            email = str(a).lower().replace("mailto:", "")
            if email in declined_by and str(a.params.get("PARTSTAT", "")).upper() == "DECLINED":
                return False
        need_att = [e.lower() for e in f.get("require_attendee_any", [])]
        need_title = f.get("include_titles_matching", [])
        if not need_att and not need_title:
            return True
        emails = {str(a).lower().replace("mailto:", "") for a in attendees}
        if need_att and emails.intersection(need_att):
            return True
        return any(re.search(p, title) for p in need_title)

    def _to_dicts(self, src: CalendarSource, ev, start: date, end: date) -> list[dict]:
        # ⭐ in the title, #special in the notes or a Settings word makes it a special day (app/special.py)
        words = (self.settings.special or {}).get("words")   # None: the title words from the turned-on art packs
        title, look, notes = flag_event(str(ev.get("SUMMARY", "(no title)")).strip(), str(ev.get("DESCRIPTION", "")),
                                        default_words() if words is None else words, self._birthday_people)
        dtstart = ev.get("DTSTART").dt
        dtend_prop = ev.get("DTEND")
        all_day = not isinstance(dtstart, datetime)
        if all_day:
            first = dtstart
            last_excl = dtend_prop.dt if dtend_prop else first + timedelta(days=1)
            sort, label, end_label = "", "All day", ""
        else:
            local = dtstart.astimezone(self.tz) if dtstart.tzinfo else dtstart.replace(tzinfo=self.tz)
            first = local.date()
            end_dt = dtend_prop.dt if dtend_prop else local
            if isinstance(end_dt, datetime):
                end_local = end_dt.astimezone(self.tz) if end_dt.tzinfo else end_dt.replace(tzinfo=self.tz)
                last_excl = (end_local - timedelta(seconds=1)).date() + timedelta(days=1)
            else:
                last_excl = first + timedelta(days=1)
            sort, label = local.strftime("%H:%M"), fmt_clock(local)
            end_label = fmt_clock(end_local) if isinstance(end_dt, datetime) and end_local > local else ""
            if last_excl <= first:
                last_excl = first + timedelta(days=1)
        title = self._strip_name_tag(title)
        names = self._names(str(ev.get("SUMMARY", "")) + " " + str(ev.get("DESCRIPTION", "")))
        if names and src.who_default and src.who_default != "everyone" and src.who_default not in names:
            names.insert(0, src.who_default)
        who = _join(names) or src.who_default
        where = str(ev.get("LOCATION", "") or "").strip()[:90]
        span_days = (last_excl - first).days
        out = []
        d = max(first, start)
        while d < min(last_excl, end):
            out.append({
                "day": d.isoformat(), "cal": src.key, "title": title, "who": who,
                "uid": str(ev.get("UID", "")),
                "all_day": all_day, "time": label if d == first or all_day else "Continues",
                "end_time": end_label if d == first else "",
                "sort": sort if d == first else "",
                "start": dtstart.isoformat() if not all_day else first.isoformat(),
                "where": where,
                # Only a special day's own notes go to the frame (other notes can hold call-in codes).
                "look": look, "notes": notes[:300] if look is not None else "",
                "span": [(d - first).days, span_days],
            })
            d += timedelta(days=1)
        return out

    @staticmethod
    def _compile_people(people) -> list[tuple[str, re.Pattern]]:
        out = []
        for p in people or []:
            if isinstance(p, str):
                p = {"name": p}
            names = [p["name"], *p.get("aliases", [])]
            pat = re.compile(r"\b(" + "|".join(re.escape(n) for n in names) + r")\b", re.I)
            out.append((p["name"], pat))
        return out

    def _names(self, text: str) -> list[str]:
        return [name for name, pat in self._people if pat.search(text)]

    def _strip_name_tag(self, title: str) -> str:
        """'Swim lesson (Child 3)' -> 'Swim lesson' when the parentheses only hold names."""
        m = re.search(r"\s*\(([^)]*)\)\s*$", title)
        if not m:
            return title
        parts = [p.strip() for p in re.split(r",|&|\band\b", m.group(1)) if p.strip()]
        if parts and all(any(pat.fullmatch(p) for _, pat in self._people) for p in parts):
            return title[:m.start()].strip()
        return title


HISTORY_DAYS = 62  # the calendar views look back at most about two months


def trim_history(cal: icalendar.Calendar, tz) -> icalendar.Calendar:
    """Drop one-time events that ended long ago. Real calendars carry years of history
    (Mom's had 2,816 events, 322 still relevant), and expanding all of it on every
    request made the Pi take over a minute. Repeating events and their exceptions stay."""
    cutoff = datetime.now(tz).date() - timedelta(days=HISTORY_DAYS)
    def old(ev) -> bool:
        if ev.get("RRULE") or ev.get("RDATE") or ev.get("RECURRENCE-ID"):
            return False
        prop = ev.get("DTEND") or ev.get("DTSTART")
        if prop is None:
            return False
        d = prop.dt
        d = d.date() if isinstance(d, datetime) else d
        return d < cutoff
    cal.subcomponents = [c for c in cal.subcomponents if not (c.name == "VEVENT" and old(c))]
    return cal


def _join(names: list[str]) -> str:
    if len(names) <= 1:
        return names[0] if names else ""
    return ", ".join(names[:-1]) + " & " + names[-1]
