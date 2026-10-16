"""Open almanac look (themes/almanac/): valid, scoped, self-contained and safe for the frame's old browser."""
import json
import re
from pathlib import Path

from app import artcolor, themes

ROOT = Path(__file__).resolve().parent.parent
LOOK = ROOT / "themes" / "almanac"


def test_almanac_is_found_and_valid():
    t = next(t for t in themes.all_themes() if t["id"] == "almanac")
    assert t["name"] == "Open almanac" and t["kind"] == "both"
    m = json.loads((LOOK / "theme.json").read_text())
    themes._check(m, LOOK)
    assert set(m["art"]["palette"]) == set(artcolor.FAMILIES)


def test_css_is_scoped_and_chrome_106_safe():
    css = (LOOK / "theme.css").read_text()
    assert themes.unscoped_selectors(css, "almanac") == []
    plain = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    for bad in (":has(", "color-mix(", "@container", "oklch(", "@layer"):
        assert bad not in plain, bad
    assert not re.search(r"#[0-9A-Fa-f]{8}\b", plain), "no 8-digit hex colors"
    depth = 0
    for ch in plain:   # no nesting: a rule never opens inside another (only @font-face/@media blocks would)
        if ch == "{":
            depth += 1
            assert depth == 1, "nested CSS rule"
        elif ch == "}":
            depth -= 1


def test_fonts_are_local_small_and_licensed():
    css = (LOOK / "theme.css").read_text()
    urls = re.findall(r"url\((fonts/[^)]+)\)", css)
    assert urls
    total = 0
    for u in urls:
        f = LOOK / u
        assert f.is_file(), u
        total += f.stat().st_size
    assert total < 200_000
    assert "http" not in re.sub(r"url\(\"data:[^)]*\)", "", css)
    lic = sorted(p.name for p in (LOOK / "fonts").glob("OFL-*.txt"))
    assert lic == ["OFL-libre-caslon-text.txt", "OFL-mrs-saint-delafield.txt", "OFL-playfair-display.txt"]


def test_script_is_plain_old_javascript():
    js = (LOOK / "theme.js").read_text()
    assert "FrameLooks.register('almanac'" in js
    code = re.sub(r"/\*.*?\*/|//[^\n]*", "", js, flags=re.S)
    assert "=>" not in code and "`" not in code
    assert not re.search(r"\b(let|const|class)\s", code)
