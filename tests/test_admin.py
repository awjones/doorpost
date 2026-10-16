"""Admin panel API: saving settings, secrets handling, uploads, kid faces, and who may get in."""
import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image


def jpeg(color=(200, 120, 60), size=(900, 600)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "JPEG")
    return buf.getvalue()


@pytest.fixture
def make_client(demo_env, monkeypatch):
    def make(addon=False):
        if addon:
            monkeypatch.setenv("FRAME_ADDON", "1")
        monkeypatch.setenv("FRAME_NOW", "2026-10-15T16:12:00")
        import importlib
        import sys
        sys.modules.pop("app.admin", None)
        sys.modules.pop("app.admin_providers", None)
        import app.main
        importlib.reload(app.main)
        return TestClient(app.main.app)
    return make


@pytest.fixture
def admin(make_client):
    with make_client() as c:
        assert c.post("/api/parent/unlock?remember=1", json={"pin": "1234"}).status_code == 200
        yield c


def test_admin_needs_sign_in(make_client):
    with make_client() as c:
        assert c.get("/api/admin/settings").status_code == 401


def test_addon_admin_only_through_home_assistant(make_client):
    with make_client(addon=True) as c:
        # Direct port (the frame / the LAN): refused even with a PIN session
        c.post("/api/parent/unlock?remember=1", json={"pin": "1234"})
        r = c.get("/api/admin/settings")
        assert r.status_code == 403 and "sidebar" in r.json()["detail"]
    import app.main
    with TestClient(app.main.app, client=("172.30.32.2", 50000)) as c:  # HA's ingress proxy
        assert c.get("/api/admin/settings").status_code == 200
        page = c.get("/", headers={"X-Ingress-Path": "/api/hassio_ingress/abc"}).text
        assert '<base href="/api/hassio_ingress/abc/">' in page and "Settings" in page


def test_calendar_address_is_never_sent_back(admin):
    cals = admin.get("/api/admin/settings").json()["calendars"]
    body = [dict(c, ics_url="") for c in cals]
    body[0]["ics_url"] = "https://calendar.google.com/calendar/ical/secret123/basic.ics"
    assert admin.put("/api/admin/calendars", json=body).status_code == 200
    got = admin.get("/api/admin/settings").json()["calendars"][0]
    assert got["has_url"] and got["url_hint"] == "…ic.ics"
    assert "secret123" not in admin.get("/api/admin/settings").text
    # saving again with the field blank keeps the saved address
    admin.put("/api/admin/calendars", json=[dict(c, ics_url="") for c in admin.get("/api/admin/settings").json()["calendars"]])
    assert admin.get("/api/admin/settings").json()["calendars"][0]["has_url"]


def test_bad_save_is_rejected_and_rolled_back(admin):
    before = admin.get("/api/admin/settings").json()["kids"]
    r = admin.put("/api/admin/kids", json=[{"id": "x", "name": "", "color": "#000000"}])
    assert r.status_code == 400
    assert admin.get("/api/admin/settings").json()["kids"] == before


def test_chores_save_and_show_on_frame(admin):
    chores = admin.get("/api/admin/settings").json()["chores"]
    chores.append({"kid": "child3", "title": "Feed the fish", "minutes": 5, "days": ["thu"]})
    assert admin.put("/api/admin/chores", json=chores).status_code == 200
    sol = [k for k in admin.get("/api/frame").json()["kids"] if k["id"] == "child3"][0]
    assert "Feed the fish" in [c["title"] for c in sol["chores"]]


def test_kid_face_photo(admin):
    r = admin.post("/api/admin/kids/child3/photo", files={"file": ("child3.jpg", jpeg(), "image/jpeg")})
    assert r.status_code == 200
    kid = [k for k in admin.get("/api/frame").json()["kids"] if k["id"] == "child3"][0]
    assert kid["photo"].startswith("kids/child3.jpg?v=")
    img = admin.get("/" + kid["photo"])
    assert img.status_code == 200 and img.headers["content-type"] == "image/jpeg"
    with Image.open(io.BytesIO(img.content)) as im:
        assert im.size == (320, 320)
    assert admin.delete("/api/admin/kids/child3/photo").status_code == 200
    assert [k for k in admin.get("/api/frame").json()["kids"] if k["id"] == "child3"][0]["photo"] is None


def test_photo_upload_and_remove(admin):
    r = admin.post("/api/admin/photos", files=[("files", ("beach day.jpg", jpeg(), "image/jpeg")),
                                               ("files", ("notes.txt", b"hello", "text/plain"))])
    body = r.json()
    assert body["saved"] == ["beach-day.jpg"] and len(body["errors"]) == 1
    photos = admin.get("/api/admin/photos").json()["photos"]
    assert len(photos) == 1 and photos[0]["source"] == "uploads"
    assert admin.get(f"/photos/{photos[0]['id']}.jpg").status_code == 200
    assert admin.delete(f"/api/admin/photos/{photos[0]['id']}").status_code == 200
    assert admin.get("/api/admin/photos").json()["photos"] == []


def test_mac_favorites_upload_needs_token(admin):
    token = admin.get("/api/admin/settings").json()["photos"]["upload_token"]
    files = {"file": ("IMG_1.jpg", jpeg(), "image/jpeg")}
    assert admin.post("/api/photos/upload", files=files).status_code == 401
    assert admin.post("/api/photos/upload", files=files, headers={"X-Upload-Token": token}).status_code == 200
    # iPhone originals arrive as .JPG; the frame stores .jpg, and pruning must still match them
    admin.post("/api/photos/upload", files={"file": ("IMG_2.JPG", jpeg(), "image/jpeg")}, headers={"X-Upload-Token": token})
    r = admin.post("/api/photos/prune", json={"keep": ["IMG_2.JPG"]}, headers={"X-Upload-Token": token})
    assert r.json()["removed"] == 1
    names = [p["name"] for p in admin.get("/api/admin/photos").json()["photos"]]
    assert names == ["apple-favorites/IMG_2.jpg"]


def test_set_pin(admin):
    assert admin.post("/api/admin/pin", json={"pin": "12"}).status_code == 400
    assert admin.post("/api/admin/pin", json={"pin": "8642"}).status_code == 200
    assert admin.post("/api/parent/unlock", json={"pin": "8642"}).status_code == 200
    assert admin.post("/api/parent/unlock", json={"pin": "1234"}).status_code == 403


def test_a_pin_each_parent(admin):
    assert admin.post("/api/admin/pin", json={"name": "Dad", "pin": "2468"}).status_code == 200
    r = admin.post("/api/admin/pin", json={"name": "Mom", "pin": "2468"})
    assert r.status_code == 400 and "already uses that PIN" in r.json()["detail"]
    assert admin.post("/api/admin/pin", json={"name": "Mom", "pin": "1357"}).status_code == 200
    assert admin.post("/api/parent/unlock", json={"pin": "1357"}).json()["name"] == "Mom"
    assert admin.post("/api/parent/unlock", json={"pin": "1234"}).status_code == 403   # demo PINs are gone
    sec = admin.get("/api/admin/settings").json()["security"]
    assert sec["parents"] == ["Dad", "Mom"] and "hash" not in str(sec)
    assert admin.request("DELETE", "/api/admin/pin?name=Mom").status_code == 200
    assert admin.post("/api/parent/unlock", json={"pin": "1357"}).status_code == 403


def test_screen_time_settings(admin):
    body = {"base_saturday_minutes": 120, "base_sunday_minutes": 60, "good_day_minutes": 20, "full_minutes": 600,
            "new_week_day": "sun", "new_week_time": "20:30", "views": ["rocket", "vault"]}
    assert admin.put("/api/admin/screen_time", json=body).status_code == 200
    st = admin.get("/api/admin/settings").json()["screen_time"]
    assert st["base_saturday_minutes"] == 120 and st["views"] == ["rocket", "vault"]
    sc = admin.get("/api/frame").json()["screen"]
    assert sc["base"] == 180 and sc["good_day_minutes"] == 20 and sc["views"] == ["rocket", "vault"]
    assert admin.put("/api/admin/screen_time", json=dict(body, good_day_minutes="lots")).status_code == 400


def test_each_settings_section_has_its_own_address(make_client):
    with make_client() as c:
        for path in ("/admin", "/admin/calendars", "/admin/chores", "/admin/special-days", "/admin/pins"):
            r = c.get(path)
            assert r.status_code == 200 and 'id="side"' in r.text, path
        assert c.get("/admin/nope").status_code == 404


def test_public_calendar_address_is_flagged(admin):
    cals = admin.get("/api/admin/settings").json()["calendars"]
    body = [{"key": x["key"], "label": x["label"], "color": x["color"]} for x in cals]
    body[0]["ics_url"] = "https://calendar.google.com/calendar/ical/someone%40example.com/public/basic.ics"
    assert admin.put("/api/admin/calendars", json=body).status_code == 200
    cals = admin.get("/api/admin/settings").json()["calendars"]
    assert cals[0]["public"] is True and cals[1]["public"] is False


def test_lists_settings_frame_and_mac_sync(admin):
    d = admin.get("/api/frame").json()["lists"]
    assert [x["name"] for x in d["lists"]] == ["Groceries"] and d["home"] == "demo-groceries"
    # Settings > Lists: add Family To-Do, keep Groceries on the Today screen.
    assert admin.put("/api/admin/lists", json={"shown": ["demo-groceries", "demo-todo"], "home": "demo-groceries",
                                               "sections": ["demo-groceries"], "anyone_add": True, "anyone_check": True}).status_code == 200
    d = admin.get("/api/frame").json()["lists"]
    assert [x["name"] for x in d["lists"]] == ["Groceries", "Family To-Do"]
    # On the frame: add and check off (no PIN needed).
    new = admin.post("/api/lists/demo-groceries/add", json={"title": "Yogurt"}).json()
    assert admin.post(f"/api/lists/item/{new['id']}/toggle").json()["done"] is True
    # The Mac's check-in needs the upload key and gets the frame's change back.
    assert admin.post("/api/lists/sync", json={}).status_code in (401, 403)
    token = admin.get("/api/admin/lists").json()["upload_token"]
    r = admin.post("/api/lists/sync", json={"lists": []}, headers={"X-Upload-Token": token}).json()
    assert r["want"] == ["demo-groceries", "demo-todo"]
    assert r["changes"][0]["op"] == "add" and r["changes"][0]["title"] == "Yogurt" and r["changes"][0]["done"] is True
    # Turning adding off hides it from the frame and refuses it.
    admin.put("/api/admin/lists", json={"anyone_add": False})
    assert admin.post("/api/lists/demo-groceries/add", json={"title": "Eggs"}).status_code == 403


def test_faces_and_focus_api(admin, tmp_path):
    import app.main
    s = app.main.app.state.services
    folder = s.settings.photos_folder / "apple-favorites"
    folder.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO(); Image.new("RGB", (1500, 1000), (0, 160, 0)).save(buf, "JPEG")
    (folder / "20240101-120000-XYZ.jpg").write_bytes(buf.getvalue())
    token = admin.get("/api/admin/lists").json()["upload_token"]
    r = admin.post("/api/photos/faces", json={"faces": {"20240101-120000-XYZ.jpg": [0.7, 0.3], "missing.jpg": [0.1, 0.1]}},
                   headers={"X-Upload-Token": token}).json()
    assert r["changed"] == 1
    p = next(x for x in admin.get("/api/admin/photos").json()["photos"] if x["name"].endswith("XYZ.jpg"))
    assert p["focus"]["faces"] == [0.7, 0.3] and p["w"] == 1500 and p["v"]
    r = admin.put(f"/api/admin/photos/{p['id']}/focus", json={"point": [0.2, 0.6], "wide_fit": True}).json()
    assert r["focus"]["point"] == [0.2, 0.6] and r["focus"]["faces"] == [0.7, 0.3] and r["focus"]["wide_fit"] is True
    assert admin.get(f"/photos/{p['id']}.jpg?shape=tall&v={r['v']}").status_code == 200
    assert admin.get(f"/photos/{p['id']}.jpg?size=edit").status_code == 200
    # Back to the faces: clear the hand-set point.
    r = admin.put(f"/api/admin/photos/{p['id']}/focus", json={"point": None}).json()
    assert r["focus"]["point"] is None and r["focus"]["faces"] == [0.7, 0.3]


def test_frames_profiles(admin):
    # The demo starts with the kitchen (everything on, the default frame) and a playroom frame on the Kids screen.
    d = admin.get("/api/frame?frame=&w=1280&h=800").json()
    assert d["frame"]["id"] == "kitchen" and "lists" in d["frame"]["screens"]
    frames = admin.get("/api/admin/frames").json()
    assert [f["id"] for f in frames["frames"]] == ["kitchen", "playroom"] and frames["frames"][0]["seen"]["online"]
    assert "kids" in frames["homes"]
    body = [frames["frames"][0], {"id": "", "name": "Kids' playroom", "look": "kids", "home": "chores", "screens": ["chores", "screen", "photos"],
                                  "kids": ["child1", "child2"], "calendars": ["kids"], "approvals": False, "night": {"start": "20:00", "end": "07:00"}}]
    assert admin.put("/api/admin/frames", json=body).status_code == 200
    kids = admin.get("/api/frame?frame=kids-playroom").json()
    assert kids["frame"]["home"] == "chores" and kids["frame"]["approvals"] is False
    assert [k["id"] for k in kids["kids"]] == ["child1", "child2"]
    assert [s["key"] for s in kids["calendar"]["sources"]] == ["kids"]
    assert all(e["cal"] == "kids" for d in kids["calendar"]["week"]["days"] for e in d["events"])
    wk = admin.get("/api/calendar?view=week&offset=1&frame=kids-playroom").json()
    assert all(e["cal"] == "kids" for d in wk["days"] for e in d["events"])
    # Unknown frame: the first one. The picker list has both.
    assert admin.get("/api/frame?frame=nope").json()["frame"]["id"] == "kitchen"
    assert [f["name"] for f in admin.get("/api/frames").json()["frames"]] == ["Kitchen", "Kids' playroom"]   # the saved list replaces the demo's
    # "New frame here" on a frame (after the parent PIN).
    tok = admin.post("/api/parent/unlock", json={"pin": "1234"}).json()["token"]
    r = admin.post("/api/parent/frames", json={"name": "Bedroom", "look": "night"}, headers={"X-Parent-Token": tok}).json()
    assert r["id"] == "bedroom"
    b = admin.get("/api/frame?frame=bedroom").json()["frame"]
    assert b["home"] == "clock" and b["look"] == "night"
    r = admin.post("/api/parent/frames", json={"name": "Den", "look": "kids", "home": "kids"}, headers={"X-Parent-Token": tok}).json()
    den = admin.get(f"/api/frame?frame={r['id']}").json()["frame"]
    assert den["home"] == "kids" and den["screens"][0] == "kids" and den["bedtime"] == "20:00"


def test_chores_can_be_worth_any_minutes(admin):
    chores = admin.get("/api/admin/settings").json()["chores"]
    chores[0]["minutes"] = 25
    assert admin.put("/api/admin/chores", json=chores).status_code == 200
    assert admin.get("/api/admin/settings").json()["chores"][0]["minutes"] == 25
    chores[0]["minutes"] = 500
    r = admin.put("/api/admin/chores", json=chores)
    assert r.status_code == 400 and "1 to 240" in r.json()["detail"]


def test_birthday_portraits(admin):
    token = admin.get("/api/admin/settings").json()["photos"]["upload_token"]
    wanted = admin.get("/api/portraits/wanted", headers={"X-Upload-Token": token}).json()
    slugs = {p["slug"] for p in wanted}
    assert wanted and all(p["have"] is None for p in wanted)
    assert admin.get("/api/portraits/wanted").status_code == 401           # the Mac's key is required
    who = sorted(slugs)[0]
    r = admin.post(f"/api/portraits/upload?slug={who}&taken=2026-06-01T10:00:00&ref=U1&fx=0.5&fy=0.4&fs=0.2",
                   files={"file": ("p.jpg", jpeg(size=(1600, 1200)), "image/jpeg")}, headers={"X-Upload-Token": token})
    assert r.status_code == 200 and r.json()["source"] == "apple"
    view = admin.get("/api/admin/portraits").json()
    me = next(p for p in view["people"] if p["slug"] == who)
    assert me["source"] == "apple" and me["portrait"].startswith(f"portraits/{who}.jpg")
    assert admin.get(f"/portraits/{who}.jpg").status_code == 200
    # a hand-picked portrait stays when the Mac sends another
    assert admin.post(f"/api/admin/portraits/{who}", files={"file": ("p.jpg", jpeg(), "image/jpeg")}).json()["source"] == "upload"
    r = admin.post(f"/api/portraits/upload?slug={who}&ref=U2", files={"file": ("p.jpg", jpeg(), "image/jpeg")},
                   headers={"X-Upload-Token": token}).json()
    assert r == {"ok": True, "kept": "upload"}
    assert admin.put("/api/admin/portraits/names", json={who: "Someone Example"}).status_code == 200
    assert next(p for p in admin.get("/api/portraits/wanted", headers={"X-Upload-Token": token}).json() if p["slug"] == who)["photos_name"] == "Someone Example"
    assert admin.delete(f"/api/admin/portraits/{who}").json()["ok"] is True
    # Google: the secret is never sent back; connecting needs both halves
    assert admin.put("/api/admin/google", json={"client_id": "nope"}).status_code == 400
    assert admin.put("/api/admin/google", json={"client_id": "123.apps.googleusercontent.com", "client_secret": "shh"}).status_code == 200
    g = admin.get("/api/admin/portraits").json()["google"]
    assert g["has_secret"] and "shh" not in str(g) and not g["connected"]
    url = admin.get("/api/admin/google/connect").json()["url"]
    assert url.startswith("https://accounts.google.com/") and "photospicker.mediaitems.readonly" in url
    assert admin.get("/api/google/callback?code=x&state=forged").status_code == 200   # refused politely, nothing saved
    assert not admin.get("/api/admin/portraits").json()["google"]["connected"]


def test_family_page(admin):
    fam = admin.get("/api/admin/family").json()
    members = fam["members"]
    kids_before = [m for m in members if m["kid"]]
    assert kids_before and any(not m["kid"] for m in members)            # parents and kids in one list
    body = {"members": [{**m, "aliases": m["aliases"]} for m in members]}
    first_kid = next(m for m in body["members"] if m["kid"])
    first_kid["birthday"] = "2016-10-16"
    first_kid["photos_name"] = "Someone Example Jr."
    body["members"].append({"key": "", "name": "Grandma", "aliases": ["Nana"], "birthday": "1950-03-02", "photos_name": "", "kid": None})
    assert admin.put("/api/admin/family", json=body).status_code == 200
    got = admin.get("/api/admin/family").json()["members"]
    me = next(m for m in got if m["key"] == first_kid["key"])
    assert me["birthday"] == "2016-10-16" and me["photos_name"] == "Someone Example Jr." and me["kid"]["id"] == first_kid["kid"]["id"]
    assert any(m["name"] == "Grandma" and m["aliases"] == ["Nana"] and not m["kid"] for m in got)
    # the birthday comes up by itself on the frame (demo clock: Oct 15, 2026)
    week = admin.get("/api/calendar?view=week").json()
    days = {d["date"]: d for d in week.get("days", [])}
    if "2026-10-16" in days:
        sp = days["2026-10-16"]["special"]
        assert sp and sp["theme"] == "birthday" and sp["name"] == first_kid["name"] and "10th" in sp["script"]
    # renaming carries the photo along; duplicate names are refused
    dup = {"members": got + [dict(got[0], key="")]}
    assert admin.put("/api/admin/family", json=dup).status_code == 400
    assert admin.put("/api/admin/family", json={"members": [dict(got[0], birthday="Oct 16")]}).status_code == 400


def test_weather_source_and_units(admin):
    d = admin.get("/api/admin/settings").json()["display"]
    assert (d["weather_source"], d["weather_temp"], d["weather_wind"]) == ("auto", "auto", "auto")
    assert admin.get("/api/frame").json()["weather"]["units"]["temp"] == "F"
    d.update(weather_source="open-meteo", weather_temp="C", weather_wind="kmh")
    assert admin.put("/api/admin/display", json=d).status_code == 200
    d = admin.get("/api/admin/settings").json()["display"]
    assert (d["weather_source"], d["weather_temp"], d["weather_wind"]) == ("open-meteo", "C", "kmh")
    w = admin.get("/api/frame").json()["weather"]
    assert w["temp"] == 17 and w["units"]["wind_label"] == "km/h"   # demo's sample weather, in Celsius
    d["weather_temp"] = "kelvin"
    assert admin.put("/api/admin/display", json=d).status_code == 400
