"""Shared hooks for looks (docs/themes.md): fresh /themes.css after edits, unique order, and the hooks
app.js and kids.js give a look to hang its design on."""
import json
import os
import re
from pathlib import Path

import pytest

from app import themes

ROOT = Path(__file__).resolve().parent.parent
APP_JS = (ROOT / "web" / "js" / "app.js").read_text(encoding="utf-8")
KIDS_JS = (ROOT / "web" / "js" / "kids.js").read_text(encoding="utf-8")
LOOKS_JS = (ROOT / "web" / "js" / "looks.js").read_text(encoding="utf-8")
FRAME_CSS = (ROOT / "web" / "css" / "frame.css").read_text(encoding="utf-8")


@pytest.fixture
def local_look(tmp_path):
    d = tmp_path / "harbor"
    d.mkdir()
    (d / "theme.json").write_text(json.dumps({"id": "harbor", "name": "Harbor"}))
    (d / "theme.css").write_text("body.look-harbor { --paper: #111111; }")
    themes.reload([(ROOT / "themes", "built-in"), (tmp_path, "local")])
    yield d
    themes.reload()


def _touch(p: Path, text: str):
    p.write_text(text)
    st = p.stat()
    os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns + 5_000_000_000))   # a clearly newer file time
    themes._cache["checked"] = 0.0                                       # skip the one-second wait


def test_an_edited_theme_css_is_served_without_a_restart(local_look):
    v1, css1 = themes.signature(), themes.css()
    assert "#111111" in css1
    _touch(local_look / "theme.css", "body.look-harbor { --paper: #222222; }")
    v2, css2 = themes.signature(), themes.css()
    assert "#222222" in css2 and "#111111" not in css2
    assert v1 != v2                       # /themes.css?v= and its ETag change with it


def test_an_edited_theme_js_and_json_are_read_again(local_look):
    _touch(local_look / "theme.js", "FrameLooks.register('harbor', {});")
    assert "FrameLooks.register('harbor'" in themes.js()
    _touch(local_look / "theme.json", json.dumps({"id": "harbor", "name": "Harbor Two"}))
    assert themes.by_id("harbor")["name"] == "Harbor Two"


def test_every_look_has_its_own_order():
    want = ["navy", "night", "kids", "kids-room", "light", "modern", "illuminated", "gilt-binding", "almanac", "glass", "mica", "tonal"]
    found = [t["id"] for t in themes.discover([(ROOT / "themes", "built-in")])]
    orders = [json.loads((ROOT / "themes" / t / "theme.json").read_text())["order"] for t in found]
    assert len(set(orders)) == len(orders)
    assert found == want


# ---------------- theme.json: words, date style, monogram, picture fit, readouts ----------------

def _meta(**extra):
    return {"id": "harbor", "name": "Harbor", **extra}


@pytest.mark.parametrize("extra, words", [
    ({"words": {"nope": "x"}}, '"words"'),
    ({"words": {"today_title": "x" * 61}}, '"words"'),
    ({"date_style": "medium"}, '"date_style"'),
    ({"monogram": "logo"}, '"monogram"'),
    ({"picture_fit": {"wide": "stretch"}}, '"picture_fit"'),
    ({"options": {"frost": {"type": "range", "preview": "thumbs"}}}, '"preview"'),
    ({"options": {"frost": {"type": "range", "readouts": {"Blur": "blur"}}}}, '"readouts"'),
])
def test_bad_hook_settings_are_explained(tmp_path, extra, words):
    with pytest.raises(themes.ThemeError, match=words):
        themes._check(_meta(**extra), tmp_path / "harbor")


def test_hook_settings_reach_the_frame(tmp_path):
    d = tmp_path / "harbor"
    d.mkdir()
    (d / "theme.json").write_text(json.dumps(_meta(
        words={"today_title": "Order of the day", "tomorrow": "On the morrow"}, date_style="long", monogram="initial",
        picture_fit={"tall": "slice"},
        options={"frost": {"type": "range", "preview": "readouts", "readouts": {"Blur": "--h-blur"}, "help": "h" * 200}})))
    t = themes.discover([(tmp_path, "local")])[0]
    assert t["words"]["today_title"] == "Order of the day" and t["date_style"] == "long" and t["monogram"] == "initial"
    assert t["picture_fit"] == {"tall": "slice"}
    o = t["options"][0]
    assert o["preview"] == "readouts" and o["readouts"] == [["Blur", "--h-blur"]] and len(o["help"]) == 200   # help is no longer cut short


def test_frame_payload_has_the_hooks(demo_env, monkeypatch):
    monkeypatch.setenv("FRAME_NOW", "2026-10-15T16:12:00")
    import importlib
    import sys
    from fastapi.testclient import TestClient
    sys.modules.pop("app.admin", None)
    import app.main
    importlib.reload(app.main)
    with TestClient(app.main.app) as c:
        d = c.get("/api/frame?frame=kitchen").json()
        assert d["date_long"] == "Thursday, the Fifteenth of October"
        assert d["initial"] and len(d["initial"]) == 1 and d["initial"].isalpha()
        f = d["frame"]
        assert f["look_words"] == {} and f["look_date_style"] == "short" and f["look_monogram"] == "image" and f["look_picture_fit"] == {}
        # Settings > General: a family initial of its own
        assert c.post("/api/parent/unlock?remember=1", json={"pin": "1234"}).status_code == 200
        body = dict(c.get("/api/admin/settings").json()["display"], family_initial="q")
        assert c.put("/api/admin/display", json=body).status_code == 200
        assert c.get("/api/frame?frame=kitchen").json()["initial"] == "Q"
        assert c.put("/api/admin/display", json=dict(body, family_initial="7")).status_code == 400
        # The illuminated look asks for the long date and its own words
        frames = c.get("/api/admin/frames").json()["frames"]
        next(x for x in frames if x["id"] == "kitchen").update(look="illuminated")
        assert c.put("/api/admin/frames", json=frames).status_code == 200
        f = c.get("/api/frame?frame=kitchen").json()["frame"]
        assert f["look_date_style"] == "long" and f["look_monogram"] == "initial" and f["look_words"]


def test_family_initial_from_the_name():
    from app.frame import family_initial, long_date
    from datetime import date
    assert family_initial("The Example Family") == "E"
    assert family_initial("Our Family") == "F"
    assert family_initial("Smith household") == "S"
    assert family_initial("Anything", "w") == "W"
    assert long_date(date(2026, 1, 1)) == "Thursday, the First of January"
    assert long_date(date(2026, 10, 31)) == "Saturday, the Thirty-first of October"


def test_themes_js_carries_the_art_families():
    js = themes.js()
    assert "FrameLooks.artFamilies = {" in js and "FrameLooks.artAnchors = {" in js
    fam = json.loads(re.search(r"artFamilies = (\{.*?\});", js).group(1))
    assert fam["C9A55A"] == "gold" and fam["16324F"] in ("night", "navy")


# ---------------- the frame's hooks (web/js) ----------------

def test_drawings_use_css_variables_for_colors_and_fonts():
    assert "function drawVars(svg)" in APP_JS and ":var(--draw-'" in APP_JS and "var(--art-" in APP_JS
    assert "--draw-serif" in APP_JS and "--draw-sans" in APP_JS
    assert 'font-family="Playfair' not in APP_JS and 'font-family="Libre' not in APP_JS
    assert "drawVars(DRAW[v](sc, d.kids, ++svgN))" in APP_JS                  # Screen Time
    assert "return drawVars((DRAW[v] || DRAW.rocket)" in APP_JS               # the Kids screen's picture
    assert "pictureFit()" in APP_JS and "look_picture_fit" in APP_JS


def test_slots_a_look_can_use():
    for slot in ('class="mono-i"', 'data-initial="', 'class="tod"', 'rb-count', 'rb-n', 'rb-date', 'rb-icon', 'rb-more',
                 '<span class="day-tag">Today</span>', 'week-panel', 'and \' +', 'fitDays(', 'fitWeather(', 'class="kbar"', 'kwbadge', '--kt:',
                 'class="nwx"', '<span class="ap">', 'grownups()'):
        assert slot in APP_JS, slot
    for css in (".mono-i { display: none; }", "body.mono-initial .mono-i", ".day-tag { display: none; }", ".week-panel { display: contents; }",
                ".medal { background: var(--medal-bg, var(--kt)); }", ".rb-count, .rb-icon, .rb-more { display: none; }"):
        assert css in FRAME_CSS, css
    assert "style=\"background:' + esc(k.tint)" not in APP_JS                   # the medal color is a CSS variable now
    assert "look === 'kids'" not in APP_JS and "frameOf().look_kids ? 'kids_hi'" in APP_JS
    assert "!important" not in FRAME_CSS.split(".vert .band.tall")[1].split("\n")[0]


def test_words_have_defaults_for_every_key():
    defaults = re.search(r"var WORDS = \{(.*?)\};", APP_JS, re.S).group(1)
    for k in themes.WORD_KEYS:
        assert k + ":" in defaults, k
    assert "H.word('kids_grownups')" in KIDS_JS


def test_looks_js_hooks():
    assert "derive: derive" in LOOKS_JS and "function artVars(art)" in LOOKS_JS and "mono-initial" in LOOKS_JS
    assert "frame.pictures === 'match'" in LOOKS_JS


def test_inline_colors_became_variables():
    assert "style=\"--ct:' + esc(s.tint)" in APP_JS and "var(--ce-bg, var(--ct))" in FRAME_CSS
    assert "var(--minibar-empty, #E6DDCB)" in APP_JS
    # the landed looks no longer need !important or attribute selectors for these
    for t in ("light", "modern", "illuminated", "gilt-binding", "almanac", "glass", "kids-room", "mica", "tonal"):
        css = (ROOT / "themes" / t / "theme.css").read_text()
        assert "[fill=" not in css and 'span.b[style*=' not in css, t
        assert not re.search(r"\.medal \{[^}]*!important", css), t
        assert not re.search(r"\.ce \{[^}]*background:[^;]*!important", css), t
        assert not re.search(r"\.mono \{[^}]*width: \d+px !important", css), t


def test_glass_matches_its_mockup_palette():
    pal = json.loads((ROOT / "themes" / "glass" / "theme.json").read_text())["art"]["palette"]
    assert pal == {"night": "#DCE9F7", "navy": "#6E9BEA", "deep": "#7F95AE", "gold": "#F5D27E", "paper": "#FFFFFF", "red": "#F07C82",
                   "warm": "#F4A86A", "brown": "#B9A48F", "green": "#7CC6A0", "sky": "#2F7CF6", "pink": "#F7C6D3"}
    frost = json.loads((ROOT / "themes" / "glass" / "theme.json").read_text())["options"]["frost"]
    assert frost["preview"] == "readouts" and set(frost["readouts"]) == {"Blur", "Tint", "Text"}
    js = (ROOT / "themes" / "glass" / "theme.js").read_text()
    for v in frost["readouts"].values():
        assert f"out['{v}']" in js


def test_tonal_recolors_matched_pictures_from_its_seed():
    js = (ROOT / "themes" / "tonal" / "theme.js").read_text()
    assert "out.art = {" in js
    assert json.loads((ROOT / "themes" / "tonal" / "theme.json").read_text())["monogram"] == "initial"
