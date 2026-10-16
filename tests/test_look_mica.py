"""Mica View (themes/mica): valid, scoped, Chrome 106 safe, and its accent option drives the tints."""
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import artcolor, themes

ROOT = Path(__file__).resolve().parent.parent
FOLDER = ROOT / "themes" / "mica"


@pytest.fixture
def client(demo_env, monkeypatch):
    import importlib
    import sys
    sys.modules.pop("app.admin", None)
    import app.main
    importlib.reload(app.main)
    with TestClient(app.main.app) as c:
        yield c


def test_mica_is_found_valid_and_scoped():
    m = json.loads((FOLDER / "theme.json").read_text())
    themes._check(m, FOLDER)
    assert "mica" in [t["id"] for t in themes.all_themes()]
    assert themes.unscoped_selectors((FOLDER / "theme.css").read_text(), "mica") == []
    assert set(m["art"]["palette"]) == set(artcolor.FAMILIES)


def test_accent_option_offers_the_four_swatches():
    t = themes.by_id("mica")
    opt = next(o for o in t["options"] if o["name"] == "accent")
    assert opt["type"] == "color" and opt["default"] == "#1F6FC5"
    assert opt["swatches"] == ["#1F6FC5", "#00707A", "#7A4FC0", "#B34A1A"]
    assert themes.option_values(t, {"accent": "#00707A"})["accent"] == "#00707A"
    assert themes.option_values(t, {"accent": "teal"})["accent"] == "#1F6FC5"


def test_css_and_js_stay_chrome_106_safe():
    css = re.sub(r"/\*.*?\*/", "", (FOLDER / "theme.css").read_text(), flags=re.S)
    for bad in ("color-mix(", ":has(", "@container", "backdrop-filter", "&"):
        assert bad not in css, bad
    assert not re.search(r"#[0-9A-Fa-f]{8}\b", css), "no 8-digit hex colors"
    js = (FOLDER / "theme.js").read_text()
    for bad in ("=>", "`", "let ", "const ", "?.", "??"):
        assert bad not in js, bad
    for var in ("--mica-accent", "--mica-ink", "--mica-soft", "--mica-line", "--mica-faint"):
        assert var in js and var in css


def test_mica_reaches_the_frame(client):
    css = client.get("/themes.css").text
    assert "body.look-mica" in css
    # the monogram is borrowed from the shared images, not copied into the look
    assert 'themes/../static/img/monogram.png' in css
    assert "FrameLooks.register('mica'" in client.get("/themes.js").text
