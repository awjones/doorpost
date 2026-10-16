"""Storage: disk warnings, the folder breakdown, clearing prepared photos, and frame heartbeats."""
import json

import pytest
from fastapi.testclient import TestClient

from app import storage

GB, MB = storage.GB, storage.MB


def test_warning_levels():
    assert storage.level(100 * GB, 50 * GB) == "ok"
    assert storage.level(100 * GB, 14 * GB) == "amber"       # under 15%
    assert storage.level(1000 * GB, int(1.5 * GB)) == "red"         # 0.15% free
    assert storage.level(20 * GB, int(1.9 * GB)) == "amber"  # under 2 GB, though 9.5% free
    assert storage.level(100 * GB, 4 * GB) == "red"          # under 5%
    assert storage.level(4 * GB, 400 * MB) == "red"          # under 500 MB
    assert storage.level(0, 0) == "ok"


def write(path, n):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * n)


@pytest.fixture
def tree(tmp_path):
    data, photos = tmp_path / "data", tmp_path / "photos"
    write(photos / "uploads" / "a.jpg", 5000)
    write(photos / "apple-favorites" / "b.jpg", 7000)
    write(data / "photo-cache" / "p1.jpg", 300)
    write(data / "photo-cache" / "p1-h.jpg", 200)
    write(data / "photo-cache" / "index.json", 50)
    write(data / "special-photos" / "trip.jpg", 400)
    write(data / "kid-photos" / "child1.jpg", 30)
    write(data / "portraits" / "mom.jpg", 70)
    write(data / "packs" / "seasons" / "x.svg", 900)
    write(data / "frame.db", 1000)
    write(data / "settings.json", 100)
    write(data / "calendar-cache" / "fam.ics", 60)
    write(data / "server.log", 40)
    write(data / "odd.bin", 11)
    return data, photos


def test_breakdown_counts_each_part(tree):
    data, photos = tree
    m = storage.measure(data, photos, data / "photo-cache")
    got = {i["key"]: (i["bytes"], i["files"]) for i in m["items"]}
    assert got["photos"] == (12000, 2)
    assert got["photo_cache"] == (500, 2)       # index.json is not a prepared photo
    assert got["special"] == (400, 1)
    assert got["profile"] == (100, 2)
    assert got["packs"] == (900, 1)
    assert got["database"] == (1100, 2)
    assert got["caches"] == (100, 2)
    assert got["other"] == (61, 2)              # index.json + odd.bin
    assert m["total"] == sum(b for b, _ in got.values())
    assert [i["key"] for i in m["items"] if i["clearable"]] == ["photo_cache"]


def test_photos_inside_the_data_folder_are_not_counted_twice(tmp_path):
    data = tmp_path / "data"
    write(data / "photos" / "a.jpg", 5000)
    write(data / "frame.db", 10)
    m = storage.measure(data, data / "photos", data / "photo-cache")
    got = {i["key"]: i["bytes"] for i in m["items"]}
    assert got["photos"] == 5000 and got["other"] == 0 and m["total"] == 5010


def test_server_report_and_cache(tree, monkeypatch):
    data, photos = tree
    storage.SIZES.value = None
    rep = storage.server_report(data, photos, data / "photo-cache")
    assert rep["disk"]["total"] > 0 and rep["disk"]["level"] in ("ok", "amber", "red")
    assert rep["breakdown"]["total"] > 0 and not rep["counting"]
    # Reused for a few minutes: a new file doesn't show until the count is stale.
    write(photos / "c.jpg", 999)
    again = storage.server_report(data, photos, data / "photo-cache")
    assert again["breakdown"]["at"] == rep["breakdown"]["at"]
    storage.SIZES.invalidate()
    fresh = storage.server_report(data, photos, data / "photo-cache")
    assert [i["bytes"] for i in fresh["breakdown"]["items"] if i["key"] == "photos"] == [12999]


def test_clear_photo_cache_only_removes_prepared_copies(tree):
    data, photos = tree
    r = storage.clear_photo_cache(data / "photo-cache")
    assert r == {"freed": 500, "files": 2}
    assert (data / "photo-cache" / "index.json").exists()
    assert (photos / "uploads" / "a.jpg").exists() and (data / "special-photos" / "trip.jpg").exists()
    assert storage.clear_photo_cache(data / "nowhere") == {"freed": 0, "files": 0}


def test_heartbeat_is_cleaned():
    hb = storage.clean_heartbeat({
        "screen": {"w": 1280, "h": "800", "dpr": 1.5, "orientation": "landscape-primary"},
        "ua": storage.DEMO_UA, "storage": {"usage": 1000, "quota": -5}, "device_memory": 2,
        "heap": {"used": "lots"}, "photo_ms": 1e12, "evil": "<script>", "device_storage": {"total": 8 * GB, "free": 100 * MB},
    }, 1000.0)
    assert hb["screen"] == {"w": 1280, "h": 800, "dpr": 1.5, "orientation": "landscape-primary"}
    assert hb["browser"] == "Chrome 106 WebView on Android 6.0.1"
    assert hb["storage"] == {"usage": 1000, "quota": None}
    assert hb["heap"] == {"used": None, "limit": None}
    assert hb["photo_ms"] is None and "evil" not in hb
    assert hb["device_storage"]["level"] == "red"
    assert storage.clean_heartbeat({}, 1.0)["device_storage"] is None


def test_browser_names():
    assert storage.browser_name("") == ""
    assert storage.browser_name("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0 Safari/537.36") == "Chrome 120 on Mac"


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


def test_storage_needs_sign_in(client):
    assert client.get("/api/admin/storage").status_code == 401
    assert client.post("/api/admin/storage/clear-photo-cache").status_code == 401


def test_demo_storage_and_heartbeat(client, demo_env):
    assert client.post("/api/parent/unlock?remember=1", json={"pin": "1234"}).status_code == 200
    rep = client.get("/api/admin/storage").json()
    assert rep["demo"] and rep["disk"]["level"] == "amber" and rep["breakdown"]["items"]
    first = next(iter(rep["frames"]))
    assert rep["frames"][first]["browser"].startswith("Chrome 106")   # the sample frame
    assert client.post("/api/admin/storage/clear-photo-cache").json()["demo"] is True

    body = {"frame": first, "ua": "Mozilla/5.0 (Linux; Android 6.0) Chrome/106.0 Safari/537.36",
            "screen": {"w": 800, "h": 1280, "dpr": 1, "orientation": "portrait-primary"}, "photo_ms": 900}
    assert client.post(f"/api/frame/heartbeat?frame={first}", content=json.dumps(body)).json() == {"ok": True}
    got = client.get("/api/admin/storage").json()["frames"][first]
    assert got["screen"]["h"] == 1280 and got["photo_ms"] == 900 and got["ago"] <= 2
    saved = json.loads((demo_env / "data" / "frame-heartbeats.demo.json").read_text())
    assert saved[first]["screen"]["w"] == 800

    assert client.post("/api/frame/heartbeat", content=b"not json").status_code == 400
    assert client.post("/api/frame/heartbeat", content=b"[1]").status_code == 400
    assert client.post("/api/frame/heartbeat", content=b"x" * 9000).status_code == 413
