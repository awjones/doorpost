"""Glass View (themes/glass/): glass panels over the family photo, driven by the Glass (frost) option."""
import json
import re
from pathlib import Path

from app import themes

FOLDER = Path(__file__).resolve().parent.parent / "themes" / "glass"


def _read(name: str) -> str:
    return (FOLDER / name).read_text()


def test_glass_look_is_valid_with_its_options():
    m = json.loads(_read("theme.json"))
    opts = themes.check_options(m["options"])
    assert m["background"] == "photo"
    frost = opts["frost"]
    assert (frost["type"], frost["min"], frost["max"], frost["default"]) == ("range", 0, 100, 60)
    assert frost["presets"] == {"Frosted": 100, "Balanced": 60, "Clear": 0}
    assert opts["reduce_effects"]["type"] == "bool" and opts["reduce_effects"]["default"] is False
    assert [c[0] for c in opts["background"]["choices"]] == ["slideshow", "one", "favorite"]
    t = themes.by_id("glass")
    assert t and t["background"] == "photo"
    assert themes.option_values(t, {"frost": 140})["frost"] == 60   # out of range goes back to the default


def test_glass_stays_inside_what_chrome_106_can_do():
    css, js = _read("theme.css"), _read("theme.js")
    assert themes.unscoped_selectors(css, "glass") == []
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    for bad in ("color-mix(", ":has(", "@container", "oklch(", "&"):
        assert bad not in css, bad
    assert not re.search(r"#[0-9A-Fa-f]{8}\b", css), "no 8-digit hex colors"
    assert "backdrop-filter: var(--gl-blur)" in css and "backdrop-filter: var(--glp-blur)" in css
    for bad in ("=>", "`", "let ", "const ", "class "):
        assert bad not in js, bad


def test_frost_drives_the_glass_and_popups_stay_frosted():
    js = _read("theme.js")
    assert "FrameLooks.register('glass'" in js
    assert "Math.max(f, 50 + f / 2)" in js            # pop-ups never go below about 50
    assert "reduce ? 'none'" in js                     # Reduce glass effects: no blur at all
    assert "'--gl-'" in js and "'--glp-'" in js and "out['--ink']" in js and "out['--look-photo-dim']" in js


def test_glass_script_and_styles_reach_the_frame():
    assert "FrameLooks.register('glass'" in themes.js()
    assert "body.look-glass .sheet" in themes.css()
