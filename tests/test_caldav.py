"""Private calendars over CalDAV (iCloud with an app-specific password), against a fake server."""
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from app import caldav
from app.calendar_feed import CalendarService
from app.config import CalendarSource

from fake_caldav import HOST, PASSWORD, USER, FakeCalDAV


@pytest.fixture
def fake(monkeypatch):
    server = FakeCalDAV()
    monkeypatch.setattr(caldav, "make_http", server.client)
    return server


def test_discovery_follows_icloud_redirect_and_skips_task_lists(fake):
    cals = caldav.CalDAVClient(caldav.ICLOUD_SERVER, USER, PASSWORD).calendars()
    assert [c["name"] for c in cals] == ["Home", "Kids"]          # Reminders (tasks only) left out
    assert cals[0]["url"] == HOST + "/123/calendars/home/"
    assert cals[0]["color"] == "#2E4A7A"
    # The login went along to the new host after the redirect
    assert all(r.headers.get("authorization") for r in fake.requests)


def test_wrong_password_is_plain_english(fake):
    with pytest.raises(caldav.CalDAVError, match="app-specific password"):
        caldav.CalDAVClient(caldav.ICLOUD_SERVER, USER, "nope").calendars()


def test_server_address_is_normalized():
    assert caldav.normalize_server("") == "https://caldav.icloud.com/"
    assert caldav.normalize_server("webcal://dav.example.com/x") == "https://dav.example.com/x/"
    assert caldav.normalize_server("caldav.example.com") == "https://caldav.example.com/"


def _src():
    return CalendarSource(key="icloud", label="Home", color="#2E4A7A", tint="#E5EAF2", kind="caldav",
                          caldav_server=caldav.ICLOUD_SERVER, caldav_user=USER, caldav_password=PASSWORD,
                          caldav_calendar=HOST + "/123/calendars/home/")


def test_caldav_events_use_the_same_parser_and_repeats(settings, tmp_path, fake):
    settings.calendars = [_src()]
    c = CalendarService(settings, tmp_path / "cache")
    c.refresh()
    assert c.errors == {}
    week = c.events_between(date(2026, 10, 11), date(2026, 10, 18))
    by_title = {e["title"]: e for e in week}
    assert by_title["Piano lesson"]["day"] == "2026-10-15"       # weekly repeat expanded, name tag stripped
    assert by_title["Piano lesson"]["who"] == "Child 1"
    assert by_title["Park picnic"]["all_day"]
    assert (tmp_path / "cache" / "icloud.ics").exists()          # cached like an .ics address
    report = next(r for r in fake.requests if r.method == "REPORT")
    assert b"time-range" in report.content


def test_caldav_failure_keeps_last_good_copy(settings, tmp_path, fake):
    settings.calendars = [_src()]
    c = CalendarService(settings, tmp_path / "cache")
    c.refresh()
    fake.down = True
    c.refresh()
    assert "icloud" in c.errors and "503" in c.errors["icloud"]
    assert any(e["title"] == "Piano lesson" for e in c.events_between(date(2026, 10, 15), date(2026, 10, 16)))
    # A restart while the server is down still shows the cached copy
    fresh = CalendarService(settings, tmp_path / "cache")
    fresh.refresh()
    assert any(e["title"] == "Piano lesson" for e in fresh.events_between(date(2026, 10, 15), date(2026, 10, 16)))


def test_no_calendar_picked_is_an_error_not_a_crash(settings, tmp_path, fake):
    src = _src()
    src.caldav_calendar = ""
    settings.calendars = [src]
    c = CalendarService(settings, tmp_path / "cache")
    c.refresh()
    assert "Find my calendars" in c.errors["icloud"]


# ---------- Settings > Calendars ----------

@pytest.fixture
def admin(demo_env, monkeypatch, fake):
    monkeypatch.setenv("FRAME_NOW", "2026-10-15T16:12:00")
    import importlib
    import sys
    sys.modules.pop("app.admin", None)
    import app.main
    importlib.reload(app.main)
    with TestClient(app.main.app) as c:
        assert c.post("/api/parent/unlock?remember=1", json={"pin": "1234"}).status_code == 200
        yield c


def test_find_calendars_then_save_without_echoing_the_password(admin):
    r = admin.post("/api/admin/test/caldav", json={"key": "", "provider": "icloud", "caldav_user": USER, "caldav_password": PASSWORD}).json()
    assert r["ok"] and [c["name"] for c in r["calendars"]] == ["Home", "Kids"]
    home = r["calendars"][0]

    cals = admin.get("/api/admin/settings").json()["calendars"]
    cals.append({"key": "", "label": "iCloud home", "color": "#2E4A7A", "who_default": "everyone", "filter_mode": "all",
                 "kind": "caldav", "provider": "icloud", "caldav_user": USER, "caldav_password": PASSWORD,
                 "caldav_calendar": home["url"], "caldav_calendar_name": home["name"]})
    assert admin.put("/api/admin/calendars", json=cals).status_code == 200
    raw = admin.get("/api/admin/settings")
    assert PASSWORD not in raw.text
    got = next(c for c in raw.json()["calendars"] if c["label"] == "iCloud home")
    assert got["kind"] == "caldav" and got["has_password"] and got["has_url"]
    assert got["caldav_calendar_name"] == "Home" and "caldav_password" not in got

    # Saving again with a blank password keeps the saved one; Check still signs in.
    cals = raw.json()["calendars"]
    assert admin.put("/api/admin/calendars", json=cals).status_code == 200
    r = admin.post("/api/admin/test/calendar", json={"key": got["key"], "kind": "caldav", "provider": "icloud",
                                                     "caldav_user": USER, "caldav_calendar": home["url"]}).json()
    assert r["ok"], r
    assert "events in the next two weeks" in r["message"]

    # A different sign-in name does not reuse the saved password.
    r = admin.post("/api/admin/test/caldav", json={"key": got["key"], "provider": "icloud", "caldav_user": "someone@example.com"}).json()
    assert not r["ok"]


def test_webcal_address_saved_as_https(admin):
    cals = admin.get("/api/admin/settings").json()["calendars"]
    cals[0]["ics_url"] = "webcal://p01-caldav.example.com/published/2/abc"
    assert admin.put("/api/admin/calendars", json=cals).status_code == 200
    from app.config import effective_config
    assert effective_config(True)["calendars"][0]["ics_url"] == "https://p01-caldav.example.com/published/2/abc"
    got = admin.get("/api/admin/settings").json()["calendars"][0]
    assert got["kind"] == "ics" and got["has_url"]
