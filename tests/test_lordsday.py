"""Lord's Day pictures: five series take turns, starting fresh on January 3, 2027."""
from datetime import date, timedelta

from fastapi.testclient import TestClient
import pytest

from app import lordsday as L


def test_series_take_turns_from_january_2027():
    seq = [L.for_sunday(date(2027, 1, 3) + timedelta(weeks=k)) for k in range(6)]
    assert [(x["series_key"], x["n"]) for x in seq] == [
        ("lordsday", 1), ("commandments", 1), ("trinity", 1), ("confession", 1), ("bible", 1), ("lordsday", 2)]
    assert seq[0]["title"] == "The Lord's Day" and seq[4]["title"] == "Genesis"
    # the Sundays just before land at the end of each series
    assert (L.for_sunday(date(2026, 12, 27))["title"], L.for_sunday(date(2026, 12, 20))["title"]) == (
        "Revelation", "Chapter 32: Of the Last Judgment")
    x = L.for_sunday(date(2027, 1, 10))
    assert x["verse"].endswith("Exodus 20:3") and "idol" in x["about"] and x["svg"].startswith("<svg")


def test_every_picture_draws_and_has_words():
    for s in L.SERIES:
        for i, it in enumerate(s["items"]):
            assert it["about"] and it["verse"] and it["ref"]
            assert L._picture(L.SERIES.index(s), i).startswith("<svg")


@pytest.fixture
def client(demo_env, monkeypatch):
    monkeypatch.setenv("FRAME_NOW", "2026-10-15T16:12:00")
    import importlib, sys
    sys.modules.pop("app.admin", None)
    import app.main
    importlib.reload(app.main)
    with TestClient(app.main.app) as c:
        yield c


def test_sunday_on_the_frame(client):
    d = client.get("/api/frame").json()
    sun = next(x for x in d["calendar"]["rolling"]["days"] if x["date"] == "2026-10-18")
    sp = sun["special"]
    assert sp["kind"] == "sunday" and sp["title"] == "3 John" and sp["countdown"] == "" and sp["about"]
    assert sp["lines"] == ["Through the Bible · 64 of 66"]
    assert d["calendar"]["upcoming"]["title"] == "Theme park day"         # the weekly picture never takes the ribbon
    assert client.post("/api/parent/unlock?remember=1", json={"pin": "1234"}).status_code == 200
    assert client.put("/api/admin/special", json={"sundays": False}).status_code == 200
    sun = next(x for x in client.get("/api/calendar?view=rolling&offset=0").json()["days"] if x["date"] == "2026-10-18")
    assert sun["special"] is None


def test_holiday_sundays_pause_the_series(client):
    """Resurrection Sunday (Mar 28, 2027) and Mother's Day (May 9, set to Special by default) take
    their Sundays; the pictures pick up the next open Sunday, in order."""
    from app import special as sp
    import app.main
    s = app.main.app.state.services.special
    assert s.holiday_sunday(date(2027, 3, 28)) and s.holiday_sunday(date(2027, 5, 9))
    assert not s.holiday_sunday(date(2027, 2, 14))                     # Valentine's Day is only "Show"
    easter = s.for_day(date(2027, 3, 28), [], date(2026, 10, 15))[0]
    assert easter["kind"] == "church" and easter["title"] == "Resurrection Sunday"
    before = s.for_day(date(2027, 3, 21), [], date(2026, 10, 15))[0]
    after = s.for_day(date(2027, 4, 4), [], date(2026, 10, 15))[0]
    k_before = L.sunday_number(date(2027, 3, 21), s.holiday_sunday)
    assert L.sunday_number(date(2027, 4, 4), s.holiday_sunday) == k_before + 1   # no picture skipped
    assert after["title"] == L.for_sunday(date(2027, 3, 28))["title"]            # Easter's would-be picture moved a week
    assert before["kind"] == after["kind"] == "sunday"
