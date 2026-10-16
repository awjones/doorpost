"""The Kids home screen: what a playroom frame receives (and never receives)."""
import json
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app import kidsview


def make_client(monkeypatch, now):
    monkeypatch.setenv("FRAME_NOW", now)
    import importlib
    import sys
    sys.modules.pop("app.admin", None)
    import app.main
    importlib.reload(app.main)
    return TestClient(app.main.app)


@pytest.fixture
def client(demo_env, monkeypatch):
    with make_client(monkeypatch, "2026-10-15T16:12:00") as c:
        yield c


def test_pictures_from_titles():
    assert kidsview.picture_for("Make your bed") == "bed"
    assert kidsview.picture_for("Practice piano") == "music"
    assert kidsview.picture_for("Soccer practice") == "ball"
    assert kidsview.picture_for("Supper: tacos") == "food"
    assert kidsview.picture_for("Unload the dishwasher") == "dishes"
    assert kidsview.picture_for("Feed the dog") == "dog"
    assert kidsview.picture_for("Field trip") == "school"
    assert kidsview.picture_for("Dentist (Child 2)") == "tooth"
    assert kidsview.picture_for("Something new") == "star"


def test_next_today_ends_with_bedtime():
    events = [
        {"title": "Piano lesson", "time": "3:30 PM", "end_time": "4:00 PM", "sort": "15:30", "all_day": False, "who": "Child 1"},
        {"title": "Trash night", "time": "All day", "end_time": "", "sort": "", "all_day": True, "who": "everyone"},
        {"title": "Soccer practice", "time": "5:30 PM", "end_time": "6:30 PM", "sort": "17:30", "all_day": False, "who": "Child 2"},
        {"title": "Late movie", "time": "9:00 PM", "end_time": "", "sort": "21:00", "all_day": False, "who": "Mom"},
    ]
    kids = [{"id": "child1", "name": "Child 1"}, {"id": "child2", "name": "Child 2"}]
    out = kidsview.next_today(events, kids, datetime(2026, 10, 15, 16, 12), "20:00")
    assert [x["title"] for x in out] == ["Soccer practice", "Bedtime"]      # past, all-day and after-bedtime left out
    assert out[0]["next"] and out[0]["kids"] == ["child2"] and out[0]["picture"] == "ball"
    assert out[1]["bedtime"] and out[1]["time"] == "8:00 PM"
    # During practice it is "now", and bedtime is next.
    out = kidsview.next_today(events, kids, datetime(2026, 10, 15, 17, 45), "20:00")
    assert out[0]["now"] and not out[0]["next"] and out[1]["next"]


def test_bedtime_countdown():
    b = kidsview.bedtime_info("20:00", datetime(2026, 10, 15, 19, 40))
    assert b["minutes"] == 20 and b["evening"] and not b["past"] and b["in"] == "20 min"
    assert not kidsview.bedtime_info("20:00", datetime(2026, 10, 15, 16, 12))["evening"]
    assert kidsview.bedtime_info("20:00", datetime(2026, 10, 15, 20, 30))["past"]


def test_playroom_frame_payload(client):
    d = client.get("/api/frame?frame=playroom").json()
    assert d["frame"]["home"] == "kids" and d["frame"]["look"] == "kids" and d["frame"]["bedtime"] == "20:00"
    kv = d["kidsview"]
    assert [x["title"] for x in kv["next"]] == ["Soccer practice", "Supper: tacos", "Scout meeting", "Bedtime"]
    assert kv["view"] == "rocket" and kv["bedtime"]["minutes"] == 228 and not kv["bedtime"]["evening"]
    assert all("picture" in c for k in d["kids"] for c in k["chores"])
    # The kitchen frame is unchanged: no kids screen data.
    assert "kidsview" not in client.get("/api/frame?frame=kitchen").json()


def test_private_notes_never_reach_a_kids_frame(client, monkeypatch):
    # The starred park day has notes ("Season passes are on the phones...") and an address.
    kitchen = client.get("/api/frame?frame=kitchen").json()
    park = next(e for d in kitchen["calendar"]["rolling"]["days"] for e in d["events"] if e["title"] == "Theme park day")
    assert "Season passes" in park["notes"]
    kids = client.get("/api/frame?frame=playroom")
    assert "Season passes" not in kids.text and "Springfield" not in kids.text
    d = kids.json()
    assert all(not e["notes"] and not e["where"] for d2 in d["calendar"]["rolling"]["days"] for e in d2["events"])
    assert len(d["calendar"]["upcoming"]["lines"]) == 1
    assert d["home"] == [] and d["status"] == {}
    # Paging the calendar from a kids frame: no notes either.
    for view, off in (("rolling", 0), ("month", 0), ("week", 0)):
        page = client.get(f"/api/calendar?view={view}&offset={off}&frame=playroom")
        assert "Season passes" not in page.text and "Springfield" not in page.text
    assert "Season passes" in client.get("/api/calendar?view=rolling&offset=0&frame=kitchen").text


def test_deductions_stay_off_a_kids_frame(client):
    tok = client.post("/api/parent/unlock", json={"pin": "1234"}).json()["token"]
    h = {"X-Parent-Token": tok}
    assert client.post("/api/parent/screen/adjust", json={"minutes": -10, "kid": "child2", "scope": "kid", "note": "Unkind words"}, headers=h).status_code == 200
    assert client.post("/api/parent/screen/adjust", json={"minutes": -15, "kid": None, "scope": "family", "note": "Fighting"}, headers=h).status_code == 200
    d = client.get("/api/frame?frame=playroom").json()
    sc = d["screen"]
    assert all(e["minutes"] >= 0 for e in sc["feed"]) and all(p["minutes"] >= 0 for p in sc["parts"])
    assert "log" not in sc and all(v >= 0 for v in sc["kid_bonus"].values())
    assert all(k["bonus"] >= 0 for k in d["kids"])
    text = json.dumps(d)
    assert "Unkind words" not in text and "Fighting" not in text and "Taken away" not in text


def test_evening_payload(demo_env, monkeypatch):
    with make_client(monkeypatch, "2026-10-15T19:40:00") as c:
        d = c.get("/api/frame?frame=playroom").json()
    b = d["kidsview"]["bedtime"]
    assert b["evening"] and b["minutes"] == 20
    assert [x["title"] for x in d["kidsview"]["next"]] == ["Scout meeting", "Bedtime"]
    assert d["kidsview"]["next"][0]["now"] and d["is_night"] is False


def test_settings_keep_bedtime_and_picture(client):
    assert client.post("/api/parent/unlock?remember=1", json={"pin": "1234"}).status_code == 200
    frames = client.get("/api/admin/frames").json()["frames"]
    play = next(f for f in frames if f["id"] == "playroom")
    play.update(bedtime="19:30", screen_view="vault")
    assert client.put("/api/admin/frames", json=frames).status_code == 200
    d = client.get("/api/frame?frame=playroom").json()
    assert d["frame"]["bedtime"] == "19:30" and d["kidsview"]["view"] == "vault"
    play.update(bedtime="nope", screen_view="spaceship")
    assert client.put("/api/admin/frames", json=frames).status_code == 200
    f = client.get("/api/frame?frame=playroom").json()["frame"]
    assert f["bedtime"] == "20:00" and f["screen_view"] is None


def _kitchen_with_look(client, look):
    assert client.post("/api/parent/unlock?remember=1", json={"pin": "1234"}).status_code == 200
    frames = client.get("/api/admin/frames").json()["frames"]
    kitchen = next(f for f in frames if f["id"] == "kitchen")
    kitchen.update(look=look, home="today")
    assert client.put("/api/admin/frames", json=frames).status_code == 200


def test_a_kids_look_gets_the_kids_scrub_on_any_home_screen(client):
    # A frame dressed in a look made for kids (theme.json "kids": true) is scrubbed even with Today as its home.
    tok = client.post("/api/parent/unlock", json={"pin": "1234"}).json()["token"]
    assert client.post("/api/parent/screen/adjust", json={"minutes": -10, "kid": "child2", "scope": "kid", "note": "Unkind words"},
                       headers={"X-Parent-Token": tok}).status_code == 200
    _kitchen_with_look(client, "kids-room")
    r = client.get("/api/frame?frame=kitchen")
    d = r.json()
    assert d["frame"]["look_kids"] is True and d["frame"]["home"] == "today"
    assert "Season passes" not in r.text and "Springfield" not in r.text and "Unkind words" not in r.text
    assert all(not e["notes"] and not e["where"] for e in d["calendar"]["today"])
    for v in ("week", "rolling"):
        assert all(not e["notes"] and not e["where"] for day in d["calendar"][v]["days"] for e in day["events"])
    up = d["calendar"]["upcoming"]
    assert up is None or len(up["lines"]) <= 1          # the Today ribbon: the time, never the address
    assert d["home"] == [] and d["status"] == {}
    assert all(e["minutes"] >= 0 for e in d["screen"]["feed"]) and all(k["bonus"] >= 0 for k in d["kids"])
    for view, off in (("rolling", 0), ("week", 0), ("week", 1), ("month", 0), ("month", 1)):
        page = client.get(f"/api/calendar?view={view}&offset={off}&frame=kitchen")
        assert page.status_code == 200 and "Season passes" not in page.text and "Springfield" not in page.text


def test_a_grownup_look_keeps_the_details(client):
    _kitchen_with_look(client, "light")
    r = client.get("/api/frame?frame=kitchen")
    assert r.json()["frame"]["look_kids"] is False and "Season passes" in r.text
    assert "Season passes" in client.get("/api/calendar?view=rolling&offset=0&frame=kitchen").text


def test_the_scrub_leaves_the_shared_payload_alone(client):
    # A kids' frame polled first must not take the notes away from the kitchen frame (they share one cached payload).
    client.get("/api/frame?frame=playroom")
    assert "Season passes" in client.get("/api/frame?frame=kitchen").text


def test_park_sign_from_an_address_is_scrubbed():
    sp = {"kind": "event", "title": "Theme park day", "lines": ["All day", "1 Park Rd, Springfield"], "place": "1 Park Rd",
          "place_from_where": True}
    kidsview._scrub_special(sp)
    assert sp["lines"] == ["All day"] and sp["place"] == "Theme park day"
