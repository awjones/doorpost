"""More special-day drawings: family milestones, kids' activities, Scouts, church life, seasons, outings and visitors.
Same canvas as app/scenes.py: portrait viewBox 0 0 300 600, art in y 150-430, the middle (x 70-230) survives the
narrow week-view crop. The birthday picture has placeholders the frame fills in: {{NAME}} / {{NAME_SIZE}} for the
banner and {{PORTRAIT}} for the person's photo in the round window (app/portraits.py)."""
import math

from .scenes import C, G, R, burst, heart, star5, stars_sky, svg, SKY

NAVY, CREAM, GREEN, DKGREEN, BLUE, ORANGE, BROWN = "#16324F", "#F3EBDA", "#4E8A4A", "#2F5A3E", "#2E8FB8", "#D9822B", "#7A4A26"


def sky(gid, top, bottom):
    return (f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{top}"></stop>'
            f'<stop offset="1" stop-color="{bottom}"></stop></linearGradient></defs><rect width="300" height="600" fill="url(#{gid})"></rect>')


def ground(y, col, curve=14):
    return f'<path d="M0 {y} Q150 {y - curve} 300 {y} V600 H0Z" fill="{col}"></path>'


def pine(x, base, h, col=DKGREEN, w=None):
    w = w or h * 0.32
    return (f'<path d="M{x} {base - h} L{x - w * 0.6} {base - h * 0.55} H{x - w * 0.3} L{x - w} {base - h * 0.12} H{x + w} '
            f'L{x + w * 0.3} {base - h * 0.55} H{x + w * 0.6}Z" fill="{col}"></path><rect x="{x - 3}" y="{base - h * 0.12}" width="6" height="{h * 0.12 + 2:.0f}" fill="#4A3524"></rect>')


def cloud(x, y, s=1.0, col="#FFFFFF", op=0.9):
    return (f'<g transform="translate({x} {y}) scale({s})" fill="{col}" opacity="{op}"><ellipse cx="0" cy="0" rx="30" ry="12"></ellipse>'
            f'<ellipse cx="18" cy="-8" rx="18" ry="12"></ellipse><ellipse cx="-16" cy="-5" rx="14" ry="10"></ellipse></g>')


def sun(x, y, r, col=G, rays=True):
    return (burst(x, y, r * 1.9, col, 16, 2) if rays else "") + f'<circle cx="{x}" cy="{y}" r="{r}" fill="{col}"></circle>'


def balloon(x, y, col, s=1.0):
    return (f'<g transform="translate({x} {y}) scale({s})"><path d="M0 44 q-6 30 4 56" stroke="{CREAM}" stroke-width="1.2" fill="none" opacity="0.7"></path>'
            f'<ellipse cx="0" cy="0" rx="20" ry="25" fill="{col}"></ellipse><path d="M-3 24 h6 l-3 6z" fill="{col}"></path>'
            f'<ellipse cx="-7" cy="-9" rx="5" ry="8" fill="#FFFFFF" opacity="0.35"></ellipse></g>')


def bunting(y0, sag, cols, x0=0, x1=300, n=11):
    out = [f'<path d="M{x0} {y0} Q{(x0 + x1) / 2} {y0 + sag * 2} {x1} {y0}" stroke="{CREAM}" stroke-width="1.5" fill="none"></path>']
    for i in range(n):
        t = (i + 0.5) / n
        x = x0 + (x1 - x0) * t
        y = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * (y0 + sag * 2) + t * t * y0
        out.append(f'<path d="M{x - 8:.1f} {y:.1f} L{x + 8:.1f} {y:.1f} L{x:.1f} {y + 16:.1f}Z" fill="{cols[i % len(cols)]}"></path>')
    return "".join(out)


def string_lights(y0, sag, x0=0, x1=300, n=14, cols=(G, "#F6E3B0", "#E5484D", "#7FC8E8")):
    out = [f'<path d="M{x0} {y0} Q{(x0 + x1) / 2} {y0 + sag * 2} {x1} {y0}" stroke="#2A2A2E" stroke-width="1.4" fill="none"></path>']
    for i in range(n):
        t = (i + 0.5) / n
        x = x0 + (x1 - x0) * t
        y = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * (y0 + sag * 2) + t * t * y0
        c = cols[i % len(cols)]
        out.append(f'<circle cx="{x:.1f}" cy="{y + 5:.1f}" r="7" fill="{c}" opacity="0.25"></circle><ellipse cx="{x:.1f}" cy="{y + 5:.1f}" rx="2.6" ry="3.6" fill="{c}"></ellipse>')
    return "".join(out)


def person(x, base, s=1.0, shirt=R, skin="#E8B48A", hair="#5A3A22"):
    return (f'<g transform="translate({x} {base}) scale({s})"><rect x="-9" y="-46" width="18" height="30" rx="7" fill="{shirt}"></rect>'
            f'<rect x="-8" y="-18" width="7" height="18" fill="#2F3E56"></rect><rect x="1" y="-18" width="7" height="18" fill="#2F3E56"></rect>'
            f'<circle cx="0" cy="-56" r="10" fill="{skin}"></circle><path d="M-10 -58 q10 -14 20 0 q-4 -6 -10 -6 q-6 0 -10 6z" fill="{hair}"></path></g>')


# ---------------- family milestones ----------------

def birthday():
    """The person's photo in a round gilt frame with their name on the banner; a cake below and balloons around."""
    cx, cy, rx, ry = 150, 264, 74, 74
    candles = "".join(f'<rect x="{x - 2.5}" y="352" width="5" height="18" rx="1" fill="{c}"></rect>'
                      f'<path d="M{x} 340 q5 7 0 11 q-5 -4 0 -11z" fill="#F6C24A"></path>' for x, c in [(124, C), (138, "#7FC8E8"), (150, C), (162, "#E8A3B5"), (176, C)])
    cake = (f'<rect x="96" y="370" width="108" height="30" rx="5" fill="#F3D6DF"></rect><rect x="96" y="370" width="108" height="9" rx="4" fill="#FFFFFF"></rect>'
            + "".join(f'<path d="M{x} 378 q5 9 10 0" fill="#FFFFFF"></path>' for x in range(96, 204, 10))
            + f'<rect x="84" y="398" width="132" height="34" rx="6" fill="#E8A3B5"></rect><rect x="84" y="398" width="132" height="10" rx="5" fill="#FFFFFF"></rect>'
            + "".join(f'<path d="M{x} 407 q5 9 10 0" fill="#FFFFFF"></path>' for x in range(84, 216, 11))
            + "".join(f'<circle cx="{x}" cy="{y}" r="2.6" fill="{c}"></circle>' for x, y, c in [(104, 388, R), (130, 390, BLUE), (172, 388, G), (196, 390, R), (100, 420, BLUE), (140, 422, G), (180, 420, R), (206, 422, BLUE)])
            + f'<ellipse cx="150" cy="434" rx="80" ry="7" fill="#C9A55A"></ellipse>')
    window = (f'<defs><clipPath id="bdwin"><ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}"></ellipse></clipPath></defs>'
              f'<ellipse cx="{cx}" cy="{cy}" rx="{rx + 9}" ry="{ry + 9}" fill="{G}"></ellipse>'
              f'<ellipse cx="{cx}" cy="{cy}" rx="{rx + 4}" ry="{ry + 4}" fill="#8C7A4E"></ellipse>'
              # no portrait yet: a small gift waits in the window (the photo covers it)
              f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="#24406B"></ellipse>'
              f'<rect x="126" y="250" width="48" height="40" rx="3" fill="{R}"></rect><rect x="122" y="240" width="56" height="12" rx="3" fill="#E5484D"></rect>'
              f'<rect x="146" y="240" width="8" height="50" fill="{G}"></rect><path d="M150 240 q-16 -18 -20 -4 q4 6 20 4 q16 2 20 -4 q-4 -14 -20 4z" fill="{G}"></path>'
              f'<g clip-path="url(#bdwin)">{{{{PORTRAIT}}}}</g>'
              + "".join(f'<circle cx="{cx + (rx + 6.5) * math.cos(math.radians(a)):.1f}" cy="{cy + (ry + 6.5) * math.sin(math.radians(a)):.1f}" r="1.6" fill="#FFF3C4"></circle>' for a in range(0, 360, 15)))
    banner = (f'<path d="M58 176 L70 168 L70 196 L58 188 L46 196 L52 182Z" fill="#9E0E25"></path><path d="M242 176 L230 168 L230 196 L242 188 L254 196 L248 182Z" fill="#9E0E25"></path>'
              f'<path d="M66 164 Q150 150 234 164 L234 194 Q150 180 66 194Z" fill="{R}"></path>'
              f'<text x="150" y="184" text-anchor="middle" font-family="Playfair Display, Georgia, serif" font-weight="700" font-size="{{{{NAME_SIZE}}}}" fill="{CREAM}">{{{{NAME}}}}</text>')
    confetti = "".join(f'<rect x="{x}" y="{y}" width="5" height="9" rx="1" transform="rotate({r} {x} {y})" fill="{c}"></rect>'
                       for x, y, r, c in [(40, 230, 20, G), (262, 226, -30, "#7FC8E8"), (28, 320, 50, "#E8A3B5"), (272, 318, 10, G), (52, 380, -20, "#7FC8E8"), (250, 372, 35, "#E8A3B5"), (110, 214, 70, C), (196, 212, -60, C)])
    return svg(f'''{stars_sky(SKY[:9], G)}{balloon(42, 270, R, 0.9)}{balloon(262, 262, BLUE, 0.9)}{balloon(28, 196, G, 0.7)}{balloon(274, 190, "#E8A3B5", 0.7)}
{confetti}{window}{banner}<rect y="432" width="300" height="168" fill="#24406B"></rect>{candles}{cake}''', NAVY)


def anniversary():
    rings = (f'<circle cx="132" cy="276" r="40" fill="none" stroke="{G}" stroke-width="11"></circle>'
             f'<circle cx="168" cy="276" r="40" fill="none" stroke="#E2C27A" stroke-width="11"></circle>'
             f'<path d="M151 243 A40 40 0 0 1 166 238" stroke="{G}" stroke-width="11" fill="none"></path>'
             f'<path d="M135 237 a40 40 0 0 1 4 0" stroke="#FFF3C4" stroke-width="3" fill="none"></path>'
             f'<path d="M150 230 l8 -10 l8 10 l-8 8z" fill="#DDEFF8" stroke="#FFFFFF" stroke-width="1"></path>')
    def rose(x, y, s):
        return (f'<g transform="translate({x} {y}) scale({s})"><path d="M0 0 q-4 40 2 70" stroke="{DKGREEN}" stroke-width="3" fill="none"></path>'
                f'<path d="M1 40 q14 -10 20 -2 q-10 8 -20 2z" fill="{GREEN}"></path><circle cx="0" cy="0" r="14" fill="#B3263A"></circle>'
                f'<path d="M-8 -2 q8 -12 16 0 q-8 6 -16 0z M-4 4 q4 -6 8 0" stroke="#7A1426" stroke-width="1.6" fill="none"></path></g>')
    return svg(f'''{heart(150, 196, 1.3, "#E8A3B5")}{heart(72, 230, 0.8, "#B3263A")}{heart(232, 234, 0.8, "#B3263A")}
{burst(150, 276, 110, G, 24, 1)}{rings}{rose(104, 360, 1)}{rose(150, 350, 1.1)}{rose(196, 360, 1)}
<rect y="420" width="300" height="180" fill="#3A0F1C"></rect>''', "#5A1A2C")


def first_day():
    chalk = (f'<rect x="40" y="168" width="220" height="130" rx="6" fill="#3E2A1A"></rect><rect x="48" y="176" width="204" height="114" fill="#2F4F3E"></rect>'
             f'<text x="150" y="226" text-anchor="middle" font-family="Georgia, serif" font-size="30" fill="{CREAM}" opacity="0.9">ABC</text>'
             f'<text x="150" y="268" text-anchor="middle" font-family="Georgia, serif" font-size="26" fill="{CREAM}" opacity="0.75">1 + 2 = 3</text>'
             f'<rect x="60" y="292" width="40" height="5" fill="#DDD"></rect>')
    books = (f'<rect x="80" y="388" width="140" height="22" rx="3" fill="#24406B"></rect><rect x="84" y="392" width="132" height="4" fill="{CREAM}"></rect>'
             f'<rect x="92" y="366" width="118" height="22" rx="3" fill="{R}"></rect><rect x="96" y="370" width="110" height="4" fill="{CREAM}"></rect>'
             f'<rect x="86" y="344" width="126" height="22" rx="3" fill="{GREEN}"></rect><rect x="90" y="348" width="118" height="4" fill="{CREAM}"></rect>')
    apple = (f'<path d="M150 344 C124 344 120 312 132 302 C140 296 148 300 150 302 C152 300 160 296 168 302 C180 312 176 344 150 344Z" fill="#D32F2F"></path>'
             f'<path d="M150 302 q2 -12 8 -16" stroke="#5A3A22" stroke-width="3" fill="none"></path><path d="M154 296 q12 -12 22 -4 q-10 10 -22 4z" fill="{GREEN}"></path>'
             f'<ellipse cx="138" cy="314" rx="4" ry="8" fill="#FFFFFF" opacity="0.35"></ellipse>')
    pencil = (f'<g transform="rotate(-18 230 380)"><rect x="196" y="374" width="70" height="10" fill="#F2C230"></rect><rect x="190" y="374" width="8" height="10" fill="#E8A3B5"></rect>'
              f'<path d="M266 374 L280 379 L266 384Z" fill="#E8C9A0"></path><path d="M276 377.5 L280 379 L276 380.5Z" fill="#333"></path></g>')
    return svg(f'''{chalk}<rect y="410" width="300" height="190" fill="#8B5A2B"></rect><path d="M0 410 H300" stroke="#5C3A22" stroke-width="3"></path>
{books}{apple}{pencil}''', "#E9DCC0")


def graduation():
    cap = (f'<path d="M150 214 L250 250 L150 286 L50 250Z" fill="#1F1B16"></path><path d="M150 222 L232 250 L150 278 L68 250Z" fill="#2A2A2E"></path>'
           f'<path d="M100 268 V306 Q150 334 200 306 V268 L150 286Z" fill="#1F1B16"></path>'
           f'<circle cx="150" cy="250" r="5" fill="{G}"></circle><path d="M150 250 Q206 262 214 300" stroke="{G}" stroke-width="3" fill="none"></path>'
           f'<path d="M209 298 h10 l4 34 h-18z" fill="{G}"></path>')
    diploma = (f'<g transform="rotate(-12 150 384)"><rect x="70" y="370" width="160" height="28" rx="14" fill="{CREAM}"></rect>'
               f'<ellipse cx="70" cy="384" rx="8" ry="14" fill="#E2D8C3"></ellipse><ellipse cx="230" cy="384" rx="8" ry="14" fill="#E2D8C3"></ellipse>'
               f'<rect x="140" y="368" width="20" height="32" fill="{R}"></rect><path d="M144 398 l-8 20 l10 -6 l4 8 z M156 398 l8 20 l-10 -6 l-4 8z" fill="{R}"></path></g>')
    confetti = "".join(f'<rect x="{x}" y="{y}" width="5" height="10" rx="1" transform="rotate({r} {x} {y})" fill="{c}"></rect>'
                       for x, y, r, c in [(50, 180, 20, G), (240, 176, -30, C), (36, 310, 50, G), (264, 320, 10, C), (90, 170, 70, C), (210, 340, -60, G), (60, 360, -10, C), (250, 400, 40, G)])
    return svg(f'''{burst(150, 260, 120, G, 20, 1)}{confetti}{cap}{diploma}<rect y="432" width="300" height="168" fill="#0E1D2B"></rect>''', "#1E3B5E")


# ---------------- kids' activities ----------------

def baseball():
    lights = "".join(f'<rect x="{x}" y="170" width="4" height="200" fill="#5E6B73"></rect><rect x="{x - 16}" y="160" width="36" height="16" rx="2" fill="#3A4652"></rect>'
                     + "".join(f'<circle cx="{x - 10 + i * 8}" cy="168" r="3" fill="#FFF8D6"></circle>' for i in range(4))
                     + f'<path d="M{x + 2} 176 L{x - 60} 420 H{x + 64}Z" fill="#FFF8D6" opacity="0.06"></path>' for x in (40, 260))
    field = (f'<rect y="330" width="300" height="270" fill="#3F7A3A"></rect>'
             + "".join(f'<rect x="{i * 40}" y="330" width="20" height="270" fill="#46843F"></rect>' for i in range(8))
             + f'<path d="M150 360 L230 420 L150 480 L70 420Z" fill="#B97A45"></path><path d="M150 378 L206 420 L150 462 L94 420Z" fill="#3F7A3A"></path>'
             f'<circle cx="150" cy="420" r="9" fill="#B97A45"></circle>'
             + "".join(f'<rect x="{x - 5}" y="{y - 5}" width="10" height="10" fill="#FFFFFF" transform="rotate(45 {x} {y})"></rect>' for x, y in [(150, 364), (228, 420), (72, 420)])
             + f'<path d="M150 478 l6 4 v6 h-12 v-6z" fill="#FFFFFF"></path>')
    ball = (f'<circle cx="150" cy="250" r="34" fill="#FAFAF5"></circle><path d="M126 226 q14 24 0 48 M174 226 q-14 24 0 48" stroke="#C8102E" stroke-width="2.4" fill="none"></path>'
            + "".join(f'<path d="M{128 + 6 * (abs(dy) / 20)} {250 + dy} l6 -3 M{172 - 6 * (abs(dy) / 20)} {250 + dy} l-6 -3" stroke="#C8102E" stroke-width="1.6"></path>' for dy in range(-18, 20, 6)))
    bat = f'<g transform="rotate(-38 150 300)"><path d="M70 296 H190 Q222 292 236 300 Q222 308 190 304 H70Z" fill="#C89A5E"></path><rect x="64" y="294" width="8" height="12" rx="2" fill="#7A5A3A"></rect></g>'
    return svg(f'''{stars_sky(SKY, C)}{lights}{field}{bat}{ball}''', "#0E1D2B")


def soccer():
    goal = (f'<path d="M48 250 H252 V372 H48Z" fill="none" stroke="#FFFFFF" stroke-width="6"></path>'
            + "".join(f'<path d="M{x} 254 V370" stroke="#FFFFFF" stroke-width="1" opacity="0.5"></path>' for x in range(60, 252, 12))
            + "".join(f'<path d="M50 {y} H250" stroke="#FFFFFF" stroke-width="1" opacity="0.5"></path>' for y in range(262, 372, 12)))
    def ball(x, y, r):
        pent = lambda cx, cy, rr: " ".join(f"{cx + rr * math.cos(math.radians(-90 + 72 * i)):.1f},{cy + rr * math.sin(math.radians(-90 + 72 * i)):.1f}" for i in range(5))
        return (f'<circle cx="{x}" cy="{y}" r="{r}" fill="#FFFFFF" stroke="#1F1B16" stroke-width="2"></circle><polygon points="{pent(x, y, r * 0.36)}" fill="#1F1B16"></polygon>'
                + "".join(f'<path d="M{x + r * 0.36 * math.cos(math.radians(-90 + 72 * i)):.1f} {y + r * 0.36 * math.sin(math.radians(-90 + 72 * i)):.1f} L{x + r * 0.78 * math.cos(math.radians(-90 + 72 * i)):.1f} {y + r * 0.78 * math.sin(math.radians(-90 + 72 * i)):.1f}" stroke="#1F1B16" stroke-width="2"></path>'
                          f'<polygon points="{pent(x + r * 0.9 * math.cos(math.radians(-90 + 72 * i)), y + r * 0.9 * math.sin(math.radians(-90 + 72 * i)), r * 0.22)}" fill="#1F1B16"></polygon>' for i in range(5)))
    return svg(f'''{sky("socsky", "#5E9AC6", "#CFE6F2")}{cloud(70, 190, 1.0)}{cloud(236, 214, 0.8)}{sun(240, 160, 16, "#F6C24A", False)}
<rect y="372" width="300" height="228" fill="#4E9A43"></rect>{"".join(f'<rect y="{372 + i * 36}" width="300" height="18" fill="#58A64C"></rect>' for i in range(7))}
<path d="M0 470 Q150 440 300 470" stroke="#FFFFFF" stroke-width="3" fill="none" opacity="0.8"></path>{goal}{ball(150, 418, 26)}''', "#5E9AC6")


def football():
    posts = f'<path d="M150 410 V316 M110 316 H190 M110 316 V200 M190 316 V200" stroke="#F2C230" stroke-width="7" stroke-linecap="round" fill="none"></path>'
    ball = (f'<g transform="rotate(-25 150 386)"><ellipse cx="150" cy="386" rx="46" ry="26" fill="#8B4A22"></ellipse>'
            f'<path d="M112 380 q38 -10 76 0 M112 392 q38 10 76 0" stroke="#FFFFFF" stroke-width="2" fill="none" opacity="0.8"></path>'
            f'<path d="M132 386 H168" stroke="#FFFFFF" stroke-width="3"></path>'
            + "".join(f'<path d="M{x} 380 V392" stroke="#FFFFFF" stroke-width="2.4"></path>' for x in range(136, 168, 6)) + '</g>')
    lines = "".join(f'<path d="M0 {y} H300" stroke="#FFFFFF" stroke-width="2.5" opacity="0.8"></path>' for y in (430, 470, 520, 580))
    return svg(f'''{sky("fbsky", "#1B2E4A", "#C98A4A")}{stars_sky(SKY[:6], C)}<circle cx="70" cy="190" r="22" fill="{G}" opacity="0.6"></circle>
<rect y="410" width="300" height="190" fill="#3F7A3A"></rect>{lines}{posts}{ball}''', "#1B2E4A")


def recital():
    curtains = (f'<path d="M0 150 H300 V186 Q150 210 0 186Z" fill="#8E1B2C"></path>'
                f'<path d="M0 150 H54 Q46 300 70 430 H0Z" fill="#A8243A"></path><path d="M300 150 H246 Q254 300 230 430 H300Z" fill="#A8243A"></path>'
                + "".join(f'<path d="M{x} 160 Q{x - 4} 300 {x + 8} 430" stroke="#7A1426" stroke-width="2" fill="none"></path>' for x in (14, 30, 270, 286)))
    spot = f'<path d="M120 150 L60 410 H240 L180 150Z" fill="#FFF8D6" opacity="0.12"></path><ellipse cx="150" cy="412" rx="92" ry="12" fill="#FFF8D6" opacity="0.22"></ellipse>'
    piano = (f'<path d="M82 324 H200 C236 324 238 352 214 360 C204 364 204 380 196 384 H82Z" fill="#141414"></path>'
             f'<path d="M86 320 L120 248 L124 250 L94 322Z" fill="#141414"></path>'
             f'<rect x="78" y="340" width="34" height="8" fill="#FFFFFF"></rect>' + "".join(f'<rect x="{x}" y="340" width="2" height="5" fill="#141414"></rect>' for x in range(81, 112, 4))
             + f'<path d="M92 384 V410 M188 384 V410 M140 384 V410" stroke="#141414" stroke-width="5"></path>'
             f'<rect x="60" y="374" width="22" height="6" fill="#141414"></rect><path d="M64 380 V410 M78 380 V410" stroke="#141414" stroke-width="3"></path>')
    notes = "".join(f'<g transform="translate({x} {y}) scale({s})" fill="{G}"><ellipse cx="0" cy="0" rx="7" ry="5" transform="rotate(-20)"></ellipse><path d="M6 -2 V-28 l12 4" stroke="{G}" stroke-width="2.4" fill="none"></path></g>'
                    for x, y, s in [(170, 238, 1.0), (206, 214, 0.8), (144, 206, 0.7)])
    return svg(f'''{spot}{curtains}{notes}{piano}<rect y="410" width="300" height="190" fill="#5C3A22"></rect><path d="M0 410 H300" stroke="#8B5A2B" stroke-width="4"></path>''', "#121826")


def school_play():
    curtains = (f'<path d="M0 150 H300 V190 Q150 214 0 190Z" fill="#24406B"></path>'
                f'<path d="M0 150 H70 Q40 260 86 330 Q40 380 52 430 H0Z" fill="{R}"></path><path d="M300 150 H230 Q260 260 214 330 Q260 380 248 430 H300Z" fill="{R}"></path>'
                f'<circle cx="86" cy="330" r="5" fill="{G}"></circle><circle cx="214" cy="330" r="5" fill="{G}"></circle>')
    masks = (f'<g transform="translate(126 290) rotate(-12)"><path d="M-30 -30 H30 V4 C30 34 -30 34 -30 4Z" fill="{CREAM}"></path>'
             f'<path d="M-18 -10 q6 -6 12 0 M6 -10 q6 -6 12 0" stroke="#1F1B16" stroke-width="3" fill="none"></path><path d="M-14 8 Q0 24 14 8" stroke="#1F1B16" stroke-width="3" fill="none"></path></g>'
             f'<g transform="translate(176 300) rotate(12)"><path d="M-30 -30 H30 V4 C30 34 -30 34 -30 4Z" fill="{G}"></path>'
             f'<path d="M-18 -6 q6 6 12 0 M6 -6 q6 6 12 0" stroke="#1F1B16" stroke-width="3" fill="none"></path><path d="M-14 18 Q0 4 14 18" stroke="#1F1B16" stroke-width="3" fill="none"></path></g>')
    stars = "".join(star5(x, y, r, G) for x, y, r in [(150, 222, 14), (104, 236, 7), (198, 238, 7)])
    footlights = "".join(f'<ellipse cx="{x}" cy="414" rx="7" ry="4" fill="#FFF3C4"></ellipse>' for x in range(30, 300, 30))
    return svg(f'''<path d="M110 190 L80 410 H220 L190 190Z" fill="#FFF8D6" opacity="0.1"></path>{curtains}{stars}{masks}
<rect y="410" width="300" height="190" fill="#7A4A26"></rect>{footlights}''', "#121826")


def movie_night():
    screen = (f'<rect x="46" y="176" width="208" height="128" rx="8" fill="#0B0F17"></rect><rect x="54" y="184" width="192" height="112" fill="#2C5E8C"></rect>'
              f'<path d="M54 296 L110 240 L150 272 L190 226 L246 280 V296Z" fill="#1E3F60"></path><circle cx="210" cy="212" r="12" fill="#F6E3B0"></circle>'
              f'<path d="M54 184 L246 296" stroke="#FFFFFF" stroke-width="1" opacity="0.06"></path><rect x="138" y="304" width="24" height="12" fill="#0B0F17"></rect>'
              f'<path d="M80 300 L40 420 H260 L220 300Z" fill="#7FB8E8" opacity="0.08"></path>')
    def popcorn():
        tub = (f'<path d="M110 336 H190 L180 424 H120Z" fill="#FFFFFF"></path>'
               + "".join(f'<path d="M{110 + i * 16} 336 L{120 + i * 12} 424 H{126 + i * 12} L{118 + i * 16} 336Z" fill="{R}"></path>' for i in range(5)))
        kernels = "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#FFF3C4"></circle>' for x, y, r in
                          [(116, 332, 9), (132, 324, 10), (150, 320, 11), (168, 324, 10), (184, 332, 9), (124, 318, 7), (142, 310, 8), (160, 308, 8), (176, 316, 7), (150, 298, 6), (200, 350, 5)])
        return kernels + tub
    pillows = (f'<ellipse cx="62" cy="420" rx="40" ry="18" fill="#8E6BBF"></ellipse><ellipse cx="240" cy="418" rx="42" ry="18" fill="#3DAE8B"></ellipse>'
               f'<path d="M0 430 Q80 410 150 432 Q220 410 300 430 V600 H0Z" fill="#C24A6A"></path><path d="M0 446 Q80 426 150 448 Q220 426 300 446" stroke="#E8A3B5" stroke-width="3" fill="none"></path>')
    return svg(f'''{stars_sky(SKY[:8], G)}{screen}{pillows}{popcorn()}''', "#1A1F33")


# ---------------- Scouts ----------------

def court_of_honor():
    ribbon = (f'<path d="M126 150 H174 L168 248 H132Z" fill="#FFFFFF"></path><path d="M126 150 H142 L138 248 H132Z" fill="{R}"></path>'
              f'<path d="M158 150 H174 L168 248 H162Z" fill="#24406B"></path><rect x="122" y="244" width="56" height="10" rx="3" fill="#C0C6CC"></rect>')
    eagle = (f'<g transform="translate(150 318) scale(1.5)"><path d="M0 -36 C8 -36 12 -28 10 -20 L40 -34 C36 -14 26 -2 12 4 L18 24 L6 18 L0 30 L-6 18 L-18 24 L-12 4 C-26 -2 -36 -14 -40 -34 L-10 -20 C-12 -28 -8 -36 0 -36Z" fill="#D7DCE0" stroke="#8A949C" stroke-width="2"></path>'
             f'<circle cx="-3" cy="-28" r="2" fill="#3A4652"></circle><path d="M4 -30 l8 3 l-8 2z" fill="#F2C230"></path>'
             f'<path d="M-20 -22 L-30 -26 M-24 -14 L-34 -20 M20 -22 L30 -26 M24 -14 L34 -20" stroke="#8A949C" stroke-width="1.6"></path></g>')
    scroll = (f'<rect x="64" y="382" width="172" height="24" rx="4" fill="{CREAM}"></rect><circle cx="64" cy="394" r="12" fill="#E2D8C3"></circle><circle cx="236" cy="394" r="12" fill="#E2D8C3"></circle>'
              f'<path d="M84 390 H216 M84 398 H180" stroke="#8C7A4E" stroke-width="2"></path>')
    return svg(f'''{burst(150, 300, 120, G, 24, 1)}{"".join(star5(x, y, 6, G) for x, y in [(60, 200), (240, 196), (52, 300), (248, 304)])}
{ribbon}{eagle}{scroll}<rect y="420" width="300" height="180" fill="#0E1D2B"></rect>''', "#1E3B5E")


def pinewood_derby():
    track = (f'<path d="M20 190 L280 380 L280 400 L20 210Z" fill="#B9BFC6"></path><path d="M20 210 L280 400 V412 L20 222Z" fill="#7C858E"></path>'
             + "".join(f'<path d="M20 {196 + i * 5} L280 {386 + i * 5 - 2}" stroke="#E6E9EC" stroke-width="1.4"></path>' for i in range(3))
             + f'<path d="M262 362 V420 M280 372 V420" stroke="#5E6B73" stroke-width="4"></path>')
    def car(x, y, col, num):
        return (f'<g transform="translate({x} {y}) rotate(36)"><path d="M-22 -6 H14 Q24 -6 26 2 H-24Z" fill="{col}"></path><rect x="-24" y="2" width="50" height="6" rx="2" fill="{col}"></rect>'
                f'<circle cx="-14" cy="10" r="4.5" fill="#1F1B16"></circle><circle cx="16" cy="10" r="4.5" fill="#1F1B16"></circle>'
                f'<text x="-2" y="6" text-anchor="middle" font-size="8" font-weight="700" font-family="Arial" fill="#FFFFFF">{num}</text></g>')
    flag = (f'<path d="M240 194 V330" stroke="#5E6B73" stroke-width="3"></path>'
            + "".join(f'<rect x="{242 + c * 10}" y="{196 + r * 10}" width="10" height="10" fill="{"#1F1B16" if (c + r) % 2 else "#FFFFFF"}"></rect>' for r in range(4) for c in range(5)))
    return svg(f'''{sky("pdsky", "#24406B", "#7FB8D9")}{flag}{track}{car(92, 236, R, 7)}{car(156, 282, BLUE, 3)}{car(210, 322, "#F2C230", 12)}
<rect y="420" width="300" height="180" fill="#8B5A2B"></rect>{"".join(f'<path d="M0 {420 + i * 14} H300" stroke="#6E4826" stroke-width="1" opacity="0.6"></path>' for i in range(1, 12))}''', "#24406B")


def scout_camp():
    lake = f'<path d="M0 340 Q150 326 300 340 V420 H0Z" fill="#3E7FA8"></path>' + "".join(f'<path d="M{x} {y} q8 -3 16 0" stroke="#BFE0F0" stroke-width="1.6" fill="none"></path>' for x, y in [(30, 360), (200, 374), (110, 396), (240, 400)])
    canoe = (f'<path d="M94 368 Q150 392 210 368 L204 364 H100Z" fill="#C8742A"></path><path d="M100 364 H204" stroke="#7A4A1E" stroke-width="2"></path>'
             f'<path d="M126 366 L112 340 M176 366 L192 344" stroke="#7A4A1E" stroke-width="2.4"></path><ellipse cx="110" cy="338" rx="3" ry="7" fill="#7A4A1E"></ellipse>')
    flagpole = f'<path d="M248 210 V340" stroke="#C0C6CC" stroke-width="3"></path><path d="M250 214 h34 v20 h-34z" fill="{R}"></path><path d="M250 214 h14 v10 h-14z" fill="#24406B"></path><path d="M250 222 h34 M250 228 h34" stroke="#FFFFFF" stroke-width="2"></path>'
    pines = "".join(pine(x, 336, h) for x, h in [(20, 130), (52, 100), (86, 120), (222, 110)])
    hills = '<path d="M0 300 Q70 250 150 290 Q220 250 300 296 V340 H0Z" fill="#5C8A6A"></path>'
    return svg(f'''{sky("scsky", "#5E9AC6", "#EAF3F0")}{sun(220, 180, 18, "#F6C24A", False)}{cloud(80, 190, 0.9)}{hills}{pines}{flagpole}{lake}{canoe}
<path d="M0 420 H300 V600 H0Z" fill="#2F5A3E"></path>''', "#5E9AC6")


# ---------------- church life ----------------

def church_small(x, base, s=1.0, wall=CREAM, roof=R):
    return (f'<g transform="translate({x} {base}) scale({s})"><rect x="-30" y="-50" width="60" height="50" fill="{wall}"></rect>'
            f'<path d="M-36 -50 L0 -78 L36 -50Z" fill="{roof}"></path><rect x="-9" y="-104" width="18" height="40" fill="{wall}"></rect>'
            f'<path d="M-13 -102 L0 -118 L13 -102Z" fill="{roof}"></path><path d="M0 -136 V-118 M-6 -130 H6" stroke="{G}" stroke-width="2.4"></path>'
            f'<path d="M-8 0 V-20 A8 8 0 0 1 8 -20 V0Z" fill="#7A4A1E"></path><rect x="-22" y="-40" width="9" height="12" fill="#7FB8D9"></rect><rect x="13" y="-40" width="9" height="12" fill="#7FB8D9"></rect></g>')


def picnic():
    tree = (f'<path d="M232 400 V280" stroke="#5A3A22" stroke-width="12"></path><circle cx="232" cy="250" r="50" fill="#3F7A3A"></circle>'
            f'<circle cx="196" cy="276" r="32" fill="#4E8A4A"></circle><circle cx="266" cy="280" r="30" fill="#4E8A4A"></circle>')
    blanket = (f'<path d="M40 378 L210 364 L250 424 L20 440Z" fill="#FFFFFF"></path>'
               + "".join(f'<path d="M{40 + i * 21} {378 - i * 1.6} L{20 + i * 29} {440 - i * 2}" stroke="{R}" stroke-width="9" opacity="0.8"></path>' for i in range(9))
               + "".join(f'<path d="M{40 - k * 2.5} {378 + k * 8} L{210 + k * 5} {364 + k * 8}" stroke="{R}" stroke-width="7" opacity="0.55"></path>' for k in range(1, 8)))
    basket = (f'<path d="M90 360 H150 L144 396 H96Z" fill="#B9853A"></path><path d="M96 364 A30 26 0 0 1 144 364" stroke="#8B5A2B" stroke-width="5" fill="none"></path>'
              + "".join(f'<path d="M{94 + i * 8} 362 L{98 + i * 6} 394" stroke="#8B5A2B" stroke-width="1.4"></path>' for i in range(7))
              + f'<path d="M100 364 q14 -12 30 -2 q-14 8 -30 2z" fill="{R}" opacity="0.9"></path>')
    food = f'<circle cx="182" cy="392" r="12" fill="#FFFFFF"></circle><circle cx="182" cy="392" r="8" fill="#F2C230"></circle><path d="M200 404 l18 -8 l4 10z" fill="#F6E3B0"></path>'
    return svg(f'''{sky("pksky", "#6FA8D6", "#E8F2E8")}{cloud(70, 180, 1)}{cloud(220, 166, 0.7)}
<path d="M0 330 Q150 300 300 330 V600 H0Z" fill="#7BB062"></path>{church_small(70, 334, 0.7)}{tree}{blanket}{basket}{food}
<rect y="446" width="300" height="154" fill="#5E9A4E"></rect>''', "#6FA8D6")


def mission_trip():
    globe = (f'<circle cx="150" cy="270" r="84" fill="#2E8FB8"></circle>'
             f'<path d="M96 222 C112 206 140 214 136 236 C132 256 112 250 108 268 C104 284 88 278 82 262 C76 246 84 232 96 222Z" fill="#5BA35A"></path>'
             f'<path d="M160 206 C186 200 206 214 214 236 C220 254 204 260 196 252 C186 242 170 250 166 236 C162 224 150 214 160 206Z" fill="#5BA35A"></path>'
             f'<path d="M150 292 C170 286 186 300 182 318 C178 336 160 344 150 330 C140 316 136 298 150 292Z" fill="#5BA35A"></path>'
             f'<ellipse cx="150" cy="270" rx="84" ry="30" fill="none" stroke="#FFFFFF" stroke-width="1" opacity="0.35"></ellipse>'
             f'<ellipse cx="150" cy="270" rx="34" ry="84" fill="none" stroke="#FFFFFF" stroke-width="1" opacity="0.35"></ellipse>')
    route = f'<path d="M96 246 Q150 150 196 230" stroke="{CREAM}" stroke-width="2.4" stroke-dasharray="5 5" fill="none"></path>'
    pin = f'<path d="M196 200 C186 200 180 208 180 216 C180 228 196 242 196 242 C196 242 212 228 212 216 C212 208 206 200 196 200Z" fill="{R}"></path><path d="M196 207 V223 M190 212 H202" stroke="#FFFFFF" stroke-width="2.4"></path>'
    plane = f'<g transform="translate(140 182) rotate(18)"><path d="M-18 0 H18 Q24 0 24 3 Q24 6 18 6 H-18Z" fill="#FFFFFF"></path><path d="M-2 2 L-12 16 H-6 L8 2Z M-2 2 L-10 -10 H-5 L6 2Z M-16 1 L-22 -7 H-18 L-12 1Z" fill="#E3E8EE"></path></g>'
    suitcase = (f'<rect x="96" y="366" width="108" height="64" rx="8" fill="#8B4F24"></rect><path d="M132 366 V352 H168 V366" stroke="#5A3A22" stroke-width="6" fill="none"></path>'
                f'<path d="M96 390 H204" stroke="#5A3A22" stroke-width="3"></path><circle cx="124" cy="410" r="8" fill="{G}"></circle><rect x="160" y="402" width="26" height="14" rx="2" fill="{CREAM}"></rect>')
    return svg(f'''{stars_sky(SKY, C)}{globe}{route}{pin}{plane}<rect y="430" width="300" height="170" fill="#10263D"></rect>{suitcase}''', NAVY)


def church_camp():
    cabin = (f'<rect x="150" y="334" width="96" height="60" fill="#8B5A2B"></rect>' + "".join(f'<path d="M150 {y} H246" stroke="#5C3A22" stroke-width="1.4"></path>' for y in range(342, 394, 8))
             + f'<path d="M140 336 L198 296 L256 336Z" fill="#4E6B5A"></path><rect x="188" y="358" width="18" height="36" fill="#5C3A22"></rect>'
             f'<rect x="160" y="350" width="18" height="16" fill="#F6E3B0"></rect><rect x="218" y="350" width="18" height="16" fill="#F6E3B0"></rect>')
    cross = f'<path d="M84 196 V300 M66 222 H102" stroke="{CREAM}" stroke-width="8" stroke-linecap="round"></path>{burst(84, 226, 50, G, 14, 1.4)}'
    hill = '<path d="M0 310 Q84 270 170 312 V420 H0Z" fill="#4E7A55"></path>'
    fire = (f'<path d="M100 400 L132 394 M100 394 L132 400" stroke="#5A3A22" stroke-width="5" stroke-linecap="round"></path>'
            f'<path d="M116 396 Q104 380 112 364 Q116 374 120 368 Q130 382 116 396Z" fill="#E07A2A"></path><path d="M116 396 Q110 386 115 378 Q118 386 121 382 Q122 390 116 396Z" fill="{G}"></path>')
    return svg(f'''{sky("ccsky", "#24406B", "#E6A55E")}{stars_sky(SKY[:6], C)}{"".join(pine(x, 330, h, "#24432F") for x, h in [(20, 120), (276, 130), (250, 100)])}
{hill}{cross}{cabin}<path d="M0 394 Q150 380 300 394 V600 H0Z" fill="#2F5A3E"></path>{fire}''', "#24406B")


def christmas_program():
    stage = f'<rect y="392" width="300" height="208" fill="#5C3A22"></rect><path d="M0 392 H300" stroke="#8B5A2B" stroke-width="4"></path>'
    star = f'{burst(150, 196, 46, G, 16, 1.6)}{star5(150, 196, 16, G)}<path d="M150 212 L118 392 H182Z" fill="#FFF8D6" opacity="0.1"></path>'
    manger = (f'<path d="M116 366 L184 366 L176 392 H124Z" fill="#8B5A2B"></path><path d="M112 392 L130 350 M188 392 L170 350" stroke="#5C3A22" stroke-width="5"></path>'
              f'<path d="M118 366 Q150 346 182 366" fill="#E8C060"></path><ellipse cx="150" cy="356" rx="16" ry="8" fill="#FFFFFF"></ellipse><circle cx="140" cy="352" r="6" fill="#E8B48A"></circle>')
    choir = "".join(f'<g transform="translate({x} 392)"><path d="M-14 0 V-38 Q0 -46 14 -38 V0Z" fill="{c}"></path><rect x="-14" y="-40" width="28" height="6" fill="#FFFFFF"></rect>'
                    f'<circle cx="0" cy="-50" r="9" fill="#E8B48A"></circle><ellipse cx="0" cy="-45" rx="3" ry="2.4" fill="#7A3A2A"></ellipse></g>' for x, c in [(44, R), (78, "#24406B"), (222, "#24406B"), (256, R)])
    wreaths = "".join(f'<circle cx="{x}" cy="248" r="18" fill="none" stroke="{DKGREEN}" stroke-width="8"></circle><path d="M{x - 6} 266 l6 -6 l6 6" fill="{R}"></path>' for x in (52, 248))
    notes = "".join(f'<g transform="translate({x} {y}) scale(0.7)" fill="{G}"><ellipse cx="0" cy="0" rx="7" ry="5" transform="rotate(-20)"></ellipse><path d="M6 -2 V-28" stroke="{G}" stroke-width="2.4"></path></g>' for x, y in [(96, 290), (204, 286), (230, 318)])
    return svg(f'''{stars_sky(SKY[:8], C)}{star}{wreaths}{notes}{stage}{choir}{manger}''', "#141E30")


def fall_festival():
    lights = string_lights(196, 22)
    bales = (f'<rect x="40" y="370" width="100" height="44" rx="6" fill="#D9B45A"></rect><rect x="160" y="370" width="100" height="44" rx="6" fill="#D9B45A"></rect>'
             f'<rect x="100" y="328" width="100" height="44" rx="6" fill="#E2C46E"></rect>'
             + "".join(f'<path d="M{x} {y} h{w}" stroke="#B48A34" stroke-width="1.6"></path>' for x, y, w in [(44, 384, 92), (44, 400, 92), (164, 384, 92), (164, 400, 92), (104, 342, 92), (104, 358, 92)])
             + f'<path d="M40 380 H140 M160 380 H260 M100 338 H200" stroke="{R}" stroke-width="2"></path>')
    def pumpkin(x, y, s):
        return (f'<g transform="translate({x} {y}) scale({s})"><ellipse cx="0" cy="0" rx="26" ry="20" fill="{ORANGE}"></ellipse><ellipse cx="0" cy="0" rx="10" ry="20" fill="none" stroke="#A85A1A" stroke-width="2"></ellipse>'
                f'<path d="M0 -18 q2 -8 7 -10" stroke="#4E6B3A" stroke-width="4" fill="none"></path></g>')
    corn = "".join(f'<path d="M{x} 414 Q{x + d} 330 {x + 2 * d} 250" stroke="#C8A253" stroke-width="5" fill="none"></path><path d="M{x + d} 340 q{14 * (1 if d > 0 else -1)} -20 {24 * (1 if d > 0 else -1)} -18" stroke="#B48A34" stroke-width="3" fill="none"></path>' for x, d in [(18, 6), (30, -4), (276, -6), (288, 4)])
    leaves = "".join(f'<path transform="translate({x} {y}) rotate({r})" d="M0 0 q8 -10 0 -22 q-8 12 0 22z" fill="{c}"></path>' for x, y, r, c in [(80, 250, -20, "#A8432A"), (220, 262, 30, G), (130, 280, 40, ORANGE), (180, 240, -30, "#A8432A")])
    return svg(f'''{sky("ffsky", "#3E2A4F", "#E07A3A")}{lights}{leaves}{corn}<rect y="414" width="300" height="186" fill="#4A3524"></rect>
{bales}{pumpkin(150, 314, 1.1)}{pumpkin(70, 360, 0.8)}{pumpkin(232, 362, 0.75)}{pumpkin(120, 430, 0.9)}{pumpkin(196, 432, 1.0)}''', "#3E2A4F")


def baptism():
    rays = "".join(f'<path d="M150 150 L{150 + math.cos(math.radians(a)) * 300:.0f} {150 + math.sin(math.radians(a)) * 300:.0f}" stroke="{G}" stroke-width="10" opacity="0.08"></path>' for a in range(40, 141, 12))
    dove = (f'<g transform="translate(150 230)"><path d="M0 0 C-8 -6 -18 -4 -24 2 C-14 0 -8 4 -4 8 C-20 2 -40 -10 -56 -30 C-46 -6 -26 10 -6 14 L-10 24 L2 16 L12 24 L8 12 C20 8 28 0 30 -8 C24 -4 14 -2 0 0Z" fill="#FFFFFF"></path>'
            f'<path d="M0 0 C10 -10 30 -28 54 -36 C40 -16 26 -4 8 4Z" fill="#F3F6F9"></path><circle cx="-18" cy="-1" r="1.6" fill="#1F1B16"></circle></g>')
    water = (f'<path d="M0 360 Q75 350 150 360 T300 360 V600 H0Z" fill="#2E8FB8"></path>'
             + "".join(f'<ellipse cx="150" cy="{372 + i * 14}" rx="{40 + i * 26}" ry="{5 + i * 2}" fill="none" stroke="#BFE6F6" stroke-width="2" opacity="{0.9 - i * 0.18:.2f}"></ellipse>' for i in range(5))
             + f'<path d="M0 352 Q75 344 150 352 T300 352" stroke="#7FC8E8" stroke-width="3" fill="none"></path>')
    return svg(f'''{sky("bpsky", "#1E3B5E", "#7FB8D9")}{rays}<circle cx="150" cy="150" r="40" fill="{G}" opacity="0.25"></circle>{dove}{water}''', "#1E3B5E")


# ---------------- seasons ----------------

def spring():
    tree = (f'<path d="M150 410 V300 M150 330 L118 296 M150 316 L184 284" stroke="#6B4A33" stroke-width="10" stroke-linecap="round"></path>'
            + "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{c}"></circle>' for x, y, r, c in
                      [(150, 250, 54, "#F4C6D4"), (106, 276, 38, "#F8D7E1"), (196, 270, 40, "#F8D7E1"), (130, 222, 30, "#FBE3EA"), (176, 218, 32, "#F4C6D4")])
            + "".join(f'<circle cx="{x}" cy="{y}" r="3" fill="#E8A3B5"></circle>' for x, y in [(120, 250), (150, 236), (184, 252), (140, 280), (168, 290), (104, 286), (196, 286)]))
    tulips = "".join(f'<path d="M{x} 430 V{y + 14}" stroke="{GREEN}" stroke-width="3"></path><path d="M{x - 7} {y + 2} Q{x - 8} {y + 18} {x} {y + 18} Q{x + 8} {y + 18} {x + 7} {y + 2} L{x + 3} {y + 8} L{x} {y} L{x - 3} {y + 8}Z" fill="{c}"></path>'
                     for x, y, c in [(40, 396, R), (62, 404, "#F2C230"), (84, 398, "#E8A3B5"), (216, 400, "#F2C230"), (238, 394, R), (260, 402, "#8E6BBF")])
    bird = f'<path d="M226 196 q8 -8 16 0 q8 -8 16 0" stroke="#24406B" stroke-width="2.4" fill="none"></path><path d="M70 214 q6 -6 12 0 q6 -6 12 0" stroke="#24406B" stroke-width="2" fill="none"></path>'
    return svg(f'''{sky("spsky", "#8EC3E6", "#EAF6EC")}{sun(240, 168, 16, "#F6D365", False)}{cloud(70, 176, 0.9)}{bird}
<path d="M0 410 Q150 392 300 410 V600 H0Z" fill="#7BC46A"></path>{tree}{tulips}''', "#8EC3E6")


def summer():
    flowers = "".join(f'<path d="M{x} 440 V{y}" stroke="#4E7A35" stroke-width="4"></path><path d="M{x} {y + 30} q-14 -6 -20 4 q12 6 20 -4z" fill="#5E9A3E"></path>'
                      + "".join(f'<ellipse cx="{x + math.cos(math.radians(a)) * s * 14:.1f}" cy="{y + math.sin(math.radians(a)) * s * 14:.1f}" rx="{s * 8:.1f}" ry="{s * 3.4:.1f}" transform="rotate({a} {x + math.cos(math.radians(a)) * s * 14:.1f} {y + math.sin(math.radians(a)) * s * 14:.1f})" fill="#F6C02A"></ellipse>' for a in range(0, 360, 30))
                      + f'<circle cx="{x}" cy="{y}" r="{s * 9:.1f}" fill="#6B3E1E"></circle>' for x, y, s in [(70, 330, 1.2), (150, 300, 1.4), (230, 336, 1.15), (110, 372, 0.9), (196, 380, 0.85)])
    return svg(f'''{sky("susky", "#2E8FD6", "#BFE4F6")}{sun(150, 200, 30, "#F6C24A")}{cloud(52, 250, 0.8)}{cloud(250, 240, 0.7)}
<path d="M0 390 Q150 370 300 390 V600 H0Z" fill="#5EA84A"></path><path d="M0 420 Q150 404 300 420 V600 H0Z" fill="#4E9A3E"></path>{flowers}''', "#2E8FD6")


def fall():
    tree = (f'<path d="M150 412 V300 M150 340 L116 304 M150 322 L188 292" stroke="#5A3A22" stroke-width="11" stroke-linecap="round"></path>'
            + "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{c}"></circle>' for x, y, r, c in
                      [(150, 250, 56, "#D9822B"), (104, 280, 38, "#C8541E"), (198, 274, 40, "#E8A23A"), (128, 220, 30, "#E8A23A"), (178, 216, 32, "#C8541E")]))
    def leaf(x, y, r, c):
        return f'<path transform="translate({x} {y}) rotate({r}) scale(0.9)" d="M0 -12 L3 -5 L10 -7 L7 0 L12 4 L4 5 L5 12 L0 8 L-5 12 L-4 5 L-12 4 L-7 0 L-10 -7 L-3 -5Z" fill="{c}"></path>'
    falling = "".join(leaf(x, y, r, c) for x, y, r, c in [(60, 230, 20, "#C8541E"), (240, 220, -30, "#E8A23A"), (80, 330, 60, "#D9822B"), (226, 340, 10, "#C8541E"), (190, 380, -40, "#E8A23A"), (50, 390, 30, "#D9822B")])
    pile = "".join(leaf(x, y, r, c) for x, y, r, c in [(110, 414, 0, "#C8541E"), (126, 418, 40, "#E8A23A"), (176, 416, -20, "#D9822B"), (192, 420, 70, "#C8541E"), (150, 420, 10, "#E8A23A")])
    return svg(f'''{sky("fasky", "#5E86B0", "#F2D7A8")}<path d="M0 360 Q80 320 160 352 Q230 324 300 350 V420 H0Z" fill="#B97A45" opacity="0.6"></path>
<path d="M0 412 Q150 396 300 412 V600 H0Z" fill="#7A6A3A"></path>{tree}{falling}{pile}''', "#5E86B0")


def winter():
    snowpines = "".join(pine(x, b, h, "#2F5A4E") + f'<path d="M{x} {b - h} L{x - h * 0.12} {b - h * 0.78} H{x + h * 0.12}Z M{x - h * 0.2} {b - h * 0.5} H{x + h * 0.2} L{x} {b - h * 0.62}Z" fill="#FFFFFF"></path>'
                        for x, b, h in [(60, 410, 140), (110, 404, 100), (200, 406, 120), (248, 410, 150)])
    flakes = "".join(f'<g transform="translate({x} {y})" stroke="#FFFFFF" stroke-width="1.6"><path d="M-6 0 H6 M0 -6 V6 M-4 -4 L4 4 M-4 4 L4 -4"></path></g>' for x, y in [(40, 200), (150, 180), (250, 210), (100, 260), (210, 280), (30, 320), (170, 330), (270, 350)])
    return svg(f'''{sky("wisky", "#1E3B5E", "#9FBAD3")}<circle cx="226" cy="186" r="22" fill="#F3EBDA"></circle><circle cx="236" cy="180" r="18" fill="#2A4D72"></circle>{flakes}
{snowpines}<path d="M0 404 Q150 384 300 404 V600 H0Z" fill="#EEF4F8"></path><path d="M0 430 Q150 414 300 430" stroke="#D6E2EC" stroke-width="3" fill="none"></path>''', "#1E3B5E")


def snow_day():
    house = (f'<rect x="196" y="320" width="80" height="70" fill="#8E3B2E"></rect><path d="M186 324 L236 280 L286 324Z" fill="#FFFFFF"></path>'
             f'<rect x="210" y="338" width="20" height="18" fill="#F6E3B0"></rect><rect x="244" y="350" width="18" height="40" fill="#5C3A22"></rect><rect x="250" y="286" width="12" height="22" fill="#5C3A22"></rect>'
             f'<path d="M256 284 q-6 -12 2 -20 q8 -8 0 -18" stroke="#DDE6EE" stroke-width="4" fill="none" opacity="0.7"></path>')
    snowman = (f'<circle cx="118" cy="378" r="36" fill="#FFFFFF"></circle><circle cx="118" cy="322" r="26" fill="#FFFFFF"></circle><circle cx="118" cy="280" r="18" fill="#FFFFFF"></circle>'
               f'<rect x="102" y="252" width="32" height="8" fill="#1F1B16"></rect><rect x="107" y="232" width="22" height="22" fill="#1F1B16"></rect><rect x="107" y="246" width="22" height="4" fill="{R}"></rect>'
               f'<circle cx="112" cy="276" r="2.4" fill="#1F1B16"></circle><circle cx="124" cy="276" r="2.4" fill="#1F1B16"></circle><path d="M118 282 L134 286 L118 288Z" fill="{ORANGE}"></path>'
               f'<path d="M98 296 Q118 304 138 296 L140 306 Q118 312 96 306Z" fill="{R}"></path><path d="M132 304 L136 324 L128 324Z" fill="{R}"></path>'
               f'<path d="M94 318 L62 296 M142 318 L172 300" stroke="#5A3A22" stroke-width="3"></path>'
               + "".join(f'<circle cx="118" cy="{y}" r="2.6" fill="#1F1B16"></circle>' for y in (316, 330, 364)))
    sled = f'<path d="M30 410 H90 Q100 410 98 402" stroke="#7A4A26" stroke-width="3" fill="none"></path><rect x="34" y="398" width="52" height="8" rx="2" fill="{R}"></rect>'
    snow = "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#FFFFFF" opacity="0.9"></circle>' for x, y, r in
                   [(30, 190, 2.4), (80, 220, 2), (150, 180, 2.6), (200, 220, 2), (260, 190, 2.4), (40, 280, 2), (180, 260, 2.4), (280, 250, 2), (60, 340, 2.2), (170, 360, 2), (230, 240, 1.8), (110, 200, 1.8)])
    return svg(f'''{sky("sdsky", "#7F9CB8", "#DCE6EE")}{snow}{house}<path d="M0 392 Q150 372 300 392 V600 H0Z" fill="#FFFFFF"></path>{snowman}{sled}''', "#7F9CB8")


# ---------------- outings ----------------

def zoo():
    acacia = (f'<path d="M226 410 V300 M226 330 L204 304 M226 320 L250 298" stroke="#6B4A33" stroke-width="7" stroke-linecap="round"></path>'
              f'<ellipse cx="226" cy="290" rx="62" ry="18" fill="#5B8A3A"></ellipse><ellipse cx="206" cy="298" rx="30" ry="10" fill="#4E7A35"></ellipse>')
    giraffe = (f'<g transform="translate(92 410)"><path d="M-30 -84 H24 Q32 -84 32 -74 V-62 Q32 -54 24 -54 H-30 Q-38 -54 -38 -62 V-74 Q-38 -84 -30 -84Z" fill="#E8B24A"></path>'
               f'<path d="M-30 -56 V0 M-18 -56 V0 M12 -56 V0 M24 -56 V0" stroke="#E8B24A" stroke-width="7"></path>'
               f'<path d="M20 -80 L46 -170 L60 -166 L36 -76Z" fill="#E8B24A"></path><path d="M44 -176 Q60 -186 74 -176 Q76 -166 66 -164 L48 -162Z" fill="#E8B24A"></path>'
               f'<path d="M50 -178 V-188 M58 -180 V-190" stroke="#8B5A2B" stroke-width="3"></path><circle cx="62" cy="-174" r="2" fill="#1F1B16"></circle>'
               + "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#A8642A"></circle>' for x, y, r in [(-24, -74, 6), (-6, -66, 7), (12, -76, 6), (30, -96, 5), (36, -120, 4.5), (42, -144, 4), (-30, -60, 4), (4, -60, 4)])
               + '</g>')
    elephant = (f'<g transform="translate(232 412)"><ellipse cx="0" cy="-34" rx="40" ry="28" fill="#8A949C"></ellipse><path d="M-28 -16 V0 M-10 -12 V0 M14 -12 V0 M28 -16 V0" stroke="#8A949C" stroke-width="12"></path>'
                f'<circle cx="-40" cy="-48" r="20" fill="#8A949C"></circle><path d="M-56 -44 Q-66 -20 -56 -6" stroke="#8A949C" stroke-width="9" fill="none" stroke-linecap="round"></path>'
                f'<ellipse cx="-28" cy="-48" rx="14" ry="18" fill="#7A848C"></ellipse><circle cx="-46" cy="-54" r="2" fill="#1F1B16"></circle></g>')
    return svg(f'''{sky("zsky", "#E6A55E", "#F6E3B0")}{sun(80, 230, 26, "#F6C24A", False)}<path d="M0 360 Q150 340 300 360 V420 H0Z" fill="#C9A35E"></path>
{acacia}<path d="M0 410 Q150 398 300 410 V600 H0Z" fill="#B48A44"></path>{giraffe}{elephant}''', "#E6A55E")


def aquarium():
    rays = "".join(f'<path d="M{x} 150 L{x - 40} 430 H{x + 10}Z" fill="#FFFFFF" opacity="0.06"></path>' for x in (90, 170, 250))
    def fish(x, y, s, col, face=1):
        return (f'<g transform="translate({x} {y}) scale({s * face} {s})"><path d="M-20 0 C-10 -14 14 -14 20 0 C14 14 -10 14 -20 0Z" fill="{col}"></path>'
                f'<path d="M-18 0 L-32 -10 V10Z" fill="{col}"></path><circle cx="11" cy="-3" r="2.4" fill="#1F1B16"></circle>'
                f'<path d="M-2 -10 V10 M4 -9 V9" stroke="#FFFFFF" stroke-width="2.4" opacity="0.8"></path></g>')
    turtle = (f'<g transform="translate(150 290) rotate(-10)"><ellipse cx="0" cy="0" rx="40" ry="26" fill="#4E7A55"></ellipse>'
              f'<path d="M-20 -14 L0 -20 L20 -14 L24 6 L0 14 L-24 6Z" fill="none" stroke="#2F5A3E" stroke-width="2"></path>'
              f'<ellipse cx="50" cy="-4" rx="14" ry="10" fill="#8BB07A"></ellipse><circle cx="56" cy="-6" r="2" fill="#1F1B16"></circle>'
              f'<path d="M20 18 Q34 40 18 44 Q12 30 8 22Z M-24 16 Q-38 36 -26 40 Q-18 28 -14 22Z M24 -20 Q40 -42 26 -46 Q18 -32 14 -24Z" fill="#8BB07A"></path></g>')
    jelly = (f'<g transform="translate(232 214)"><path d="M-16 0 Q-16 -20 0 -20 Q16 -20 16 0Z" fill="#E8A3D8" opacity="0.8"></path>'
             + "".join(f'<path d="M{x} 0 q4 10 0 20 q-4 10 0 20" stroke="#E8A3D8" stroke-width="1.6" fill="none" opacity="0.7"></path>' for x in (-10, -3, 4, 11)) + '</g>')
    bubbles = "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="none" stroke="#BFE6F6" stroke-width="1.4"></circle>' for x, y, r in [(70, 200, 4), (76, 184, 3), (66, 170, 2), (200, 340, 3), (206, 326, 2)])
    weeds = "".join(f'<path d="M{x} 430 Q{x - 10} 390 {x} 360 Q{x + 10} 330 {x} 300" stroke="#3E8A5A" stroke-width="6" fill="none" stroke-linecap="round"></path>' for x in (30, 48, 262, 278))
    return svg(f'''{sky("aqsky", "#0E4C7A", "#1E7FA8")}{rays}{bubbles}{jelly}{fish(84, 250, 1.1, ORANGE)}{fish(220, 360, 0.9, "#F2C230", -1)}{fish(96, 360, 0.8, "#E5484D")}{turtle}
<path d="M0 410 Q150 396 300 410 V600 H0Z" fill="#D9C08A"></path>{weeds}''', "#0E4C7A")


def county_fair():
    wheel = (f'<g transform="translate(206 270)"><circle r="62" fill="none" stroke="#E8E2D2" stroke-width="3"></circle>'
             + "".join(f'<path d="M0 0 L{62 * math.cos(math.radians(a)):.1f} {62 * math.sin(math.radians(a)):.1f}" stroke="#E8E2D2" stroke-width="1.4"></path><rect x="{62 * math.cos(math.radians(a)) - 6:.1f}" y="{62 * math.sin(math.radians(a)):.1f}" width="12" height="10" rx="2" fill="{c}"></rect>'
                       for a, c in zip(range(0, 360, 36), [R, G, BLUE, "#E8A3B5", GREEN] * 2))
             + f'<path d="M0 0 L-30 140 M0 0 L30 140" stroke="#E8E2D2" stroke-width="4"></path><circle r="6" fill="{G}"></circle></g>')
    barn = (f'<rect x="30" y="314" width="110" height="96" fill="#B3262D"></rect><path d="M22 318 L50 274 H120 L148 318Z" fill="#8E1B24"></path>'
            f'<rect x="64" y="350" width="42" height="60" fill="#8E1B24"></rect><path d="M64 350 L106 410 M106 350 L64 410" stroke="#FFFFFF" stroke-width="3"></path><rect x="64" y="350" width="42" height="60" fill="none" stroke="#FFFFFF" stroke-width="3"></rect>'
            f'<rect x="74" y="292" width="22" height="16" fill="#FFFFFF"></rect>')
    rosette = (f'<g transform="translate(150 230)">' + "".join(f'<ellipse cx="{22 * math.cos(math.radians(a)):.1f}" cy="{22 * math.sin(math.radians(a)):.1f}" rx="12" ry="7" transform="rotate({a} {22 * math.cos(math.radians(a)):.1f} {22 * math.sin(math.radians(a)):.1f})" fill="#2E6FD0"></ellipse>' for a in range(0, 360, 30))
               + f'<path d="M-12 20 L-20 70 L-8 62 L-2 74 L2 24Z M12 20 L20 70 L8 62 L2 74 L-2 24Z" fill="#2E6FD0"></path><circle r="20" fill="#3E86E8"></circle><circle r="14" fill="#F3EBDA"></circle>'
               f'<text y="5" text-anchor="middle" font-family="Georgia, serif" font-weight="700" font-size="13" fill="#2E6FD0">1st</text></g>')
    return svg(f'''{sky("cfsky", "#6FA8D6", "#EAF3F0")}{bunting(170, 12, [R, G, BLUE, "#E8A3B5"], n=13)}{wheel}{barn}{rosette}
<path d="M0 410 Q150 398 300 410 V600 H0Z" fill="#6EA84E"></path>''', "#6FA8D6")


def state_park():
    falls = f'<path d="M190 250 Q196 300 188 360 H214 Q208 300 214 250Z" fill="#BFE6F6"></path><path d="M196 260 V352 M206 260 V352" stroke="#FFFFFF" stroke-width="2" opacity="0.7"></path><ellipse cx="200" cy="364" rx="30" ry="8" fill="#FFFFFF" opacity="0.6"></ellipse>'
    cliffs = '<path d="M150 260 L176 240 L190 250 V380 H150Z M214 250 L236 236 L270 256 V380 H214Z" fill="#7A6E62"></path>'
    trail = '<path d="M60 600 Q90 470 130 430 Q160 400 150 380" stroke="#C9A35E" stroke-width="22" fill="none" stroke-linecap="round"></path>'
    sign = (f'<path d="M84 420 V350" stroke="#5C3A22" stroke-width="5"></path><path d="M60 350 H110 L118 358 L110 366 H60Z" fill="#7A4A26"></path><path d="M108 372 H58 L50 380 L58 388 H108Z" fill="#7A4A26"></path>'
            f'<path d="M66 358 H100 M66 380 H98" stroke="{CREAM}" stroke-width="2"></path>')
    return svg(f'''{sky("stsky", "#6FA8D6", "#E3F0E6")}{cloud(70, 186, 0.9)}<path d="M0 290 L60 220 L120 270 L170 210 L230 260 L300 214 V380 H0Z" fill="#6E8FA8"></path>
{cliffs}{falls}{"".join(pine(x, 400, h) for x, h in [(24, 150), (130, 110), (280, 140), (252, 100)])}<path d="M0 380 Q150 366 300 380 V600 H0Z" fill="#4E8A4A"></path>{trail}{sign}''', "#6FA8D6")


def lake_day():
    dock = f'<path d="M0 372 H120 V384 H0Z" fill="#8B5A2B"></path>' + "".join(f'<path d="M{x} 384 V404" stroke="#5C3A22" stroke-width="4"></path>' for x in (14, 54, 94)) + "".join(f'<path d="M{x} 372 V384" stroke="#6E4826" stroke-width="1"></path>' for x in range(10, 120, 10))
    boat = (f'<g transform="translate(196 366)"><path d="M-56 0 H56 Q50 18 30 20 H-44 Q-56 14 -56 0Z" fill="#FFFFFF"></path><path d="M-56 6 H54" stroke="{BLUE}" stroke-width="4"></path>'
            f'<path d="M-30 0 V-26 H24 V0" stroke="#5E6B73" stroke-width="2.4" fill="none"></path><path d="M-36 -26 H30 V-32 H-36Z" fill="{R}"></path>'
            f'<rect x="-22" y="-14" width="16" height="12" rx="2" fill="#24406B"></rect><rect x="4" y="-14" width="16" height="12" rx="2" fill="#24406B"></rect></g>')
    water = f'<path d="M0 340 Q150 330 300 340 V430 H0Z" fill="#2E8FB8"></path>' + "".join(f'<path d="M{x} {y} q10 -4 20 0" stroke="#BFE6F6" stroke-width="2" fill="none"></path>' for x, y in [(30, 352), (150, 400), (240, 410), (70, 420), (120, 356)])
    trees = "".join(pine(x, 340, h, "#2F5A3E") for x, h in [(20, 90), (44, 70), (250, 96), (278, 80)])
    return svg(f'''{sky("lksky", "#4FA0D8", "#DFF1F8")}{sun(150, 196, 24, "#F6C24A")}<path d="M0 340 Q100 296 170 326 Q230 300 300 330 V340 H0Z" fill="#5C8A6A"></path>{trees}
{water}{dock}{boat}<rect y="430" width="300" height="170" fill="#1F6F96"></rect>''', "#4FA0D8")


def pumpkin_patch():
    def pumpkin(x, y, s):
        return (f'<g transform="translate({x} {y}) scale({s})"><ellipse cx="0" cy="0" rx="22" ry="16" fill="{ORANGE}"></ellipse><ellipse cx="0" cy="0" rx="9" ry="16" fill="none" stroke="#A85A1A" stroke-width="2"></ellipse>'
                f'<path d="M0 -14 q2 -8 6 -9" stroke="#4E6B3A" stroke-width="3.4" fill="none"></path></g>')
    vines = "".join(f'<path d="M0 {y} Q75 {y - 8} 150 {y} T300 {y}" stroke="#4E7A35" stroke-width="2" fill="none"></path>' for y in (376, 404, 432))
    patch = "".join(pumpkin(x, y, s) for x, y, s in [(40, 374, 0.8), (110, 380, 0.9), (190, 372, 0.75), (260, 382, 0.9), (70, 406, 1.1), (160, 410, 1.2), (236, 414, 1.0), (30, 440, 1.2), (120, 446, 1.3), (210, 448, 1.2)])
    wagon = (f'<rect x="180" y="306" width="100" height="30" fill="#B3262D"></rect><rect x="184" y="296" width="92" height="12" fill="#E2C46E"></rect>'
             f'<circle cx="200" cy="340" r="10" fill="#1F1B16"></circle><circle cx="262" cy="340" r="10" fill="#1F1B16"></circle><path d="M180 322 H160" stroke="#5C3A22" stroke-width="4"></path>')
    barn = f'<rect x="24" y="290" width="70" height="56" fill="#8E1B24"></rect><path d="M18 292 L40 262 H78 L100 292Z" fill="#6E1520"></path><rect x="46" y="314" width="26" height="32" fill="#6E1520"></rect>'
    return svg(f'''{sky("ppsky", "#5E86B0", "#F2D7A8")}{cloud(220, 196, 0.8)}<path d="M0 340 Q150 320 300 340 V600 H0Z" fill="#7A6A3A"></path>{barn}{wagon}{vines}{patch}''', "#5E86B0")


def apple_picking():
    def tree(x, s):
        apples = "".join(f'<circle cx="{x + dx * s:.0f}" cy="{260 + dy * s:.0f}" r="{5 * s:.1f}" fill="#D32F2F"></circle>' for dx, dy in [(-30, -10), (-10, -30), (18, -20), (34, 4), (-24, 18), (6, 10), (24, 30), (-40, 30)])
        return (f'<path d="M{x} 412 V{300}" stroke="#6B4A33" stroke-width="{10 * s:.0f}"></path><ellipse cx="{x}" cy="260" rx="{58 * s:.0f}" ry="{50 * s:.0f}" fill="#4E8A3A"></ellipse>'
                f'<ellipse cx="{x - 20 * s:.0f}" cy="{276}" rx="{30 * s:.0f}" ry="{24 * s:.0f}" fill="#5E9A4A"></ellipse>{apples}')
    ladder = f'<path d="M188 412 L214 250 M210 412 L232 254" stroke="#B48A44" stroke-width="5"></path>' + "".join(f'<path d="M{190 + i * 4.3:.0f} {396 - i * 26} L{212 + i * 3.7:.0f} {396 - i * 26}" stroke="#B48A44" stroke-width="4"></path>' for i in range(6))
    basket = (f'<path d="M64 384 H136 L128 426 H72Z" fill="#B9853A"></path><path d="M72 388 A28 26 0 0 1 128 388" stroke="#8B5A2B" stroke-width="5" fill="none"></path>'
              + "".join(f'<circle cx="{x}" cy="{y}" r="9" fill="{c}"></circle>' for x, y, c in [(82, 380, "#D32F2F"), (100, 376, "#E5484D"), (118, 380, "#D32F2F"), (92, 368, "#E5484D"), (110, 368, "#D32F2F")]))
    return svg(f'''{sky("apsky", "#7FB8E8", "#EEF4E2")}{cloud(150, 180, 0.9)}<path d="M0 404 Q150 388 300 404 V600 H0Z" fill="#6EA84E"></path>
{tree(70, 0.9)}{tree(226, 1.0)}{ladder}{basket}''', "#7FB8E8")


def christmas_lights():
    def house(x, w, h, wall, roof):
        bulbs = "".join(f'<circle cx="{x + i * w / 10:.1f}" cy="{404 - h + 2:.0f}" r="2.6" fill="{c}"></circle>' for i, c in zip(range(11), [R, G, "#7FC8E8", "#7FD27F"] * 3))
        return (f'<rect x="{x}" y="{404 - h}" width="{w}" height="{h}" fill="{wall}"></rect><path d="M{x - 6} {404 - h} L{x + w / 2} {404 - h - w * 0.4:.0f} L{x + w + 6} {404 - h}Z" fill="{roof}"></path>'
                f'<rect x="{x + w * 0.2:.0f}" y="{404 - h * 0.7:.0f}" width="{w * 0.22:.0f}" height="{h * 0.3:.0f}" fill="#F6E3B0"></rect><rect x="{x + w * 0.58:.0f}" y="{404 - h * 0.6:.0f}" width="{w * 0.2:.0f}" height="{h * 0.6:.0f}" fill="#5C3A22"></rect>'
                f'{bulbs}' + "".join(f'<circle cx="{x - 6 + i * (w + 12) / 12 + (w + 12) / 24:.1f}" cy="{404 - h - (w * 0.4) * (1 - abs(i - 5.5) / 6):.1f}" r="2.4" fill="{c}"></circle>' for i, c in zip(range(12), [G, R, "#7FC8E8"] * 4)))
    car = (f'<g transform="translate(110 446)"><path d="M-40 -14 L-26 -30 H22 L36 -14 H48 Q54 -14 54 -6 V4 H-54 V-6 Q-54 -14 -48 -14Z" fill="#24406B"></path>'
           f'<path d="M-22 -26 H-2 V-14 H-32Z M4 -26 H20 L30 -14 H4Z" fill="#BFD7EA"></path><circle cx="-30" cy="6" r="9" fill="#1F1B16"></circle><circle cx="30" cy="6" r="9" fill="#1F1B16"></circle>'
           f'<path d="M54 -8 L120 -20 V8Z" fill="#FFF3C4" opacity="0.18"></path><circle cx="52" cy="-8" r="3" fill="#FFF3C4"></circle></g>')
    tree = f'<path d="M252 404 L232 404 L242 370 L236 370 L248 336 L260 370 L254 370 L264 404Z" fill="#2F5A3E"></path>' + "".join(f'<circle cx="{x}" cy="{y}" r="2.4" fill="{c}"></circle>' for x, y, c in [(244, 360, R), (252, 374, G), (240, 386, "#7FC8E8"), (256, 394, R), (248, 350, G)]) + star5(248, 334, 6, G)
    snow = "".join(f'<circle cx="{x}" cy="{y}" r="1.8" fill="#FFFFFF" opacity="0.8"></circle>' for x, y in [(30, 190), (90, 230), (150, 170), (210, 220), (270, 180), (60, 290), (240, 280), (120, 260)])
    return svg(f'''{stars_sky(SKY, C)}{snow}<circle cx="236" cy="186" r="16" fill="{C}"></circle>{house(20, 90, 64, "#5A3A2A", "#2A2A2E")}{house(130, 80, 76, "#3E4F66", "#2A2A2E")}{tree}
<rect y="404" width="300" height="196" fill="#EEF4F8"></rect><rect y="420" width="300" height="48" fill="#3A3F48"></rect><path d="M0 444 h30 M60 444 h30 M120 444 h30 M180 444 h30 M240 444 h30" stroke="{G}" stroke-width="3"></path>{car}''', "#0E1D2B")


def christmas_tree_farm():
    rows = "".join(pine(x, b, h, c) + f'<path d="M{x} {b - h} L{x - h * 0.1} {b - h * 0.8} H{x + h * 0.1}Z" fill="#FFFFFF" opacity="0.8"></path>'
                   for x, b, h, c in [(20, 320, 70, "#3E6B4E"), (60, 316, 60, "#3E6B4E"), (240, 318, 66, "#3E6B4E"), (280, 320, 72, "#3E6B4E"), (34, 360, 90, "#2F5A3E"), (266, 362, 94, "#2F5A3E")])
    car = (f'<g transform="translate(150 404)"><path d="M-70 -20 L-52 -42 H40 L62 -20 H76 Q84 -20 84 -10 V2 H-84 V-10 Q-84 -20 -76 -20Z" fill="{R}"></path>'
           f'<path d="M-46 -38 H-8 V-22 H-60Z M-2 -38 H36 L50 -22 H-2Z" fill="#BFD7EA"></path><circle cx="-46" cy="4" r="12" fill="#1F1B16"></circle><circle cx="46" cy="4" r="12" fill="#1F1B16"></circle>'
           f'<circle cx="-46" cy="4" r="5" fill="#8A8170"></circle><circle cx="46" cy="4" r="5" fill="#8A8170"></circle></g>')
    # the tree lies on the roof, trunk to the back, tied down with red twine
    tree = (f'<path d="M78 360 L96 340 L112 352 L130 330 L150 348 L170 326 L190 346 L208 330 L238 360Z" fill="#2F5A3E"></path>'
            f'<path d="M96 360 L112 344 L128 356 L146 338 L166 356 L186 340 L204 356 L222 346 L234 360Z" fill="#3E6B4E"></path>'
            f'<path d="M100 340 l4 6 M140 334 l4 6 M182 332 l4 6" stroke="#FFFFFF" stroke-width="2" opacity="0.8"></path>'
            f'<rect x="62" y="350" width="18" height="8" fill="#5A3A22"></rect><rect x="76" y="358" width="164" height="4" fill="#3A3F48"></rect>'
            f'<path d="M116 334 V364 M188 330 V364" stroke="#C8102E" stroke-width="3"></path>')
    flakes = "".join(f'<circle cx="{x}" cy="{y}" r="2" fill="#FFFFFF" opacity="0.85"></circle>' for x, y in [(40, 190), (110, 220), (180, 180), (250, 210), (140, 260), (210, 270), (70, 250)])
    return svg(f'''{sky("tfsky", "#4E6F92", "#D8E3EC")}{flakes}<path d="M0 330 Q150 310 300 330 V600 H0Z" fill="#F3F6F9"></path>{rows}{tree}{car}<rect y="418" width="300" height="182" fill="#E6ECF1"></rect>''', "#4E6F92")


# ---------------- visitors and evenings ----------------

def grandparents():
    house = (f'<rect x="56" y="270" width="188" height="130" fill="#E9DCC0"></rect><path d="M44 274 L150 204 L256 274Z" fill="#7A4A26"></path>'
             f'<rect x="56" y="330" width="188" height="10" fill="#FFFFFF"></rect><path d="M64 340 V400 M236 340 V400" stroke="#FFFFFF" stroke-width="6"></path>'
             f'<rect x="80" y="286" width="34" height="30" fill="#F6E3B0" stroke="#FFFFFF" stroke-width="3"></rect><rect x="186" y="286" width="34" height="30" fill="#F6E3B0" stroke="#FFFFFF" stroke-width="3"></rect>'
             f'<rect x="134" y="350" width="32" height="50" fill="{R}"></rect><circle cx="160" cy="376" r="2.4" fill="{G}"></circle>'
             f'{heart(150, 240, 0.7, R)}<path d="M50 400 H250 V408 H50Z" fill="#B48A5E"></path>')
    def rocker(x):
        return (f'<g transform="translate({x} 400)"><path d="M-14 0 Q0 6 14 0" stroke="#5C3A22" stroke-width="3" fill="none"></path><path d="M-10 -2 V-36 M10 -2 V-20 M-10 -20 H14" stroke="#5C3A22" stroke-width="3"></path>'
                f'<path d="M-10 -36 h8 v16" stroke="#5C3A22" stroke-width="3" fill="none"></path></g>')
    flowers = "".join(f'<circle cx="{x}" cy="{y}" r="5" fill="{c}"></circle>' for x, y, c in [(70, 404, "#E8A3B5"), (84, 406, "#F2C230"), (216, 404, "#E8A3B5"), (230, 406, "#8E6BBF"), (98, 404, R), (202, 406, R)])
    walk = '<path d="M134 408 L120 600 H180 L166 408Z" fill="#C9B89A"></path>'
    return svg(f'''{sky("gpsky", "#7FB8E8", "#F6E3B0")}{sun(240, 170, 16, "#F6C24A", False)}{cloud(60, 184, 0.8)}<path d="M0 404 Q150 394 300 404 V600 H0Z" fill="#6EA84E"></path>
{house}{rocker(92)}{rocker(208)}{flowers}{walk}''', "#7FB8E8")


def family_reunion():
    oak = (f'<path d="M150 404 V290 M150 330 L110 290 M150 316 L196 282" stroke="#5A3A22" stroke-width="16" stroke-linecap="round"></path>'
           + "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{c}"></circle>' for x, y, r, c in [(150, 236, 70, "#3F7A3A"), (90, 270, 46, "#4E8A4A"), (212, 266, 48, "#4E8A4A"), (118, 206, 40, "#4E8A4A"), (186, 204, 42, "#3F7A3A")])
           + "".join(heart(x, y, 0.42, c) for x, y, c in [(110, 236, R), (150, 210, "#E8A3B5"), (190, 236, R), (130, 270, "#E8A3B5"), (176, 278, R), (82, 278, "#E8A3B5"), (220, 280, "#E8A3B5"), (150, 252, R)]))
    table = (f'<rect x="30" y="384" width="240" height="10" fill="#8B5A2B"></rect><path d="M44 394 L36 430 M256 394 L264 430 M120 394 V430 M180 394 V430" stroke="#6E4826" stroke-width="5"></path>'
             f'<rect x="30" y="378" width="240" height="8" fill="{R}" opacity="0.8"></rect>')
    people = "".join(person(x, 430, 0.8, c) for x, c in [(20, BLUE), (66, "#F2C230"), (234, GREEN), (280, "#8E6BBF")])
    return svg(f'''{sky("frsky", "#6FA8D6", "#EAF3F0")}{bunting(176, 10, [R, G, BLUE], n=12)}<path d="M0 400 Q150 388 300 400 V600 H0Z" fill="#6EA84E"></path>{oak}{table}{people}''', "#6FA8D6")


def date_night():
    skyline = "".join(f'<rect x="{x}" y="{y}" width="{w}" height="{430 - y}" fill="#1A2740"></rect>' + "".join(f'<rect x="{x + 4 + c * 8}" y="{y + 8 + r * 12}" width="4" height="6" fill="#F6E3B0" opacity="{0.4 + ((r + c + x) % 3) * 0.2:.1f}"></rect>' for r in range((430 - y) // 14) for c in range(w // 8 - 1))
                      for x, y, w in [(0, 260, 40), (44, 220, 34), (82, 280, 30), (196, 240, 36), (236, 206, 30), (270, 270, 30)])
    table = (f'<ellipse cx="150" cy="392" rx="110" ry="22" fill="#FFFFFF"></ellipse><path d="M40 392 Q40 430 60 440 H240 Q260 430 260 392" fill="#F3EBDA"></path>'
             f'<ellipse cx="104" cy="390" rx="26" ry="7" fill="#E2D8C3"></ellipse><ellipse cx="196" cy="390" rx="26" ry="7" fill="#E2D8C3"></ellipse>')
    candle = (f'<rect x="144" y="336" width="12" height="46" fill="{CREAM}"></rect><path d="M150 312 Q142 326 150 334 Q158 326 150 312Z" fill="#F6C24A"></path>'
              f'<circle cx="150" cy="324" r="24" fill="#F6C24A" opacity="0.18"></circle><ellipse cx="150" cy="382" rx="16" ry="4" fill="{G}"></ellipse>')
    rose = (f'<path d="M206 386 L210 352" stroke="#BFD7EA" stroke-width="10" opacity="0.6"></path><path d="M208 352 q-2 -20 2 -30" stroke="{DKGREEN}" stroke-width="2.4" fill="none"></path>'
            f'<circle cx="210" cy="318" r="9" fill="#B3263A"></circle>')
    return svg(f'''{stars_sky(SKY, C)}<circle cx="70" cy="190" r="20" fill="{C}"></circle><circle cx="78" cy="184" r="17" fill="#141E30"></circle>{skyline}
{string_lights(300, 14, n=12, cols=("#F6E3B0",))}<rect y="430" width="300" height="170" fill="#2A1E2E"></rect>{table}{candle}{rose}{heart(104, 350, 0.5, "#E8A3B5")}''', "#141E30")


THEMES = {
    "birthday": birthday, "anniversary": anniversary, "firstday": first_day, "graduation": graduation,
    "baseball": baseball, "soccer": soccer, "football": football, "recital": recital, "schoolplay": school_play, "movienight": movie_night,
    "courtofhonor": court_of_honor, "pinewood": pinewood_derby, "scoutcamp": scout_camp,
    "picnic": picnic, "missiontrip": mission_trip, "churchcamp": church_camp, "christmasprogram": christmas_program,
    "fallfestival": fall_festival, "baptism": baptism,
    "spring": spring, "summer": summer, "fall": fall, "winter": winter, "snowday": snow_day,
    "zoo": zoo, "aquarium": aquarium, "fair": county_fair, "statepark": state_park, "lake": lake_day,
    "pumpkinpatch": pumpkin_patch, "applepicking": apple_picking, "christmaslights": christmas_lights, "treefarm": christmas_tree_farm,
    "grandparents": grandparents, "reunion": family_reunion, "datenight": date_night,
}

# What each picture is called in Settings, and the line under it on the frame.
NAMES = {
    "birthday": ("Birthday (their photo)", "Happy birthday!"), "anniversary": ("Anniversary", "Happy anniversary!"),
    "firstday": ("First day of school", "First day!"), "graduation": ("Graduation", "Congratulations!"),
    "baseball": ("Baseball / softball", "Play ball!"), "soccer": ("Soccer", "Game day!"), "football": ("Football", "Game day!"),
    "recital": ("Recital / concert", "Recital day!"), "schoolplay": ("School play", "Showtime!"), "movienight": ("Movie night / sleepover", "Movie night!"),
    "courtofhonor": ("Court of Honor / Eagle", "Court of Honor"), "pinewood": ("Pinewood Derby", "Race day!"), "scoutcamp": ("Scout summer camp", "Off to camp!"),
    "picnic": ("Church picnic / potluck", "Fellowship!"), "missiontrip": ("Mission trip", "Go and make disciples"),
    "churchcamp": ("Church camp / retreat", "Camp week!"), "christmasprogram": ("Christmas program", "Christmas program"),
    "fallfestival": ("Fall festival", "Fall festival!"), "baptism": ("Baptism", "Baptism day"),
    "spring": ("First day of spring", "Spring is here!"), "summer": ("First day of summer", "Summer!"), "fall": ("First day of fall", "Hello, fall!"),
    "winter": ("First day of winter", "Winter is here"), "snowday": ("Snow day", "Snow day!"),
    "zoo": ("Zoo", "Zoo day!"), "aquarium": ("Aquarium", "Aquarium day!"), "fair": ("County / state fair", "Fair day!"),
    "statepark": ("State park / hike", "Hike day!"), "lake": ("Lake day / boating", "Lake day!"),
    "pumpkinpatch": ("Pumpkin patch / hayride", "Pumpkin patch!"), "applepicking": ("Apple picking", "Apple picking!"),
    "christmaslights": ("Christmas lights drive", "Christmas lights!"), "treefarm": ("Christmas tree farm", "Tree day!"),
    "grandparents": ("Grandparents visiting", "Grandparents are here!"), "reunion": ("Family reunion", "Family reunion!"),
    "datenight": ("Date night", "Date night"),
}
assert set(NAMES) == set(THEMES)

# Words in an event title that pick these pictures (added to Settings > Special days; first match wins).
# Everyday things (a weekly game, Sunday potluck, dinner at Grandma's) only pick the picture for an event that's
# already special (⭐ or #special); the rest make the day special by themselves.
PICTURE_ONLY = {"Baseball", "Softball", "T-ball", "Soccer", "Football", "Concert", "Musical", "Movie night", "Sleepover",
                "Hike", "Hiking", "Boating", "Potluck", "Fellowship meal", "Grandparents", "Grandma", "Grandpa", "Date night"}
WORDS = [("Birthday", "birthday"), ("Bday", "birthday"), ("Anniversary", "anniversary"),
         ("First day of school", "firstday"), ("Back to school", "firstday"), ("Graduation", "graduation"), ("Commencement", "graduation"),
         ("Court of Honor", "courtofhonor"), ("Eagle Scout", "courtofhonor"), ("Pinewood Derby", "pinewood"),
         ("Scout camp", "scoutcamp"), ("Summer camp", "scoutcamp"),
         ("Christmas program", "christmasprogram"), ("Christmas cantata", "christmasprogram"), ("Christmas pageant", "christmasprogram"),
         ("Christmas lights", "christmaslights"), ("Tree farm", "treefarm"), ("Christmas tree", "treefarm"),
         ("Church camp", "churchcamp"), ("Retreat", "churchcamp"), ("Mission trip", "missiontrip"),
         ("Fall festival", "fallfestival"), ("Trunk or treat", "fallfestival"), ("Baptism", "baptism"),
         ("Picnic", "picnic"), ("Potluck", "picnic"), ("Fellowship meal", "picnic"),
         ("Baseball", "baseball"), ("Softball", "baseball"), ("T-ball", "baseball"), ("Soccer", "soccer"), ("Football", "football"),
         ("Recital", "recital"), ("Concert", "recital"), ("School play", "schoolplay"), ("Musical", "schoolplay"),
         ("Movie night", "movienight"), ("Sleepover", "movienight"), ("Snow day", "snowday"),
         ("Zoo", "zoo"), ("Aquarium", "aquarium"), ("County fair", "fair"), ("State fair", "fair"), ("4-H fair", "fair"),
         ("State park", "statepark"), ("Hike", "statepark"), ("Hiking", "statepark"), ("Lake day", "lake"), ("Boating", "lake"),
         ("Pumpkin patch", "pumpkinpatch"), ("Hayride", "pumpkinpatch"), ("Apple picking", "applepicking"), ("Orchard", "applepicking"),
         ("Grandparents", "grandparents"), ("Grandma", "grandparents"), ("Grandpa", "grandparents"),
         ("Family reunion", "reunion"), ("Reunion", "reunion"), ("Date night", "datenight")]
