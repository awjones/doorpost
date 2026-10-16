from datetime import date

from app.calendar_feed import CalendarService


def svc(settings, tmp_path):
    c = CalendarService(settings, tmp_path / "cache")
    c.refresh()
    assert c.errors == {}
    return c


def test_recurring_events_expand_into_any_week(settings, tmp_path):
    c = svc(settings, tmp_path)
    evs = c.events_between(date(2026, 10, 11), date(2026, 10, 18))
    titles = [(e["day"], e["title"]) for e in evs]
    assert ("2026-10-11", "Church") in titles
    assert ("2026-10-15", "Soccer practice") in titles    # "(Child 2)" tag stripped from the title
    # Same weekly events a year later: the demo never goes stale
    later = c.events_between(date(2027, 10, 10), date(2027, 10, 17))
    assert any(e["title"] == "Church" for e in later)


def test_who_and_name_tags(settings, tmp_path):
    c = svc(settings, tmp_path)
    by_title = {e["title"]: e for e in c.events_between(date(2026, 10, 15), date(2026, 10, 16))}
    assert by_title["Soccer practice"]["who"] == "Child 2"
    assert by_title["Library story time with Child 3"]["who"] == "Mom & Child 3"
    assert by_title["Scout meeting"]["who"] == "Dad, Child 1 & Child 2"
    assert by_title["Supper: tacos"]["who"] == "everyone"


def test_all_day_and_sorting(settings, tmp_path):
    c = svc(settings, tmp_path)
    thu = c.events_between(date(2026, 10, 15), date(2026, 10, 16))
    assert thu[0]["all_day"] and thu[0]["time"] == "All day"
    times = [e["sort"] for e in thu if not e["all_day"]]
    assert times == sorted(times)


def test_mom_filter(settings, tmp_path):
    c = svc(settings, tmp_path)
    week = [e["title"] for e in c.events_between(date(2026, 10, 11), date(2026, 10, 18)) if e["cal"] == "mom"]
    assert "Bible study" in week                      # Dad is an attendee
    assert "Library story time with Child 3" in week    # names a kid
    assert "Coffee with Hannah" not in week           # neither: filtered out


def test_failed_refresh_keeps_last_copy(settings, tmp_path):
    c = svc(settings, tmp_path)
    settings.calendars[0].ics_file = "does/not/exist.ics"
    c.refresh()
    assert "family" in c.errors
    assert any(e["cal"] == "family" for e in c.events_between(date(2026, 10, 11), date(2026, 10, 18)))
