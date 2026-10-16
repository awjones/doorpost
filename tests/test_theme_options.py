"""Look options (theme.json "options"), theme.js, the photo background and kids' looks (app/themes.py, web/js/looks.js)."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import frames, themes

ROOT = Path(__file__).resolve().parent.parent

OPTIONS = {
    "frost": {"label": "Glass", "type": "range", "min": 0, "max": 100, "default": 60,
              "presets": {"Frosted": 100, "Balanced": 60, "Clear": 0}},
    "seed": {"label": "Color", "type": "color", "default": "#2F7A68", "swatches": ["#2F7A68", "#16324F"]},
    "reduce_effects": {"label": "Reduce glass effects on this frame", "type": "bool", "default": False},
    "background": {"type": "choice", "choices": [["slideshow", "Photo slideshow"], ["one", "One photo"], ["favorite", "Today's favorite"]]},
}


def _look(root: Path, tid: str, js: str = "", **extra) -> Path:
    d = root / tid
    d.mkdir(parents=True)
    (d / "theme.json").write_text(json.dumps({"id": tid, "name": tid.title(), **extra}))
    (d / "theme.css").write_text(f"body.look-{tid}[data-opt-reduce-effects=\"1\"] .card {{ box-shadow: none; }}")
    if js:
        (d / "theme.js").write_text(js)
    return d


@pytest.mark.parametrize("bad, words", [
    ({"Frost": {"type": "range"}}, "lowercase"),
    ({"frost": {"type": "slider"}}, "type"),
    ({"frost": {"type": "range", "min": 5, "max": 1}}, "min below max"),
    ({"frost": {"type": "range", "default": 400}}, "default"),
    ({"frost": {"type": "range", "presets": {"A": 200}}}, "presets"),
    ({"seed": {"type": "color", "default": "teal"}}, "color like"),
    ({"seed": {"type": "color", "swatches": ["#FFF"]}}, "swatches"),
    ({"x": {"type": "bool", "default": "yes"}}, "true or false"),
    ({"x": {"type": "choice", "choices": []}}, "choices"),
    ({"x": {"type": "choice", "choices": [["a", "A"]], "default": "b"}}, "one of the choices"),
])
def test_bad_options_are_explained(bad, words):
    with pytest.raises(themes.ThemeError, match=words):
        themes.check_options(bad)


def test_options_background_and_kids_are_read(tmp_path):
    _look(tmp_path, "glass", options=OPTIONS, background="photo", kids=True)
    _look(tmp_path, "badbg", background="video")
    found = themes.discover([(tmp_path, "local")])
    assert [t["id"] for t in found] == ["glass"]
    t = found[0]
    assert t["background"] == "photo" and t["kids"] is True
    by = {o["name"]: o for o in t["options"]}
    assert by["frost"]["presets"] == [["Frosted", 100], ["Balanced", 60], ["Clear", 0]]
    assert by["background"]["default"] == "slideshow"          # first choice when none is given
    assert by["reduce_effects"]["label"].startswith("Reduce")
    pub = themes.public(t)
    assert pub["options"] == t["options"] and pub["background"] == "photo" and pub["kids"] is True


def test_option_values_fill_defaults_and_drop_bad_values(tmp_path):
    _look(tmp_path, "glass", options=OPTIONS)
    t = themes.discover([(tmp_path, "local")])[0]
    assert themes.option_values(t, None) == {"frost": 60, "seed": "#2F7A68", "reduce_effects": False, "background": "slideshow"}
    v = themes.option_values(t, {"frost": 250, "seed": "#abcdef", "reduce_effects": "1", "background": "one", "extra": 1})
    assert v == {"frost": 60, "seed": "#ABCDEF", "reduce_effects": False, "background": "one"}
    assert themes.option_values(None, {"a": 1}) == {}


@pytest.fixture
def glass(tmp_path, monkeypatch):
    """A look with options, theme.js and a photo background, alongside the shipped ones."""
    _look(tmp_path, "glass", js="FrameLooks.register('glass', {derive: function (o) { return {'--glass-tint': o.seed}; }});",
          options=OPTIONS, background="photo", kids=True, order=99)
    themes.reload([(ROOT / "themes", "built-in"), (tmp_path, "local")])
    monkeypatch.setattr(frames, "LOOKS", themes.looks())
    yield themes.by_id("glass")
    themes.reload()


def test_clean_keeps_options_per_look(glass):
    c = frames.clean({"name": "X", "look": "glass", "look_options": {"glass": {"frost": 10}, "navy": {"a": 1}, "gone": {"b": 2}}}, set(), set())
    assert c["look_options"] == {"glass": {"frost": 10, "seed": "#2F7A68", "reduce_effects": False, "background": "slideshow"}}
    assert frames.clean({"name": "Y", "look_options": "nope"}, set(), set())["look_options"] == {}


@pytest.fixture
def client(demo_env, monkeypatch, glass):
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


def test_options_are_saved_and_sent_to_the_frame(client):
    f = client.get("/api/frame?frame=kitchen").json()["frame"]
    assert f["look_options"] == {} and f["look_background"] == "" and f["look_kids"] is False   # navy offers none
    _signin(client)
    fr = client.get("/api/admin/frames").json()
    assert next(l for l in fr["looks"] if l["key"] == "glass")["options"][0]["name"] == "frost"
    frs = fr["frames"]
    frs[0]["look"] = "glass"
    frs[0]["look_options"] = {"glass": {"frost": 0, "seed": "#16324f", "reduce_effects": True, "background": "favorite"}}
    assert client.put("/api/admin/frames", json=frs).status_code == 200
    f = client.get("/api/frame?frame=kitchen").json()["frame"]
    assert f["look"] == "glass" and f["look_background"] == "photo" and f["look_kids"] is True
    assert f["look_options"] == {"frost": 0, "seed": "#16324F", "reduce_effects": True, "background": "favorite"}
    assert client.get("/api/admin/frames").json()["frames"][0]["look_options"]["glass"]["frost"] == 0


def test_theme_js_is_served_wrapped_and_cache_busted(client):
    r = client.get("/themes.js")
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/javascript")
    assert "FrameLooks.register('glass'" in r.text and "catch (e)" in r.text
    assert client.get("/themes.js", headers={"if-none-match": r.headers["etag"]}).status_code == 304
    page = client.get("/frame/kitchen").text
    assert 'src="themes.js?v=' in page and 'src="static/js/looks.js?v=' in page
    assert page.index("looks.js") < page.index("themes.js") < page.index("static/js/app.js")
    assert "#look-bg" in client.get("/themes.css").text


def test_sample_photo_is_a_real_picture(tmp_path):
    from PIL import Image
    from app import demo_photo
    assert demo_photo.ensure(tmp_path / "photos") is True
    with Image.open(tmp_path / "photos" / demo_photo.NAME) as im:
        assert im.size == (2400, 1500) and im.format == "JPEG"
    main = (ROOT / "app" / "main.py").read_text()
    assert "demo_photo.ensure(services.settings.photos_folder)" in main   # demo start, own folder only


def test_sample_photo_only_when_the_folder_is_empty(tmp_path):
    from app import demo_photo
    (tmp_path / "a.jpg").write_bytes(b"x")
    assert demo_photo.ensure(tmp_path) is False and not (tmp_path / demo_photo.NAME).exists()


def test_frame_scripts_stay_chrome_106_safe():
    for name in ("looks.js", "look-options.js"):
        js = (ROOT / "web" / "js" / name).read_text()
        for bad in ("=>", "`", "let ", "const ", "color-mix(", "?.", "??"):
            assert bad not in js, f"{name}: {bad}"
    admin = (ROOT / "web" / "admin.html").read_text()
    assert admin.index("look-options.js") < admin.index("static/js/admin.js")
