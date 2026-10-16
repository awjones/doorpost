"""Gilt binding (themes/gilt-binding/): its fonts are there and licensed, and its CSS and script stay inside what the frame's Chrome 106 can run."""
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import themes

FOLDER = Path(__file__).resolve().parent.parent / "themes" / "gilt-binding"
CSS = (FOLDER / "theme.css").read_text()
JS = (FOLDER / "theme.js").read_text()


def test_every_font_it_points_at_is_there_with_its_license():
    urls = re.findall(r"url\((fonts/[^)]+)\)", CSS)
    assert len(urls) == 5
    total = 0
    for u in urls:
        f = FOLDER / u
        assert f.is_file() and f.read_bytes()[:4] == b"wOF2", u
        total += f.stat().st_size
    assert total < 250_000, "keep the frame's fonts small"
    for lic in ("OFL-cormorantgaramond.txt", "OFL-ebgaramond.txt", "OFL-greatvibes.txt"):
        assert "SIL Open Font License" in (FOLDER / "fonts" / lic).read_text()


def test_css_is_chrome_106_safe_and_scoped():
    text = re.sub(r"/\*.*?\*/", "", CSS, flags=re.S)
    assert themes.unscoped_selectors(CSS, "gilt-binding") == []
    for bad in (":has(", "color-mix(", "@container", "&", "@layer"):
        assert bad not in text, bad
    assert not re.search(r"#[0-9A-Fa-f]{8}\b", text), "8-digit hex colors"


def test_script_is_plain_old_javascript():
    for bad in ("=>", "`", "let ", "const ", "class "):
        assert bad not in JS, bad
    assert "FrameLooks.register('gilt-binding'" in JS


@pytest.fixture
def client(demo_env):
    import importlib
    import sys
    sys.modules.pop("app.admin", None)
    import app.main
    importlib.reload(app.main)
    with TestClient(app.main.app) as c:
        yield c


def test_the_look_and_its_fonts_are_served(client):
    looks = {l["key"]: l for l in client.get("/api/frames").json()["looks"]}
    assert looks["gilt-binding"]["name"] == "Gilt binding"
    css = client.get("/themes.css").text
    assert "body.look-gilt-binding .screen::before" in css
    assert 'url("themes/gilt-binding/fonts/eb-garamond.woff2")' in css
    assert client.get("/themes/gilt-binding/fonts/great-vibes.woff2").status_code == 200
    assert "FrameLooks.register('gilt-binding'" in client.get("/themes.js").text


def test_match_the_look_maps_every_family():
    m = json.loads((FOLDER / "theme.json").read_text())
    from app import artcolor
    assert set(m["art"]["palette"]) == set(artcolor.FAMILIES)
