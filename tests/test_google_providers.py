"""Google as a source: the shared sign-in, Google Tasks lists and Google Photos picks for the slideshow.
Google itself is never called: every test talks to a fake Google through httpx.MockTransport."""
import io
import json
import time
import urllib.parse
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
import pytest
from PIL import Image

from app.db import Database
from app.google_auth import SCOPES, GoogleAccount, GoogleError
from app.google_photos import GooglePhotos
from app.google_tasks import GoogleTasks, sync
from app.lists import FRAME_NOTE, Lists
from app.photo_picks import PickImport

TZ = ZoneInfo("America/New_York")
NOW = datetime(2026, 10, 15, 16, 12, tzinfo=TZ)
BOTH = " ".join(SCOPES.values())


def account(tmp_path, handler, scope=BOTH, signed_in=True):
    acct = GoogleAccount(tmp_path / "google.json", "123.apps.googleusercontent.com", "shh", "https://frame.example.com", "k" * 32,
                         http=httpx.Client(transport=httpx.MockTransport(handler)))
    if signed_in:
        acct._save({"refresh_token": "r1", "access_token": "a1", "expires_at": time.time() + 3000, "scope": scope})
    return acct


# ---------------- the shared sign-in ----------------

def test_one_sign_in_asks_for_several_scopes_and_adds_more_later(tmp_path):
    calls = []

    def handler(req):
        calls.append(req)
        body = urllib.parse.parse_qs(req.content.decode())
        if body["code"] == ["first"]:
            return httpx.Response(200, json={"access_token": "a", "refresh_token": "r1", "expires_in": 3600, "scope": SCOPES["photos"]})
        # Second time (incremental): Google may leave out the refresh token; the scope list covers both now.
        return httpx.Response(200, json={"access_token": "b", "expires_in": 3600, "scope": BOTH})
    acct = account(tmp_path, handler, signed_in=False)
    url = acct.auth_url(["tasks"])
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    assert q["include_granted_scopes"] == ["true"] and q["scope"] == [SCOPES["tasks"]] and q["access_type"] == ["offline"]
    assert set(urllib.parse.parse_qs(urllib.parse.urlparse(acct.auth_url()).query)["scope"][0].split()) == set(SCOPES.values())
    assert acct.finish("first") == {"photos"}
    assert acct.finish("second") == {"photos", "tasks"}
    assert json.loads((tmp_path / "google.json").read_text())["refresh_token"] == "r1"   # kept
    assert oct((tmp_path / "google.json").stat().st_mode)[-3:] == "600"


def test_older_photos_only_sign_in_is_picked_up(tmp_path):
    (tmp_path / "google-photos.json").write_text(json.dumps({"refresh_token": "old", "scope": SCOPES["photos"]}))
    acct = GoogleAccount(tmp_path / "google.json", "x", "y", "https://f", "k")
    assert acct.connected and acct.granted() == {"photos"} and not acct.has("tasks")


# ---------------- Google Tasks ----------------

class FakeTasks:
    """Just enough of the Google Tasks API."""

    def __init__(self):
        self.lists = [{"id": "L1", "title": "Groceries"}, {"id": "L2", "title": "Chores"}]
        self.tasks = {"L1": [{"id": "t1", "title": "Milk", "status": "needsAction", "position": "002", "updated": "2026-10-15T18:00:00.000Z"},
                             {"id": "t2", "title": "Bananas", "status": "needsAction", "position": "001", "updated": "2026-10-15T18:00:00.000Z"},
                             {"id": "t3", "title": "Coffee filters", "status": "completed", "completed": "2026-10-15T19:40:00.000Z",
                              "hidden": True, "updated": "2026-10-15T19:40:00.000Z"},
                             {"id": "t4", "title": "Old thing", "status": "completed", "completed": "2026-10-01T10:00:00.000Z"}],
                      "L2": [{"id": "c1", "title": "Rake leaves", "status": "needsAction"}]}
        self.log = []
        self.fail_insert = None

    def __call__(self, req: httpx.Request):
        assert req.headers["Authorization"] == "Bearer a1"
        path = req.url.path.replace("/tasks/v1", "")
        self.log.append((req.method, path, dict(req.url.params)))
        if path == "/users/@me/lists":
            return httpx.Response(200, json={"items": self.lists})
        parts = path.strip("/").split("/")    # lists/<id>/tasks[/<task>]
        tl = parts[1]
        if req.method == "GET":
            assert req.url.params["showHidden"] == "true" and req.url.params["showCompleted"] == "true"
            return httpx.Response(200, json={"items": self.tasks.get(tl, [])})
        body = json.loads(req.content)
        if req.method == "POST":
            if self.fail_insert:
                return httpx.Response(self.fail_insert, json={"error": {"message": "busy"}})
            t = {"id": f"n{len(self.tasks[tl])}", "updated": "2026-10-15T20:13:00.000Z", **body}
            if body["status"] == "completed":
                t["completed"] = "2026-10-15T20:13:00.000Z"
            self.tasks[tl].append(t)
            return httpx.Response(200, json=t)
        if req.method == "PATCH":
            t = next(t for t in self.tasks[tl] if t["id"] == parts[3])
            t.update(body, updated="2026-10-15T20:14:00.000Z")
            if body["status"] == "completed":
                t["completed"] = "2026-10-15T20:14:00.000Z"
            return httpx.Response(200, json=t)
        return httpx.Response(405)


def test_google_tasks_lists_sit_beside_reminders(tmp_path):
    L = Lists(Database(tmp_path / "t.db"))
    L.sync({"lists": [{"id": "R1", "name": "Family To-Do", "count": 1}], "items": {"R1": [{"ext": "x", "title": "Call the plumber"}]}}, NOW)
    fake = FakeTasks()
    api = GoogleTasks(account(tmp_path, fake))
    sync(L, api, NOW)
    by_id = {a["id"]: a for a in L.available()}
    assert by_id["R1"]["source"] == "apple" and by_id["gtasks:L1"]["source"] == "google" and by_id["gtasks:L2"]["name"] == "Chores"
    # Not shown yet, so only the list names were read: the Groceries list shows by default, then its tasks are read.
    assert L.shown() == ["gtasks:L1"]
    sync(L, api, NOW)
    v = L.frame_view(NOW)
    g = v["lists"][0]
    assert g["source"] == "google" and g["from"] == "Google Tasks" and v["stale"] is False
    assert [i["title"] for i in g["items"]] == ["Bananas", "Milk"]          # Produce before Dairy
    assert [d["title"] for d in g["done"]] == ["Coffee filters"]              # checked off today; the old one is left out
    assert g["items"][0]["id"] == "g:t2"
    # The Mac's next check-in doesn't touch the Google lists, and Google's doesn't touch Reminders.
    r = L.sync({"lists": [{"id": "R1", "name": "Family To-Do", "count": 1}], "items": {}}, NOW)
    assert r["want"] == [] and any(a["id"] == "gtasks:L1" for a in L.available())
    sync(L, api, NOW)
    assert any(a["id"] == "R1" for a in L.available())


def test_frame_changes_go_to_google(tmp_path):
    L = Lists(Database(tmp_path / "t.db"), {"shown": ["gtasks:L1"]})
    fake = FakeTasks()
    api = GoogleTasks(account(tmp_path, fake))
    sync(L, api, NOW)
    new = L.add("gtasks:L1", "Yogurt", NOW)
    L.toggle("g:t1", NOW)
    assert L.changes("google") and L.changes("apple") == []
    sync(L, api, NOW)
    posted = next(t for t in fake.tasks["L1"] if t["title"] == "Yogurt")
    assert posted["notes"] == FRAME_NOTE and posted["status"] == "needsAction"
    assert next(t for t in fake.tasks["L1"] if t["id"] == "t1")["status"] == "completed"
    g = L.frame_view(NOW)["lists"][0]
    assert "g:" + posted["id"] in [i["id"] for i in g["items"]] and not any(i["waiting"] for i in g["items"])
    assert new["id"] not in [i["id"] for i in g["items"]]
    assert "Milk" in [d["title"] for d in g["done"]]
    # Putting it back on the list.
    L.toggle("g:t1", NOW)
    sync(L, api, NOW)
    t1 = next(t for t in fake.tasks["L1"] if t["id"] == "t1")
    assert t1["status"] == "needsAction" and t1["completed"] is None


def test_google_busy_means_try_again_not_lose_it(tmp_path):
    L = Lists(Database(tmp_path / "t.db"), {"shown": ["gtasks:L1"]})
    fake = FakeTasks()
    api = GoogleTasks(account(tmp_path, fake))
    sync(L, api, NOW)
    L.add("gtasks:L1", "Eggs", NOW)
    fake.fail_insert = 503
    sync(L, api, NOW)
    assert [c["title"] for c in L.changes("google")] == ["Eggs"]     # still waiting
    fake.fail_insert = None
    sync(L, api, NOW)
    assert L.changes("google") == [] and sum(t["title"] == "Eggs" for t in fake.tasks["L1"]) == 1
    # A lost sign-in is an error Settings can show.
    fake.fail_insert = 401
    L.add("gtasks:L1", "Jam", NOW)
    with pytest.raises(GoogleError):
        sync(L, api, NOW)


def test_google_tasks_can_be_turned_off(tmp_path):
    L = Lists(Database(tmp_path / "t.db"), {"shown": ["gtasks:L1", "R1"], "google": False})
    assert L.shown() == ["R1"] and not L.google_on


# ---------------- Google Photos picks for the slideshow ----------------

def jpeg(color=(200, 120, 40)):
    b = io.BytesIO()
    Image.new("RGB", (64, 48), color).save(b, "JPEG")
    return b.getvalue()


def test_picked_photos_are_copied_once(tmp_path):
    seen = []
    items = [{"id": "m1", "type": "PHOTO", "mediaFile": {"baseUrl": "https://lh3.example/m1", "filename": "IMG_0001.HEIC"}},
             {"id": "m2", "type": "PHOTO", "mediaFile": {"baseUrl": "https://lh3.example/m2", "filename": "beach day.jpg"}},
             {"id": "v1", "type": "VIDEO", "mediaFile": {"baseUrl": "https://lh3.example/v1", "filename": "clip.mp4"}}]

    def handler(req):
        seen.append(str(req.url))
        if req.url.host == "photospicker.googleapis.com":
            if req.url.path.endswith("/mediaItems"):
                return httpx.Response(200, json={"mediaItems": items})
            if req.method == "DELETE":
                return httpx.Response(200, json={})
            return httpx.Response(200, json={"id": "S1", "mediaItemsSet": True})
        return httpx.Response(200, content=jpeg())
    gp = GooglePhotos(account(tmp_path, handler))
    imp = PickImport(tmp_path / "photos")
    job = imp.run(gp, "S1")
    assert job == {"total": 2, "added": 2, "skipped": 0, "failed": 0, "state": "done"}     # the video is left out
    assert "https://lh3.example/m1=w2048-h2048" in seen
    files = sorted(p.name for p in (tmp_path / "photos" / "google-picks").glob("*.jpg"))
    assert len(files) == 2 and any(f.endswith("-IMG_0001.jpg") for f in files) and any(f.endswith("-beach-day.jpg") for f in files)
    assert imp.run(gp, "S1")["skipped"] == 2                       # picked again: not copied twice
    (tmp_path / "photos" / "google-picks" / files[0]).unlink()     # removed from the frame, then picked again: back
    assert imp.run(gp, "S1")["added"] == 1


# ---------------- Settings (demo mode, no accounts) ----------------

@pytest.fixture
def admin(demo_env, monkeypatch):
    import importlib
    import sys
    from fastapi.testclient import TestClient
    monkeypatch.setenv("FRAME_NOW", "2026-10-15T16:12:00")
    sys.modules.pop("app.admin", None)
    sys.modules.pop("app.admin_providers", None)
    import app.main
    importlib.reload(app.main)
    with TestClient(app.main.app) as c:
        assert c.post("/api/parent/unlock?remember=1", json={"pin": "1234"}).status_code == 200
        yield c


def test_settings_show_both_sources_in_demo(admin):
    v = admin.get("/api/admin/lists").json()
    assert {a["source"] for a in v["available"]} == {"apple", "google"}
    assert v["sources"]["google"]["ready"] and v["sources"]["google"]["lists"] == 3 and v["google"]["demo"]
    gid = next(a["id"] for a in v["available"] if a["source"] == "google")
    assert admin.put("/api/admin/lists", json={"shown": v["shown"] + [gid]}).status_code == 200
    frame = admin.get("/api/admin/lists").json()
    assert gid in frame["shown"]
    r = admin.post("/api/admin/lists/google/sync").json()
    assert r["ok"] and "3 Google Tasks lists" in r["message"]
    # Picking photos needs a real Google sign-in; demo mode says so plainly.
    r = admin.post("/api/admin/photos/google")
    assert r.status_code == 400 and "Demo mode" in r.json()["detail"]
    # The client ID is saved in one place for every Google feature; the secret never comes back.
    assert admin.put("/api/admin/google", json={"client_id": "123.apps.googleusercontent.com", "client_secret": "shh"}).status_code == 200
    g = admin.get("/api/admin/google").json()
    assert g["client_id"] == "123.apps.googleusercontent.com" and g["has_secret"] and "shh" not in json.dumps(g)
    url = admin.get("/api/admin/google/connect?features=tasks").json()["url"]
    assert "include_granted_scopes=true" in url and urllib.parse.quote(SCOPES["tasks"], safe="") in url
