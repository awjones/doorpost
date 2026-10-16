"""Modules (Settings > Modules): turning each part of the frame off and back on.

A module that is off: its addresses answer 404, its frame screens and Today pieces leave the
frame's data, its Settings page leaves the menu, its background work stops, and Overview stops
asking about it. Turning it back on brings everything back; nothing is deleted.
"""
import re
import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import modules as M

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def admin(demo_env, monkeypatch):
    monkeypatch.setenv("FRAME_NOW", "2026-10-15T16:12:00")
    import importlib
    import sys
    sys.modules.pop("app.admin", None)
    sys.modules.pop("app.admin_providers", None)
    import app.main
    importlib.reload(app.main)
    with TestClient(app.main.app) as c:
        assert c.post("/api/parent/unlock?remember=1", json={"pin": "1234"}).status_code == 200
        yield c


def turn(c, **changes):
    r = c.put("/api/admin/modules", json=changes)
    assert r.status_code == 200, r.text
    return r.json()


def concrete(pattern: str) -> str:
    """A real address for a ROUTES pattern ("/kids/*" -> "/kids/x/y")."""
    p = pattern.replace("*", "x")
    return p + "/x" if pattern.endswith("/*") else p


# ---------------- the registry ----------------

def test_registry_is_consistent():
    assert len(M.IDS) == len(set(M.IDS))
    for m in M.MODULES:
        assert m["name"] and m["description"] and m["needs_text"]
        assert all(r in M.BY_ID for r in m.get("requires", []))
        assert all(n in M.NEEDS for n in m.get("needs", []))
    assert M.BY_ID["screen_time"]["requires"] == ["chores"]
    assert M.BY_ID["calendar"]["always_on"]
    from app import frames
    assert set(M.SCREEN_MODULE) <= set(frames.SCREENS)


def test_admin_pages_match_the_menu():
    from app.main import ADMIN_PAGES
    js = (ROOT / "web/js/admin.js").read_text()
    menu = re.findall(r"\['([a-z-]+)', '[^']+'\]", js.split("var PAGES = ", 1)[1].split(";", 1)[0])
    assert "modules" in ADMIN_PAGES and "modules" in menu
    for page in M.PAGE_MODULE:
        assert page in ADMIN_PAGES and page in menu, page


def test_route_matching():
    assert M.owner("/api/chores/abc/claim") == "chores"
    assert M.owner("/api/parent/screen/log") == "screen_time"
    assert M.owner("/api/parent/screenx") is None
    assert M.owner("/kids/child1.jpg") == "portraits"
    assert M.owner("/api/admin/kids/child1/photo") == "portraits"
    assert M.owner("/api/admin/kids") is None          # saving the kids list is core
    assert M.owner("/frame/kids") is None
    assert M.owner("/api/frame") is None
    assert M.owner("/api/photos/upload") == "photos"


def test_defaults_for_a_setup_from_before_modules():
    """No `modules` saved yet: on what's already in use, off what isn't."""
    bare = M.chosen({}, demo=False)
    assert bare["chores"] and bare["weather"] and bare["photos"] and bare["calendar"]
    assert not bare["lists"] and not bare["house"] and not bare["multi_frame"] and not bare["kids_view"]
    used = M.chosen({"lists": {"shown": ["groceries"]}, "home_assistant": {"enabled": True},
                     "frames": [{"id": "a"}, {"id": "b", "home": "kids"}],
                     "cloudflare_access": {"team_domain": "x.example.com", "aud": "y"}}, demo=False)
    assert used["lists"] and used["house"] and used["multi_frame"] and used["kids_view"] and used["remote_access"]
    assert all(M.chosen({}, demo=True).values())          # demo mode: everything on


def test_requires_and_choices():
    on = M.resolve({"modules": {"chores": False, "screen_time": True}}, demo=True)
    assert "screen_time" not in on and "chores" not in on
    new, notes = M.apply_choice({"chores": False, "screen_time": False}, {"screen_time": True})
    assert new["chores"] and new["screen_time"] and "Chores was turned on too" in notes[0]
    new, notes = M.apply_choice({"chores": True, "screen_time": True}, {"chores": False})
    assert not new["chores"] and new["screen_time"] and "Screen time is off too while Chores is off" in notes[0]
    assert "screen_time" not in M.resolve({"modules": new}, demo=True)          # resting until chores is back
    with pytest.raises(ValueError):
        M.apply_choice({"chores": True, "screen_time": False}, {"chores": False, "screen_time": True})


# ---------------- every module, off and back on ----------------

def test_demo_starts_with_everything_on(admin):
    d = admin.get("/api/frame").json()
    assert set(d["modules"]) == set(M.IDS)   # the tests install the Faith pack, so Lord's Day is there too
    mods = admin.get("/api/admin/modules").json()
    assert mods["count"] == mods["total"] == len(M.IDS)
    assert all(r["status"] is not None for r in mods["modules"])


@pytest.mark.parametrize("mid", [m["id"] for m in M.MODULES if not m.get("always_on")])
def test_each_module_off_and_back_on(admin, mid):
    before = admin.get("/api/frame?frame=kitchen").json()
    turn(admin, **{mid: False})
    on = set(M.on_set(admin.app.state.services.settings))
    assert mid not in on

    # the frame's data
    for fid in ("kitchen", "playroom"):
        d = admin.get(f"/api/frame?frame={fid}").json()
        assert mid not in d["modules"]
        for screen in M.BY_ID[mid].get("screens", []):
            assert screen not in d["frame"]["screens"], (fid, screen)
            assert d["frame"]["home"] != screen
    d = admin.get("/api/frame?frame=kitchen").json()
    checks = {
        "weather": lambda: d["weather"] is None,
        "house": lambda: d["home"] == [],
        "lists": lambda: d["lists"]["lists"] == [],
        "photos": lambda: d["photos_count"] == 0,
        "screen_time": lambda: d["screen"] is None,
        "chores": lambda: all(k["chores"] == [] and k["total"] == 0 for k in d["kids"]) and d["screen"] is None,
        "portraits": lambda: all(k["photo"] is None for k in d["kids"]),
        "special_days": lambda: d["calendar"]["upcoming"] is None and not any(
            day["special"] for day in d["calendar"]["week"]["days"]),
        "multi_frame": lambda: len(admin.get("/api/frames").json()["frames"]) == 1,
        "kids_view": lambda: "kidsview" not in admin.get("/api/frame?frame=playroom").json(),
    }
    if mid in checks:
        assert checks[mid](), mid

    # its addresses and Settings pages
    for pattern in M.BY_ID[mid].get("routes", []):
        assert admin.get(concrete(pattern)).status_code == 404, pattern
        assert admin.post(concrete(pattern)).status_code == 404, pattern
    settings = admin.get("/api/admin/settings").json()
    assert mid not in settings["modules"]
    for page, owner in settings["page_modules"].items():
        if owner == mid:
            assert admin.get(f"/admin/{page}").status_code == 404

    # back on: everything returns
    turn(admin, **{mid: True})
    after = admin.get("/api/frame?frame=kitchen").json()
    assert set(after["modules"]) == set(before["modules"])
    assert after["frame"]["screens"] == before["frame"]["screens"]
    for page, owner in admin.get("/api/admin/settings").json()["page_modules"].items():
        if owner == mid:
            assert admin.get(f"/admin/{page}").status_code == 200


def test_screen_time_brings_chores_back(admin):
    r = turn(admin, chores=False)
    assert any("Screen time is off too" in n for n in r["notes"])
    assert admin.get("/api/parent/screen").status_code == 404
    row = [m for m in admin.get("/api/admin/modules").json()["modules"] if m["id"] == "screen_time"][0]
    assert row["chosen"] and not row["on"] and row["blocked_by"] == ["Chores"]
    turn(admin, chores=True)    # screen time comes back with it
    assert admin.get("/api/parent/screen").status_code == 200
    turn(admin, chores=False, screen_time=False)
    r = turn(admin, screen_time=True)
    assert any("Chores was turned on too" in n for n in r["notes"])
    assert admin.get("/api/parent/screen").status_code == 200


def test_nothing_is_deleted(admin):
    chores = admin.get("/api/admin/settings").json()["chores"]
    lists_before = admin.get("/api/admin/lists").json()["shown"]
    turn(admin, chores=False, lists=False, multi_frame=False)
    # Saving Settings > Frames while modules are off keeps the hidden frames and screens
    fr = admin.get("/api/admin/frames").json()
    assert len(fr["frames"]) == 1 and not fr["multi"]
    assert "lists" not in [s["key"] for s in fr["screens"]]
    body = [dict(fr["frames"][0], name="Kitchen wall")]
    assert admin.put("/api/admin/frames", json=body).status_code == 200
    turn(admin, chores=True, lists=True, multi_frame=True)
    assert admin.get("/api/admin/settings").json()["chores"] == chores
    assert admin.get("/api/admin/lists").json()["shown"] == lists_before
    frames = {f["id"]: f for f in admin.get("/api/admin/frames").json()["frames"]}
    assert frames["kitchen"]["name"] == "Kitchen wall"
    assert "lists" in frames["kitchen"]["screens"] and "chores" in frames["kitchen"]["screens"]
    assert "playroom" in frames


def test_kids_frame_without_chores(admin):
    turn(admin, chores=False)
    d = admin.get("/api/frame?frame=playroom").json()
    assert d["frame"]["home"] == "kids" and "kidsview" in d
    assert all(k["chores"] == [] for k in d["kids"]) and d["screen"] is None
    assert d["frame"]["screens"] == ["kids", "photos"]
    turn(admin, kids_view=False)
    d = admin.get("/api/frame?frame=playroom").json()
    assert d["frame"]["home"] == "today" and "kids" not in d["frame"]["screens"]


def test_one_frame_when_multiple_frames_is_off(admin):
    turn(admin, multi_frame=False)
    assert admin.get("/api/frame?frame=playroom").json()["frame"]["id"] == "kitchen"
    assert admin.post("/api/parent/frames", json={"name": "Hall"}).status_code == 404


def test_phone_page_and_needs_attention(admin):
    turn(admin, screen_time=False, weather=False, house=False, photos=False)
    s = admin.get("/api/parent/summary").json()
    assert "screen_time" not in s["modules"] and "chores" in s["modules"]
    st = admin.get("/api/admin/status").json()
    assert st["weather_error"] is None and st["home_error"] is None and not st["screen_new_week_due"]
    assert st["photo_sources"] == [] and "weather" not in st["modules"]


def test_lords_day_needs_the_faith_pack(admin, monkeypatch):
    assert any(r["id"] == "lords_day" for r in admin.get("/api/admin/modules").json()["modules"])
    monkeypatch.delenv("FRAME_EXTRA_PACKS")
    from app import config, packs
    admin.app.state.services.packs = packs.load(True)
    admin.app.state.services.settings.modules_on = M.resolve(config.effective_config(True), True, packs.load(True))
    rows = admin.get("/api/admin/modules").json()["modules"]
    assert "lords_day" not in [r["id"] for r in rows]
    r = admin.put("/api/admin/modules", json={"lords_day": True})
    assert r.status_code == 400 and "Faith" in r.json()["detail"]


def test_background_jobs_stop(admin):
    """The minute loop skips the photo scan and the Google Tasks sync when their modules are off."""
    import app.main as main
    turn(admin, photos=False, lists=False, special_days=False)
    s = admin.app.state.services
    calls = []
    s.photos.maybe_rescan = lambda *a, **k: calls.append("photos")
    s.photos.prepare_some = lambda *a, **k: calls.append("photos")
    s.sync_google_tasks = lambda: calls.append("tasks")
    s.holidays.refresh = lambda *a, **k: calls.append("holidays")
    s.calendar.refresh = lambda *a, **k: calls.append("calendar")

    class Once:
        n = 0

        def is_set(self):
            self.n += 1
            return self.n > 1

        def wait(self, _):
            pass
    main.background_loop(admin.app, Once())
    assert "photos" not in calls and "tasks" not in calls and "holidays" not in calls


def test_enabled_dependency(admin):
    from fastapi import HTTPException
    dep = M.enabled("lists")
    req = type("R", (), {"app": admin.app})()
    dep(req)
    turn(admin, lists=False)
    with pytest.raises(HTTPException) as e:
        dep(req)
    assert e.value.status_code == 404


def test_frame_page_knows_the_modules():
    """The frame, kids view and phone page read `modules` and leave out what is off."""
    app_js = (ROOT / "web/js/app.js").read_text()
    assert "function on(mod)" in app_js and "S.data.modules" in app_js
    assert "H.on('chores')" in (ROOT / "web/js/kids.js").read_text()
    assert "P.sum.modules" in (ROOT / "web/parent.html").read_text()
    assert "=>" not in app_js   # Chrome 106 / Android 6 WebView: no arrow functions
