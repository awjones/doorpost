"""Looks (themes/<id>/) and picture styles (Pictures: Original / Match the look)."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import artcolor, frames, themes

ROOT = Path(__file__).resolve().parent.parent


# ---------------- the looks that come with Doorpost ----------------

def test_shipped_looks_are_found_in_order():
    ids = [t["id"] for t in themes.all_themes()]
    assert ids[:3] == ["navy", "night", "kids"]
    assert themes.default_id() == "navy"
    assert frames.LOOKS["night"] == ("Quiet night", "Dark, dim, easy on the eyes")
    assert set(frames.LOOKS) == set(ids)


@pytest.mark.parametrize("tid", [p.name for p in (ROOT / "themes").iterdir() if (p / "theme.json").is_file()])
def test_every_shipped_look_is_valid_and_scoped(tid):
    folder = ROOT / "themes" / tid
    m = json.loads((folder / "theme.json").read_text())
    themes._check(m, folder)
    assert themes.unscoped_selectors((folder / "theme.css").read_text(), tid) == []
    assert m["kind"] in themes.KINDS and m["swatches"] and m["blurb"]
    assert set(m["art"]["palette"]) == set(artcolor.FAMILIES), "a shipped look maps every color family"


def test_unscoped_rules_are_caught():
    css = "body.look-x .a { color: red; }\n.b, body.look-x .c { color: blue; }\nbody.look-xy .d { }\n@media (max-width: 9px) { .e { } }"
    assert themes.unscoped_selectors(css, "x") == [".b", "body.look-xy .d"]


def _theme(root: Path, tid: str, css: str = "", **extra) -> Path:
    d = root / tid
    d.mkdir(parents=True)
    (d / "theme.json").write_text(json.dumps({"id": tid, "name": tid.title(), **extra}))
    (d / "theme.css").write_text(css)
    return d


def test_bad_looks_are_skipped_and_local_wins(tmp_path):
    built, local = tmp_path / "themes", tmp_path / "local"
    _theme(built, "plain", "body.look-plain { --paper: #FFFFFF; }", order=5)
    _theme(built, "wrongid").joinpath("theme.json").write_text(json.dumps({"id": "other", "name": "X"}))
    _theme(built, "badpal", art={"palette": {"sparkle": "#FFFFFF"}})
    _theme(built, "badfilter", art={"filter": "url(#x)"})
    _theme(built, "off", enabled=False)
    _theme(local, "plain", name="Mine")
    found = themes.discover([(built, "built-in"), (local, "local")])
    assert sorted(t["id"] for t in found) == ["off", "plain"]
    assert next(t for t in found if t["id"] == "plain")["where"] == "local"
    assert next(t for t in found if t["id"] == "off")["enabled"] is False


def test_theme_css_parts(tmp_path):
    d = _theme(tmp_path, "sea", "@font-face { font-family: Sea; src: url(fonts/sea.woff2); }\nbody.look-sea { --paper: #E0F0FF; }",
               fonts={"serif": "Sea, Georgia, serif"},
               art={"palette": {"gold": "#FFCC00"}, "filter": "saturate(1.2)", "frame": {"border-radius": "20px"}})
    t = themes.discover([(tmp_path, "local")])[0]
    css = themes.theme_css(t, {"#C9A55A": "gold", "#C8102E": "red"})
    assert "body.look-sea { --serif: Sea, Georgia, serif; }" in css
    assert "body.look-sea.pics-match { --art-C9A55A: #FFCC00; }" in css   # red: not in the look's palette, stays as drawn
    assert "filter: saturate(1.2)" in css and "border-radius: 20px" in css
    assert 'url("themes/sea/fonts/sea.woff2")' in css
    assert d.name == "sea"


# ---------------- color families ----------------

def test_families_keep_backgrounds_and_ink_apart():
    svg_a = '<svg><rect width="100%" height="100%" fill="#24406B"></rect><circle fill="#C9A55A"></circle></svg>'
    svg_b = '<svg><rect width="100%" height="100%" fill="#9FC2D9"></rect><rect fill="#2E4A7A" stroke="#c8102e"></rect></svg>'
    colors, backs = set(), set()
    for s in (svg_a, svg_b):
        c, b = artcolor.colors_in(s)
        colors |= c
        backs |= b
    fam = artcolor.families(colors, backs, {"#C9A55A": "paper", "#123456": "nope"})
    assert fam["#24406B"] == "night"          # a dark full background
    assert fam["#9FC2D9"] == "sky"            # a light background keeps its own family
    assert fam["#2E4A7A"] == "navy"           # dark blue drawn on top: ink blue
    assert fam["#C8102E"] == "red"
    assert fam["#C9A55A"] == "paper"          # a pack's own word wins


def test_remap_keeps_shade_order():
    assert artcolor.remap("#C9A55A", "gold", "#F4B400") == "#F4B400"
    light, dark = artcolor.remap("#F6E3B0", "gold", "#F4B400"), artcolor.remap("#8C7A4E", "gold", "#F4B400")
    assert artcolor.oklch(light)[0] > artcolor.oklch("#F4B400")[0] > artcolor.oklch(dark)[0]
    assert all(artcolor.HEX6.match(artcolor.remap(h, artcolor.family(h), "#3FA9F5")) for h in ("#000000", "#FFFFFF", "#5E86B0"))


# ---------------- the server ----------------

@pytest.fixture
def client(demo_env, monkeypatch):
    monkeypatch.setenv("FRAME_NOW", "2026-10-17T10:00:00")
    import importlib
    import sys
    sys.modules.pop("app.admin", None)
    import app.main
    importlib.reload(app.main)
    with TestClient(app.main.app) as c:
        yield c


def _signin(c):
    assert c.post("/api/parent/unlock?remember=1", json={"pin": "1234"}).status_code == 200


def test_themes_css_is_served_and_cache_busted(client):
    r = client.get("/themes.css")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/css")
    css = r.text
    for tid in ("navy", "night", "kids"):
        assert f"body.look-{tid}" in css
    assert "body.look-kids.pics-match { --art-" in css and "--art-C9A55A: #F4B400;" in css
    assert client.get("/themes.css", headers={"if-none-match": r.headers["etag"]}).status_code == 304
    page = client.get("/frame/playroom").text
    assert 'href="themes.css?v=' in page
    assert "body.look-night" not in (ROOT / "web" / "css" / "frame.css").read_text()   # moved to themes/night/theme.css


def test_theme_files_are_served_safely(client, tmp_path):
    t = themes.by_id("night")
    (t["folder"] / "fonts").mkdir(exist_ok=True)
    f = t["folder"] / "fonts" / "test-font.woff2"
    f.write_bytes(b"wOF2")
    try:
        assert client.get("/themes/night/fonts/test-font.woff2").content == b"wOF2"
        assert client.get("/themes/night/theme.json").status_code == 404     # not a font or picture
        assert client.get("/themes/night/../navy/theme.css").status_code == 404
        assert client.get("/themes/nope/fonts/test-font.woff2").status_code == 404
    finally:
        f.unlink()
        (t["folder"] / "fonts").rmdir()


def test_looks_reach_the_frame_picker_and_settings(client):
    looks = client.get("/api/frames").json()["looks"]
    assert [l["key"] for l in looks][:3] == ["navy", "night", "kids"]
    assert next(l for l in looks if l["key"] == "night")["home"] == "clock"
    _signin(client)
    v = client.get("/api/admin/frames").json()
    assert next(l for l in v["looks"] if l["key"] == "kids")["swatches"]


def test_a_new_frame_starts_the_way_its_look_says(client):
    _signin(client)
    r = client.post("/api/parent/frames", json={"name": "Bedroom", "look": "night"})
    assert r.status_code == 200
    f = client.get(f"/api/frame?frame={r.json()['id']}").json()["frame"]
    assert f["look"] == "night" and f["home"] == "clock" and f["screens"] == ["clock", "calendar", "photos"]
    r = client.post("/api/parent/frames", json={"name": "Den", "look": "no-such-look"})
    assert client.get(f"/api/frame?frame={r.json()['id']}").json()["frame"]["look"] == "navy"


def test_picture_style_is_per_frame(client):
    assert client.get("/api/frame?frame=kitchen").json()["frame"]["pictures"] == "original"
    _signin(client)
    fr = client.get("/api/admin/frames").json()["frames"]
    fr[1]["pictures"] = "match"
    fr[0]["pictures"] = "sparkly"
    assert client.put("/api/admin/frames", json=fr).status_code == 200
    assert client.get("/api/frame?frame=playroom").json()["frame"]["pictures"] == "match"
    assert client.get("/api/frame?frame=kitchen").json()["frame"]["pictures"] == "original"


def test_clean_keeps_known_values():
    c = frames.clean({"name": "X", "look": "kids", "pictures": "match"}, set(), set())
    assert c["look"] == "kids" and c["pictures"] == "match"
    c = frames.clean({"name": "X", "look": "gone", "pictures": None}, set(), set())
    assert c["look"] == "navy" and c["pictures"] == "original"


def test_every_drawn_color_has_a_family(client):
    """The colors in the turned-on packs (the Faith pack comes on) and the screen time drawings all get a value per look."""
    import app.main
    fam = themes.art_families(app.main.app.state.services.packs)
    assert len(fam) > 150 and {"#C9A55A", "#16324F", "#FFFDF8"} <= set(fam)
    css = client.get("/themes.css").text
    kids = next(line for line in css.splitlines() if line.startswith("body.look-kids.pics-match {"))
    assert kids.count("--art-") == len(fam)


def test_pack_palette_is_checked_and_used(tmp_path):
    from app import packs as P
    with pytest.raises(P.PackError, match="palette"):
        P.check_manifest({"id": "x", "name": "X", "palette": {"red": "#FF0000"}})
    P.check_manifest({"id": "x", "name": "X", "palette": {"#FF0000": "red"}})


def test_frame_js_recolors_only_with_match_the_look():
    js = (ROOT / "web" / "js" / "app.js").read_text()
    assert "frameOf().pictures !== 'match'" in js and "var(--art-' + h + ',#' + h + ')" in js
    assert "pics-' + (d.frame.pictures || 'original')" in js
    assert "LOOK_NAMES = { navy" not in js   # the look list comes from the server
