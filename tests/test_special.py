"""Special days: church-year dates, flags on our own events, holidays from Google, and the settings that choose them.
Demo mode, clock pinned to Thursday, October 15, 2026 (the theme park day is that Saturday)."""
import io
from datetime import date

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app import special as sp


def test_easter_and_the_church_year():
    assert [sp.easter(y) for y in (2024, 2025, 2026, 2027)] == [
        date(2024, 3, 31), date(2025, 4, 20), date(2026, 4, 5), date(2027, 3, 28)]
    days = {c["key"]: c["date"] for c in sp.church_days(2027)}
    assert days["palm"] == date(2027, 3, 21) and days["goodfriday"] == date(2027, 3, 26)
    assert days["ascension"] == date(2027, 5, 6) and days["pentecost"] == date(2027, 5, 16)
    assert days["reformation"] == date(2027, 10, 31) and days["christmas"] == date(2027, 12, 25)


def test_flags_on_our_own_events():
    assert sp.flag_event("⭐ Theme park day", "", []) == ("Theme park day", "", "")
    assert sp.flag_event("⭐️ Zoo day", "", [])[:2] == ("Zoo day", "")              # star with the emoji variation mark
    assert sp.flag_event("Zoo", "Bring lunch\n#special", [])[1] == ""
    title, look, notes = sp.flag_event("⭐ Trip", "Pack swimsuits\nphoto: Water Park", [])
    assert (look, notes) == ("water-park", "Pack swimsuits")
    words = [{"word": "Splash Lodge", "look": "waterpark"}]
    assert sp.flag_event("Splash Lodge weekend", "", words)[1] == "waterpark"
    assert sp.flag_event("Soccer game", "photo: x", words)[1] == "x"                 # asking for a picture flags it
    assert sp.flag_event("Vacation Bible School", "", sp.DEFAULT_WORDS)[1] == "vbs"   # VBS look, not the beach
    assert sp.flag_event("VBS day 3", "", sp.DEFAULT_WORDS)[1] == "vbs"
    assert sp.flag_event("Camping at the lake", "", sp.DEFAULT_WORDS)[1] == "camping"
    assert sp.flag_event("Beach vacation", "", sp.DEFAULT_WORDS)[1] == "beach"
    assert sp.flag_event("Road trip to Tennessee", "", sp.DEFAULT_WORDS)[1] == "roadtrip"
    assert sp.flag_event("Fly to Denver", "", sp.DEFAULT_WORDS)[1] == "flight"
    assert sp.flag_event("Vacation at Grandma's", "", sp.DEFAULT_WORDS)[1] == "trip"
    assert sp.flag_event("Field trip", "", sp.DEFAULT_WORDS)[1] is None              # "Trip" alone isn't a word


def test_holiday_names():
    assert sp.norm("Presidents’ Day") == "presidents' day"
    assert sp.norm("Juneteenth (substitute)") == "juneteenth" and sp.is_substitute("Juneteenth (substitute)")


@pytest.fixture
def client(demo_env, monkeypatch):
    monkeypatch.setenv("FRAME_NOW", "2026-10-15T16:12:00")
    import importlib
    import sys
    sys.modules.pop("app.admin", None)
    import app.main
    importlib.reload(app.main)
    with TestClient(app.main.app) as c:
        yield c


def _days(client, view, offset=0):
    d = client.get(f"/api/calendar?view={view}&offset={offset}").json()
    days = d["days"] if "days" in d else [x for wk in d["weeks"] for x in wk]
    return {x["date"]: x for x in days}


def test_flagged_event_takes_over_its_day(client):
    d = client.get("/api/frame").json()
    sat = d["calendar"]["week"]["days"][6]
    s = sat["special"]
    assert (s["kind"], s["title"], s["theme"], s["script"]) == ("event", "Theme park day", "park", "Park day!")
    assert s["countdown"] == "In 2 days" and "Lakeside Fun Park" in s["lines"][1] and s["place"] == "Lakeside Fun Park"
    own = next(e for e in sat["events"] if e["uid"] == s["uid"])
    assert own["title"] == "Theme park day" and "Season passes" in own["notes"] and "photo:" not in own["notes"]
    others = [e for e in sat["events"] if e is not own]
    assert others and all(e["notes"] == "" for e in others)            # only the special event's notes reach the frame
    up = d["calendar"]["upcoming"]
    assert up["title"] == "Theme park day" and up["days_until"] == 2


def test_holidays_and_church_year_in_the_month(client):
    oct_ = _days(client, "month", 0)
    assert oct_["2026-10-31"]["special"]["title"] == "Reformation Day"
    assert oct_["2026-10-31"]["holidays"] == []                           # Halloween is hidden by default
    nov = _days(client, "month", 1)
    vet = nov["2026-11-11"]["special"]
    assert vet["title"] == "Veterans Day" and vet["solemn"] and vet["countdown"] == "" and vet["icon"] is None
    assert nov["2026-11-26"]["special"]["theme"] == "thanksgiving"
    assert nov["2026-11-03"]["holidays"] == ["Election Day"] and nov["2026-11-03"]["special"] is None
    dec = _days(client, "month", 2)
    assert dec["2026-12-25"]["special"]["kind"] == "church"               # Google's Christmas shows once, as the church day
    assert dec["2026-12-25"]["holidays"] == []
    jan = _days(client, "month", 3)
    assert [jan[d]["special"]["span"] for d in ("2027-01-15", "2027-01-16")] == [[0, 2], [1, 2]]   # water park lodge, two days
    assert jan["2027-01-15"]["special"]["theme"] == "waterpark"


def jpeg() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (900, 600), (40, 120, 200)).save(buf, "JPEG")
    return buf.getvalue()


def test_settings_choose_what_is_special(client):
    assert client.post("/api/parent/unlock?remember=1", json={"pin": "1234"}).status_code == 200
    view = client.get("/api/admin/special").json()
    names = [h["name"] for h in view["google"]]
    assert "Veterans Day" in names and "Easter Sunday" not in names and "Christmas Day" not in names
    assert {c["key"]: c["on"] for c in view["church"]}["palm"] is False

    r = client.put("/api/admin/special", json={"holiday_modes": {"Election Day": "hide", "Veterans Day": "show"},
                                               "church": {"reformation": False, "palm": True},
                                               "words": [{"word": "Zoo", "look": "pattern"}], "countdown_days": 3})
    assert r.status_code == 200
    nov = _days(client, "month", 1)
    assert nov["2026-11-03"]["holidays"] == [] and nov["2026-11-11"]["special"] is None
    assert nov["2026-11-11"]["holidays"] == ["Veterans Day"]
    assert _days(client, "month", 0)["2026-10-31"]["special"] is None
    assert client.get("/api/frame").json()["calendar"]["upcoming"]["title"] == "Theme park day"   # 2 days out, within 3

    # A real photo replaces the drawing
    r = client.post("/api/admin/special/pictures", files={"file": ("x.jpg", jpeg(), "image/jpeg")}, data={"name": "Theme park"})
    assert r.json()["name"] == "theme-park"
    sat = client.get("/api/calendar?view=week&offset=0").json()["days"][6]["special"]
    assert sat["photo"] is None   # the event asks for "photo: park", not "theme-park"
    assert client.get("/special/theme-park.jpg").headers["content-type"] == "image/jpeg"
    assert "theme-park" in client.get("/api/admin/special").json()["pictures"]
    assert client.delete("/api/admin/special/pictures/theme-park").status_code == 200
    assert client.get("/special/theme-park.jpg").status_code == 404


def test_settings_need_sign_in(client):
    assert client.get("/api/admin/special").status_code == 401
    assert client.put("/api/admin/special", json={"countdown_days": 1}).status_code == 401


def test_photo_line_alone_flags_it_even_with_formatting():
    from app.special import flag_event
    t, look, notes = flag_event("Troop 100 — Fall Camporee", "Leave at 5<br>photo: camping<br>Bring a tarp", [])
    assert look == "camping" and notes == "Leave at 5\n\nBring a tarp"
    t, look, notes = flag_event("Troop 100 — Fall Camporee", "<p>photo:&nbsp;camping</p>", [])
    assert look == "camping"
    assert flag_event("Troop meeting", "Bring a flashlight", [])[1] is None



def _special_days(words=None):
    class NoHolidays:
        days, error = [], None
    from pathlib import Path
    return sp.SpecialDays({"words": words or sp.DEFAULT_WORDS}, NoHolidays(), Path("/nonexistent"))


def _ev(title, look, where="", all_day=True):
    return {"title": title, "look": look, "where": where, "all_day": all_day, "time": "All day", "uid": title, "span": [0, 1]}


def test_water_park_picture():
    S = _special_days()
    day = S.for_day(date(2027, 6, 12), [_ev("Water park day", "waterpark")], date(2027, 6, 1))[0]
    assert (day["theme"], day["script"]) == ("waterpark", "Splash day!")
    assert sp.flag_event("Water park with friends", "", sp.DEFAULT_WORDS)[1] == "waterpark"


def test_park_picture_says_the_parks_name():
    words = [{"word": "Fun Park", "look": "park"}] + sp.DEFAULT_WORDS
    S = _special_days(words)
    look = sp.flag_event("Fun Park with the cousins", "", words)[1]
    assert look == "park"
    day = S.for_day(date(2027, 6, 12), [_ev("Fun Park with the cousins", look)], date(2027, 6, 1))[0]
    assert (day["theme"], day["place"], day["script"]) == ("park", "Fun Park", "Park day!")
    trip = S.for_day(date(2027, 6, 12), [_ev("Amusement park day", "park", where="Lakeside Fun Park, Springfield")], date(2027, 6, 1))[0]
    assert trip["place"] == "Lakeside Fun Park"
    assert sp.flag_event("Garden railroad train show", "", sp.DEFAULT_WORDS)[1] == "gardentrain"
    assert sp.flag_event("Theme park", "", sp.DEFAULT_WORDS)[1] == "park"
    assert sp.flag_event("Railfan trip to the mountains", "", sp.DEFAULT_WORDS)[1] == "trains"


def test_cruise():
    assert sp.flag_event("Caribbean cruise", "", sp.DEFAULT_WORDS)[1] == "cruise"      # before the catch-all Vacation
    assert sp.flag_event("Cruise vacation", "", sp.DEFAULT_WORDS)[1] == "cruise"
