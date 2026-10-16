"""The Light look (themes/light): valid, scoped, safe for the frame's old browser, readable."""
import json
import re
from pathlib import Path

from app import themes

LOOK = Path(__file__).resolve().parent.parent / "themes" / "light"


def _lum(hex_):
    c = [int(hex_[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def _contrast(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def test_light_is_found_and_valid():
    t = themes.by_id("light")
    assert t and t["name"] == "Light"
    meta = json.loads((LOOK / "theme.json").read_text())
    assert meta["id"] == "light" and meta["order"] > 30
    assert set(meta["art"]["palette"]) == {"night", "navy", "deep", "gold", "paper", "red", "warm", "brown", "green", "sky", "pink"}


def test_light_css_is_scoped_and_chrome_106_safe():
    css = (LOOK / "theme.css").read_text()
    body = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    for sel in re.findall(r"(?:^|})\s*([^{}@]+){", body):
        for part in sel.split(","):
            assert part.strip().startswith("body.look-light"), part
    for bad in ("color-mix(", ":has(", "@container", "oklch(", "&"):
        assert bad not in body, bad
    assert not re.search(r"#[0-9A-Fa-f]{8}\b", body)


def test_light_text_colors_are_readable():
    paper, card, ink, soft = "#F6F1E7", "#FFFDF8", "#1F1B16", "#5E5547"
    for fg in (ink, soft, "#7A6236", "#9E2235"):
        assert _contrast(fg, paper) >= 4.5 and _contrast(fg, card) >= 4.5, fg
    assert _contrast("#FFFDF8", ink) >= 4.5     # cream text on the ink pills
    assert _contrast("#C9A55A", ink) >= 4.5     # gold on the dark screen time panel
