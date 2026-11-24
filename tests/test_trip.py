"""Trip tracker (app/trip.py): where the ship is in words, the estimate when the position is old,
and the module showing only between the trip's dates."""
import importlib
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from app import trip

TZ = ZoneInfo("America/New_York")
CFG = trip.config({"trip": {
    "show_from": "2027-11-20", "show_until": "2027-11-28",
    "ports": [
        {"day": "2027-11-21", "port": "miami", "depart": "16:30"},
        {"day": "2027-11-24", "port": "montego-bay", "arrive": "10:00", "depart": "18:00"},
        {"day": "2027-11-26", "port": "cococay", "arrive": "07:00", "depart": "17:00"},
        {"day": "2027-11-27", "port": "miami", "arrive": "06:00", "note": "Home"},
    ]}})


def at(s):
    return datetime.fromisoformat(s).replace(tzinfo=TZ)


def fix(lat, lon, when, sog=18.0):
    return {"lat": lat, "lon": lon, "sog": sog, "cog": 140, "nav": 0, "at": when.astimezone(ZoneInfo("UTC")).isoformat()}


def test_days_fill_sea_days_between_ports():
    v = trip.view(CFG, {"fixes": []}, at("2027-11-23T12:00"))
    assert [d["port"] for d in v["days"]] == ["Miami", "At sea", "At sea", "Montego Bay", "At sea", "Perfect Day at CocoCay", "Miami"]
    assert [d["today"] for d in v["days"]].index(True) == 2
    assert v["home"] == "Home in 4 days"


def test_live_position_stopped_near_a_port_is_in_port():
    now = at("2027-11-24T13:00")
    v = trip.view(CFG, {"fixes": [fix(18.47, -77.925, now - timedelta(minutes=8), sog=0.1)]}, now)
    assert v["headline"] == "In port · Montego Bay"
    assert "sails 6 PM" in v["sub"]
    assert not v["estimated"] and v["heard"] == "8 min ago"


def test_live_position_at_sea_points_to_the_next_port():
    now = at("2027-11-25T09:00")
    v = trip.view(CFG, {"fixes": [fix(21.0, -76.0, now - timedelta(minutes=20))]}, now)
    assert v["headline"] == "At sea"
    assert v["next"]["name"] == "Perfect Day at CocoCay"
    assert v["sub"] == "on the way to Perfect Day at CocoCay"


def test_an_old_position_stays_where_she_was_last_heard():
    now = at("2027-11-25T05:00")   # between Montego Bay (sails Wed 6 PM) and CocoCay (Fri 7 AM)
    v = trip.view(CFG, {"fixes": [fix(20.0, -73.85, now - timedelta(hours=5))]}, now)
    assert not v["estimated"] and v["ship"]["stale"]
    assert (v["ship"]["lat"], v["ship"]["lon"]) == (20.0, -73.85)
    assert v["headline"] == "At sea" and v["heard"] == "5 hr ago"


def test_nothing_heard_for_days_falls_back_to_the_itinerary_by_sea():
    now = at("2027-11-25T05:00")
    v = trip.view(CFG, {"fixes": [fix(25.77, -80.15, now - timedelta(days=3), sog=0)]}, now)
    assert v["estimated"] and v["ship"]["estimated"]
    from app import searoute
    assert not searoute.on_land(tuple(v["ship"]["xy"]))


def test_the_way_ahead_goes_around_cuba():
    from app import searoute
    now = at("2027-11-23T10:00")
    cfg = trip.config({"trip": {"show_from": "2027-11-20", "show_until": "2027-11-28", "ports": [
        {"day": "2027-11-22", "port": "nassau", "arrive": "08:00", "depart": "17:00"},
        {"day": "2027-11-24", "port": "falmouth", "arrive": "08:30", "depart": "16:30"}]}})
    v = trip.view(cfg, {"fixes": [fix(23.82, -74.73, now - timedelta(hours=3))]}, now)
    way = v["ahead"]
    assert len(way) > 2 and way[-1] == [round(c, 1) for c in v["next"]["xy"]]
    for a, b in zip(way, way[1:-1]):   # every leg but the last few miles into port is at sea
        assert searoute.clear(tuple(a), tuple(b), searoute.SHIP_TRIM if a == way[0] else 0, 0)


def test_in_port_by_the_itinerary_when_nothing_heard():
    v = trip.view(CFG, {"fixes": []}, at("2027-11-26T11:00"))
    assert v["headline"] == "In port · Perfect Day at CocoCay" and v["estimated"]


def test_before_she_sails():
    v = trip.view(CFG, {"fixes": []}, at("2027-11-20T20:00"))
    assert v["before"] and v["headline"] == "Sails Sunday" and v["sub"] == "from Miami at 4:30 PM"


def test_showing_only_between_the_dates():
    assert not trip.showing(CFG, at("2027-11-19T12:00").date())
    assert trip.showing(CFG, at("2027-11-20T12:00").date())
    assert trip.showing(CFG, at("2027-11-28T23:00").date())
    assert not trip.showing(CFG, at("2027-11-29T00:10").date())


def test_map_units_match_the_drawing():
    # web/img/caribbean.svg is 1112.6 x 750 in these units; Miami sits near (496, 217)
    x, y = trip.xy(25.774, -80.170)
    assert abs(x - 496) < 1 and abs(y - 217) < 1


@pytest.fixture
def client(demo_env, monkeypatch):
    monkeypatch.setenv("FRAME_NOW", "2027-11-23T12:00:00")
    sys.modules.pop("app.admin", None)
    import app.main
    importlib.reload(app.main)
    with TestClient(app.main.app) as c:
        assert c.post("/api/parent/unlock?remember=1", json={"pin": "1234"}).status_code == 200
        yield c


def test_module_off_then_on(client):
    assert client.put("/api/admin/modules", json={"trip": False}).status_code == 200
    assert client.get("/api/frame").json().get("trip") is None
    assert client.get("/api/admin/trip").status_code == 404
    assert client.put("/api/admin/modules", json={"trip": True}).status_code == 200
    r = client.put("/api/admin/trip", json={"ports": CFG["ports"], "show_from": "2027-11-20", "show_until": "2027-11-28", "aisstream_key": "secret-key"})
    assert r.status_code == 200, r.text
    assert r.json()["key_set"] and "aisstream_key" not in r.text.replace('"aisstream_key"', "")
    assert "secret-key" not in r.text
    t = client.get("/api/frame").json()["trip"]
    assert t["name"] == "Where’s the ship?" and len(t["days"]) == 7


def test_bad_mmsi_is_refused(client):
    client.put("/api/admin/modules", json={"trip": True})
    r = client.put("/api/admin/trip", json={"mmsi": "123"})
    assert r.status_code == 400 and "9 digits" in r.json()["detail"]


CM_PAGE = ('<script>{"shipCurrentPositionMap":{"lat":25.77007,"lon":-80.15219,"zoom":4}}</script>'
           '<p>The current location of Example Of The Seas is in North West Atlantic Ocean cruising en route to '
           '<b>MIA US</b>. The AIS position was last reported 6 minutes ago.</p>')


def test_reads_the_position_off_a_cruisemapper_page():
    now = datetime(2027, 11, 21, 15, 0, tzinfo=ZoneInfo("UTC"))
    fix, dest = trip.parse_cruisemapper(CM_PAGE, now)
    assert (fix["lat"], fix["lon"]) == (25.77007, -80.15219)
    assert fix["at"] == "2027-11-21T14:54:00+00:00"
    assert dest == "MIA US"
    fix2, _ = trip.parse_cruisemapper(CM_PAGE.replace("6 minutes", "an hour"), now)
    assert fix2["at"] == "2027-11-21T14:00:00+00:00"
    with pytest.raises(trip.PageError):
        trip.parse_cruisemapper("<html>changed</html>", now)


def test_no_speed_but_the_itinerary_says_in_port():
    now = at("2027-11-21T10:00")
    f = {"lat": 25.77007, "lon": -80.15219, "sog": None, "cog": None, "nav": None, "at": (now - timedelta(minutes=6)).isoformat()}
    v = trip.view(CFG, {"fixes": [f]}, now)
    assert v["ship"]["estimated"] is False
    assert "Miami" in v["headline"]


def test_speed_worked_out_from_the_last_position():
    t = {"fixes": [{"lat": 25.0, "lon": -80.0, "sog": None, "at": "2027-11-22T10:00:00+00:00"}]}
    trip._keep(t, {"lat": 25.0, "lon": -79.5, "sog": None, "at": "2027-11-22T12:00:00+00:00"})
    assert len(t["fixes"]) == 2 and 13 < t["fixes"][-1]["sog"] < 14   # ~50 km in 2 h
    trip._keep(t, {"lat": 25.0, "lon": -79.5, "sog": None, "at": "2027-11-22T13:00:00+00:00"})
    assert len(t["fixes"]) == 2 and t["fixes"][-1]["at"].startswith("2027-11-22T13")   # same spot: time moves on


class _Rng:
    def __init__(self, v):
        self.v = v

    def uniform(self, a, b):
        return self.v


@pytest.mark.parametrize("now,jit,want", [
    ("2027-11-21T10:20", 7, "2027-11-21T11:07"),
    ("2027-11-21T10:50", -12, "2027-11-21T11:48"),      # at least 30 min away, so the hour after
    ("2027-11-21T22:40", 10, "2027-11-21T23:10"),      # overnight too: she sails at night
    ("2027-11-22T03:00", -15, "2027-11-22T03:45"),
])
def test_hourly_day_and_night(now, jit, want):
    assert trip.next_check(at(now), _Rng(jit)) == at(want)
    assert trip.in_window(at("2027-11-22T03:00"))


def test_daytime_window_still_works(monkeypatch):
    monkeypatch.setattr(trip, "WINDOW", (6, 21))
    assert trip.next_check(at("2027-11-21T20:40"), _Rng(10)) == at("2027-11-22T06:10")
    assert trip.next_check(at("2027-11-21T20:10"), _Rng(14)) == at("2027-11-21T21:00")
    assert not trip.in_window(at("2027-11-21T21:01"))


def test_export_has_the_route_every_position_and_the_ports():
    t = {"fixes": [{"lat": 25.77, "lon": -80.15, "sog": 0.0, "at": "2027-11-21T21:00:00+00:00", "since": "2027-11-21T11:30:00+00:00", "src": "cruisemapper"},
                   {"lat": 25.5, "lon": -79.0, "sog": 18.2, "at": "2027-11-21T23:00:00+00:00", "src": "cruisemapper"}]}
    g = trip.export(CFG, t)
    kinds = [f["properties"]["kind"] for f in g["features"]]
    assert kinds.count("route") == 1 and kinds.count("position") == 2 and "port" in kinds
    assert g["features"][0]["geometry"]["coordinates"] == [[-80.15, 25.77], [-79.0, 25.5]]
    assert g["features"][0]["properties"]["from"] == "2027-11-21T11:30:00+00:00"
    csv = trip.export_csv(t).splitlines()
    assert csv[0].startswith("at_utc,since_utc") and csv[2] == "2027-11-21T23:00:00+00:00,2027-11-21T23:00:00+00:00,25.5,-79.0,18.2,,cruisemapper"


def test_a_stay_in_port_keeps_when_she_arrived():
    t = {"fixes": []}
    trip._keep(t, {"lat": 25.08, "lon": -77.34, "sog": None, "at": "2027-11-22T13:00:00+00:00"})
    trip._keep(t, {"lat": 25.08, "lon": -77.34, "sog": None, "at": "2027-11-22T14:00:00+00:00"})
    assert t["fixes"] == [{"lat": 25.08, "lon": -77.34, "sog": 0.0, "at": "2027-11-22T14:00:00+00:00", "since": "2027-11-22T13:00:00+00:00"}]
    v = trip.view(CFG, t, at("2027-11-22T10:30"))
    assert v["moves"][0]["since"] == "2027-11-22T13:00:00+00:00"


def test_how_far_from_home():
    now = at("2027-11-23T12:00")
    track = {"fixes": [fix(18.47, -77.925, now - timedelta(minutes=8), sog=0.1)]}   # Falmouth, Jamaica
    v = trip.view(CFG, track, now, house=(40.71, -74.01))   # New York
    assert 1530 <= v["far"]["miles"] <= 1570 and v["far"]["miles"] % 10 == 0
    assert v["far"]["xy"][1] < 0   # north of the Caribbean map, on north.svg
    assert trip.view(CFG, track, now)["far"] is None   # no weather location: no button


def test_an_old_report_shown_again_keeps_its_time():
    t = {"fixes": []}
    trip._keep(t, {"lat": 22.68, "lon": -74.48, "sog": None, "at": "2027-11-23T15:11:00+00:00", "src": "cruisemapper"})
    trip._keep(t, {"lat": 22.68, "lon": -74.48, "sog": None, "at": "2027-11-23T15:21:00+00:00", "src": "cruisemapper", "rough": True})
    assert [f["at"] for f in t["fixes"]] == ["2027-11-23T15:11:00+00:00"]   # "3 hours ago" again: not a new hearing


def test_a_late_position_goes_in_its_place():
    t = {"fixes": []}
    trip._keep(t, {"lat": 22.0, "lon": -74.0, "sog": None, "at": "2027-11-23T15:00:00+00:00", "src": "cruisemapper"})
    trip._keep(t, {"lat": 21.0, "lon": -74.2, "sog": None, "at": "2027-11-23T18:00:00+00:00", "src": "phone"})
    trip._keep(t, {"lat": 21.5, "lon": -74.1, "sog": None, "at": "2027-11-23T16:30:00+00:00", "src": "phone"})
    assert [f["src"] + f["at"][11:16] for f in t["fixes"]] == ["cruisemapper15:00", "phone16:30", "phone18:00"]


def test_add_fix_checks_what_it_gets(tmp_path, monkeypatch):
    monkeypatch.setattr(trip, "DATA_DIR", tmp_path)
    with pytest.raises(ValueError):
        trip.add_fix(True, "north", "-74")
    with pytest.raises(ValueError):
        trip.add_fix(True, 22.5, -74.3, "2020-01-01T00:00:00+00:00")
    with pytest.raises(ValueError):
        trip.add_fix(True, 22.5, -74.3, "2027-11-23T12:00")   # no time zone
    f = trip.add_fix(True, "22.51234567", "-74.3", None, "hand")
    assert f["src"] == "hand" and f["lat"] == 22.51235
    assert trip.read_track(True)["fixes"][-1]["at"] == f["at"]


def test_the_guess_sails_on_from_where_she_was_heard():
    now = at("2027-11-23T20:00")   # heard 6 hours ago between Miami and Montego Bay (arrives tomorrow 10 AM)
    track = {"fixes": [{**fix(21.3, -73.8, now - timedelta(hours=6)), "src": "cruisemapper"}]}
    v = trip.view(CFG, track, now)
    assert v["ship"]["stale"] and v["ship"]["src"] == "cruisemapper"
    g = v["guess"]
    assert g and 6 <= g["knots"] <= 22
    heard, port = v["ship"]["xy"], v["next"]["xy"]
    assert g["xy"][1] > heard[1] and g["xy"][1] < port[1]   # further south than where she was heard, not there yet
    fresh = {"fixes": [{**fix(21.3, -73.8, now - timedelta(minutes=20)), "src": "phone"}]}
    assert trip.view(CFG, fresh, now)["guess"] is None   # heard lately: no guess


class _FakeHA:
    def __init__(self, state):
        self.state, self.asked = state, []

    def get(self, url, headers=None):
        self.asked.append(url)
        state = self.state

        class R:
            def raise_for_status(self):
                pass

            def json(self):
                return state
        return R()


def test_the_phone_position_comes_from_home_assistant(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from datetime import timezone
    monkeypatch.setattr(trip, "DATA_DIR", tmp_path)
    settings = SimpleNamespace(ha_url="http://ha.test:8123", ha_token="t")
    when = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(minutes=4)
    ha = _FakeHA({"state": "not_home", "last_updated": when.isoformat(),
                  "attributes": {"latitude": 20.1, "longitude": -74.9, "gps_accuracy": 35}})
    got = trip.read_phone(settings, "device_tracker.phone_on_board", True, http=ha)
    assert got["src"] == "phone" and got["lat"] == 20.1
    assert ha.asked == ["http://ha.test:8123/api/states/device_tracker.phone_on_board"]
    assert trip.read_phone(settings, "device_tracker.phone_on_board", True, http=ha) is None   # nothing new
    ha.state["attributes"]["gps_accuracy"] = 5000
    ha.state["last_updated"] = datetime.now(timezone.utc).isoformat()
    assert trip.read_phone(settings, "device_tracker.phone_on_board", True, http=ha) is None   # too rough to keep
    assert trip.read_phone(settings, "light.kitchen", True, http=ha) is None
    assert len(trip.read_track(True)["fixes"]) == 1
