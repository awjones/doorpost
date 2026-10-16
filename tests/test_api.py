"""End to end through the HTTP API in demo mode, clock pinned to Thursday 4:12 PM."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(demo_env, monkeypatch):
    monkeypatch.setenv("FRAME_NOW", "2026-10-15T16:12:00")
    import importlib
    import sys

    sys.modules.pop("app.admin", None)  # re-import against the fresh app.main
    import app.main
    importlib.reload(app.main)
    with TestClient(app.main.app) as c:
        yield c


def test_frame_payload(client):
    d = client.get("/api/frame").json()
    assert d["date_label"] == "Thursday · October 15"
    assert d["is_night"] is False
    assert [k["name"] for k in d["kids"]] == ["Child 1", "Child 2", "Child 3"]
    nxt = [e for e in d["calendar"]["today"] if e.get("next")]
    assert nxt and nxt[0]["title"] == "Soccer practice" and nxt[0]["in"] == "1 hr 18 min"
    assert [x["dow"] for x in d["calendar"]["week"]["days"]][0] == "Sun"
    assert d["calendar"]["rolling"]["days"][0]["today"] is True
    assert len(d["calendar"]["rolling"]["days"]) == 7
    assert d["screen"]["headline"] == "Family weekend so far"


def test_calendar_paging(client):
    nov = client.get("/api/calendar?view=month&offset=1").json()
    assert nov["title"] == "November 2026"
    days = [d for wk in nov["weeks"] for d in wk if d["in_month"]]
    assert len(days) == 30 and days[0]["date"] == "2026-11-01"
    assert any(e["title"] == "Church" for e in days[0]["events"])     # Nov 1 is a Sunday
    jan = client.get("/api/calendar?view=month&offset=3").json()
    assert jan["title"] == "January 2027"                             # rolls over the year
    nxt = client.get("/api/calendar?view=week&offset=1").json()
    assert nxt["title"] == "Next Week" and nxt["days"][0]["date"] == "2026-10-18"
    assert client.get("/api/calendar?view=month&offset=999").status_code == 400


def test_kid_cannot_approve_without_pin(client):
    r = client.post("/api/parent/chores/child2-set-the-table/approve")
    assert r.status_code == 401


def test_claim_unlock_approve_flow(client):
    assert client.post("/api/chores/child2-set-the-table/claim").json() == {"status": "waiting"}
    assert client.post("/api/parent/unlock", json={"pin": "0000"}).status_code == 403
    tok = client.post("/api/parent/unlock", json={"pin": "1234"}).json()["token"]
    r = client.post("/api/parent/chores/child2-set-the-table/approve", headers={"X-Parent-Token": tok})
    assert r.status_code == 200
    child2 = [k for k in client.get("/api/frame").json()["kids"] if k["id"] == "child2"][0]
    assert {c["id"]: c["status"] for c in child2["chores"]}["child2-set-the-table"] == "done"


def test_phone_cookie_login(client):
    r = client.post("/api/parent/unlock?remember=1", json={"pin": "1234"})
    assert r.status_code == 200 and "ff_parent" in r.cookies
    s = client.get("/api/parent/summary")
    assert s.status_code == 200
    assert {w["id"] for w in s.json()["waiting"]} >= {"child1-unload-the-dishwasher", "child2-sweep-the-kitchen"}


def test_pages_and_static(client):
    assert "Family" in client.get("/").text or client.get("/").status_code == 200
    assert client.get("/parent").status_code == 200
    assert client.get("/static/css/frame.css").status_code == 200
    assert client.get("/static/img/monogram.png").headers["content-type"] == "image/png"


def test_screen_time_in_the_frame_payload(client):
    sc = client.get("/api/frame").json()["screen"]
    assert sc["good_days"] == 3 and sc["sleeps"] == 2 and sc["views"] == ["leader", "vault", "rocket", "glass"]
    assert sc["total"] == sc["pool"] + 180 and 0 < sc["pct"] <= 100
    assert "log" not in sc and sc["feed"] and sc["waiting_minutes"] > 0


def test_parent_tools_are_stamped_with_who(client):
    assert client.post("/api/parent/screen/good-day").status_code == 401        # kids can't
    before = client.get("/api/frame").json()["screen"]["pool"]
    mom = {"X-Parent-Token": client.post("/api/parent/unlock", json={"pin": "5678"}).json()["token"]}
    assert client.post("/api/parent/screen/good-day", headers=mom).status_code == 200
    again = client.post("/api/parent/screen/good-day", headers=mom)
    assert again.status_code == 409 and "Mom already" in again.json()["detail"]
    r = client.post("/api/parent/screen/adjust", headers=mom,
                    json={"minutes": 10, "kid": "child2", "scope": "family", "note": "Kind to a sibling"})
    assert r.status_code == 200
    assert client.post("/api/parent/screen/adjust", headers=mom, json={"minutes": 5, "kid": "nobody"}).status_code == 400
    d = client.get("/api/parent/screen", headers=mom).json()
    assert d["pool"] == before + 40 and d["you"] == "Mom"
    assert d["log"][0]["title"] == "Kind to a sibling" and d["log"][0]["by"] == "Mom"
    assert client.post(f"/api/parent/screen/{d['log'][0]['id']}/undo", headers=mom).status_code == 200
    assert client.get("/api/parent/screen", headers=mom).json()["pool"] == before + 30


def test_phone_sign_in_remembers_who(client):
    client.post("/api/parent/unlock?remember=1", json={"pin": "1234"})
    assert client.get("/api/parent/me").json()["name"] == "Dad"
    assert client.post("/api/parent/screen/new-week").json()["ok"]
    weeks = client.get("/api/parent/screen/log").json()["weeks"]
    assert weeks[0]["started_by"] == "Dad" and weeks[0]["pool"] == 0


def test_photo_list_is_fetched_separately(client):
    d = client.get("/api/frame").json()
    assert "photos" not in d and d["photos_count"] == 0 and d["photos_version"]
    p = client.get("/api/photos").json()
    assert p["photos"] == [] and p["version"] == d["photos_version"]


def test_refresh_now_is_limited_to_once_a_minute(client):
    import app.main
    app.main._forced["at"] = 0
    assert client.post("/api/refresh-now").json()["fresh"] is True
    assert client.post("/api/refresh-now").json()["fresh"] is False   # a second tap right away just re-pulls
    assert client.get("/api/frame").status_code == 200


def test_frame_data_is_compressed(client):
    r = client.get("/api/frame", headers={"Accept-Encoding": "gzip"})
    assert r.headers.get("content-encoding") == "gzip"
