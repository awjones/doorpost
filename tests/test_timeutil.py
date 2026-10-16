from datetime import datetime

from app.timeutil import fmt_clock, fmt_minutes, is_night


def test_night_window_crosses_midnight():
    assert is_night(datetime(2026, 10, 15, 23, 0), "22:00", "06:00")
    assert is_night(datetime(2026, 10, 15, 5, 59), "22:00", "06:00")
    assert not is_night(datetime(2026, 10, 15, 6, 0), "22:00", "06:00")
    assert not is_night(datetime(2026, 10, 15, 16, 0), "22:00", "06:00")


def test_formats():
    assert fmt_minutes(45) == "45 min"
    assert fmt_minutes(120) == "2 hr"
    assert fmt_minutes(165) == "2 hr 45 min"
    assert fmt_clock(datetime(2026, 1, 1, 0, 5)) == "12:05 AM"
    assert fmt_clock(datetime(2026, 1, 1, 16, 12)) == "4:12 PM"
