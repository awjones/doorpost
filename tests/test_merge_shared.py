"""Events shared between calendars show once."""
from datetime import date
from pathlib import Path

import pytest

from app.calendar_feed import CalendarService
from app.config import CalendarSource

ICS = """BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//t//t//EN\r\n{events}END:VCALENDAR\r\n"""
EV = ("BEGIN:VEVENT\r\nUID:{uid}\r\nDTSTAMP:20260101T000000Z\r\n"
      "DTSTART;TZID=America/New_York:{start}\r\nDTEND;TZID=America/New_York:{end}\r\n"
      "SUMMARY:{title}\r\nEND:VEVENT\r\n")


def write(tmp: Path, name: str, *events) -> str:
    p = tmp / f"{name}.ics"
    p.write_text(ICS.format(events="".join(EV.format(**e) for e in events)))
    return str(p)


@pytest.fixture
def cals(settings, tmp_path):
    invite = dict(uid="abc123@google.com", start="20261015T190000", end="20261015T200000", title="Date night (Dad & Mom)")
    settings.calendars = [
        CalendarSource(key="dad", label="Dad", color="#2E4A7A", tint="#E5EAF2", who_default="Dad",
                       ics_file=write(tmp_path, "a", invite,
                                      dict(uid="a1", start="20261015T090000", end="20261015T100000", title="Dentist"))),
        CalendarSource(key="mom", label="Mom", color="#8B4F24", tint="#F3E8DC", who_default="Mom",
                       ics_file=write(tmp_path, "s", invite,
                                      # same thing typed in by hand on her calendar: different UID, same time + title
                                      dict(uid="s1", start="20261015T090000", end="20261015T100000", title="Dentist!"),
                                      dict(uid="s2", start="20261015T120000", end="20261015T130000", title="Lunch with Mom"))),
    ]
    return settings


def test_shared_events_show_once(cals, tmp_path):
    c = CalendarService(cals, tmp_path / "cache")
    c.refresh()
    evs = c.events_between(date(2026, 10, 15), date(2026, 10, 16))
    assert [e["title"] for e in evs] == ["Dentist", "Lunch with Mom", "Date night"]
    date_night = evs[2]
    assert date_night["cal"] == "dad" and date_night["also"] == ["Mom"]   # first calendar's color wins
    assert date_night["who"] == "Dad & Mom"
    assert evs[0]["also"] == ["Mom"]                                          # hand-copied duplicate merged too
    assert evs[1]["also"] == []


def test_can_be_turned_off(cals, tmp_path):
    cals.merge_shared_events = False
    c = CalendarService(cals, tmp_path / "cache")
    c.refresh()
    assert len(c.events_between(date(2026, 10, 15), date(2026, 10, 16))) == 5
