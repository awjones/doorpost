"""Writes the diagrams in docs/img/.

Run from the repo root:  python3 scripts/docs/gen_diagrams.py            (writes docs/img/)
                         python3 scripts/docs/gen_diagrams.py <outdir>   (writes somewhere else)

Every diagram uses the same look: navy, gilt and paper colors, system fonts, drawn icons and a
dark-mode version through prefers-color-scheme. Edit the text here, never the SVG files.
To check a change, open the SVG in a browser in light and dark mode, or screenshot it with
headless Chrome, and look for text that overlaps or runs past its box.
"""
import sys
from html import escape
from pathlib import Path

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2] / "docs" / "img"

STYLE = """<style>
svg { --bg:#faf6ee; --card:#ffffff; --soft:#f3ecdc; --ink:#1d2a44; --muted:#5a6273; --line:#d8ccb2;
  --navy:#1d2a44; --onnavy:#faf6ee; --gilt:#b8913a; --icon:#1d2a44; --off:#c9c2b2; --knob:#ffffff; }
@media (prefers-color-scheme: dark) {
  svg { --bg:#12161f; --card:#1a2030; --soft:#202839; --ink:#e8dcc0; --muted:#a8a08d; --line:#3a4358;
    --navy:#27365a; --onnavy:#e8dcc0; --gilt:#b8913a; --icon:#e8dcc0; --off:#4a5268; --knob:#e8dcc0; }
}
text { font-family: system-ui, -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; fill: var(--ink); }
.bg { fill: var(--bg); }
.card { fill: var(--card); stroke: var(--line); stroke-width: 1.5; }
.soft { fill: var(--soft); stroke: var(--line); stroke-width: 1.5; }
.zone { fill: var(--soft); stroke: var(--line); stroke-width: 2; stroke-dasharray: 8 6; }
.zoneg { fill: none; stroke: var(--gilt); stroke-width: 2.5; stroke-dasharray: 8 6; }
.gcard { fill: var(--card); stroke: var(--gilt); stroke-width: 2.5; }
.dcard { fill: var(--card); stroke: var(--line); stroke-width: 1.5; stroke-dasharray: 6 5; }
.navy { fill: var(--navy); }
.giltf { fill: var(--gilt); }
.offf { fill: var(--off); }
.knob { fill: var(--knob); }
.onnavy { fill: var(--onnavy); }
.muted { fill: var(--muted); }
.gilt { fill: var(--gilt); }
.title { font-size: 30px; font-weight: 700; }
.sub { font-size: 17px; fill: var(--muted); }
.h { font-size: 18px; font-weight: 700; }
.b { font-size: 15px; }
.s { font-size: 14px; fill: var(--muted); }
.lbl { font-size: 14px; font-weight: 600; fill: var(--gilt); }
.cap { font-size: 13.5px; font-weight: 700; letter-spacing: 1.2px; fill: var(--gilt); }
.ln { stroke: var(--muted); stroke-width: 2; fill: none; }
.lng { stroke: var(--gilt); stroke-width: 2.5; fill: none; }
.lnd { stroke: var(--muted); stroke-width: 2; fill: none; stroke-dasharray: 6 5; }
.ic { fill: none; stroke: var(--icon); stroke-width: 2.4; stroke-linecap: round; stroke-linejoin: round; }
.icg { fill: none; stroke: var(--gilt); stroke-width: 2.4; stroke-linecap: round; stroke-linejoin: round; }
.icf { fill: var(--gilt); }
.icn { fill: var(--icon); }
.ah { fill: var(--muted); }
.ahg { fill: var(--gilt); }
</style>"""

DEFS = """<defs>
<marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0L10 5L0 10z"/></marker>
<marker id="ahg" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path class="ahg" d="M0 0L10 5L0 10z"/></marker>
<symbol id="i-cal" viewBox="0 0 48 48"><rect class="ic" x="6" y="10" width="36" height="32" rx="4"/><path class="ic" d="M6 19h36M16 6v8M32 6v8"/><rect class="icf" x="13" y="25" width="6" height="5" rx="1"/><rect class="icf" x="21" y="25" width="6" height="5" rx="1"/><rect class="icf" x="29" y="25" width="6" height="5" rx="1"/><rect class="icf" x="13" y="33" width="6" height="5" rx="1"/><rect class="icf" x="21" y="33" width="6" height="5" rx="1"/></symbol>
<symbol id="i-weather" viewBox="0 0 48 48"><circle class="icg" cx="18" cy="17" r="7"/><path class="icg" d="M18 4v3M6 17H3M9 8l2 2M27 8l-2 2"/><path class="ic" d="M15 40h22a7 7 0 0 0 0-14 10 10 0 0 0-19 3 6 6 0 0 0-3 11z"/></symbol>
<symbol id="i-photo" viewBox="0 0 48 48"><rect class="ic" x="5" y="9" width="38" height="30" rx="3"/><path class="ic" d="M5 34l11-11 9 9 6-6 12 12"/><circle class="icf" cx="33" cy="18" r="4"/></symbol>
<symbol id="i-house" viewBox="0 0 48 48"><path class="ic" d="M6 22L24 7l18 15M10 19v22h28V19"/><rect class="icg" x="17" y="27" width="14" height="14"/><path class="icg" d="M17 32h14M17 36.5h14"/></symbol>
<symbol id="i-mac" viewBox="0 0 48 48"><rect class="ic" x="4" y="7" width="40" height="27" rx="3"/><path class="ic" d="M19 34l-2 7h14l-2-7M14 41h20"/><path class="icg" d="M12 15h12M12 21h20M12 27h8"/></symbol>
<symbol id="i-pi" viewBox="0 0 48 48"><rect class="ic" x="4" y="10" width="40" height="28" rx="3"/><rect class="icf" x="17" y="18" width="13" height="13" rx="1.5"/><path class="ic" d="M9 14.5h2M14 14.5h2M19 14.5h2M24 14.5h2M29 14.5h2M34 14.5h2M39 14.5h1"/><path class="ic" d="M37 22h7M37 29h7M8 34h5"/></symbol>
<symbol id="i-frame" viewBox="0 0 48 48"><rect class="ic" x="3" y="6" width="42" height="30" rx="3"/><rect class="icg" x="8" y="11" width="32" height="20" rx="1"/><path class="icg" d="M8 27l8-7 7 6 5-4 12 9"/><path class="ic" d="M20 36l-4 7M28 36l4 7"/></symbol>
<symbol id="i-phone" viewBox="0 0 48 48"><rect class="ic" x="13" y="3" width="22" height="42" rx="4"/><path class="ic" d="M21 39h6"/><path class="icg" d="M18 12h12M18 18h12M18 24h8"/></symbol>
<symbol id="i-sliders" viewBox="0 0 48 48"><path class="ic" d="M7 13h34M7 24h34M7 35h34"/><circle class="icf" cx="16" cy="13" r="4.5"/><circle class="icf" cx="31" cy="24" r="4.5"/><circle class="icf" cx="21" cy="35" r="4.5"/></symbol>
<symbol id="i-cloud" viewBox="0 0 48 48"><path class="ic" d="M13 38h24a9 9 0 0 0 1-18A13 13 0 0 0 13 21a8.5 8.5 0 0 0 0 17z"/></symbol>
<symbol id="i-router" viewBox="0 0 48 48"><rect class="ic" x="5" y="25" width="38" height="14" rx="3"/><path class="ic" d="M14 25l-4-14M34 25l4-14"/><circle class="icf" cx="13" cy="32" r="2"/><circle class="icf" cx="20" cy="32" r="2"/><circle class="icf" cx="27" cy="32" r="2"/></symbol>
<symbol id="i-laptop" viewBox="0 0 48 48"><rect class="ic" x="9" y="10" width="30" height="21" rx="2"/><path class="ic" d="M4 37h40l-3-6H7z"/></symbol>
<symbol id="i-check" viewBox="0 0 48 48"><rect class="ic" x="7" y="7" width="34" height="34" rx="6"/><path class="icg" d="M15 24l7 7 12-14"/></symbol>
<symbol id="i-hourglass" viewBox="0 0 48 48"><path class="ic" d="M12 5h24M12 43h24M15 5c0 10 9 13 9 19s-9 9-9 19M33 5c0 10-9 13-9 19s9 9 9 19"/><path class="icf" d="M18 39c2-6 6-8 6-11 0 3 4 5 6 11z"/></symbol>
<symbol id="i-list" viewBox="0 0 48 48"><path class="icg" d="M7 12l3 3 5-6M7 24l3 3 5-6"/><path class="ic" d="M20 12h21M20 24h21M20 36h21"/><rect class="ic" x="7" y="32" width="8" height="8" rx="1.5"/></symbol>
<symbol id="i-star" viewBox="0 0 48 48"><path class="icg" d="M24 5l5.6 12 13 1.4-9.8 8.7 2.8 12.8L24 33.3 12.4 39.9l2.8-12.8-9.8-8.7 13-1.4z"/></symbol>
<symbol id="i-clock" viewBox="0 0 48 48"><circle class="ic" cx="24" cy="24" r="18"/><path class="icg" d="M24 13v11l8 5"/></symbol>
<symbol id="i-lock" viewBox="0 0 48 48"><rect class="ic" x="9" y="21" width="30" height="22" rx="3"/><path class="ic" d="M15 21v-6a9 9 0 0 1 18 0v6"/><circle class="icf" cx="24" cy="32" r="3"/></symbol>
<symbol id="i-download" viewBox="0 0 48 48"><path class="ic" d="M24 6v24M14 21l10 10 10-10M8 41h32"/></symbol>
<symbol id="i-pin" viewBox="0 0 48 48"><rect class="ic" x="6" y="6" width="36" height="36" rx="5"/><circle class="icf" cx="16" cy="16" r="2.6"/><circle class="icf" cx="24" cy="16" r="2.6"/><circle class="icf" cx="32" cy="16" r="2.6"/><circle class="icf" cx="16" cy="24" r="2.6"/><circle class="icf" cx="24" cy="24" r="2.6"/><circle class="icf" cx="32" cy="24" r="2.6"/><circle class="icf" cx="16" cy="32" r="2.6"/><circle class="icf" cx="24" cy="32" r="2.6"/><circle class="icf" cx="32" cy="32" r="2.6"/></symbol>
</defs>"""


# Icons only the setup explainers use (kept apart so the older diagrams stay byte-for-byte the same).
MORE_ICONS = """<defs>
<symbol id="i-warn" viewBox="0 0 48 48"><path class="icg" d="M24 6L44 41H4z"/><path class="ic" d="M24 19v10"/><circle class="icn" cx="24" cy="34.5" r="2.2"/></symbol>
<symbol id="i-chat" viewBox="0 0 48 48"><path class="ic" d="M9 8h30a5 5 0 0 1 5 5v15a5 5 0 0 1-5 5H23l-10 8v-8H9a5 5 0 0 1-5-5V13a5 5 0 0 1 5-5z"/><circle class="icf" cx="16" cy="20.5" r="2.6"/><circle class="icf" cx="24" cy="20.5" r="2.6"/><circle class="icf" cx="32" cy="20.5" r="2.6"/></symbol>
<symbol id="i-chip" viewBox="0 0 48 48"><rect class="ic" x="11" y="11" width="26" height="26" rx="3"/><rect class="icf" x="18" y="18" width="12" height="12" rx="1.5"/><path class="ic" d="M17 4v7M24 4v7M31 4v7M17 37v7M24 37v7M31 37v7M4 17h7M4 24h7M4 31h7M37 17h7M37 24h7M37 31h7"/></symbol>
<symbol id="i-code" viewBox="0 0 48 48"><path class="ic" d="M16 13L5 24l11 11M32 13l11 11-11 11"/><path class="icg" d="M28 8l-8 32"/></symbol>
<symbol id="i-cable" viewBox="0 0 48 48"><path class="ic" d="M18 4v8M30 4v8M12 12h24v8a12 12 0 0 1-24 0z"/><path class="icg" d="M24 32v4a6 6 0 0 0 6 6h12"/></symbol>
<symbol id="i-shield" viewBox="0 0 48 48"><path class="ic" d="M24 4l17 6v12c0 10-7 18-17 22C14 40 7 32 7 22V10z"/><path class="icg" d="M16 24l6 6 10-12"/></symbol>
<symbol id="i-target" viewBox="0 0 48 48"><circle class="ic" cx="24" cy="24" r="15"/><path class="ic" d="M24 3v10M24 35v10M3 24h10M35 24h10"/><circle class="icf" cx="24" cy="24" r="4"/></symbol>
<symbol id="i-monitor" viewBox="0 0 48 48"><rect class="ic" x="3" y="6" width="42" height="28" rx="3"/><path class="ic" d="M24 34v7M15 42h18"/><rect class="icg" x="9" y="12" width="30" height="16" rx="1"/></symbol>
<symbol id="i-sd" viewBox="0 0 48 48"><path class="ic" d="M14 4h20l6 6v32a2 2 0 0 1-2 2H14a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z"/><path class="icg" d="M19 10v7M24 10v7M29 10v7"/></symbol>
<symbol id="i-moon" viewBox="0 0 48 48"><path class="icg" d="M34 30A15 15 0 0 1 19 9a15 15 0 1 0 15 21z"/></symbol>
</defs>"""


def head(w, h, title, desc):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-labelledby="title desc">',
            f'<title id="title">{escape(title)}</title>', f'<desc id="desc">{escape(desc)}</desc>',
            STYLE, DEFS, f'<rect class="bg" x="0" y="0" width="{w}" height="{h}"/>']


def T(x, y, s, cls="b", anchor=None, extra=""):
    a = f' text-anchor="{anchor}"' if anchor else ""
    return f'<text x="{x}" y="{y}" class="{cls}"{a}{extra}>{escape(s)}</text>'


def lines(x, y, rows, cls="s", step=20, anchor=None):
    return [T(x, y + i * step, r, cls, anchor) for i, r in enumerate(rows)]


def icon(name, x, y, size=44):
    return f'<use href="#i-{name}" x="{x}" y="{y}" width="{size}" height="{size}"/>'


def rect(x, y, w, h, cls="card", rx=12):
    return f'<rect class="{cls}" x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}"/>'


def arrow(x1, y1, x2, y2, cls="ln", both=False, gilt=False):
    m = "ahg" if gilt else "ah"
    start = f' marker-start="url(#{m})"' if both else ""
    return f'<path class="{cls}" d="M{x1} {y1}L{x2} {y2}"{start} marker-end="url(#{m})"/>'


def path(d, cls="ln", end=True, both=False, gilt=False):
    m = "ahg" if gilt else "ah"
    e = f' marker-end="url(#{m})"' if end else ""
    s = f' marker-start="url(#{m})"' if both else ""
    return f'<path class="{cls}" d="{d}"{s}{e}/>'


def header(o, w, title, sub):
    o.append(T(40, 56, title, "title"))
    o.append(T(40, 88, sub, "sub"))
    o.append(f'<rect class="giltf" x="40" y="104" width="64" height="3" rx="1.5"/>')


def save(name, o):
    o.append("</svg>")
    (OUT / name).write_text("\n".join(o) + "\n")


# ---------------------------------------------------------------- 1. how it works
def how_it_works():
    W, H = 1200, 800
    o = head(W, H, "The frame is just a screen",
             "Data sources on the left feed one home computer in the middle, which serves finished pages to the picture frame, the parent phone page and the settings page on the right.")
    header(o, W, "The frame is just a screen",
           "One small computer at home does all the work. The frame only shows the page it is given.")

    # column captions
    o.append(T(30, 150, "WHERE THE DATA COMES FROM", "cap"))
    o.append(T(630, 150, "THE HOME COMPUTER", "cap", "middle"))
    o.append(T(915, 150, "WHAT IT SERVES", "cap"))

    # left: sources
    srcs = [
        ("cal", "Calendars", ["Private iCal addresses"], "events", False),
        ("weather", "Weather", ["National Weather Service"], "forecast", False),
        ("photo", "Photos", ["A folder, uploads, or", "shared album links"], "pictures", False),
        ("house", "Home Assistant", ["Garage, doors, locks"], "states", False),
        ("mac", "Mac helper (optional)", ["Apple Photos favorites,", "Reminders lists every 30 s"], "favorites, lists", True),
    ]
    y = 172
    for ic, name, sub, lab, both in srcs:
        h = 92
        cls = "dcard" if "optional" in name else "card"
        o.append(rect(30, y, 290, h, cls))
        o.append(icon(ic, 46, y + 24))
        o.append(T(104, y + 36, name, "h"))
        o += lines(104, y + 60, sub, "s", 19)
        cy = y + h // 2
        o.append(arrow(326, cy, 476, cy, both=both))
        o.append(T(401, cy - 10, lab, "lbl", "middle"))
        y += h + 16

    # middle: the brain
    bx, by, bw, bh = 482, 172, 296, 532
    o.append(rect(bx, by, bw, bh, "gcard", 16))
    o.append(f'<path class="navy" d="M{bx} {by+16}a16 16 0 0 1 16-16h{bw-32}a16 16 0 0 1 16 16v78H{bx}z"/>')
    o.append(f'<g style="--icon:#faf6ee">{icon("pi", bx+20, by+22, 50)}</g>')
    o.append(T(bx + 84, by + 44, "The brain", "h", extra=' style="fill:#faf6ee;font-size:21px"'))
    o.append(T(bx + 84, by + 68, "always on, port 8090", "s", extra=' style="fill:#e8dcc0"'))
    o += lines(bx + 22, by + 124, ["A Raspberry Pi running Home", "Assistant (as an add-on), or any", "always-on computer with Python."], "s", 20)
    o.append(f'<path class="ln" d="M{bx+22} {by+186}H{bx+bw-22}" style="stroke:var(--line)"/>')
    jobs = ["Reads calendars every few minutes", "Checks the weather", "Crops photos to fit the screen",
            "Reads garage and door states", "Keeps chores and screen time", "in its own SQLite database",
            "Holds settings and parent PINs", "Builds the finished page"]
    jy = by + 222
    for j in jobs:
        if j.startswith("in its own"):
            o.append(T(bx + 42, jy - 16, j, "b"))
            jy += 22
            continue
        o.append(f'<circle class="giltf" cx="{bx+28}" cy="{jy-5}" r="4"/>')
        o.append(T(bx + 42, jy, j, "b"))
        jy += 38

    # right: screens
    outs = [
        ("frame", "Picture frame(s)", ["One full-screen browser,", "1280 x 800"], "finished page", "every 30 s", False),
        ("phone", "Parent phone page", ["/parent: approve chores,", "add screen time"], "approvals", None, True),
        ("sliders", "Settings", ["/admin, or the Home", "Assistant sidebar"], "settings", None, True),
    ]
    y = 220
    for ic, name, sub, lab, lab2, both in outs:
        h = 100
        o.append(rect(916, y, 254, h))
        o.append(icon(ic, 930, y + 28))
        o.append(T(986, y + 40, name, "h"))
        o += lines(986, y + 64, sub, "s", 19)
        cy = y + h // 2
        o.append(arrow(784, cy, 910, cy, both=both))
        o.append(T(847, cy - 10, lab, "lbl", "middle"))
        if lab2:
            o.append(T(847, cy + 24, lab2, "s", "middle"))
        y += h + 40

    # footer note
    o.append(rect(30, 728, 1140, 50, "soft", 10))
    o.append(icon("lock", 46, 736, 34))
    o.append(T(92, 759, "No logins, accounts or private addresses live on the frame. If it is lost or swapped, nothing private goes with it.", "b"))
    save("how-it-works.svg", o)


# ---------------------------------------------------------------- 2. network
def network():
    W, H = 1200, 880
    o = head(W, H, "Two networks, one door",
             "The home router runs a main network with phones, laptops and the home computer, and an isolated frame network that can reach only the home computer on port 8090. Optional remote access goes through a tunnel with sign-in.")
    header(o, W, "Two networks, one door",
           "The frame sits on its own Wi-Fi. It can reach the home computer on port 8090 and nothing else.")

    # internet cloud
    o.append(icon("cloud", 650, 128, 80))
    o.append(T(690, 222, "Internet", "h", "middle"))
    # away-from-home box
    o.append(rect(40, 134, 430, 104, "dcard"))
    o.append(icon("phone", 54, 158, 52))
    o.append(T(116, 166, "Away from home (optional)", "h"))
    o += lines(116, 190, ["/parent and /admin through a tunnel with", "sign-in, e.g. Cloudflare Tunnel + Access"], "s", 19)
    o.append(arrow(476, 186, 642, 172, "lnd", both=False))
    # tunnel line from cloud down to computer (drawn later), label
    # router
    o.append(rect(630, 270, 120, 74, "card"))
    o.append(icon("router", 666, 270, 48))
    o.append(T(690, 334, "Router", "b", "middle"))
    o.append(path("M690 234V264", "ln", end=True, both=True))

    # zones
    o.append(rect(40, 380, 580, 300, "zone", 18))
    o.append(T(64, 414, "Main network", "h"))
    o.append(T(64, 436, "Phones, laptops, the home computer", "s"))
    o.append(rect(760, 380, 400, 300, "zoneg", 18))
    o.append(T(784, 414, "Frame network (isolated)", "h"))
    o.append(T(784, 436, "Its own Wi-Fi / VLAN", "s"))
    # router to zones
    o.append(path("M640 344L560 376", "ln", end=True))
    o.append(path("M740 344L840 376", "ln", end=True))

    # devices in main
    o.append(icon("phone", 70, 470, 56))
    o.append(T(98, 548, "Phones", "b", "middle"))
    o.append(icon("laptop", 160, 470, 56))
    o.append(T(188, 548, "Laptops", "b", "middle"))
    o.append(T(70, 610, "Parents open /parent here,", "s"))
    o.append(T(70, 630, "and /admin for settings.", "s"))
    # home computer
    o.append(rect(330, 460, 260, 190, "gcard", 14))
    o.append(icon("pi", 348, 476, 52))
    o.append(T(412, 498, "Home computer", "h"))
    o.append(T(412, 520, "the brain", "s"))
    o += lines(350, 560, ["doorpost.local:8090", "Pi with Home Assistant,", "or any always-on computer"], "s", 21)

    # frames
    o.append(icon("frame", 900, 462, 70))
    o.append(icon("frame", 990, 470, 56))
    o.append(T(966, 556, "Picture frame(s)", "b", "middle"))
    o.append(f'<circle class="giltf" cx="792" cy="602" r="4"/>')
    o.append(T(806, 607, "Can reach: home computer, port 8090", "b"))
    o.append(f'<circle class="offf" cx="792" cy="636" r="4"/>')
    o.append(T(806, 641, "Blocked: the internet, the main network", "b"))
    # the one door
    o.append(arrow(892, 506, 596, 506, "lng", gilt=True))
    o.append(T(690, 494, "port 8090 only", "lbl", "middle"))

    # key
    o.append(T(40, 730, "WHAT LIVES WHERE", "cap"))
    o.append(rect(40, 746, 540, 112, "card"))
    o.append(icon("frame", 58, 770, 48))
    o.append(T(122, 782, "On the frame: nothing private", "h"))
    o += lines(122, 808, ["A kiosk browser showing one page. No logins,", "accounts, calendar addresses or photo library."], "s", 20)
    o.append(rect(620, 746, 540, 112, "card"))
    o.append(icon("pi", 638, 770, 48))
    o.append(T(702, 782, "On the home computer", "h"))
    o += lines(702, 808, ["Settings, secret calendar addresses, parent PINs,", "the chores and screen time database, photos."], "s", 20)
    save("network.svg", o)


# ---------------------------------------------------------------- 3. modules
def toggle(o, x, y, on):
    if on:
        o.append(f'<rect class="giltf" x="{x}" y="{y}" width="46" height="26" rx="13"/>')
        o.append(f'<circle class="knob" cx="{x+33}" cy="{y+13}" r="9"/>')
        o.append(T(x + 23, y + 46, "on", "s", "middle"))
    else:
        o.append(f'<rect class="offf" x="{x}" y="{y}" width="46" height="26" rx="13"/>')
        o.append(f'<circle class="knob" cx="{x+13}" cy="{y+13}" r="9"/>')
        o.append(T(x + 23, y + 46, "off", "s", "middle"))


def modules():
    W, H = 1200, 890
    o = head(W, H, "A small core, with modules",
             "A core of frame shell, clock, calendar, settings and parent PINs, surrounded by modules that can each be turned on or off in Settings, Modules, plus art packs for special-day pictures.")
    header(o, W, "A small core, with modules",
           "Turn on what your family uses in Settings > Modules. Leave the rest off. Special-day pictures come in art packs.")

    mods = [
        ("frame", "Multiple frames", ["Each screen in the house", "gets its own look and screens"], False),
        ("check", "Chores", ["Kids tap I did it, a parent", "approves or sends it back"], True),
        ("hourglass", "Screen time", ["A weekend pool that", "approved chores fill"], True),
        ("photo", "Photos", ["Slideshow after 5 idle", "minutes, from your sources"], True),
        ("weather", "Weather", ["Today and the next days,", "National Weather Service"], True),
        ("list", "Lists", ["Apple Reminders lists,", "through the Mac helper"], False),
        ("house", "Home Assistant", ["Garage and door status", "on the Today screen"], False),
        ("star", "Special days", ["Birthdays and holidays get", "a full-panel picture"], True),
    ]
    cw, ch = 300, 116
    pos = [(40, 140), (450, 140), (860, 140),
           (40, 342), (860, 342),
           (40, 544), (450, 544), (860, 544)]
    core = (430, 290, 340, 228)
    cx, cy = core[0] + core[2] / 2, core[1] + core[3] / 2
    # connectors first (behind)
    for (x, y) in pos:
        mx, my = x + cw / 2, y + ch / 2
        if y == 342:
            x1 = x + cw if x < 600 else x
            x2 = core[0] if x < 600 else core[0] + core[2]
            o.append(f'<path class="ln" d="M{x1} {my}H{x2}" style="stroke:var(--line)"/>')
        elif x == 450:
            y1 = y + ch if y < 300 else y
            y2 = core[1] if y < 300 else core[1] + core[3]
            o.append(f'<path class="ln" d="M600 {y1}V{y2}" style="stroke:var(--line)"/>')
        else:
            px = x + cw if x < 600 else x
            py = y + ch if y < 300 else y
            qx = core[0] + 40 if x < 600 else core[0] + core[2] - 40
            qy = core[1] if y < 300 else core[1] + core[3]
            o.append(f'<path class="ln" d="M{px} {py}L{qx} {qy}" style="stroke:var(--line)"/>')
    for (ic, name, sub, on), (x, y) in zip(mods, pos):
        o.append(rect(x, y, cw, ch, "card" if on else "dcard"))
        o.append(icon(ic, x + 18, y + 20, 40))
        o.append(T(x + 72, y + 46, name, "h"))
        o += lines(x + 20, y + 84, sub, "s", 19)
        toggle(o, x + cw - 66, y + 22, on)

    # core
    x, y, w, h = core
    o.append(rect(x, y, w, h, "gcard", 16))
    o.append(f'<path class="navy" d="M{x} {y+16}a16 16 0 0 1 16-16h{w-32}a16 16 0 0 1 16 16v38H{x}z"/>')
    o.append(T(cx, y + 35, "Core, always on", "h", "middle", ' style="fill:#faf6ee"'))
    items = ["Frame shell: screens, photo", "and night modes", "Clock", "Settings", "Parent PINs", "Several frames, each with its own"]
    iy = y + 86
    rows = [("Frame shell and night clock", True), ("Clock and date", True), ("Calendar", True),
            ("Settings page", True), ("A PIN for each parent", True)]
    for r, _ in rows:
        o.append(f'<circle class="giltf" cx="{x+28}" cy="{iy-5}" r="4"/>')
        o.append(T(x + 42, iy, r, "b"))
        iy += 32

    # art packs
    ay = 712
    o.append(T(40, ay, "ART PACKS", "cap"))
    o.append(T(40, ay + 26, "Pictures for special days. Some come with Doorpost; download others if you want them.", "s"))
    packs = [("Holidays", "included", True), ("Seasons", "included", True), ("Faith", "comes on", True),
             ("Outings", "download", False), ("Activities", "download", False)]
    px = 40
    for name, note, inc in packs:
        o.append(rect(px, ay + 50, 190, 96, "gcard" if inc else "dcard", 12))
        if inc:
            o.append(icon("star", px + 16, ay + 70, 36))
        else:
            o.append(icon("download", px + 16, ay + 70, 36))
        o.append(T(px + 64, ay + 90, name, "h"))
        o.append(T(px + 64, ay + 114, note, "s"))
        px += 204
    o.append(T(1112, ay + 104, "and more", "s", "middle"))
    save("modules.svg", o)


# ---------------------------------------------------------------- 4. setup paths
def setup_paths():
    W, H = 1200, 900
    o = head(W, H, "Three ways to run it",
             "Step one: run the server as a Home Assistant add-on on a Raspberry Pi, on any always-on computer with Python, or in demo mode on a laptop. Step two: take over the frame, install the kiosk app, and point it at the server.")
    header(o, W, "Three ways to run it",
           "Pick where the brain runs. Then turn a cheap picture frame into its screen.")

    o.append(T(40, 158, "1   RUN THE BRAIN (PICK ONE)", "cap"))
    cards = [
        ("pi", "Home Assistant add-on", "on a Raspberry Pi", "RECOMMENDED",
         ["Copy it in as a local add-on,", "then Install and Start.", "", "Settings open from the HA", "sidebar, and HA backups", "include them. Uses about", "60 to 90 MB of memory."]),
        ("laptop", "Any always-on computer", "Linux box, old laptop, Mac mini", None,
         ["Install the Python packages", "and run the FastAPI server", "on port 8090.", "", "A systemd service file is", "included for Linux. Settings", "open at /admin with a PIN."]),
        ("laptop", "Try it on a laptop", "demo mode, nothing to set up", None,
         ["Start it with FRAME_DEMO=1.", "Sample calendars, weather,", "house status and chores.", "", "Open localhost:8090 for the", "frame and /parent for the", "phone page."]),
    ]
    x = 40
    for ic, title, sub, badge, body in cards:
        cls = "gcard" if badge else "card"
        o.append(rect(x, 176, 360, 380, cls, 14))
        o.append(icon(ic, x + 22, 198, 52))
        o.append(T(x + 88, 220, title, "h"))
        o.append(T(x + 88, 243, sub, "s"))
        if badge:
            o.append(f'<rect class="giltf" x="{x+22}" y="268" width="128" height="26" rx="13"/>')
            o.append(T(x + 86, 286, badge, "cap", "middle", ' style="fill:#ffffff;font-size:12.5px"'))
        o.append(f'<path class="ln" d="M{x+22} 312H{x+338}" style="stroke:var(--line)"/>')
        o += [T(x + 22, 346 + i * 26, r, "b") for i, r in enumerate(body) if r]
        x += 380

    # join arrow
    o.append(path("M220 562V590H980V562", "ln", end=False))
    o.append(path("M600 562V590", "ln", end=False))
    o.append(path("M600 590V614", "ln"))
    o.append(rect(420, 620, 360, 46, "soft", 23))
    o.append(T(600, 649, "The brain at http://<server>:8090", "b", "middle"))

    o.append(T(40, 714, "2   SET UP THE FRAME", "cap"))
    steps = [
        ("lock", "Take over the frame", ["Follow Wes Bos's guide:", "github.com/wesbos/", "photo-frame-dashboard"]),
        ("frame", "Install the kiosk", ["One full-screen browser that", "opens by itself on power-up"]),
        ("sliders", "Point it at the brain", ["Set the kiosk address and put", "the frame on its own network"]),
    ]
    x = 40
    for i, (ic, title, body) in enumerate(steps):
        o.append(rect(x, 732, 340, 140, "card", 14))
        o.append(f'<circle class="navy" cx="{x+34}" cy="768" r="18"/>')
        o.append(T(x + 34, 774, str(i + 1), "h", "middle", ' style="fill:#faf6ee"'))
        o.append(icon(ic, x + 276, 748, 44))
        o.append(T(x + 64, 774, title, "h"))
        o += lines(x + 24, 812, body, "s", 20)
        if i < 2:
            o.append(arrow(x + 346, 802, x + 394, 802))
        x += 400
    save("setup-paths.svg", o)


# ---------------------------------------------------------------- 5. day in the life
def day():
    W, H = 1200, 660
    o = head(W, H, "One chore, start to finish",
             "A child claims a chore on the frame, it waits for a parent, a parent approves it with a PIN on the frame or from the phone page, and the minutes go into the family's weekend screen time pool.")
    header(o, W, "One chore, start to finish",
           "Kids can never add minutes themselves. Every change needs a parent, and every change is logged.")

    steps = [
        ("1", "Child 1 taps I did it", ["On the frame's Chores", "screen: Feed the dog,", "10 min."]),
        ("2", "It waits for a parent", ["The chore moves to", "Waiting for Mom or Dad.", "No minutes yet."]),
        ("3", "A parent approves", ["With a PIN on the frame,", "or from the phone page.", "Or sends it back."]),
        ("4", "Minutes are added", ["+10 min to the family's", "weekend pool, shown as", "Child 1's share."]),
    ]
    x = 40
    for i, (n, title, body) in enumerate(steps):
        o.append(rect(x, 140, 252, 330, "card", 14))
        # mini illustration area
        o.append(rect(x + 16, 156, 220, 140, "soft", 10))
        o.append(f'<circle class="navy" cx="{x+34}" cy="330" r="16"/>')
        o.append(T(x + 34, 336, n, "h", "middle", ' style="fill:#faf6ee;font-size:16px"'))
        o.append(T(x + 58, 336, title, "h", extra=' style="font-size:17px"'))
        o += lines(x + 20, 378, body, "s", 21)
        if i < 3:
            o.append(arrow(x + 258, 305, x + 290, 305))
        x += 290

    # illustrations
    # 1: frame with chore row and button
    bx = 56
    o.append(f'<rect class="navy" x="{bx+10}" y="168" width="200" height="116" rx="6"/>')
    o.append(f'<rect class="card" x="{bx+20}" y="178" width="180" height="96" rx="3"/>')
    o.append(T(bx + 32, 204, "Feed the dog", "b"))
    o.append(T(bx + 32, 224, "10 min", "s"))
    o.append(f'<rect class="giltf" x="{bx+32}" y="236" width="104" height="28" rx="14"/>')
    o.append(T(bx + 84, 255, "I did it", "b", "middle", ' style="fill:#ffffff;font-weight:700"'))
    # 2: waiting
    bx = 346
    o.append(icon("clock", bx + 82, 172, 56))
    o.append(T(bx + 110, 254, "Waiting for", "b", "middle"))
    o.append(T(bx + 110, 274, "Mom or Dad", "b", "middle"))
    # 3: PIN pad and phone
    bx = 636
    o.append(icon("pin", bx + 30, 186, 70))
    o.append(T(bx + 65, 280, "PIN", "s", "middle"))
    o.append(T(bx + 112, 230, "or", "s", "middle"))
    o.append(icon("phone", bx + 128, 186, 70))
    o.append(T(bx + 163, 280, "/parent", "s", "middle"))
    # 4: pool bar
    bx = 926
    o.append(T(bx + 30, 186, "Weekend pool", "b"))
    o.append(f'<rect class="offf" x="{bx+30}" y="200" width="180" height="22" rx="11"/>')
    o.append(f'<rect class="giltf" x="{bx+30}" y="200" width="118" height="22" rx="11"/>')
    o.append(T(bx + 30, 254, "Child 1", "s"))
    o.append(T(bx + 210, 254, "+10 min", "lbl", "end"))
    o.append(T(bx + 30, 278, "Child 2", "s"))
    o.append(T(bx + 210, 278, "+25 min", "s", "end"))

    # send-back branch note + ledger
    o.append(rect(40, 498, 1120, 128, "soft", 12))
    o.append(T(64, 534, "On the weekend", "h"))
    o += lines(64, 560, ["The weekend total is the pool plus the base time for", "Saturday and Sunday. Parents can also add a good-day", "bonus or take minutes away, with a reason."], "s", 21)
    o.append(T(620, 534, "The ledger", "h"))
    o += lines(620, 560, ["Every change is a row with who made it and when.", "Undo adds an opposite entry; nothing is deleted.", "Nothing resets by itself: a parent starts the new week."], "s", 21)
    save("day-in-the-life.svg", o)




# ================================================================ setup explainers
def head2(w, h, title, desc):
    return head(w, h, title, desc)[:-1] + [MORE_ICONS, head(w, h, title, desc)[-1]]


def badge(o, cx, cy, n, r=14):
    o.append(f'<circle class="navy" cx="{cx}" cy="{cy}" r="{r}"/>')
    o.append(T(cx, cy + 5, str(n), "h", "middle", f' style="fill:#faf6ee;font-size:{15 if r < 16 else 17}px"'))


def gbadge(o, cx, cy, n, r=13):
    o.append(f'<circle class="giltf" cx="{cx}" cy="{cy}" r="{r}"/>')
    o.append(T(cx, cy + 5, str(n), "h", "middle", ' style="fill:#ffffff;font-size:15px"'))


def pill(o, x, y, w, label):
    o.append(f'<rect class="giltf" x="{x}" y="{y}" width="{w}" height="24" rx="12"/>')
    o.append(T(x + w / 2, y + 17, label, "cap", "middle", ' style="fill:#ffffff;font-size:12.5px"'))


# ---------------------------------------------------------------- 6. parts and flow
def parts_and_flow():
    W, H = 1200, 1010
    o = head2(W, H, "What you need, and how it fits together",
             "A kit of six parts: the picture frame, a small always-on computer or a Home Assistant box, the home router, "
             "a parent's phone, an optional Mac and cables. Below, six numbered steps show how information moves between them.")
    header(o, W, "What you need, and how it fits together",
           "A picture frame, one small computer that stays on, and your home Wi-Fi. The rest is optional.")

    o.append(T(40, 152, "THE KIT", "cap"))
    kit = [
        ("frame", "The picture frame", "NEEDED", ["A 10.1 inch Android frame, 1280 x 800.", "Tested: one cheap frame with an", "Allwinner A33 board (see Hardware)."]),
        ("pi", "The brain", "PICK ONE", ["A Raspberry Pi 4 or 5 (2 GB or more),", "its power supply, a microSD card or SSD.", "Or the Home Assistant box you have."]),
        ("router", "Home Wi-Fi router", "NEEDED", ["Your normal router. Best if it can make", "a separate Wi-Fi network for the frame", "and reserve a fixed address."]),
        ("phone", "A parent's phone", "NICE TO HAVE", ["Opens the /parent page in its browser", "to approve chores and add screen time.", "No app to install."]),
        ("mac", "A Mac", "OPTIONAL", ["Only for Apple Photos Favorites and", "Apple Reminders lists. It sends them", "to the brain on a schedule."]),
        ("cable", "Cables", "FOR SETUP", ["A USB data cable from a computer to the", "frame (USB-A to USB-C for some boards),", "and the frame's own power adapter."]),
    ]
    for i, (ic, title, tag, body) in enumerate(kit):
        x, y = 40 + (i % 3) * 387, 168 + (i // 3) * 188
        cls = "dcard" if tag == "OPTIONAL" else "card"
        o.append(rect(x, y, 346, 170, cls, 14))
        o.append(icon(ic, x + 18, y + 22, 48))
        o.append(T(x + 80, y + 44, title, "h"))
        o.append(T(x + 80, y + 68, tag, "cap"))
        o += lines(x + 20, y + 108, body, "s", 20)

    o.append(T(40, 584, "HOW INFORMATION FLOWS", "cap"))
    o.append(T(40, 608, "Follow the numbers. The frame only ever talks to the brain.", "s"))
    # nodes
    o.append(rect(40, 640, 240, 130))
    o.append(icon("cloud", 54, 652, 52))
    o.append(T(116, 686, "Online services", "h"))
    o += lines(60, 734, ["Calendars, weather,", "shared photo albums"], "s", 20)
    o.append(rect(340, 655, 130, 100))
    o.append(icon("router", 381, 660, 48))
    o.append(T(405, 736, "Router", "b", "middle"))
    o.append(rect(540, 630, 320, 150, "gcard", 14))
    o.append(icon("pi", 556, 646, 52))
    o.append(T(622, 670, "The brain", "h"))
    o.append(T(622, 692, "Pi or Home Assistant, port 8090", "s"))
    o += lines(560, 730, ["Fetches, crops photos, keeps", "chores and builds the page."], "b", 22)
    o.append(rect(920, 640, 240, 130))
    o.append(icon("frame", 934, 654, 52))
    o.append(T(998, 686, "Picture frame", "h"))
    o += lines(940, 734, ["Shows the page,", "sends taps back"], "s", 20)
    o.append(rect(920, 820, 240, 100))
    o.append(icon("phone", 932, 842, 52))
    o.append(T(992, 862, "Parent phone", "h"))
    o.append(T(992, 886, "the /parent page", "s"))
    o.append(rect(540, 830, 260, 90, "dcard"))
    o.append(icon("mac", 554, 850, 48))
    o.append(T(614, 870, "Mac (optional)", "h"))
    o.append(T(614, 892, "Photos and Reminders", "s"))
    # arrows
    o.append(arrow(286, 705, 334, 705, both=True))
    o.append(arrow(476, 705, 534, 705, both=True))
    gbadge(o, 505, 682, 1)
    gbadge(o, 838, 652, 2)
    o.append(arrow(866, 680, 914, 680))
    gbadge(o, 890, 660, 3)
    o.append(arrow(914, 735, 866, 735))
    gbadge(o, 890, 757, 4)
    o.append(path("M914 870H830V786", "ln"))
    gbadge(o, 872, 870, 5)
    o.append(arrow(670, 824, 670, 786))
    gbadge(o, 696, 806, 6)
    # legend
    steps = ["The brain reads calendars, weather and albums.",
             "It crops photos and builds the finished page.",
             "The frame asks the brain for the page every 30 s.",
             "A tap on the frame (I did it) goes to the brain.",
             "A parent approves it from a phone.",
             "A Mac can send Apple favorites and lists."]
    for i, s in enumerate(steps):
        gbadge(o, 54, 818 + i * 30, i + 1, 11)
        o.append(T(74, 823 + i * 30, s, "b"))
    save("parts-and-flow.svg", o)


# ---------------------------------------------------------------- 7. inspiration and takeover
def inspiration_and_takeover():
    W, H = 1200, 930
    o = head2(W, H, "Where it started, and how we took over our frame",
             "Credit to Wes Bos, whose repo and video show how to turn a 50 dollar picture frame into a home display, and the two "
             "board types it covers. Then seven steps we used to take over our frame, with a warning to stop if anything does not match.")
    header(o, W, "Where it started, and how we took over our frame",
           "Doorpost builds on Wes Bos's work. His repo is the guide for the frame itself.")

    o.append(rect(40, 140, 1120, 210, "gcard", 16))
    o.append(icon("code", 60, 166, 56))
    o.append(T(136, 174, "INSPIRED BY", "cap"))
    o.append(T(136, 204, "Wes Bos: $50 picture frame into a home display", "h", extra=' style="font-size:21px"'))
    o += lines(136, 240, ["Written for people and AI assistants to follow, step by step.",
                          "Repo: github.com/wesbos/photo-frame-dashboard",
                          "Video: youtube.com/watch?v=ZLycoUMltNI"], "b", 28)
    o.append(T(136, 330, "His rules: ask before every write, back up first, one change at a time.", "s"))
    o.append(T(724, 174, "TWO BOARD TYPES IN HIS REPO", "cap"))
    for i, (name, note) in enumerate([("Rockchip “BIUFRAME”", "ADB on out of the box; one setup script"),
                                      ("Allwinner A33 “PF1007L”", "Often in the same-looking frame now; more steps")]):
        y = 190 + i * 76
        o.append(rect(724, y, 416, 64, "soft", 10))
        o.append(icon("chip", 736, y + 12, 40))
        o.append(T(788, y + 28, name, "h", extra=' style="font-size:17px"'))
        o.append(T(788, y + 50, note, "s"))

    o.append(T(40, 396, "HOW WE TOOK OVER OUR FRAME (A PF1007L, ANDROID 6.0.1)", "cap"))
    o.append(T(40, 420, "Every write waited for an OK, one change at a time, with the undo written down first.", "s"))
    steps = [
        ("chip", "Identify the board", ["Settings > About: model and", "chip. Use a USB data cable", "(USB-A to USB-C on ours).", "Nothing is changed yet."]),
        ("download", "Back it up", ["Copy the frame's storage to", "a computer and check the", "copy before you change", "anything."]),
        ("shield", "Vendor apps off", ["Disable the maker's apps,", "including one that gives its", "server a root shell. Keep", "Wi-Fi off until then."]),
        ("sliders", "Update the web engine", ["Android System WebView", "44 to 106, so the page runs.", "Keep the old copy for", "undo."]),
        ("frame", "Install the kiosk", ["A launcher plus the Family", "Frame kiosk app as the", "Home screen. Turn system", "animations off."]),
        ("pi", "Point it at your server", ["Set the kiosk address to", "your server, for example", "http://192.168.1.50:8090/", "(a fixed address)."]),
        ("lock", "Lock the network", ["Join the frame's own Wi-Fi", "that reaches only the", "server on port 8090.", "Now it can go online."]),
    ]
    for i, (ic, title, body) in enumerate(steps):
        x, y = 40 + (i % 4) * 285, 440 + (i // 4) * 210
        o.append(rect(x, y, 265, 190, "card", 14))
        badge(o, x + 32, y + 34, i + 1, 18)
        o.append(icon(ic, x + 205, y + 14, 44))
        o.append(T(x + 20, y + 84, title, "h"))
        o += lines(x + 20, y + 112, body, "s", 20)
        if i % 4 != 3 and i < 6:
            o.append(arrow(x + 267, y + 95, x + 283, y + 95))
    x, y = 895, 650
    o.append(rect(x, y, 265, 190, "gcard", 14))
    o.append(icon("warn", x + 18, y + 16, 44))
    o += lines(x + 20, y + 84, ["Stop if anything", "doesn't match"], "h", 24)
    o += lines(x + 20, y + 140, ["A different model, chip, size", "or checksum means a different", "frame. Ask in his repo first."], "s", 20)
    o.append(T(40, 884, "Ours already had root ADB over USB. Many PF1007L frames don't, and need extra steps from his guide.", "s"))
    o.append(T(40, 906, "Brand names are not a hardware check: two frames that look the same can have different boards.", "s"))
    save("inspiration-and-takeover.svg", o)


# ---------------------------------------------------------------- 8. network setup
def network_setup():
    W, H = 1200, 1070
    o = head2(W, H, "Setting up your home network",
             "The router runs your home Wi-Fi, with the brain at a fixed address, and a separate frame Wi-Fi that can reach only "
             "the brain on port 8090. Four steps to set it up, a check, and three example prompts to ask an AI assistant.")
    header(o, W, "Setting up your home network",
           "Two router settings keep the frame useful and private. An AI assistant can walk you through yours.")

    o.append(rect(540, 132, 120, 86))
    o.append(icon("router", 576, 132, 48))
    o.append(T(600, 206, "Router", "b", "middle"))
    o.append(path("M560 218L470 250", "ln"))
    o.append(path("M640 218L730 250", "ln"))
    o.append(rect(40, 256, 520, 170, "zone", 18))
    o.append(T(64, 288, "Home Wi-Fi", "h"))
    o.append(T(64, 310, "phones, laptops, the brain", "s"))
    o.append(icon("phone", 66, 334, 48))
    o.append(icon("laptop", 126, 334, 48))
    o.append(T(66, 404, "everyday devices", "s"))
    o.append(rect(296, 290, 240, 112, "gcard", 12))
    o.append(icon("pi", 310, 306, 48))
    o.append(T(370, 328, "The brain", "h"))
    o.append(T(370, 352, "192.168.1.50", "b"))
    o.append(T(370, 374, "a fixed address", "s"))
    o.append(rect(640, 256, 520, 170, "zoneg", 18))
    o.append(T(664, 288, "Frame Wi-Fi", "h"))
    o.append(T(664, 310, "its own network (VLAN)", "s"))
    o.append(icon("frame", 672, 326, 70))
    o.append(f'<circle class="giltf" cx="776" cy="358" r="4"/>')
    o.append(T(790, 363, "Can reach: the brain, port 8090", "b"))
    o.append(f'<circle class="offf" cx="776" cy="392" r="4"/>')
    o.append(T(790, 397, "Blocked: internet, home Wi-Fi", "b"))
    o.append(arrow(668, 360, 542, 360, "lng", gilt=True))
    o.append(T(600, 346, "8090 only", "lbl", "middle"))

    steps = [
        ("pi", "Fix the brain's address", ["In the router, find the", "brain in the device list and", "reserve its address (a DHCP", "reservation). Then the frame's", "address for it never changes."]),
        ("router", "Make a frame Wi-Fi", ["A separate network for the", "frame: a VLAN, or a guest", "network that allows one", "exception. Give it its own", "name and password."]),
        ("lock", "Allow one door", ["Allow: frame network to", "192.168.1.50, TCP port 8090.", "Allow: DNS and DHCP.", "Block: everything else,", "the internet included."]),
        ("cloud", "Away from home", ["Optional. Reach /parent and", "/admin only through a tunnel", "with sign-in, such as", "Cloudflare Tunnel + Access.", "Never open port 8090 to all."]),
    ]
    for i, (ic, title, body) in enumerate(steps):
        x, y = 40 + i * 285, 460
        o.append(rect(x, y, 265, 226, "dcard" if i == 3 else "card", 14))
        badge(o, x + 32, y + 34, i + 1, 18)
        o.append(icon(ic, x + 205, y + 14, 44))
        o.append(T(x + 20, y + 84, title, "h"))
        o += lines(x + 20, y + 112, body, "s", 20)
    o.append(rect(40, 708, 1120, 50, "soft", 10))
    o.append(icon("check", 54, 716, 34))
    o.append(T(100, 739, "Check it: on the frame, http://192.168.1.50:8090/ loads, and any public website does not.", "b"))

    o.append(rect(40, 790, 1120, 250, "gcard", 16))
    o.append(icon("chat", 60, 812, 48))
    o.append(T(124, 832, "Ask your AI assistant", "h", extra=' style="font-size:21px"'))
    o.append(T(124, 856, "Tell it your router's brand and model, then follow its steps one screen at a time. Swap in your own address.", "s"))
    prompts = ["“My router is a ___. How do I make a separate Wi-Fi network that can only reach 192.168.1.50 port 8090?”",
               "“How do I give the computer called ___ a fixed address (a DHCP reservation) on my ___ router?”",
               "“How can I check that a device on my frame Wi-Fi reaches 192.168.1.50:8090 and nothing else?”"]
    for i, p in enumerate(prompts):
        y = 878 + i * 52
        o.append(rect(124, y, 1012, 42, "card", 21))
        o.append(T(146, y + 27, p, "b"))
    save("network-setup.svg", o)


# ---------------------------------------------------------------- 9. focal point
SCENE = """<defs>
<style>svg { --sky:#dde5ec; --hill:#c9d3ae; --hill2:#b4c08f; --skin:#f1dcc4; }
@media (prefers-color-scheme: dark) { svg { --sky:#2b3852; --hill:#3c4a3c; --hill2:#33402f; --skin:#d9c2a6; } }
.sky { fill: var(--sky); } .hill { fill: var(--hill); } .hill2 { fill: var(--hill2); } .skin { fill: var(--skin); }
.shade { fill: #000; opacity: 0.45; }
</style>
<filter id="soft" x="-5%" y="-5%" width="110%" height="110%"><feGaussianBlur stdDeviation="4"/></filter>
<symbol id="scene" viewBox="0 0 300 200" preserveAspectRatio="none">
<rect class="sky" x="0" y="0" width="300" height="200"/>
<circle class="giltf" cx="58" cy="46" r="17"/>
<path class="hill2" d="M0 130Q70 92 150 122T300 112V200H0z"/>
<path class="hill" d="M0 160Q90 128 180 150T300 146V200H0z"/>
<path class="navy" d="M34 150V112" style="stroke:var(--navy);stroke-width:4"/>
<circle class="hill2" cx="34" cy="100" r="17"/>
<circle class="skin" cx="200" cy="92" r="12"/>
<path class="navy" d="M184 150v-30a16 16 0 0 1 32 0v30z"/>
<circle class="skin" cx="234" cy="104" r="10"/>
<path class="giltf" d="M221 150v-22a13 13 0 0 1 26 0v22z"/>
</symbol>
</defs>"""


def view(x, y, w, h, vb, fit=False):
    """The scene as one frame shows it: vb is the crop (x, y, w, h in scene units), or fit=True for the whole photo."""
    if not fit:
        return [f'<svg x="{x}" y="{y}" width="{w}" height="{h}" viewBox="{vb[0]} {vb[1]} {vb[2]} {vb[3]}" preserveAspectRatio="xMidYMid slice">'
                f'<use href="#scene" x="0" y="0" width="300" height="200"/></svg>']
    out = [f'<svg x="{x}" y="{y}" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
           f'<g filter="url(#soft)"><svg x="0" y="0" width="{w}" height="{h}" viewBox="0 0 300 200" preserveAspectRatio="xMidYMid slice">'
           f'<use href="#scene" x="0" y="0" width="300" height="200"/></svg></g>',
           f'<rect class="shade" x="0" y="0" width="{w}" height="{h}"/>']
    s = min(w / 300, h / 200)
    fw, fh = 300 * s, 200 * s
    out.append(f'<use href="#scene" x="{(w - fw) / 2:.1f}" y="{(h - fh) / 2:.1f}" width="{fw:.1f}" height="{fh:.1f}"/>')
    out.append("</svg>")
    return out


def crop(shape, cx, cy):
    """Same math as app/photos.py crop_rect, for a 3:2 photo, in scene units."""
    fw, fh = {"wide": (1280, 800), "tall": (800, 1280)}[shape]
    r = 1.5
    cw, ch = ((fw / fh) / r, 1.0) if r > fw / fh else (1.0, r / (fw / fh))
    left = min(max(cx - cw / 2, 0.0), 1.0 - cw)
    top = min(max(cy - ch / 2, 0.0), 1.0 - ch)
    return (round(left * 300, 1), round(top * 200, 1), round(cw * 300, 1), round(ch * 200, 1))


def focal_point():
    W, H = 1200, 1032
    o = head2(W, H, "Focal points: keep the important part in view",
             "In Settings > Photos you tap the important spot in a photo. A gold box shows what wide frames keep and a white box "
             "what tall frames keep, with live previews. Below, the same photo with nothing set, with a focal point, and shown whole.")
    o.append(SCENE)
    header(o, W, "Focal points: keep the important part in view",
           "Wide and tall frames cut off different parts of a photo. Tap what matters once; every frame crops around it.")

    o.append(T(40, 152, "IN SETTINGS > PHOTOS", "cap"))
    o.append(rect(40, 166, 1120, 424, "card", 14))
    bx = 64
    for label, w, on in [("Focal point", 124, True), ("Wide crop", 110, False), ("Tall crop", 104, False)]:
        if on:
            o.append(f'<rect class="navy" x="{bx}" y="184" width="{w}" height="32" rx="16"/>')
            o.append(T(bx + w / 2, 205, label, "b", "middle", ' style="fill:#faf6ee;font-weight:700"'))
        else:
            o.append(f'<rect class="soft" x="{bx}" y="184" width="{w}" height="32" rx="16"/>')
            o.append(T(bx + w / 2, 205, label, "b", "middle"))
        bx += w + 10
    px, py, pw, ph = 64, 228, 510, 340
    fx, fy = 0.71, 0.5
    o += view(px, py, pw, ph, (0, 0, 300, 200))
    wv, tv = crop("wide", fx, fy), crop("tall", fx, fy)
    k = pw / 300
    o.append(f'<rect x="{px + wv[0] * k:.1f}" y="{py + wv[1] * k:.1f}" width="{wv[2] * k:.1f}" height="{wv[3] * k:.1f}" '
             'style="fill:none;stroke:#C9A55A;stroke-width:4"/>')
    o.append(f'<rect x="{px + tv[0] * k:.1f}" y="{py + tv[1] * k:.1f}" width="{tv[2] * k:.1f}" height="{tv[3] * k:.1f}" '
             'style="fill:none;stroke:#ffffff;stroke-width:3;stroke-dasharray:10 6"/>')
    cx, cy = px + fx * pw, py + fy * ph
    o.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="16" style="fill:none;stroke:#ffffff;stroke-width:3"/>')
    o.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="5" style="fill:#C9A55A;stroke:#ffffff;stroke-width:2"/>')

    o.append(T(604, 248, "WIDE FRAME", "cap"))
    o += view(604, 260, 256, 160, wv)
    o.append(f'<rect x="604" y="260" width="256" height="160" rx="4" style="fill:none;stroke:#C9A55A;stroke-width:3"/>')
    o.append(T(890, 248, "TALL FRAME", "cap"))
    o += view(890, 260, 100, 160, tv)
    o.append(f'<rect x="890" y="260" width="100" height="160" rx="4" style="fill:none;stroke:var(--muted);stroke-width:2;stroke-dasharray:8 5"/>')
    o.append(T(604, 444, "Following the faces Apple Photos found", "s"))
    for i, s in enumerate(["Tap a photo in Settings > Photos.",
                           "Tap or drag to the spot that matters.",
                           "Watch the wide and tall previews move.",
                           "Save. Frames pick it up within a minute."]):
        gbadge(o, 616, 474 + i * 26, i + 1, 10)
        o.append(T(636, 479 + i * 26, s, "b"))

    o.append(T(40, 634, "WHAT IT CHANGES ON EACH FRAME", "cap"))
    cards = [
        ("Nothing set", crop("wide", 0.5, 0.4), crop("tall", 0.5, 0.4), False,
         ["Crops around a spot a little", "above the middle. Tall frames", "can cut people off."]),
        ("Focal point set", wv, tv, False,
         ["Both crops center on the spot", "you tapped. Wide crop and Tall", "crop can each be moved alone."]),
        ("Show the whole photo", None, None, True,
         ["Chosen per shape. The whole", "photo sits on a soft, darker,", "blurred copy. Nothing is cut."]),
    ]
    for i, (title, wvb, tvb, fit, body) in enumerate(cards):
        x, y = 40 + i * 380, 650
        o.append(rect(x, y, 360, 276, "gcard" if i == 1 else "card", 14))
        o.append(T(x + 20, y + 36, title, "h"))
        o += view(x + 20, y + 54, 192, 120, wvb, fit)
        o += view(x + 250, y + 54, 75, 120, tvb, fit)
        o.append(T(x + 116, y + 196, "wide", "s", "middle"))
        o.append(T(x + 287, y + 196, "tall", "s", "middle"))
        o += lines(x + 20, y + 226, body, "s", 20)
    o.append(rect(40, 950, 1120, 58, "soft", 10))
    o.append(icon("target", 54, 959, 40))
    o.append(T(106, 974, "Which spot a crop follows: a crop you moved by hand, then your focal point, then the faces", "s"))
    o.append(T(106, 994, "Apple Photos found (sent by the Mac), then a bit above the middle. Photos are cropped on the brain, not the frame.", "s"))
    save("focal-point.svg", o)


# ---------------------------------------------------------------- 10. screen sizes
def screen(o, x, y, w, h):
    b = max(3, round(min(w, h) * 0.06))
    o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{max(3, b)}" style="fill:var(--icon)"/>')
    o.append(f'<rect class="card" x="{x + b}" y="{y + b}" width="{w - 2 * b}" height="{h - 2 * b}" rx="2" style="stroke-width:1"/>')
    return b


def screen_sizes():
    W, H = 1200, 1150
    o = head2(W, H, "Screen sizes and which way up",
             "How Doorpost picks a wide or tall layout, then four screen sizes drawn to scale: 7 inch, 10.1 inch (the tested size), "
             "13 to 15.6 inch and 21.5 inch and up, each with resolution, viewing distance, the layout it gets and a caution.")
    header(o, W, "Screen sizes and which way up",
           "Doorpost lays out at 800 px on the short side, then scales to fit. Size decides how far away you can read it.")

    o.append(T(40, 152, "WIDE OR TALL: HOW IT CHOOSES", "cap"))
    o.append(rect(40, 168, 540, 226))
    b = screen(o, 64, 200, 200, 125)
    o.append(f'<rect class="giltf" x="{64 + b + 8}" y="{200 + b + 8}" width="60" height="10" rx="2"/>')
    o.append(f'<rect class="offf" x="{64 + b + 8}" y="{200 + b + 26}" width="{200 - 2 * b - 16}" height="54" rx="3"/>')
    o.append(T(290, 216, "Wide", "h"))
    o += lines(290, 242, ["The screen is wider than tall.", "Lays out 1200 to 1440 x 800,", "then scales to fill it."], "s", 20)
    o.append(T(290, 318, "16:10 screen: 1280 x 800", "s"))
    o.append(T(290, 338, "16:9 screen: 1422 x 800", "s"))
    o.append(T(290, 358, "4:3 screen: 1200 x 800, with bands", "s"))
    o.append(T(64, 360, "Most frames, hung landscape", "s"))
    o.append(rect(620, 168, 540, 226))
    b = screen(o, 650, 190, 96, 154)
    o.append(f'<rect class="giltf" x="{650 + b + 6}" y="{190 + b + 8}" width="40" height="10" rx="2"/>')
    o.append(f'<rect class="offf" x="{650 + b + 6}" y="{190 + b + 26}" width="{96 - 2 * b - 12}" height="90" rx="3"/>')
    o.append(T(780, 216, "Tall", "h"))
    o += lines(780, 242, ["Taller than wide by 5% or more.", "Lays out 800 x 1200 to 1440 and", "adds the body class vert.", "Force one with ?layout=tall", "or ?layout=wide in the address."], "s", 20)
    o.append(T(650, 370, "On its side, or a portrait panel", "s"))
    o.append(T(1136, 370, "720 x 1280 screen: 800 x 1422", "s", "end"))
    o.append(rect(40, 410, 1120, 50, "soft", 10))
    o.append(icon("frame", 54, 416, 38))
    o.append(T(104, 441, "Turn it on its side and every screen lays itself out again. Screens 1700 px or more across get HD photos.", "b"))

    o.append(T(40, 504, "FOUR SIZES, DRAWN TO SCALE", "cap"))
    o.append(T(40, 526, "Distances are rough guides for reading the calendar, not rules.", "s"))
    PPI = 9
    rows = [
        ("7 inch", "small frames, Pi Touch Display 2", None, (6.0, 3.6), "1024 x 600", "or 720 x 1280 (tall)", "1 to 3 ft", "Wide, scaled down", "tall if hung upright",
         "warn", "Untested. Text gets small: fine on a desk or nightstand, hard to read across a kitchen."),
        ("10.1 inch", "the tested frame", "TESTED", (8.56, 5.35), "1280 x 800", "16:10, 1 GB RAM", "2 to 6 ft", "Wide, exactly 1 to 1", "or tall on its side",
         "check", "Runs every day. Still check the board and Android version before you buy (see Hardware)."),
        ("13 to 15.6 inch", "larger frames", None, (13.6, 7.65), "1920 x 1080", "16:9, gets HD photos", "4 to 10 ft", "Wide, scaled up", "1422 x 800 layout",
         "warn", "Untested. Boards and Android versions vary more. Make sure the web engine can be updated."),
        ("21.5 inch and up", "big frames, monitors, TVs", None, (18.7, 10.5), "1920 x 1080+", "4K scales fine", "6 to 15 ft", "Wide, scaled up", "a mini PC is simpler",
         "warn", "Untested. Draws more power and shows burn-in sooner. Use night mode or a timer."),
    ]
    for i, (size, sub, tag, (wi, hi), res, res2, dist, lay, lay2, ci, caution) in enumerate(rows):
        y = 542 + i * 132
        o.append(rect(40, y, 1120, 120, "gcard" if tag else "card", 12))
        w, h = round(wi * PPI), round(hi * PPI)
        screen(o, 146 - w // 2, y + 56 - h // 2, w, h)
        o.append(T(260, y + 40, size, "h"))
        if tag:
            pill(o, 360, y + 23, 80, tag)
        o.append(T(260, y + 62, sub, "s"))
        for x, cap, v1, v2 in [(520, "RESOLUTION", res, res2), (720, "READ FROM", dist, None), (880, "LAYOUT", lay, lay2)]:
            o.append(T(x, y + 30, cap, "cap"))
            o.append(T(x, y + 54, v1, "b"))
            if v2:
                o.append(T(x, y + 74, v2, "s"))
        o.append(icon(ci, 258, y + 87, 22))
        o.append(T(286, y + 103, caution, "s"))
    o.append(rect(40, 1078, 1120, 50, "soft", 10))
    o.append(icon("warn", 54, 1085, 34))
    o.append(T(100, 1108, "A caution mark means untested. Read docs/screens.md before you buy a screen.", "b"))
    save("screen-sizes.svg", o)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    how_it_works()
    network()
    modules()
    setup_paths()
    day()
    parts_and_flow()
    inspiration_and_takeover()
    network_setup()
    focal_point()
    screen_sizes()
    print("wrote", OUT)


if __name__ == "__main__":
    main()
