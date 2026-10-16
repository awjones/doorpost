"""The Kids room look (themes/kids-room/): valid, scoped, made for kids' frames, self-hosted font, safe for Chrome 106."""
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import artcolor, themes

ROOT = Path(__file__).resolve().parent.parent
LOOK = ROOT / "themes" / "kids-room"


def test_kids_room_is_a_valid_kids_look():
    m = json.loads((LOOK / "theme.json").read_text())
    themes._check(m, LOOK)
    assert m["kids"] is True and m["new_frame"]["home"] == "kids"
    assert set(m["art"]["palette"]) == set(artcolor.FAMILIES)
    t = themes.by_id("kids-room")
    assert t and t["kids"] and t["js"]


def test_kids_room_css_is_scoped_and_old_browser_safe():
    css = (LOOK / "theme.css").read_text()
    assert themes.unscoped_selectors(css, "kids-room") == []
    body = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    assert ":has(" not in body and "color-mix(" not in body and "@container" not in body
    assert not re.search(r"#[0-9A-Fa-f]{8}\b", body), "no 8-digit hex colors on Chrome 106"
    assert "fonts.googleapis" not in body and "http" not in body, "fonts and pictures are self-hosted"


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


def test_kids_room_files_are_served_and_licensed(client):
    for rel in ("fonts/nunito-latin-900-normal.woff2", "img/sun.svg", "img/moon.svg", "img/star.svg"):
        assert (LOOK / rel).is_file()
        assert client.get(f"/themes/kids-room/{rel}").status_code == 200
    assert "Open Font License" in (LOOK / "fonts" / "OFL.txt").read_text()
    for url in re.findall(r"url\(([^)]+)\)", (LOOK / "theme.css").read_text()):
        assert (LOOK / url.strip("'\"")).is_file(), url


def test_kids_room_script_is_old_browser_safe():
    js = (LOOK / "theme.js").read_text()
    assert "=>" not in js and "`" not in js and not re.search(r"\b(let|const)\s", js)
    assert "FrameLooks.register('kids-room'" in js
