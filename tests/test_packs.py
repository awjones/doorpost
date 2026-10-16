"""Art packs: building, cleaning, installing, turning on and off, and what the frame shows with and without them."""
import hashlib
import io
import json
import zipfile
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import pack_build as pb
from app import packs as P

ROOT = Path(__file__).resolve().parent.parent


# ---------------- cleaning drawings ----------------

def test_clean_drawing_comes_back_unchanged():
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 600"><defs><clipPath id="w"><circle r="4"></circle></clipPath></defs>'
           '<g clip-path="url(#w)"><text>{{NAME}}</text></g><use href="#w"></use></svg>')
    assert P.sanitize_svg(svg) == svg


def test_dangerous_bits_are_removed():
    bad = ('<svg viewBox="0 0 10 10" onload="alert(1)"><script>alert(2)</script>'
           '<foreignObject><div xmlns="http://www.w3.org/1999/xhtml">hi</div></foreignObject>'
           '<a href="https://example.invalid"><rect width="1" height="1"></rect></a>'
           '<use href="https://example.invalid/x.svg#a"></use><image href="data:image/png;base64,AAAA"></image>'
           '<rect fill="url(https://example.invalid/p)" style="background:url(javascript:alert(3))" ONCLICK="x()" width="2"></rect>'
           '<animate attributeName="href" to="javascript:alert(4)"></animate><style>@import url(https://example.invalid/a.css);</style>'
           '<circle r="3" fill="url(#ok)"></circle><!-- note --></svg>')
    out = P.sanitize_svg(bad)
    low = out.lower()
    for word in ("script", "onload", "onclick", "foreignobject", "example.invalid", "javascript", "data:", "<a ", "<animate", "<style", "<image"):
        assert word not in low, word
    assert 'fill="url(#ok)"' in out and 'width="2"' in out


def test_doctype_and_broken_svg_are_refused():
    with pytest.raises(P.PackError):
        P.sanitize_svg('<!DOCTYPE svg [<!ENTITY x "y">]><svg>&x;</svg>')
    with pytest.raises(P.PackError):
        P.sanitize_svg("<svg><g></svg>")
    with pytest.raises(P.PackError):
        P.sanitize_svg("<html><body></body></html>")


# ---------------- the packs in the repo are current ----------------

def test_built_in_packs_match_the_drawing_code(tmp_path):
    for pid in pb.BUILT_IN:
        fresh = pb.build(pid, tmp_path)
        repo = ROOT / "packs" / pid
        names = sorted(p.relative_to(fresh).as_posix() for p in fresh.rglob("*") if p.is_file())
        assert names == sorted(p.relative_to(repo).as_posix() for p in repo.rglob("*") if p.is_file()), pid
        for n in names:
            assert (fresh / n).read_bytes() == (repo / n).read_bytes(), f"{pid}/{n}: run python3 scripts/build-pack.py --all"


def test_index_lists_the_downloadable_packs_with_matching_checksums(tmp_path):
    index = {e["id"]: e for e in P.read_index()}
    assert set(index) == set(pb.OPTIONAL)
    for pid in pb.OPTIONAL:
        z, sha = pb.build_zip(pid, tmp_path, tmp_path)
        assert index[pid]["sha256"] == sha and index[pid]["url"] == f"dist/packs/{z.name}", pid
        assert (ROOT / "packs" / index[pid]["preview"]).is_file()


def test_faith_pack_holds_every_series_picture(tmp_path):
    folder = pb.build("faith", tmp_path)
    series = json.loads((folder / "series.json").read_text())
    assert [len(s["items"]) for s in series["series"]] == [52, 10, 7, 32, 66]
    assert all((folder / it["file"]).is_file() and it["about"] and it["verse"] for s in series["series"] for it in s["items"])
    m = json.loads((folder / "pack.json").read_text())
    assert {r["church"] for r in m["rules"] if "church" in r} == {"palm", "goodfriday", "easter", "ascension", "pentecost",
                                                                   "reformation", "xmaseve", "christmas"}
    assert {"churchglass", "vbs", "baptism"} <= set(m["scenes"])
    assert any(r.get("holiday") == "thanksgiving day" and r.get("verse") for r in m["rules"])


# ---------------- safe unzip ----------------

def _zip(files: dict, prefix="mine/") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, body in files.items():
            z.writestr(prefix + name if not name.startswith("!") else name[1:], body)
    return buf.getvalue()


MINE = {"id": "mine", "name": "Mine", "version": "1.0", "priority": 60,
        "scenes": {"kite": {"title": "Kite day", "script": "Up it goes!", "file": "scenes/kite.svg"}},
        "groups": [{"name": "Outdoors", "scenes": ["kite"]}],
        "rules": [{"keyword": "Kite", "scene": "kite"}]}
KITE = '<svg viewBox="0 0 300 600" onload="alert(1)"><script>alert(1)</script><rect width="10" height="10" fill="#C9A55A"></rect></svg>'


def test_install_cleans_and_unpacks(tmp_path):
    m = P.install_zip(_zip({"pack.json": json.dumps(MINE), "scenes/kite.svg": KITE}), demo=False, dest_root=tmp_path)
    assert m["id"] == "mine"
    svg = (tmp_path / "mine" / "scenes" / "kite.svg").read_text()
    assert "script" not in svg and "onload" not in svg and "#C9A55A" in svg
    # files at the top of the zip work too
    P.install_zip(_zip({"pack.json": json.dumps(MINE), "scenes/kite.svg": KITE}, prefix=""), demo=False, dest_root=tmp_path)


@pytest.mark.parametrize("files, message", [
    ({"pack.json": json.dumps(MINE), "scenes/kite.svg": KITE, "!../evil.svg": KITE}, "unsafe name"),
    ({"pack.json": json.dumps(MINE), "scenes/kite.svg": KITE, "!/etc/evil.svg": KITE}, "unsafe name"),
    ({"pack.json": json.dumps(MINE), "scenes/kite.svg": KITE, "run.js": "alert(1)"}, "only .svg"),
    ({"pack.json": json.dumps(MINE), "scenes/kite.svg": KITE, "page.html": "<p>"}, "only .svg"),
    ({"pack.json": json.dumps(MINE)}, "isn't in the pack"),
    ({"pack.json": json.dumps({**MINE, "id": "../x"}), "scenes/kite.svg": KITE}, "needs an \"id\""),
    ({"pack.json": json.dumps({**MINE, "id": "seasons"}), "scenes/kite.svg": KITE}, "built-in"),
    ({"scenes/kite.svg": KITE}, "no pack.json"),
    ({"pack.json": json.dumps(MINE), "scenes/kite.svg": KITE, "photo.png": b"not a png"}, "picture"),
])
def test_bad_zips_are_refused(tmp_path, files, message):
    with pytest.raises(P.PackError, match=message):
        P.install_zip(_zip(files), demo=False, dest_root=tmp_path)
    assert not (tmp_path / "mine").exists() and not [p for p in tmp_path.iterdir() if p.name.startswith(".tmp")]


def test_links_size_and_checksum_are_refused(tmp_path, monkeypatch):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("mine/pack.json", json.dumps(MINE))
        info = zipfile.ZipInfo("mine/scenes/kite.svg")
        info.external_attr = 0o120777 << 16   # a symlink
        z.writestr(info, "/etc/passwd")
    with pytest.raises(P.PackError, match="link"):
        P.install_zip(buf.getvalue(), demo=False, dest_root=tmp_path)
    data = _zip({"pack.json": json.dumps(MINE), "scenes/kite.svg": KITE})
    with pytest.raises(P.PackError, match="sha256"):
        P.install_zip(data, demo=False, expect_sha="0" * 64, dest_root=tmp_path)
    P.install_zip(data, demo=False, expect_sha=hashlib.sha256(data).hexdigest(), dest_root=tmp_path)
    monkeypatch.setattr(P, "MAX_ZIP", 200)
    with pytest.raises(P.PackError, match="20 MB"):
        P.install_zip(data, demo=False, dest_root=tmp_path)
    with pytest.raises(P.PackError):
        P.install_zip(b"not a zip", demo=False, dest_root=tmp_path)


# ---------------- the frame with and without packs ----------------

def _start(monkeypatch, store=None):
    monkeypatch.delenv("FRAME_EXTRA_PACKS", raising=False)
    monkeypatch.setenv("FRAME_NOW", "2026-10-15T16:12:00")
    if store is not None:
        from app.config import write_store
        write_store(store, demo=True)
    import importlib
    import sys
    sys.modules.pop("app.admin", None)
    import app.main
    importlib.reload(app.main)
    return TestClient(app.main.app)


@pytest.fixture
def bare(demo_env, monkeypatch):
    """Demo mode with only the built-in packs: the family removed the Faith pack (it comes on by default)."""
    with _start(monkeypatch, {"art_packs": {"seeded": ["faith"]}}) as c:
        yield c


@pytest.fixture
def fresh(demo_env, monkeypatch):
    """A first start: nothing installed yet, so the Faith pack gets installed and turned on."""
    with _start(monkeypatch) as c:
        yield c


def _sunday(client):
    return next(x for x in client.get("/api/calendar?view=rolling&offset=0").json()["days"] if x["date"] == "2026-10-18")["special"]


def _signin(client):
    assert client.post("/api/parent/unlock?remember=1", json={"pin": "1234"}).status_code == 200


def test_without_faith_nothing_of_it_shows(bare):
    assert _sunday(bare) is None
    d = bare.get("/api/frame").json()
    assert d["clock_verses"] == []
    art = bare.get("/art.js").text
    assert art.startswith("/*") and '"birthday"' in art and '"palm"' not in art and '"vbs"' not in art
    import app.main
    s = app.main.app.state.services.special
    assert s.for_day(date(2027, 3, 28), [], date(2026, 10, 15))[0] is None                  # Easter: not special
    assert "Easter Sunday" in s.for_day(date(2027, 3, 28), [], date(2026, 10, 15))[1]        # just Google's line
    thanks = s.for_day(date(2026, 11, 26), [], date(2026, 10, 15))[0]
    assert thanks["title"] == "Thanksgiving Day" and thanks["verse"] == ""
    assert not any(w["look"] in ("vbs", "baptism") for w in s.words)
    _signin(bare)
    v = bare.get("/api/admin/special").json()
    assert v["church"] == [] and not v["has_sundays"] and v["has_seasons"]
    assert not any(g["name"] in ("Church year", "Church life") for g in v["groups"])
    packs = bare.get("/api/admin/packs").json()
    assert [p["id"] for p in packs["packs"]] == ["family-basics", "holidays-us", "seasons"]
    assert {e["id"] for e in packs["index"] if not e["installed"]} == {"faith", "outings", "kids-activities"}


def test_install_turn_off_and_remove_faith(bare, monkeypatch, tmp_path):
    _signin(bare)
    monkeypatch.setattr(P, "DIST_DIR", tmp_path / "dist")   # no zip on disk: it is built from the drawing code
    monkeypatch.setattr(P, "ROOT", tmp_path)
    (tmp_path / "dist").mkdir()
    r = bare.post("/api/admin/packs/install/faith")
    assert r.status_code == 200, r.text
    sp = _sunday(bare)
    assert sp["kind"] == "sunday" and sp["title"] == "3 John" and sp["lines"] == ["Through the Bible · 64 of 66"]
    assert '"palm"' in bare.get("/art.js").text and bare.get("/api/frame").json()["clock_verses"]
    v = bare.get("/api/admin/special").json()
    assert v["has_sundays"] and len(v["church"]) >= 8
    faith = next(p for p in bare.get("/api/admin/packs").json()["packs"] if p["id"] == "faith")
    assert faith["removable"] and faith["on"] and faith["pictures"] == 14 + 167 and faith["size"] > 100_000
    assert bare.get("/art/preview/faith.svg").headers["content-type"].startswith("image/svg+xml")
    # off: gone everywhere, still installed
    assert bare.put("/api/admin/packs/faith", json={"on": False}).status_code == 200
    assert _sunday(bare) is None and '"palm"' not in bare.get("/art.js").text
    assert bare.put("/api/admin/packs/faith", json={"on": True}).status_code == 200
    assert _sunday(bare)["kind"] == "sunday"
    # built-in packs turn off but can't be removed
    assert bare.delete("/api/admin/packs/seasons").status_code == 400
    assert bare.delete("/api/admin/packs/faith").status_code == 200
    assert _sunday(bare) is None


def test_upload_a_pack_and_its_word(bare):
    _signin(bare)
    data = _zip({"pack.json": json.dumps(MINE), "scenes/kite.svg": KITE})
    r = bare.post("/api/admin/packs/upload", files={"file": ("mine.zip", data, "application/zip")})
    assert r.status_code == 200, r.text
    art = bare.get("/art.js").text
    assert '"kite"' in art and "alert" not in art
    import app.main
    s = app.main.app.state.services.special
    assert {"word": "Kite", "look": "kite"} in s.words and s.picture("kite") == ("kite", None)
    assert any(g["name"] == "Outdoors" for g in bare.get("/api/admin/special").json()["groups"])
    bad = bare.post("/api/admin/packs/upload", files={"file": ("x.zip", b"nope", "application/zip")})
    assert bad.status_code == 400 and "zip" in bad.json()["detail"]
    assert bare.post("/api/admin/packs/upload", files={"file": ("x.zip", data, "application/zip")}).status_code == 200  # update in place


def test_settings_need_sign_in(bare):
    assert bare.get("/api/admin/packs").status_code == 401
    assert bare.post("/api/admin/packs/install/faith").status_code == 401
    assert bare.get("/art.js").status_code == 200   # the frame itself needs no sign-in


def test_turning_a_built_in_pack_off(bare):
    _signin(bare)
    import app.main
    fall = date(2026, 9, 22)   # first day of fall, a Tuesday
    assert app.main.app.state.services.special.for_day(fall, [], date(2026, 9, 1))[0]["kind"] == "season"
    assert bare.put("/api/admin/packs/seasons", json={"on": False}).status_code == 200
    assert app.main.app.state.services.special.for_day(fall, [], date(2026, 9, 1))[0] is None
    assert '"fall"' not in bare.get("/art.js").text


def test_higher_priority_wins_a_clash(tmp_path, monkeypatch):
    mine = {**MINE, "scenes": {"birthday": {"title": "Our birthday", "script": "Hooray!", "file": "scenes/b.svg"}}, "rules": []}
    P.install_zip(_zip({"pack.json": json.dumps(mine), "scenes/b.svg": KITE}), demo=False, dest_root=tmp_path / "x")
    monkeypatch.setenv("FRAME_EXTRA_PACKS", str(tmp_path / "x"))
    ps = P.load(False)
    assert ps.scenes["birthday"]["pack"] == "mine" and ps.script("birthday") == "Hooray!"


# ---------------- the Faith pack comes on by default ----------------

def test_faith_comes_installed_and_on(fresh):
    _signin(fresh)
    packs = fresh.get("/api/admin/packs").json()
    faith = next(p for p in packs["packs"] if p["id"] == "faith")
    assert faith["on"] and faith["removable"] and faith["where"] == "installed"
    assert {e["id"] for e in packs["index"] if not e["installed"]} == {"outings", "kids-activities"}
    assert next(e for e in packs["index"] if e["id"] == "faith")["default"]
    assert _sunday(fresh)["kind"] == "sunday" and '"palm"' in fresh.get("/art.js").text


def test_removed_faith_stays_removed(demo_env, monkeypatch):
    with _start(monkeypatch) as c:
        _signin(c)
        assert c.delete("/api/admin/packs/faith").status_code == 200
        assert _sunday(c) is None
    with _start(monkeypatch) as c:   # the server starts again: not put back
        assert _sunday(c) is None and '"palm"' not in c.get("/art.js").text
        _signin(c)
        assert not next(e for e in c.get("/api/admin/packs").json()["index"] if e["id"] == "faith")["installed"]


def test_turned_off_faith_stays_off(demo_env, monkeypatch):
    with _start(monkeypatch) as c:
        _signin(c)
        assert c.put("/api/admin/packs/faith", json={"on": False}).status_code == 200
    with _start(monkeypatch) as c:
        assert _sunday(c) is None
        _signin(c)
        assert not next(p for p in c.get("/api/admin/packs").json()["packs"] if p["id"] == "faith")["on"]


def test_seeding_leaves_a_faith_pack_found_elsewhere(demo_env, monkeypatch, optional_art_packs):
    """With the Faith pack already in another folder (the tests' extra folder), nothing is installed twice."""
    from app import config
    assert P.seed_defaults(True) == []
    assert not (P.installed_dir(True) / "faith").exists()
    assert config.read_store(True)["art_packs"]["seeded"] == ["faith"]
    assert P.seed_defaults(True) == []
