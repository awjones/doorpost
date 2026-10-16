"""Settings look: Settings and the phone page in a frame look, safely (app/admin_looks.py, docs/themes.md)."""
import json
import logging
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import admin_looks as A
from app import themes

ROOT = Path(__file__).resolve().parent.parent
SHIPPED = sorted(p.parent.name for p in (ROOT / "themes").glob("*/theme.json"))


def _shipped():
    themes.reload(None)
    return [t for t in themes.enabled() if t["where"] == "built-in"]


# ---------------- every look's tokens ----------------

def test_every_shipped_look_has_admin_tokens():
    ids = [t["id"] for t in _shipped()]
    assert len(ids) == 12 and set(ids) == set(SHIPPED)
    for t in _shipped():
        raw = A.admin_block(t).get("tokens", {})
        assert set(A.REQUIRED) <= set(raw), t["id"]
        assert set(raw) <= set(A.TOKENS), t["id"]


@pytest.mark.parametrize("tid", SHIPPED)
def test_tokens_pass_the_readability_check_with_every_option_preset(tid):
    t = next(t for t in _shipped() if t["id"] == tid)
    block = A.admin_block(t)
    wash = block.get("photo_wash", "rgba(236, 241, 248, 0.7)") if block.get("photo") else None
    combos = A.presets(t)
    assert combos
    for opts in combos:
        tok = A.resolve(t, opts)
        assert A.check(tok, wash) == [], (tid, opts)
        # body and button text 4.5:1, the focus ring 3:1, said straight out
        solid = lambda k: A.over(tok[k], tok["paper"]) if A.rgba(tok[k])[3] < 1 else tok[k]   # noqa: E731
        assert A.contrast(tok["ink"], solid("card")) >= 4.5
        assert A.contrast(tok["accent_ink"], tok["accent"]) >= 4.5
        assert A.contrast(tok["focus"], solid("card")) >= 3


def test_navy_is_the_plain_style_exactly():
    navy = next(t for t in _shipped() if t["id"] == "navy")
    assert A.resolve(navy, {}) == A.NAVY
    assert A.check(A.NAVY) == []
    # the CSS defaults match the code's plain style
    css = (ROOT / "web" / "css" / "admin-look.css").read_text()
    for k, v in A.NAVY.items():
        assert f"--a-{k.replace('_', '-')}: {v};" in css, k


def test_options_change_the_tokens():
    tonal = next(t for t in _shipped() if t["id"] == "tonal")
    a, b = A.resolve(tonal, {"seed": "#2F7A68"}), A.resolve(tonal, {"seed": "#8A4FA8"})
    assert a["accent"] == "#286859"            # the same as the frame's Tonal View scheme (themes/tonal/theme.js)
    assert a["accent"] != b["accent"] and a["paper"] != b["paper"]
    modern = next(t for t in _shipped() if t["id"] == "modern")
    assert A.resolve(modern, {"accent": "#1565C0"})["accent"] == "#1565C0"
    pale = A.resolve(modern, {"accent": "#FFE08A"})   # a pale pick is darkened until white text reads on it
    assert A.contrast(pale["accent"], "#FFFFFF") >= 4.5 or A.contrast(pale["accent_ink"], pale["accent"]) >= 4.5
    glass = next(t for t in _shipped() if t["id"] == "glass")
    assert A.rgba(A.resolve(glass, {"frost": 0})["card"])[3] > A.rgba(A.resolve(glass, {"frost": 100})["card"])[3]


def test_check_catches_bad_tokens():
    bad = dict(A.NAVY, ink="#CCCCCC", accent_ink="#1A2A40", focus="#F6F1E7")
    problems = A.check(bad)
    assert any(p.startswith("ink on paper") for p in problems)
    assert any(p.startswith("accent_ink on accent") for p in problems)
    assert any(p.startswith("focus on paper") for p in problems)


def test_expressions():
    ctx = A._Ctx({"card": "#FFFFFF"}, {"seed": "#2F7A68", "frost": 50}, {"--paper": "#F6F1E7"})
    assert ctx.eval("var(--paper)") == "#F6F1E7"
    assert ctx.eval("mix(#000000, #FFFFFF, 0.5)") == "#808080"
    assert ctx.eval("alpha(#FFFFFF, lerp($frost, 0.6, 0.8))") == "rgba(255, 255, 255, 0.7)"
    assert A.contrast(ctx.eval("readable(#FFE08A, #FFFFFF)"), "#FFFFFF") >= 4.5
    for bad in ("url(x.png)", "red; background: url(y)", "$nope", "@nope", "var(--nope)"):
        with pytest.raises(A.LookError):
            ctx.eval(bad)


# ---------------- admin.css: decoration only ----------------

def test_shipped_admin_css_has_no_forbidden_patterns():
    files = list((ROOT / "themes").glob("*/admin.css"))
    assert files
    for f in files:
        text = re.sub(r"/\*.*?\*/", "", f.read_text(), flags=re.S)
        for rx, what in A.FORBIDDEN:
            assert not rx.search(text), f"{f}: {what}"
        assert not re.search(r"display\s*:\s*none", text) and not re.search(r"position\s*:\s*fixed", text)
        css, problems = A.clean_admin_css(f.read_text(), f.parent.name)
        assert problems == [], (f, problems)
        assert css.strip()


@pytest.mark.parametrize("rule, words", [
    ("body.admin-look-x input { display: none; }", "display"),
    ("body.admin-look-x .side { position: fixed; }", "position"),
    ("body.admin-look-x .card { opacity: 0; }", "opacity"),
    ("body.admin-look-x .btn { visibility: hidden; }", "visibility"),
    ("body.admin-look-x .card { transform: translateX(-900px); }", "transform"),
    (".card { border: 1px solid red; }", "scoped"),
    ("body.admin-look-other .card { border: 0; }", "scoped"),
    ("body.admin-look-x .card { color: #EEEEEE; }", "text tokens"),
    ("body.admin-look-x .card { background-color: #000; }", "::before"),
    ("body.admin-look-x input { font-size: 30px; }", "headings"),
    ("body.admin-look-x .card { width: 0; }", "::before"),
    ("body.admin-look-x .card { background-image: url(https://example.com/x.png); }", "own folder"),
    ("@import url(x.css);", "@import"),
])
def test_admin_css_takes_out_what_is_not_decoration(rule, words):
    css, problems = A.clean_admin_css(rule + "\nbody.admin-look-x .card { border-radius: 4px; }", "x")
    assert problems and any(words in p for p in problems), problems
    assert "border-radius: 4px" in css
    assert not re.search(r"display\s*:\s*none|position|opacity|visibility|transform|#EEEEEE|example\.com", css)


def test_admin_css_keeps_decoration():
    css, problems = A.clean_admin_css(
        "body.admin-look-x .aband { border-bottom: 4px double #C9A55A; background-image: linear-gradient(#111111, #222222); }\n"
        "body.admin-look-x .card > h2 { color: var(--a-accent); font-size: 28px; font-style: italic; }\n"
        "body.admin-look-x .card > h2::after { content: \"\"; display: block; border-top: 1px solid #000; }\n"
        "@media (max-width: 760px) { body.admin-look-x .card { box-shadow: none; } }", "x")
    assert problems == []
    for bit in ("border-bottom: 4px double", "color: var(--a-accent)", "font-size: 28px", "display: block", "@media (max-width: 760px)"):
        assert bit in css


# ---------------- the setting and the pages ----------------

@pytest.fixture
def client(demo_env, monkeypatch):
    monkeypatch.setenv("FRAME_NOW", "2026-10-15T16:12:00")
    themes.reload(None)
    import importlib
    import sys
    sys.modules.pop("app.admin", None)
    import app.main
    importlib.reload(app.main)
    with TestClient(app.main.app) as c:
        assert c.post("/api/parent/unlock?remember=1", json={"pin": "1234"}).status_code == 200
        yield c


def _body(html):
    return re.search(r"<body[^>]*>", html).group(0)


def test_default_is_navy_and_the_page_carries_tokens(client):
    page = client.get("/admin").text
    assert 'data-admin-look="navy"' in _body(page)
    assert '<style id="admin-look">' in page and "--a-paper: #F6F1E7;" in page
    assert "Settings look: Navy &amp; gilt." in page or "Settings look: Navy & gilt." in page
    assert client.get("/admin/overview").status_code == 200
    got = client.get("/api/admin/settings-look").json()
    assert got["setting"] == {"look": "navy", "frame": "", "phone": True}
    assert {l["key"] for l in got["looks"]} == set(SHIPPED) and all(l["ready"] for l in got["looks"])
    assert all(l["swatches"] for l in got["looks"])


def test_setting_is_saved_and_validated(client):
    assert client.put("/api/admin/settings-look", json={"look": "illuminated", "phone": False}).status_code == 200
    assert client.get("/api/admin/settings-look").json()["setting"] == {"look": "illuminated", "frame": "", "phone": False}
    assert 'data-admin-look="illuminated"' in _body(client.get("/admin/frames").text)
    assert 'data-admin-look="navy"' in _body(client.get("/parent").text)      # the phone page stays plain
    for bad in ({"look": "nope"}, {"look": "frame", "frame": "nope"}, {"look": ""}):
        r = client.put("/api/admin/settings-look", json=bad)
        assert r.status_code == 400 and r.json()["detail"]
    assert client.get("/api/admin/settings-look").json()["setting"]["look"] == "illuminated"
    client.cookies.clear()
    assert client.put("/api/admin/settings-look", json={"look": "navy"}).status_code in (401, 403)


def test_phone_page_follows_when_asked(client):
    client.put("/api/admin/settings-look", json={"look": "kids-room", "phone": True})
    page = client.get("/parent").text
    assert 'data-admin-look="kids-room"' in _body(page)
    assert "Nunito" in page                       # the look's own fonts come along
    assert 'href="parent?look=plain"' in page


def test_match_a_frame_follows_its_look_and_options(client):
    frs = client.get("/api/admin/frames").json()["frames"]
    frs[0]["look"] = "tonal"
    frs[0]["look_options"] = {"tonal": {"seed": "#8A4FA8"}}
    assert client.put("/api/admin/frames", json=frs).status_code == 200
    assert client.put("/api/admin/settings-look", json={"look": "frame", "frame": frs[0]["id"]}).status_code == 200
    page = client.get("/admin").text
    tonal = themes.by_id("tonal")
    want = A.resolve(tonal, {"seed": "#8A4FA8"})
    assert 'data-admin-look="tonal"' in _body(page)
    assert f"--a-accent: {want['accent']};" in page and want["accent"] != "#286859"
    assert "Settings look: Tonal View (matching Kitchen)." in page
    # the frame changes its look: Settings follows
    frs[0]["look"] = "modern"
    frs[0]["look_options"] = {"modern": {"accent": "#1565C0"}}
    client.put("/api/admin/frames", json=frs)
    page = client.get("/admin").text
    assert 'data-admin-look="modern"' in _body(page) and "--a-accent: #1565C0;" in page


def test_look_plain_always_gives_the_plain_style(client):
    client.put("/api/admin/settings-look", json={"look": "gilt-binding", "phone": True})
    for url in ("/admin?look=plain", "/admin/calendars?look=plain", "/parent?look=plain"):
        page = client.get(url).text
        assert 'data-admin-look="plain"' in _body(page), url
        assert "admin-look-navy" in _body(page) and "--a-paper: #F6F1E7;" in page
        assert "Plain style." in page and "admin-look-gilt-binding" not in page
    assert 'data-admin-look="gilt-binding"' in _body(client.get("/admin").text)


def test_removed_or_turned_off_look_falls_back_to_navy(client, monkeypatch):
    client.put("/api/admin/settings-look", json={"look": "almanac"})
    real = themes.by_id
    monkeypatch.setattr(themes, "by_id", lambda tid: None if tid == "almanac" else real(tid))
    page = client.get("/admin").text
    assert 'data-admin-look="navy"' in _body(page) and "--a-paper: #F6F1E7;" in page
    assert "removed or turned off" in client.get("/api/admin/settings-look").json()["now"]["reason"]


def test_matched_frame_gone_falls_back_to_navy():
    cfg = {"settings_look": {"look": "frame", "frame": "attic"}}
    got = A.choose(cfg, [{"id": "kitchen", "name": "Kitchen", "look": "glass", "look_options": {}}], "admin")
    assert got["id"] == "navy" and "gone" in got["reason"]


def _bad_look(root: Path) -> None:
    d = root / "murky"
    d.mkdir(parents=True)
    tokens = dict(A.NAVY, ink="#9A9A9A", card="#A0A0A0")
    (d / "theme.json").write_text(json.dumps({"id": "murky", "name": "Murky", "admin": {"tokens": tokens}}))
    (d / "theme.css").write_text("")
    (d / "admin.css").write_text("body.admin-look-murky input { display: none; }\nbody.admin-look-murky .card { border-radius: 2px; }")


def test_failing_tokens_give_navy_and_say_why(tmp_path, caplog):
    _bad_look(tmp_path / "themes")
    themes.reload([(ROOT / "themes", "built-in"), (tmp_path / "themes", "local")])
    try:
        choice = A.choose({"settings_look": {"look": "murky"}}, [], "admin")
        assert choice["id"] == "murky"
        with caplog.at_level(logging.WARNING, logger="app.admin_looks"):
            html = A.dress("<html><head></head><body><!--admin-look-foot--></body></html>", choice, "admin")
        assert 'data-admin-look="navy"' in html and "admin-look-navy" in html and "--a-ink: #1F1B16;" in html
        assert "display: none" not in html
        assert "couldn't be used safely" in html
        assert any("murky" in r.getMessage() and "ink on" in r.getMessage() for r in caplog.records)
        assert next(l for l in A.list_public() if l["key"] == "murky")["ready"] is False
    finally:
        themes.reload(None)


def test_admin_css_problems_are_dropped_but_the_rest_is_used(tmp_path):
    _bad_look(tmp_path / "themes")
    d = tmp_path / "themes" / "murky"
    m = json.loads((d / "theme.json").read_text())
    m["admin"]["tokens"] = dict(A.NAVY)
    (d / "theme.json").write_text(json.dumps(m))
    themes.reload([(ROOT / "themes", "built-in"), (tmp_path / "themes", "local")])
    try:
        html = A.dress("<html><head></head><body></body></html>", A.choose({"settings_look": {"look": "murky"}}, [], "admin"), "admin")
        assert 'data-admin-look="murky"' in html
        assert "border-radius: 2px" in html and "display: none" not in html
    finally:
        themes.reload(None)


def test_pages_use_tokens_not_fixed_colors():
    """Settings and the phone page draw their colors from the admin tokens (Navy's values live in admin-look.css)."""
    for name in ("admin.html", "parent.html"):
        text = (ROOT / "web" / name).read_text()
        style = text.split("<style>", 1)[1].split("</style>", 1)[0]
        assert "var(--navy)" not in style and "var(--gilt)" not in style, name
        assert "admin-look.css" in text and "<!--admin-look-foot-->" in text
