"""An existing install's data, as an older version saved it, opens in this version with nothing lost.

tests/fixtures/old-addon/ was made by running the older version's own code through its HTTP API with made-up
values (a settings file, the database with chores, the screen time log and lists, photos with a focal point,
a special-day picture, a kid's photo, a portrait, three frame profiles, and the Google sign-in under its old
name google-photos.json). It has the shape of the Home Assistant add-on's /data and /media/family_frame.
"""
import io
import json
import shutil
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

FIXTURE = Path(__file__).parent / "fixtures" / "old-addon"
ORIGINAL = json.loads((FIXTURE / "data" / "settings.json").read_text())


def _tables(db: Path) -> dict:
    with sqlite3.connect(db) as c:
        names = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        return {n: c.execute(f"SELECT * FROM {n} ORDER BY 1").fetchall() for n in names}


def _png() -> bytes:
    b = io.BytesIO()
    Image.new("RGBA", (8, 8), (255, 255, 255, 255)).save(b, "PNG")
    return b.getvalue()


def make_local(root: Path) -> Path:
    """A private overlay like a family would keep: their own pack (with a seasonal variant and a png logo),
    their monogram, and their own frame.yaml."""
    pack = root / "packs" / "our-places"
    (pack / "scenes").mkdir(parents=True)
    (pack / "images").mkdir()
    (pack / "images" / "logo.png").write_bytes(_png())
    svg = '<svg viewBox="0 0 300 600"><rect width="300" height="600" fill="{c}"/>{extra}</svg>'
    (pack / "scenes" / "lakeside.svg").write_text(svg.format(c="#123456", extra=""))
    (pack / "scenes" / "lakeside-fall.svg").write_text(svg.format(c="#654321", extra=""))
    (pack / "scenes" / "lodge.svg").write_text(svg.format(
        c="#335533", extra='<image href="images/logo.png" x="1" y="2" width="20" height="20"></image>'
                           '<image href="https://example.com/x.png" width="5" height="5"></image>'))
    (pack / "pack.json").write_text(json.dumps({
        "id": "our-places", "name": "Our places", "version": "1.0.0", "priority": 60,
        "scenes": {"lakeside": {"title": "Lakeside", "script": "Fun day!", "file": "scenes/lakeside.svg",
                                "variants": [{"scene": "lakeside-fall", "from": "09-12", "to": "11-03"}]},
                   "lakeside-fall": {"title": "Lakeside in fall", "file": "scenes/lakeside-fall.svg", "hidden": True},
                   "lodge": {"title": "The lodge", "file": "scenes/lodge.svg"}},
        "groups": [{"name": "Our places", "scenes": ["lakeside", "lodge"]}],
        "rules": [{"keyword": "Lakeside Fun Park", "scene": "lakeside"}]}))
    (root / "web" / "img").mkdir(parents=True)
    (root / "web" / "img" / "monogram.png").write_bytes(_png())
    (root / "config").mkdir()
    (root / "config" / "frame.yaml").write_text(
        (Path(__file__).parent.parent / "config" / "frame.example.yaml").read_text().replace("family_name:", "family_name: From Local #", 1))
    return root


@pytest.fixture
def old_install(tmp_path, monkeypatch):
    """A copy of the old add-on's /data and photo folder, run as the add-on would run it (not demo)."""
    shutil.copytree(FIXTURE / "data", tmp_path / "data")
    shutil.copytree(FIXTURE / "media", tmp_path / "media")
    monkeypatch.delenv("FRAME_DEMO", raising=False)
    for k in ("FRAME_ADDON", "SUPERVISOR_TOKEN", "FRAME_PIN_HASH", "FRAME_SECRET"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("FRAME_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("FRAME_PHOTOS_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("FRAME_NOW", "2026-10-15T16:12:00")
    monkeypatch.setenv("FRAME_LOCAL_DIR", str(make_local(tmp_path / "local")))
    import app.special   # the U.S. holidays from the saved sample file, not the network
    monkeypatch.setattr(app.special, "US_HOLIDAYS_URL", str(Path(__file__).parent.parent / "config" / "demo-holidays.ics"))
    import importlib
    import app.config
    importlib.reload(app.config)
    yield tmp_path
    importlib.reload(app.config)


def _client():
    import importlib
    import sys
    sys.modules.pop("app.admin", None)
    import app.main
    importlib.reload(app.main)
    return TestClient(app.main.app)


def test_upgrade_keeps_everything(old_install):
    data = old_install / "data"
    before_tables = _tables(data / "frame.db")
    files_before = sorted(str(p.relative_to(data)) for p in data.rglob("*") if p.is_file())
    with _client() as c:
        assert c.post("/api/parent/unlock?remember=1", json={"pin": "1234"}).json()["name"] == "Dad"
        d = c.get("/api/frame").json()
        # Settings from the old file, not from local/config/frame.yaml (the store wins, as before)
        assert d["family_name"] == "The Example Family"
        assert [k["name"] for k in d["kids"]] == ["Child 1", "Child 2", "Child 3", "Child 4", "Child 5"]
        assert d["kids"][0]["photo"].startswith("kids/child1.jpg")
        # The screen time log and today's chores
        scr = c.get("/api/parent/screen").json()
        log = json.dumps(c.get("/api/parent/screen/log").json())
        for note in ("Helped a sibling", "Fighting in the car", "A good day for everyone"):
            assert note in log
        assert scr
        assert d["kids"][1]["chores"][0]["status"] == "waiting"            # claimed, waiting for a parent
        assert d["kids"][1]["photo"].startswith("portraits/child-2.jpg")   # the portrait from the old folder
        # Frame profiles
        frames = c.get("/api/admin/frames").json()["frames"]
        assert [f["id"] for f in frames] == ["kitchen", "bedroom", "playroom"]
        play = next(f for f in frames if f["id"] == "playroom")
        assert play["home"] == "chores" and play["kids"] == ["child3", "child4", "child5"]
        # Photos from the Mac's sync and from Settings, with the saved focal point
        assert c.get("/api/photos").json()
        adm = c.get("/api/admin/photos").json()
        assert len(adm.get("photos") or adm.get("items") or []) == 3
        # Lists from the Mac's Reminders check-in, with the item added on the frame still waiting
        lists = d["lists"]["lists"][0]
        assert lists["name"] == "Groceries" and lists["source"] == "apple"
        assert {"Milk", "Apples", "Eggs"} <= {i["title"] for i in lists["items"]}
        # Calendars: old entries have no kind or provider; they read as iCal links and keep their addresses
        cals = {x["key"]: x for x in c.get("/api/admin/settings").json()["calendars"]}
        assert list(cals) == ["family", "kids", "dad", "mom"]
        assert all(x["has_url"] and x["kind"] == "ics" for x in cals.values())
        assert cals["mom"]["filter_mode"] == "family" and cals["mom"]["filter_emails"] == "dad@example.com"
        # Google: the old sign-in file is now google.json and still counts as connected for Photos
        g = c.get("/api/admin/family").json()["google"]
        assert g["connected"] is True and g["granted"] == ["photos"]
        assert g["client_id"] == "123-fake.apps.googleusercontent.com"
        # A special-day picture and a portrait from the old folders
        sp = c.get("/api/admin/special").json()
        assert "lake-day" in json.dumps(sp["pictures"])
        assert sp["countdown_days"] == 14 if "countdown_days" in sp else True
    assert (data / "google.json").read_bytes() == (data / "google-photos.json").read_bytes()   # old file kept for going back
    assert (data / "settings.before-upgrade.json").read_text() == (FIXTURE / "data" / "settings.json").read_text()
    after = json.loads((data / "settings.json").read_text())
    assert after["data_version"] == 2
    for k, v in ORIGINAL.items():   # every old key and value is still there
        assert after[k] == v, k
    assert after["google"]["client_id"] == ORIGINAL["special_days"]["google_photos"]["client_id"]
    after_tables = _tables(data / "frame.db")
    for t, rows in before_tables.items():   # no table lost a row or changed one
        assert after_tables[t][:len(rows)] == rows, t
    files_after = {str(p.relative_to(data)) for p in data.rglob("*") if p.is_file()}
    for f in files_before:
        assert f in files_after, f


def test_saving_in_settings_keeps_old_keys(old_install):
    with _client() as c:
        c.post("/api/parent/unlock?remember=1", json={"pin": "5678"})
        r = c.put("/api/admin/screen_time", json={"base_saturday_minutes": 100, "base_sunday_minutes": 60, "good_day_minutes": 30,
                                                   "full_minutes": 480, "new_week_day": "sun", "new_week_time": "21:00",
                                                   "views": ["leader", "vault", "rocket", "glass"]})
        assert r.status_code == 200, r.text
    after = json.loads((old_install / "data" / "settings.json").read_text())
    assert after["screen_time"]["base_saturday_minutes"] == 100
    for k in ORIGINAL:
        assert k in after
    assert after["special_days"]["words"] == ORIGINAL["special_days"]["words"]
    assert after["calendars"] == ORIGINAL["calendars"]


def test_private_pack_variant_and_logo(old_install):
    from datetime import date
    with _client() as c:
        import app.main
        s = app.main.app.state.services
        ids = {p["id"]: p["where"] for p in s.packs.all}
        assert ids["our-places"] == "local"
        # The saved word "Lakeside Fun Park" finds the private scene, in its fall colors from mid-September
        assert s.special.picture("lakeside", date(2026, 10, 15))[0] == "lakeside-fall"
        assert s.special.picture("lakeside", date(2026, 7, 4))[0] == "lakeside"
        assert s.special.picture("lodge", date(2026, 7, 4))[0] == "lodge"
        art = c.get("/art.js").text
        assert 'href=\\"art/packs/our-places/images/logo.png\\"' in art   # its own logo, through the pack's address
        assert "example.com/x.png" not in art                              # an outside address is still removed
        assert c.get("/art/packs/our-places/images/logo.png").status_code == 200
        # The monogram from local/web wins over the public one
        assert c.get("/static/img/monogram.png").content == (old_install / "local" / "web" / "img" / "monogram.png").read_bytes()
        assert c.get("/static/css/frame.css").status_code == 200   # everything else still comes from web/
        # The family name from the settings is the page title
        assert "<title>The Example Family</title>" in c.get("/frame").text


def test_variant_wraps_new_year():
    from datetime import date
    from app.packs import PackSet
    ps = PackSet([], set())
    ps.scenes = {"a": {"variants": [{"scene": "b", "from": "12-20", "to": "01-05"}]}, "b": {}}
    assert ps.variant("a", date(2026, 12, 25)) == "b"
    assert ps.variant("a", date(2027, 1, 2)) == "b"
    assert ps.variant("a", date(2027, 1, 6)) == "a"
    assert ps.variant("a", None) == "a"


def test_old_install_gets_the_optional_packs(old_install, monkeypatch):
    """Older versions had every picture built in: the first start installs the optional packs."""
    monkeypatch.delenv("FRAME_EXTRA_PACKS")
    from app import compat
    import app.config as cfg
    steps = compat.plan(cfg.DATA_DIR, json.loads((cfg.DATA_DIR / "settings.json").read_text()))
    assert any("Faith" in s for s in steps) and any("google.json" in s for s in steps)
    got = []
    done = compat.upgrade(cfg.DATA_DIR, False, install=lambda pid: got.append(pid))
    assert sorted(got) == ["faith", "kids-activities", "outings"]
    assert any("Installed the Faith art pack" in x for x in done)
    store = json.loads((cfg.DATA_DIR / "settings.json").read_text())
    assert store["art_packs"]["installed_on_upgrade"] == got and "off" not in store["art_packs"]
    assert compat.upgrade(cfg.DATA_DIR, False, install=lambda pid: got.append(pid)) == []   # once only


def test_new_install_is_never_upgraded(tmp_path, monkeypatch):
    monkeypatch.setenv("FRAME_DATA_DIR", str(tmp_path))
    import importlib
    import app.config as cfg
    importlib.reload(cfg)
    from app import compat
    assert compat.upgrade(tmp_path, False, install=lambda pid: pytest.fail("installed")) == []
    assert json.loads((tmp_path / "settings.json").read_text()) == {"data_version": 2}
    assert compat.upgrade(tmp_path, True) == []   # demo mode: never


def test_compat_report(old_install, capsys):
    from app import compat
    assert compat.main([str(old_install / "data")]) == 0
    out = capsys.readouterr().out
    assert "an older version" in out and "our-places" in out
    assert not (old_install / "data" / "google.json").exists()   # the report changes nothing


def test_legacy_google_token_without_scope(tmp_path):
    from app.google_auth import GoogleAccount
    (tmp_path / "google-photos.json").write_text(json.dumps({"refresh_token": "x"}))
    g = GoogleAccount(tmp_path / "google.json", "id", "secret", "https://frame.example.com", "s")
    assert g.connected and g.granted() == {"photos"}


def test_local_config_is_read_first(old_install, monkeypatch):
    import app.config as cfg
    (old_install / "data" / "settings.json").write_text("{}")
    assert cfg.load_settings().family_name.startswith("From Local")
    monkeypatch.setenv("FRAME_DEMO", "1")   # demo mode never reads it
    assert not cfg.load_settings().family_name.startswith("From Local")


def test_own_pack_images_only(tmp_path):
    from app.packs import sanitize_svg
    (tmp_path / "images").mkdir()
    (tmp_path / "images" / "a.png").write_bytes(b"x")
    pack = {"id": "p", "folder": tmp_path}
    from app.packs import _own_url
    own = lambda rel: _own_url(pack, rel)   # noqa: E731
    svg = ('<svg viewBox="0 0 10 10"><image href="images/a.png" onload="x()" width="1"></image>'
           '<image href="../a.png"></image><image href="/etc/a.png"></image><image href="images/missing.png"></image>'
           '<image data-own="1" href="https://example.com/a.png"></image><rect data-own="1" width="2"></rect></svg>')
    out = sanitize_svg(svg, own_file=own)
    assert out.count("<image") == 1 and 'href="art/packs/p/images/a.png"' in out
    assert "onload" not in out and "data-own" not in out and "example.com" not in out
    assert "<image" not in sanitize_svg(svg)   # without a pack to look in: no pictures at all, as before


def test_old_mac_helper_checkin_still_works(old_install):
    """The Mac helpers installed today keep their upload key and the same check-in."""
    tok = {"X-Upload-Token": "fixture-upload-token-not-real"}
    with _client() as c:
        r = c.post("/api/lists/sync", headers=tok, json={"lists": [{"id": "L-groceries", "name": "Groceries", "count": 4}],
                                                          "items": {"L-groceries": [{"ext": "R9", "title": "Butter", "done": False}]}})
        assert r.status_code == 200, r.text
        assert "Butter" in json.dumps(c.get("/api/frame").json()["lists"])
        assert c.get("/api/portraits/wanted", headers=tok).status_code == 200
        assert c.post("/api/lists/sync", headers={"X-Upload-Token": "wrong"}, json={}).status_code == 401


def test_app_name_from_local_config(old_install):
    cfg = old_install / "local" / "config" / "frame.yaml"
    cfg.write_text(cfg.read_text() + "\napp_name: Our Frame\n")
    with _client() as c:
        html = c.get("/admin").text
        assert "<title>Our Frame · Settings</title>" in html and '<div class="script">Our Frame</div>' in html


def test_disconnect_removes_the_kept_old_sign_in(tmp_path):
    from app.google_auth import GoogleAccount
    tok = json.dumps({"refresh_token": "x", "scope": "s"})
    (tmp_path / "google-photos.json").write_text(tok)
    (tmp_path / "google.json").write_text(tok)

    class H:
        def post(self, *a, **k):
            return None
    g = GoogleAccount(tmp_path / "google.json", "id", "secret", "https://frame.example.com", "s", http=H())
    g.disconnect()
    assert not (tmp_path / "google.json").exists() and not (tmp_path / "google-photos.json").exists()
    assert not GoogleAccount(tmp_path / "google.json", "id", "secret", "https://frame.example.com", "s").connected
