"""Demo mode (FRAME_DEMO=1): sample calendars, weather, house status and screen
time, so the whole frame runs on a laptop with no accounts or network.
Parent PINs in demo mode: 1234 (Dad) and 5678 (Mom).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from . import chores as chore_logic
from .config import Settings
from . import screentime as st
from .db import Database

DEMO_PIN = "1234"

DEMO_WEATHER = {"temp": 62, "text": "Partly cloudy", "high": 68, "low": 49, "rain": 20,
                "icon": "partly", "phrase": "20% rain",
                "hours": [{"label": "Now", "temp": 62, "rain": 10, "icon": "partly"}, {"label": "5 PM", "temp": 61, "rain": 10, "icon": "partly"},
                          {"label": "6 PM", "temp": 58, "rain": 20, "icon": "cloud"}, {"label": "7 PM", "temp": 55, "rain": 40, "icon": "cloud"},
                          {"label": "8 PM", "temp": 53, "rain": 70, "icon": "rain"}, {"label": "9 PM", "temp": 51, "rain": 60, "icon": "rain"}],
                "days": [{"name": "Today", "date": "", "high": 68, "low": 49, "text": "Partly cloudy", "rain": 70, "icon": "partly"},
                         {"name": "Friday", "date": "", "high": 71, "low": 52, "text": "Sunny", "rain": 0, "icon": "sun"},
                         {"name": "Saturday", "date": "", "high": 66, "low": 45, "text": "Sunny, cooler", "rain": 10, "icon": "sun"}],
                "note": "Rain likely 8 PM – 10 PM (70%)", "wind": 8, "units": {"temp": "F", "wind": "mph"},
                "source": "demo"}

DEMO_HOME = [
    {"icon": "garage", "text": "Garage closed", "alert": False},
    {"icon": "lock", "text": "Front door locked", "alert": False},
]

DEMO_PINS = [("Dad", "1234"), ("Mom", "5678")]

# Sample screen time earlier in the week (before today's chores): (weekday, kind, kid, minutes, note, by)
DEMO_WEEK = [
    (0, "good_day", None, 30, "A good day for everyone", "Mom"),
    (0, "chore", "child1", 20, "Practice piano", "Dad"),
    (0, "chore", "child2", 10, "Feed the dog", "Mom"),
    (1, "good_day", None, 30, "A good day for everyone", "Dad"),
    (1, "chore", "child1", 15, "Unload the dishwasher", "Mom"),
    (1, "chore", "child3", 10, "Pick up the toys", "Dad"),
    (2, "good_day", None, 30, "A good day for everyone", "Mom"),
    (2, "chore", "child2", 15, "Read for 20 minutes", "Mom"),
    (2, "chore", "child3", 10, "Help set the table", "Dad"),
    (2, "adjust", "child2", 5, "Kind to a sibling", "Mom"),
]


def seed_week(db: Database, settings: Settings, now: datetime) -> None:
    """Fill the demo screen time ledger with a few days of sample entries (once)."""
    with db.connect() as conn:
        if conn.execute("SELECT 1 FROM screen_ledger WHERE kind != 'new_week' LIMIT 1").fetchone():
            return
        monday = st.week_monday(now.date())
        conn.execute("DELETE FROM screen_ledger WHERE kind = 'new_week'")
        conn.execute("INSERT INTO screen_ledger (at, kind, minutes, note, by) VALUES (?, 'new_week', 0, 'New week', 'Dad')",
                     (f"{(monday - timedelta(days=1)).isoformat()}T21:00:00",))
        kids = {k.id for k in settings.kids}
        for i, (wd, kind, kid, minutes, note, by) in enumerate(DEMO_WEEK):
            if wd >= now.weekday() or (kid and kid not in kids):
                continue
            at = f"{(monday + timedelta(days=wd)).isoformat()}T{17 + i % 3:02d}:{(i * 7) % 60:02d}:00"
            conn.execute("INSERT INTO screen_ledger (at, kind, minutes, scope, kid, note, by) VALUES (?, ?, ?, 'family', ?, ?, ?)",
                         (at, kind, minutes, kid, note, by))


def seed_today(db: Database, settings: Settings, day: date, now: datetime) -> None:
    """Make today's chore list look lived-in: some done, some waiting."""
    done = {"child1-make-your-bed", "child2-make-your-bed", "child3-make-your-bed", "child3-put-your-shoes-away"}
    waiting = {"child1-unload-the-dishwasher", "child2-sweep-the-kitchen"}
    todays = {c.id for c in chore_logic.scheduled(settings, day)}
    earlier = now - timedelta(hours=2)
    for cid in waiting & todays:
        chore_logic.claim(db, settings, cid, day, earlier)
    for cid in done & todays:
        try:
            chore_logic.approve(db, settings, cid, day, earlier, "Dad")
        except chore_logic.ChoreError:
            pass
