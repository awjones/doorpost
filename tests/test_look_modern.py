"""The Modern look (themes/modern/): white cards, bold Figtree, one accent color that drives the rest."""
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import artcolor, themes

ROOT = Path(__file__).resolve().parent.parent
LOOK = ROOT / "themes" / "modern"


def _manifest():
    return json.loads((LOOK / "theme.json").read_text())


def test_modern_is_a_valid_scoped_look():
    m = _manifest()
    themes._check(m, LOOK)
    assert themes.unscoped_selectors((LOOK / "theme.css").read_text(), "modern") == []
    assert set(m["art"]["palette"]) == set(artcolor.FAMILIES)
    assert m["order"] > 30   # after the three that come with Doorpost


def test_accent_option_has_the_mockup_red_and_four_swatches():
    acc = _manifest()["options"]["accent"]
    assert acc["type"] == "color" and acc["default"] == "#C8102E"
    assert acc["swatches"] == ["#C8102E", "#1A1A1A", "#1565C0", "#2E7D32"]
    assert themes.check_options(_manifest()["options"])


def test_the_accent_reaches_every_accent_place():
    css = (LOOK / "theme.css").read_text()
    js = (LOOK / "theme.js").read_text()
    assert "FrameLooks.register('modern'" in js and "'--mo-accent'" in js and "'--mo-accent-tint'" in js
    # the family mark, the next row, the countdown ribbon, today in the calendar, special days, the list button
    for sel in (".band .mono", ".pill-next", ".ev.next", ".ribbon", ".day.today .dh", ".mcell.today", ".day.sp", ".ladd-btn", ".tab .badge"):
        rule = next((r for r in css.split("\n") if sel in r and "var(--mo-accent" in r), None)
        assert rule, f"{sel} should use the accent"
    # no hard-coded default red left outside the fallbacks
    assert re.findall(r"(?<!, )#C8102E", css) == ["#C8102E"], "only the :root default may name the red"


def test_modern_stays_chrome_106_safe():
    css = (LOOK / "theme.css").read_text()
    js = (LOOK / "theme.js").read_text()
    for bad in ("color-mix(", ":has(", "@container", "&"):
        assert bad not in css, bad
    assert not re.search(r"#[0-9A-Fa-f]{8}\b", css), "no 8-digit hex colors"
    for bad in ("=>", "`", "let ", "const ", "?.", "??"):
        assert bad not in js, bad


def test_fonts_are_small_and_licensed():
    fonts = sorted((LOOK / "fonts").glob("*.woff2"))
    assert len(fonts) == 5 and sum(f.stat().st_size for f in fonts) < 100_000
    assert "SIL Open Font License" in (LOOK / "fonts" / "OFL.txt").read_text()
    css = (LOOK / "theme.css").read_text()
    for f in fonts:
        assert f"url(fonts/{f.name})" in css


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


def test_accent_is_saved_per_frame_and_served(client):
    assert "FrameLooks.register('modern'" in client.get("/themes.js").text
    css = client.get("/themes.css").text
    assert "body.look-modern" in css and 'url("themes/modern/fonts/figtree-700-normal.woff2")' in css
    assert client.post("/api/parent/unlock?remember=1", json={"pin": "1234"}).status_code == 200
    fr = client.get("/api/admin/frames").json()
    assert next(l for l in fr["looks"] if l["key"] == "modern")["options"][0]["name"] == "accent"
    frs = fr["frames"]
    frs[0]["look"] = "modern"
    frs[0]["look_options"] = {"modern": {"accent": "#1565c0"}}
    assert client.put("/api/admin/frames", json=frs).status_code == 200
    f = client.get("/api/frame?frame=kitchen").json()["frame"]
    assert f["look"] == "modern" and f["look_options"] == {"accent": "#1565C0"}
    assert client.get("/themes/modern/fonts/figtree-400-normal.woff2").status_code == 200
