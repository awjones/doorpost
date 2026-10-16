"""The Illuminated look: valid, scoped, safe for the frame's Chrome 106, and its own fonts ship with their license."""
import json
import re
from pathlib import Path

from app import themes

ROOT = Path(__file__).resolve().parent.parent
LOOK = ROOT / "themes" / "illuminated"


def test_illuminated_is_found_and_has_a_full_art_palette():
    t = next(t for t in themes.enabled() if t["id"] == "illuminated")
    assert t["name"] == "Illuminated" and t["kind"] == "both"
    m = json.loads((LOOK / "theme.json").read_text())
    assert set(m["art"]["palette"]) == {"night", "navy", "deep", "gold", "paper", "red", "warm", "brown", "green", "sky", "pink"}


def test_css_is_chrome_106_safe_and_its_fonts_exist():
    css = (LOOK / "theme.css").read_text()
    assert ":has(" not in css and "color-mix" not in css and "@container" not in css
    assert not re.search(r"#[0-9A-Fa-f]{8}\b", css)                      # no 8-digit hex colors
    for rule in re.split(r"}\s*", re.sub(r"/\*.*?\*/", "", css, flags=re.S)):
        rule = rule.strip()
        assert not rule or "{" not in rule or rule.startswith(("body.look-illuminated", "@font-face")), rule[:80]
    for url in re.findall(r"url\(([^)]+)\)", css):
        assert (LOOK / url.strip("\"'")).is_file(), url
    assert (LOOK / "fonts" / "OFL.txt").is_file()
    assert sum(f.stat().st_size for f in (LOOK / "fonts").glob("*.woff2")) < 200_000


def test_theme_js_is_plain_old_javascript():
    js = (LOOK / "theme.js").read_text()
    assert "FrameLooks.register('illuminated'" in js
    assert "=>" not in js and "`" not in js and not re.search(r"\b(let|const)\s+\w+\s*=", js)
