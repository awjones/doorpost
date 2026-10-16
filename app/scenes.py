"""Inline SVG scenes for Doorpost special days. Portrait viewBox 0 0 300 600; art lives in y 150-420, x 60-240.
(Made into art packs by scripts/build-pack.py, see docs/art-packs.md; the Lord's Day series are in app/lordsday_art.py.)"""
import math
G, C, R, DIM = "#C9A55A", "#F3EBDA", "#C8102E", "#8C7A4E"

def svg(inner, bg, vb="0 0 300 600", par="xMidYMax slice"):
    return (f'<svg viewBox="{vb}" preserveAspectRatio="{par}" style="position: absolute; inset: 0; width: 100%; height: 100%" aria-hidden="true">'
            f'<rect width="100%" height="100%" fill="{bg}"></rect>{inner}</svg>')

def burst(cx, cy, r, color, n=14, w=2.2):
    out = []
    for i in range(n):
        a = 2 * math.pi * i / n
        x1, y1 = cx + math.cos(a) * r * 0.25, cy + math.sin(a) * r * 0.25
        x2, y2 = cx + math.cos(a) * r, cy + math.sin(a) * r
        out.append(f'<path d="M{x1:.1f} {y1:.1f}L{x2:.1f} {y2:.1f}" stroke="{color}" stroke-width="{w}" stroke-linecap="round"></path>')
        out.append(f'<circle cx="{x2:.1f}" cy="{y2:.1f}" r="{w*1.1:.1f}" fill="{color}"></circle>')
    return "".join(out)

def star5(cx, cy, r, color, rot=-90):
    pts = []
    for i in range(10):
        rr = r if i % 2 == 0 else r * 0.42
        a = math.radians(rot + 36 * i)
        pts.append(f"{cx + math.cos(a) * rr:.1f},{cy + math.sin(a) * rr:.1f}")
    return f'<polygon points="{" ".join(pts)}" fill="{color}"></polygon>'

def us_flag(x, y, h):
    """Proper U.S. flag, canton at the left (hoist) edge: 13 stripes, red top and bottom, 50 stars in 9 rows of 6 and 5."""
    w, st = h * 1.9, h / 13
    cw, ch = h * 0.76, st * 7
    out = [f'<rect x="{x}" y="{y}" width="{w:.1f}" height="{h}" fill="{C}"></rect>']
    out += [f'<rect x="{x}" y="{y + i * st:.2f}" width="{w:.1f}" height="{st:.2f}" fill="{R}"></rect>' for i in range(0, 13, 2)]
    out.append(f'<rect x="{x}" y="{y}" width="{cw:.1f}" height="{ch:.2f}" fill="#24406B"></rect>')
    r = h * 0.0616 / 2 * 1.15
    for row in range(9):
        sy = y + (row + 1) * ch / 10
        cols = [(2 * c + 1) for c in range(6)] if row % 2 == 0 else [(2 * c + 2) for c in range(5)]
        for c in cols:
            out.append(star5(x + c * cw / 12, sy, r, C))
    return "".join(out)

def heart(x, y, s, fill, stroke="none"):
    return (f'<path transform="translate({x} {y}) scale({s})" d="M0 12 C-14 0 -22 -10 -12 -18 C-6 -22 0 -18 0 -12 C0 -18 6 -22 12 -18 C22 -10 14 0 0 12Z" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{1.5/s:.2f}"></path>')

def frond(x1, y1, x2, y2, bend, color):
    mx, my = (x1 + x2) / 2 + bend, (y1 + y2) / 2
    out = [f'<path d="M{x1} {y1} Q{mx} {my} {x2} {y2}" stroke="{color}" stroke-width="3" fill="none"></path>']
    for i in range(3, 20):
        t = i / 20
        px = (1-t)**2*x1 + 2*(1-t)*t*mx + t*t*x2
        py = (1-t)**2*y1 + 2*(1-t)*t*my + t*t*y2
        dx = 2*(1-t)*(mx-x1) + 2*t*(x2-mx); dy = 2*(1-t)*(my-y1) + 2*t*(y2-my)
        L = math.hypot(dx, dy); ux, uy = dx/L, dy/L
        ln = 34 * math.sin(math.pi * t) + 6
        for sgn in (1, -1):
            nx, ny = -uy*sgn, ux*sgn
            ex, ey = px + (nx*0.8 - ux*0.6)*ln, py + (ny*0.8 - uy*0.6)*ln
            out.append(f'<path d="M{px:.1f} {py:.1f}L{ex:.1f} {ey:.1f}" stroke="{color}" stroke-width="2.2" stroke-linecap="round"></path>')
    return "".join(out)

def stars_sky(seed_pts, color=C):
    return "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}" opacity="0.8"></circle>' for x, y, r in seed_pts)

SKY = [(40,60,1.4),(80,120,1),(130,40,1.6),(190,90,1.2),(250,50,1.5),(270,140,1),(30,200,1.2),(220,170,1),(110,170,1.3),(160,130,1),(60,250,1),(250,240,1.3)]

def palm_sunday():
    return svg(f'''<path d="M120 600 L145 420 L155 420 L180 600Z" fill="{C}" opacity="0.12"></path>
<rect y="420" width="300" height="180" fill="#173027"></rect>
{frond(80, 430, 215, 175, -40, G)}{frond(220, 430, 85, 175, 40, "#B7C99A")}
{stars_sky(SKY[:6], G)}''', "#1E3B30")

def good_friday():
    return svg(f'''<defs><linearGradient id="gf" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1B1A21"></stop><stop offset="1" stop-color="#3A3440"></stop></linearGradient></defs>
<rect width="300" height="600" fill="url(#gf)"></rect>
<rect x="147" y="210" width="7" height="170" fill="{DIM}"></rect><rect x="120" y="244" width="61" height="7" fill="{DIM}"></rect>
<rect x="88" y="290" width="5" height="110" fill="#6A5D3E"></rect><rect x="72" y="314" width="37" height="5" fill="#6A5D3E"></rect>
<rect x="207" y="290" width="5" height="110" fill="#6A5D3E"></rect><rect x="191" y="314" width="37" height="5" fill="#6A5D3E"></rect>
<path d="M0 470 Q150 340 300 470 V600 H0Z" fill="#141318"></path>''', "#1B1A21")

def resurrection():
    rays = "".join(f'<path d="M150 400 L{150+math.cos(math.radians(a))*260:.0f} {400+math.sin(math.radians(a))*260:.0f}" stroke="{G}" stroke-width="5" opacity="0.28"></path>' for a in range(195, 350, 18))
    return svg(f'''<defs><linearGradient id="rs" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#16324F"></stop><stop offset="0.6" stop-color="#7A5A3A"></stop><stop offset="0.75" stop-color="#E0B66A"></stop></linearGradient></defs>
<rect width="300" height="600" fill="url(#rs)"></rect>{rays}
<circle cx="150" cy="420" r="80" fill="{G}"></circle>
<rect y="420" width="300" height="180" fill="#24402F"></rect>
<path d="M40 432 Q40 300 160 300 Q262 306 262 432Z" fill="#5A4C3E"></path>
<path d="M118 432 V380 A32 32 0 0 1 182 380 V432Z" fill="#FFF3D1"></path>
<circle cx="236" cy="396" r="40" fill="#776654" stroke="#4A3E32" stroke-width="3"></circle>
<path d="M60 432 h200" stroke="#1B3024" stroke-width="4"></path>''', "#16324F")

def reformation():
    lines = "".join(f'<path d="M126 {268+i*9} h{44 if i%3 else 30}" stroke="{DIM}" stroke-width="2"></path>' for i in range(7))
    return svg(f'''<rect y="430" width="300" height="170" fill="#2A1A12"></rect>
<path d="M70 432 V250 A80 80 0 0 1 230 250 V432Z" fill="#5A3A22" stroke="{G}" stroke-width="4"></path>
<path d="M110 432V200M150 432V172M190 432V200" stroke="#3E2716" stroke-width="3"></path>
<path d="M72 300h156M72 390h156" stroke="{DIM}" stroke-width="6"></path>
<g transform="rotate(-4 150 290)"><rect x="118" y="250" width="64" height="86" fill="{C}"></rect>{lines}<circle cx="150" cy="256" r="3" fill="#3E2716"></circle></g>
<rect x="56" y="430" width="188" height="12" fill="#6B5544"></rect>''', "#3A2418")

def christmas_eve():
    def candle(x, h):
        top = 420 - h
        return (f'<circle cx="{x+11}" cy="{top-14}" r="34" fill="{G}" opacity="0.18"></circle>'
                f'<rect x="{x}" y="{top}" width="22" height="{h}" rx="3" fill="{C}"></rect>'
                f'<path d="M{x+11} {top-30} Q{x+21} {top-12} {x+11} {top-4} Q{x+1} {top-12} {x+11} {top-30}Z" fill="{G}"></path>'
                f'<ellipse cx="{x+11}" cy="{top-12}" rx="3" ry="6" fill="#FFF6DC"></ellipse>')
    return svg(f'''{stars_sky(SKY)}{candle(96, 100)}{candle(139, 135)}{candle(182, 110)}
<ellipse cx="150" cy="424" rx="110" ry="16" fill="#1F4030"></ellipse><rect y="430" width="300" height="170" fill="#0C1729"></rect>''', "#101E33")

def christmas():
    return svg(f'''{stars_sky(SKY)}
<path d="M150 210 L105 350 L195 350Z" fill="{G}" opacity="0.18"></path>
<path d="M150 150 L157 203 L210 210 L157 217 L150 270 L143 217 L90 210 L143 203Z" fill="{G}"></path>
<circle cx="150" cy="210" r="8" fill="#FFF6DC"></circle>
<path d="M0 430 Q80 400 150 425 Q220 400 300 430 V600 H0Z" fill="#0B1626"></path>
<path d="M88 350 L150 300 L212 350Z" fill="#3A2A1E" stroke="{G}" stroke-width="3"></path>
<rect x="98" y="350" width="104" height="76" fill="#2A1E15"></rect>
<path d="M126 404 h48 l-8 18 h-32z" fill="#6B4E2E"></path><path d="M126 404 q24 -14 48 0" fill="{G}"></path>''', "#0F1F38")

def new_year():
    return svg(f'''{burst(105, 215, 62, G)}{burst(205, 175, 48, C, 12)}{burst(190, 300, 40, "#E07A7A", 12, 2)}
<text x="150" y="410" text-anchor="middle" font-family="Playfair Display, serif" font-size="66" font-weight="600" fill="{G}">2027</text>''', "#101C30")

def mlk():
    return svg(f'''<circle cx="205" cy="270" r="56" fill="{G}" opacity="0.9"></circle>
<path d="M0 440 L80 320 L130 360 L205 250 L300 410 V600 H0Z" fill="#26405A"></path>
<path d="M205 250 L188 276 L200 272 L210 282 L222 270Z" fill="{C}"></path>
<path d="M0 470 Q150 430 300 470 V600 H0Z" fill="#182A3E"></path>''', "#1B2B3F")

def valentine():
    return svg(f'''{heart(150, 300, 4.2, R, G)}{heart(85, 205, 1.2, C)}{heart(225, 230, 1.6, G)}{heart(215, 380, 1, C)}{heart(78, 360, 1.4, "#E58A9A")}''', "#561522")

def presidents():
    cols = "".join(f'<rect x="{x}" y="314" width="11" height="88" fill="{C}"></rect>' for x in (80, 104, 128, 161, 185, 209))
    stars = "".join(star5(150 + math.cos(math.radians(a))*95, 300 + math.sin(math.radians(a))*120, 7, G) for a in range(210, 335, 20))
    return svg(f'''{stars}<path d="M66 302 L150 254 L234 302Z" fill="{C}"></path><rect x="66" y="302" width="168" height="12" fill="{C}"></rect>
{cols}<rect x="58" y="402" width="184" height="10" fill="{C}"></rect><rect x="48" y="412" width="204" height="10" fill="{C}"></rect>
<rect y="422" width="300" height="178" fill="#10263D"></rect>''', "#16324F")

def mothers_day():
    def flower(x, y, col, r=13):
        petals = "".join(f'<circle cx="{x+math.cos(math.radians(a))*r:.1f}" cy="{y+math.sin(math.radians(a))*r:.1f}" r="{r*0.7:.1f}" fill="{col}"></circle>' for a in range(0, 360, 60))
        return petals + f'<circle cx="{x}" cy="{y}" r="{r*0.55:.1f}" fill="{G}"></circle>'
    stems = "".join(f'<path d="M150 360 Q{150+(x-150)*0.4} 320 {x} {y}" stroke="#6E8F5E" stroke-width="3" fill="none"></path>' for x, y in [(110,250),(150,220),(192,248),(128,295),(176,292)])
    return svg(f'''{stems}{flower(110,250,"#E8A3B5")}{flower(150,220,C)}{flower(192,248,"#D9788F")}{flower(128,295,C,11)}{flower(176,292,"#E8A3B5",11)}
<path d="M118 352 h64 l-10 74 h-44z" fill="{G}"></path><path d="M118 352 h64" stroke="{DIM}" stroke-width="4"></path>
<rect y="426" width="300" height="174" fill="#381A26"></rect>''', "#4A2333")

def memorial():
    stones = "".join(f'<path d="M{x} {y} v-{h} a{w/2} {w/2} 0 0 1 {w} 0 v{h}z" fill="{C}" opacity="{op}"></path>'
                     for row, (y, w, h, op) in enumerate([(372, 10, 12, 0.45), (398, 14, 16, 0.6), (430, 18, 20, 0.8)])
                     for x in range(18 + row*6, 290, 34 - row*2))
    return svg(f'''<rect y="350" width="300" height="250" fill="#2A3A2E"></rect>{stones}
<rect x="66" y="150" width="4" height="230" fill="{C}"></rect><circle cx="68" cy="148" r="5" fill="{G}"></circle>
{us_flag(70, 262, 46)}
<circle cx="70" cy="452" r="6" fill="{R}"></circle><circle cx="84" cy="458" r="5" fill="{R}"></circle><circle cx="210" cy="455" r="6" fill="{R}"></circle>''', "#1C2533")

def fathers_day():
    ripples = "".join(f'<path d="M{x} {y} h{w}" stroke="{C}" stroke-width="2" opacity="0.35"></path>' for x, y, w in [(60,370,60),(150,380,90),(90,400,70),(180,410,50),(40,420,50)])
    return svg(f'''<circle cx="150" cy="340" r="58" fill="{G}"></circle><rect y="340" width="300" height="260" fill="#14303A"></rect>
<path d="M150 342 h-50 M150 352 h60" stroke="{G}" stroke-width="3" opacity="0.6"></path>{ripples}
<path d="M40 450 Q120 300 236 190" stroke="#B08A55" stroke-width="5" fill="none" stroke-linecap="round"></path>
<path d="M236 190 L236 372" stroke="{C}" stroke-width="1.2"></path><circle cx="236" cy="374" r="6" fill="{R}"></circle>''', "#1F3E46")

def july4():
    return svg(f'''{burst(100, 200, 58, R)}{burst(205, 175, 50, C, 12)}{burst(165, 270, 38, "#7FA7D9", 12, 2)}
{us_flag(74, 326, 80)}''', "#0F1B30")

def labor_day():
    wheat = "".join(f'<path d="M{x} 440 q-4 -30 {(x%7)-3} -{50+(x%5)*6}" stroke="{G}" stroke-width="2" fill="none"></path><ellipse cx="{x+(x%7)-3}" cy="{385-(x%5)*6}" rx="3" ry="9" fill="{G}"></ellipse>' for x in range(20, 290, 14))
    return svg(f'''<circle cx="150" cy="300" r="62" fill="{G}" opacity="0.95"></circle>
<path d="M0 380 Q90 330 170 370 Q240 340 300 370 V600 H0Z" fill="#34472F"></path>{wheat}''', "#2A3B33")

def veterans():
    stars = "".join(star5(70 + i*40, 340, 12, G) for i in range(5))
    return svg(f'''<rect x="74" y="160" width="5" height="270" fill="{C}"></rect><circle cx="76" cy="158" r="6" fill="{G}"></circle>
{us_flag(79, 172, 74)}
{stars}<rect y="430" width="300" height="170" fill="#10263D"></rect>''', "#16324F")

def thanksgiving():
    sheaf = "".join(f'<path d="M150 430 L{150+math.cos(math.radians(a))*150:.0f} {430+math.sin(math.radians(a))*150:.0f}" stroke="{G}" stroke-width="3"></path><ellipse cx="{150+math.cos(math.radians(a))*150:.0f}" cy="{430+math.sin(math.radians(a))*150:.0f}" rx="5" ry="14" transform="rotate({a+90} {150+math.cos(math.radians(a))*150:.0f} {430+math.sin(math.radians(a))*150:.0f})" fill="{G}"></ellipse>' for a in range(235, 310, 9))
    def pumpkin(x, y, s, col):
        return (f'<g transform="translate({x} {y}) scale({s})"><ellipse cx="0" cy="0" rx="34" ry="26" fill="{col}"></ellipse>'
                f'<ellipse cx="0" cy="0" rx="14" ry="26" fill="none" stroke="#8A4A1A" stroke-width="2"></ellipse>'
                f'<path d="M0 -24 q2 -10 8 -12" stroke="#4E6B3A" stroke-width="5" fill="none"></path></g>')
    leaves = "".join(f'<path transform="translate({x} {y}) rotate({r})" d="M0 0 q8 -10 0 -22 q-8 12 0 22z" fill="{c}"></path>' for x, y, r, c in [(70,220,-20,"#A8432A"),(230,240,30,G),(90,330,40,"#C8742A"),(220,330,-30,"#A8432A")])
    pie = (f'<g transform="translate(150 392)">'
           f'<path d="M-46 0 L-38 22 H38 L46 0Z" fill="#9A6A34"></path>'
           f'<ellipse cx="0" cy="0" rx="46" ry="12" fill="#E2B26A"></ellipse>'
           f'<ellipse cx="0" cy="0" rx="38" ry="8.5" fill="#C8742A"></ellipse>'
           + "".join(f'<path d="M{-44 + i*8} {-3 + abs(i-5.5)*0.9:.1f} q4 -4 8 0" stroke="#F0CE8A" stroke-width="2" fill="none"></path>' for i in range(11))
           + f'<ellipse cx="2" cy="-3" rx="11" ry="5" fill="#FFF8EA"></ellipse><path d="M-6 -4 q8 -12 16 0" fill="#FFF8EA"></path></g>')
    return svg(f'''{sheaf}{leaves}{pumpkin(82, 396, 1.0, "#C8742A")}{pumpkin(222, 400, 0.85, "#D99A3E")}<rect y="418" width="300" height="182" fill="#2E1C0F"></rect>{pie}''', "#3E2614")

def school():
    windows = "".join(f'<rect x="{x}" y="336" width="20" height="18" rx="3" fill="#BFD7EA"></rect>' for x in range(90, 220, 26))
    return svg(f'''<circle cx="220" cy="230" r="46" fill="{G}"></circle>
{"".join(star5(x, y, 6, c) for x, y, c in [(70,190,C),(120,250,G),(250,320,C),(60,300,G)])}
<g transform="translate(0 -60)"><rect y="412" width="300" height="260" fill="#2B2B2E"></rect><path d="M0 470 h40 M70 470 h40 M140 470 h40 M210 470 h40 M280 470 h40" stroke="{G}" stroke-width="4"></path>
<rect x="56" y="324" width="190" height="78" rx="12" fill="#E8B21E"></rect><rect x="56" y="370" width="190" height="6" fill="#1F1B16"></rect>
{windows}<rect x="62" y="336" width="20" height="30" rx="3" fill="#BFD7EA"></rect>
<circle cx="96" cy="404" r="15" fill="#1F1B16"></circle><circle cx="96" cy="404" r="6" fill="#8A8170"></circle>
<circle cx="210" cy="404" r="15" fill="#1F1B16"></circle><circle cx="210" cy="404" r="6" fill="#8A8170"></circle>
<polygon points="44,342 50,336 58,336 64,342 64,350 58,356 50,356 44,350" fill="{R}"></polygon></g>''', "#1E3B5E")

def pattern():
    return svg(f'''<defs><pattern id="lat" width="36" height="36" patternUnits="userSpaceOnUse"><path d="M18 0 L36 18 L18 36 L0 18Z" fill="none" stroke="{G}" stroke-width="1" opacity="0.45"></path><circle cx="18" cy="18" r="2" fill="{G}" opacity="0.6"></circle></pattern></defs>
<rect width="300" height="600" fill="url(#lat)"></rect>''', "#16324F")

def vacation_wide():
    gulls = "".join(f'<path d="M{x} {y} q6 -6 12 0 q6 -6 12 0" stroke="{C}" stroke-width="2" fill="none"></path>' for x, y in [(300,90),(340,120),(380,80)])
    waves = "".join(f'<path d="M{x} {y} q15 -6 30 0 q15 6 30 0" stroke="{C}" stroke-width="2" fill="none" opacity="0.5"></path>' for x, y in [(60,320),(250,340),(430,315),(560,350),(150,370),(620,300)])
    fr = "".join(f'<path d="M150 150 Q{150+dx*0.5} {150+dy*0.2-30} {150+dx} {150+dy}" stroke="#3F7A5A" stroke-width="12" fill="none" stroke-linecap="round"></path>' for dx, dy in [(-90,30),(-70,70),(80,20),(95,60),(10,-60),(-40,-50)])
    stripes = "".join(f'<path d="M560 250 L{500+i*24} 300" stroke="{c}" stroke-width="2"></path>' for i, c in enumerate([C]*6))
    return svg(f'''<defs><linearGradient id="vs" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#16324F"></stop><stop offset="1" stop-color="#3E7090"></stop></linearGradient></defs>
<rect width="700" height="560" fill="url(#vs)"></rect>{gulls}
<circle cx="520" cy="250" r="68" fill="{G}"></circle>
<rect y="290" width="700" height="140" fill="#1F4E6B"></rect><path d="M470 300 h100 M490 318 h60 M505 334 h30" stroke="{G}" stroke-width="5" opacity="0.7"></path>{waves}
<path d="M0 420 Q350 380 700 420 V560 H0Z" fill="#D9C08A"></path>
<path d="M150 430 Q130 300 150 150" stroke="#7A5A3A" stroke-width="14" fill="none"></path>{fr}
<path d="M500 300 A60 60 0 0 1 620 300Z" fill="{R}"></path><path d="M540 300 A20 60 0 0 1 580 300Z" fill="{C}"></path><path d="M560 300 V420" stroke="{C}" stroke-width="4"></path>''',
               "#16324F", vb="0 0 700 560", par="xMidYMid slice")



def water_park():
    """A water park lodge: a timber entrance with a plain sign, and the water park rising behind it: a treehouse
    play fort with a giant bucket tipping a wall of water down the side, tube slides looping off its decks, and a slide tower."""
    sky = grad("wpsky", [(0, "#5B8FC7"), (0.75, "#C9DFF0"), (1, "#F4E6CC")])
    pines = "".join(f'<path d="M{x} {y} L{x - w} {y + h} H{x + w}Z" fill="{c}"></path>' for x, y, w, h, c in
                    [(14, 300, 18, 130, "#2F5A3E"), (36, 324, 15, 106, "#3A6B4A"), (268, 296, 20, 134, "#2F5A3E"), (290, 320, 15, 110, "#3A6B4A")])
    wood, dark, roofc = "#8B5A2B", "#5C3A22", "#4E6B5A"
    # the play fort: posts, three decks, railings, shingled peaks, a lookout with a cupola
    posts = "".join(f'<rect x="{x}" y="{y}" width="5" height="{430 - y}" fill="{dark}"></rect>' for x, y in [(70, 290), (112, 250), (156, 250), (206, 282)])
    decks = "".join(f'<rect x="{x0}" y="{y}" width="{x1 - x0}" height="7" fill="{wood}"></rect>'
                    + "".join(f'<path d="M{xx} {y - 12}V{y}" stroke="{dark}" stroke-width="1.4"></path>' for xx in range(x0 + 4, x1, 7))
                    + f'<path d="M{x0} {y - 12}H{x1}" stroke="{dark}" stroke-width="2"></path>'
                    for x0, x1, y in [(62, 206, 390), (66, 212, 336), (104, 214, 282)])
    roofs = (f'<path d="M58 296 L84 268 L110 296Z" fill="{roofc}"></path>'
             f'<rect x="114" y="226" width="40" height="30" fill="{wood}"></rect><rect x="122" y="234" width="9" height="10" fill="#F6E3B0"></rect><rect x="137" y="234" width="9" height="10" fill="#F6E3B0"></rect>'
             f'<path d="M108 228 L134 196 L160 228Z" fill="{roofc}"></path><path d="M134 196 V186" stroke="{dark}" stroke-width="2"></path><path d="M134 186 l9 3 l-9 3z" fill="#E5484D"></path>')
    shingles = "".join(f'<path d="M{x0} {y} H{x1}" stroke="#3E5A4A" stroke-width="1" opacity="0.7"></path>' for x0, x1, y in
                       [(68, 100, 286), (64, 104, 291), (122, 146, 210), (116, 152, 218)])
    # the giant bucket on an A-frame standing on the fort's top deck, tipping toward the right
    bucket = ('<path d="M172 276 L192 200 L212 276 M178 252 H206" stroke="#5C3A22" stroke-width="4" fill="none" stroke-linejoin="round"></path>'
              '<rect x="168" y="274" width="48" height="5" fill="#5C3A22"></rect>'
              '<g transform="rotate(28 192 200)"><path d="M172 176 H212 L208 222 H176Z" fill="#9A6A3A"></path>'
              '<path d="M173 186 H211 M174.5 206 H209.5" stroke="#5C3A22" stroke-width="3"></path>'
              '<ellipse cx="192" cy="176" rx="20" ry="4" fill="#6E4826"></ellipse></g>')
    # the wall of water: pouring off the bucket's lip, down the fort's side, into a splash
    water = ('<path d="M214 186 C232 204, 238 236, 236 274 C234 318, 240 360, 246 396 L206 400 C214 360, 214 318, 212 276 C210 236, 204 208, 202 192Z" fill="#E6F6FC" opacity="0.92"></path>'
             '<path d="M218 198 C228 228, 228 268, 226 310 C224 344, 228 372, 232 396" stroke="#9FD9F0" stroke-width="2.5" fill="none" opacity="0.8"></path>'
             '<path d="M210 210 C216 248, 218 300, 216 340" stroke="#BFE6F6" stroke-width="2" fill="none" opacity="0.8"></path>'
             + "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#E6F6FC" opacity="0.85"></circle>' for x, y, r in
                       [(196, 396, 10), (214, 402, 13), (236, 400, 12), (256, 398, 9), (226, 388, 8), (188, 386, 6), (262, 386, 5),
                        (244, 226, 2.5), (248, 252, 2), (240, 300, 2.5), (204, 260, 2), (250, 336, 2)]))
    # tube slides off the fort's decks
    def tube(d, col):
        return (f'<path d="{d}" stroke="{col}" stroke-width="10" fill="none" stroke-linecap="round"></path>'
                f'<path d="{d}" stroke="#FFFFFF" stroke-width="2.2" fill="none" opacity="0.4" stroke-linecap="round"></path>')
    tubes = (tube("M66 330 C40 324, 34 352, 52 362 C70 372, 58 398, 40 404", "#E5484D")
             + tube("M108 278 C84 270, 70 292, 88 306 C104 318, 100 338, 88 350 C76 362, 82 390, 102 410", "#F4B400")
             + tube("M166 330 C190 336, 186 362, 170 372 C156 382, 166 404, 186 408", "#3DAE2B"))
    tower = slides(244, 236, 410, ["#1E8FD5", "#C77DFF", "#F28C28"], "#5E6B73", "#38B6E8", "#4E6B5A")
    pool = '<rect x="0" y="404" width="300" height="26" fill="#38B6E8"></rect><path d="M0 406 q10 -4 20 0 t20 0 t20 0 t20 0 t20 0 t20 0 t20 0 t20 0 t20 0 t20 0 t20 0 t20 0 t20 0 t20 0 t20 0" stroke="#BFE6F6" stroke-width="2" fill="none"></path>'
    # the entrance, lower in the picture: a log wall, timber posts, the gabled roof with a sign (two waves)
    logs = "".join(f'<path d="M30 {y}H270" stroke="#6B4423" stroke-width="1.2" opacity="0.6"></path>' for y in range(450, 520, 6))
    entry = (f'<rect x="30" y="440" width="240" height="80" fill="{wood}"></rect>{logs}'
             + "".join(f'<rect x="{x}" y="454" width="14" height="12" rx="1" fill="#F6E3B0" stroke="#5C3A1E" stroke-width="1.5"></rect>' for x in (44, 242))
             + '<rect x="76" y="446" width="8" height="74" fill="#5C3A22"></rect><rect x="216" y="446" width="8" height="74" fill="#5C3A22"></rect>'
             '<path d="M52 446 L150 392 L248 446 L240 452 L150 402 L60 452Z" fill="#4A3524"></path>'
             '<path d="M66 444 L150 398 L234 444Z" fill="#6B4423"></path>'
             '<path d="M84 442 L150 406 L216 442 M150 406 V442" stroke="#3E2A1A" stroke-width="3" fill="none"></path>'
             '<rect x="56" y="446" width="188" height="6" fill="#3E2A1A"></rect>'
             '<rect x="128" y="410" width="44" height="44" rx="2" fill="#173A5E" stroke="#C9A55A" stroke-width="1.5"></rect>'
             '<path d="M136 432 q14 -10 28 0 M136 440 q14 -10 28 0" stroke="#7FC3E8" stroke-width="3" fill="none" stroke-linecap="round"></path>'
             # the front doors: a pair of timber doors with glass panes under a transom
             + '<rect x="116" y="460" width="68" height="60" fill="#3E2A1A"></rect><rect x="120" y="464" width="60" height="10" fill="#F6E3B0" opacity="0.85"></rect>'
             + "".join(f'<rect x="{x}" y="477" width="28" height="43" fill="#7A4A26" stroke="#3E2A1A" stroke-width="1"></rect>'
                       f'<rect x="{x + 5}" y="481" width="18" height="20" rx="1" fill="#BFD7EA" stroke="#3E2A1A" stroke-width="1"></rect>'
                       f'<rect x="{x + 5}" y="505" width="18" height="11" fill="none" stroke="#5C3A22" stroke-width="1"></rect>' for x in (121, 151))
             + '<path d="M146 492 V504 M154 492 V504" stroke="#C9A55A" stroke-width="2.2" stroke-linecap="round"></path>')
    plaza = '<rect y="520" width="300" height="80" fill="#9C9486"></rect><path d="M0 520 H300 V525 H0Z" fill="#B5AD9F"></path>'
    stones = "".join(f'<path d="M{x} {y} h26" stroke="#8A8274" stroke-width="1.2"></path>' for x, y in [(10, 548), (90, 566), (170, 552), (240, 576), (60, 588)])
    return svg(f'''{sky}<rect width="300" height="430" fill="url(#wpsky)"></rect>
<g fill="#FFFFFF" opacity="0.85"><ellipse cx="60" cy="182" rx="26" ry="9"></ellipse><ellipse cx="250" cy="170" rx="22" ry="8"></ellipse></g>
{pines}{tower}{pool}{posts}{decks}{roofs}{shingles}{tubes}{bucket}{water}{entry}{plaza}{stones}''', "#9C9486")


def vacation_tall():
    fr = "".join(f'<path d="M96 210 Q{96+dx*0.5} {210+dy*0.2-26} {96+dx} {210+dy}" stroke="#3F7A5A" stroke-width="10" fill="none" stroke-linecap="round"></path>' for dx, dy in [(-60,30),(-50,62),(58,24),(66,58),(8,-48),(-30,-40)])
    return svg(f'''<defs><linearGradient id="vt" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#16324F"></stop><stop offset="1" stop-color="#3E7090"></stop></linearGradient></defs>
<rect width="300" height="600" fill="url(#vt)"></rect>
<path d="M150 180 q6 -6 12 0 q6 -6 12 0 M190 150 q5 -5 10 0 q5 -5 10 0" stroke="{C}" stroke-width="2" fill="none"></path>
<circle cx="200" cy="300" r="52" fill="{G}"></circle><rect y="300" width="300" height="80" fill="#1F4E6B"></rect>
<path d="M170 310 h60 M182 324 h36" stroke="{G}" stroke-width="4" opacity="0.7"></path>
<path d="M40 340 q12 -5 24 0 q12 5 24 0 M200 356 q12 -5 24 0 q12 5 24 0" stroke="{C}" stroke-width="2" fill="none" opacity="0.5"></path>
<path d="M0 380 Q150 360 300 380 V600 H0Z" fill="#D9C08A"></path>
<path d="M100 410 Q86 310 96 210" stroke="#7A5A3A" stroke-width="11" fill="none"></path>{fr}
<path d="M180 372 A44 44 0 0 1 268 372Z" fill="{R}"></path><path d="M210 372 A14 44 0 0 1 238 372Z" fill="{C}"></path><path d="M224 372 V420" stroke="{C}" stroke-width="3"></path>
<ellipse cx="160" cy="412" rx="22" ry="5" fill="#C8102E" opacity="0.8"></ellipse>''', "#16324F")

def camping():
    trees = "".join(f'<path d="M{x} {b} L{x-w} {b} L{x} {b-h} L{x+w} {b}Z" fill="#14281F"></path><rect x="{x-3}" y="{b}" width="6" height="12" fill="#2A1E15"></rect>'
                    for x, b, w, h in [(40, 400, 30, 140), (85, 405, 24, 110), (255, 400, 32, 150), (215, 410, 22, 100)])
    flames = (f'<path d="M150 404 Q134 380 146 356 Q150 372 156 362 Q168 384 150 404Z" fill="#E07A2A"></path>'
              f'<path d="M150 404 Q142 388 149 374 Q154 386 158 380 Q160 394 150 404Z" fill="{G}"></path>')
    return svg(f'''{stars_sky(SKY)}<circle cx="226" cy="170" r="26" fill="{C}"></circle><circle cx="236" cy="164" r="22" fill="#0E1D2B"></circle>
{trees}<path d="M0 410 Q150 396 300 410 V600 H0Z" fill="#1B2E22"></path>
<path d="M58 404 L108 322 L158 404Z" fill="#C8742A"></path><path d="M108 322 L94 404 L122 404Z" fill="#F0CE8A"></path><path d="M108 322 L108 404" stroke="#7A4A1E" stroke-width="2"></path>
<circle cx="150" cy="392" r="34" fill="{G}" opacity="0.18"></circle>{flames}
<path d="M128 408 L172 398 M128 398 L172 408" stroke="#5A3A22" stroke-width="6" stroke-linecap="round"></path>''', "#0E1D2B")


def vbs():
    rays = "".join(f'<path d="M230 170 L{230+math.cos(math.radians(a))*66:.0f} {170+math.sin(math.radians(a))*66:.0f}" stroke="{G}" stroke-width="4" stroke-linecap="round"></path>' for a in range(0, 360, 30))
    flags = "".join(f'<path d="M{x} {232 + (x-20)*(280-x)/1300:.0f} l12 22 l12 -22z" fill="{c}"></path>' for x, c in zip(range(20, 290, 26), [R, G, "#2E8FB8", "#3F7A5A", "#E8A3B5"] * 3))
    return svg(f'''<defs><linearGradient id="vb" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1F5E8A"></stop><stop offset="1" stop-color="#7FB8D9"></stop></linearGradient></defs>
<rect width="300" height="600" fill="url(#vb)"></rect>{rays}<circle cx="230" cy="170" r="40" fill="{G}"></circle>
<path d="M0 230 Q150 260 300 230" stroke="{C}" stroke-width="2" fill="none"></path>{flags}
<path d="M0 404 Q150 386 300 404 V600 H0Z" fill="#4E8A4A"></path>
<rect x="90" y="300" width="100" height="104" fill="{C}"></rect><path d="M80 304 L140 262 L200 304Z" fill="{R}"></path>
<rect x="130" y="214" width="20" height="56" fill="{C}"></rect><path d="M124 218 L140 196 L156 218Z" fill="{R}"></path>
<path d="M138 168 h4 v10 h8 v4 h-8 v14 h-4 v-14 h-8 v-4 h8z" fill="{G}"></path>
<path d="M128 404 V358 A12 12 0 0 1 152 358 V404Z" fill="#7A4A1E"></path><rect x="104" y="330" width="14" height="18" fill="#7FB8D9"></rect><rect x="162" y="330" width="14" height="18" fill="#7FB8D9"></rect>
<g transform="translate(150 420)"><path d="M-44 -4 Q-22 -14 0 -4 Q22 -14 44 -4 L44 10 Q22 0 0 10 Q-22 0 -44 10Z" fill="{C}" stroke="#7A4A1E" stroke-width="2"></path><path d="M0 -4 V10" stroke="#7A4A1E" stroke-width="2"></path><path d="M-6 -8 L-6 14" stroke="{R}" stroke-width="3"></path></g>''', "#1F5E8A")

def roadtrip():
    car = f'''<g transform="translate(70 352)">
<rect x="0" y="22" width="150" height="34" rx="10" fill="{R}"></rect>
<path d="M24 22 L44 0 H108 L130 22Z" fill="{R}"></path><path d="M34 22 L50 6 H74 V22Z M80 6 H104 L120 22 H80Z" fill="#BFD7EA"></path>
<rect x="40" y="-14" width="34" height="14" rx="2" fill="#7A5A3A"></rect><rect x="78" y="-10" width="26" height="10" rx="2" fill="{G}"></rect><path d="M36 0 H112" stroke="#2A2A2E" stroke-width="3"></path>
<circle cx="34" cy="58" r="14" fill="#1F1B16"></circle><circle cx="34" cy="58" r="5" fill="#8A8170"></circle>
<circle cx="118" cy="58" r="14" fill="#1F1B16"></circle><circle cx="118" cy="58" r="5" fill="#8A8170"></circle>
<rect x="144" y="30" width="8" height="8" rx="2" fill="{G}"></rect></g>'''
    return svg(f'''<defs><linearGradient id="rt" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#16324F"></stop><stop offset="0.75" stop-color="#C98A4A"></stop></linearGradient></defs>
<rect width="300" height="600" fill="url(#rt)"></rect><circle cx="210" cy="300" r="46" fill="{G}"></circle>
<path d="M0 340 L60 260 L110 310 L170 230 L240 300 L300 250 V600 H0Z" fill="#3A3448"></path>
<path d="M0 360 L80 300 L150 345 L220 290 L300 330 V600 H0Z" fill="#2A2638"></path>
<rect y="400" width="300" height="200" fill="#2B2B2E"></rect><path d="M0 426 h36 M64 426 h36 M128 426 h36 M192 426 h36 M256 426 h36" stroke="{G}" stroke-width="4"></path>
<rect x="250" y="320" width="5" height="82" fill="#8A8170"></rect><path d="M232 318 h44 v22 h-44z" fill="#2F6B3A" stroke="{C}" stroke-width="2"></path>{car}''', "#16324F")


def airtravel():
    def cloud(x, y, s):
        return f'<g transform="translate({x} {y}) scale({s})" fill="{C}" opacity="0.92"><ellipse cx="0" cy="0" rx="30" ry="14"></ellipse><ellipse cx="22" cy="-8" rx="20" ry="14"></ellipse><ellipse cx="-20" cy="-4" rx="16" ry="11"></ellipse></g>'
    plane = f'''<g transform="translate(150 290) rotate(-18)">
<path d="M-90 0 C-90 -10 -70 -14 -40 -14 H70 C88 -14 96 -6 96 0 C96 6 88 10 70 10 H-60 C-80 10 -90 6 -90 0Z" fill="#FFFFFF"></path>
<path d="M-70 -12 L-86 -46 H-70 L-46 -12Z" fill="{R}"></path>
<path d="M-10 0 L-46 46 H-26 L30 0Z" fill="#E3E8EE"></path><path d="M-10 -8 L-30 -30 H-18 L14 -8Z" fill="#E3E8EE"></path>
{"".join(f'<circle cx="{x}" cy="-4" r="2.6" fill="#7FA7D9"></circle>' for x in range(-36, 66, 10))}
<path d="M76 -6 Q88 -6 90 0 H76Z" fill="#7FA7D9"></path></g>'''
    return svg(f'''<defs><linearGradient id="at" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#16324F"></stop><stop offset="1" stop-color="#5E9AC6"></stop></linearGradient></defs>
<rect width="300" height="600" fill="url(#at)"></rect><circle cx="236" cy="190" r="34" fill="{G}"></circle>
<path d="M-10 410 L64 320" stroke="{C}" stroke-width="4" stroke-dasharray="10 8" opacity="0.7"></path>
{cloud(70, 210, 1.1)}{cloud(230, 400, 1.3)}{cloud(40, 430, 0.9)}{plane}
<path d="M0 470 Q150 440 300 470 V600 H0Z" fill="#3E7090"></path>''', "#16324F")


def trip():
    route = '<path d="M86 312 C120 250, 150 360, 190 300 S 230 250, 222 230" stroke="#C8102E" stroke-width="3" stroke-dasharray="6 6" fill="none"></path>'
    return svg(f'''{stars_sky(SKY[:8], G)}
<path d="M50 210 L110 226 L170 206 L240 222 V360 L170 344 L110 364 L50 348Z" fill="{C}"></path>
<path d="M110 226 V364 M170 206 V344" stroke="#D9C9A6" stroke-width="2"></path>
<path d="M60 250 Q90 240 100 270 M180 240 Q200 280 230 270 M120 300 Q140 320 160 300" stroke="#9FC2A0" stroke-width="6" fill="none" opacity="0.8"></path>{route}
<path d="M222 212 C212 212 206 220 206 228 C206 240 222 254 222 254 C222 254 238 240 238 228 C238 220 232 212 222 212Z" fill="{R}"></path><circle cx="222" cy="228" r="5" fill="{C}"></circle>
<g transform="translate(82 360)"><rect x="0" y="16" width="110" height="74" rx="10" fill="#8B4F24"></rect><path d="M36 16 V4 H74 V16" stroke="#5A3A22" stroke-width="6" fill="none"></path>
<path d="M0 40 H110" stroke="#5A3A22" stroke-width="3"></path><circle cx="28" cy="62" r="11" fill="{G}"></circle><rect x="58" y="52" width="30" height="18" rx="3" fill="#2E8FB8"></rect><circle cx="92" cy="30" r="6" fill="{C}"></circle></g>
<rect y="450" width="300" height="150" fill="#10263D"></rect>''', "#16324F")


def church_glass():
    panes = [("M100 230 L150 200 L150 290 L100 290Z", R), ("M150 200 L200 230 L200 290 L150 290Z", "#2E8FB8"),
             ("M100 290 H150 V360 H100Z", "#3F7A5A"), ("M150 290 H200 V360 H150Z", "#E8B21E"),
             ("M100 360 H150 V420 H100Z", "#7A4A9A"), ("M150 360 H200 V420 H150Z", R)]
    glass = "".join(f'<path d="{d}" fill="{c}" opacity="0.88"></path>' for d, c in panes)
    return svg(f'''<rect width="300" height="600" fill="#101E33"></rect><circle cx="150" cy="320" r="130" fill="{G}" opacity="0.14"></circle>
<path d="M90 424 V240 A60 60 0 0 1 210 240 V424Z" fill="#1F1B16"></path>{glass}
<path d="M150 214 V420 M100 290 H200 M100 360 H200" stroke="#1F1B16" stroke-width="5"></path>
<path d="M140 250 H160 V282 H182 V300 H160 V380 H140 V300 H118 V282 H140Z" fill="{G}" stroke="#000000" stroke-width="4" stroke-linejoin="round"></path>
<path d="M90 424 V240 A60 60 0 0 1 210 240 V424Z" fill="none" stroke="{G}" stroke-width="6"></path>
<rect x="76" y="424" width="148" height="12" fill="#5A4636"></rect><rect y="436" width="300" height="164" fill="#0B1626"></rect>''', "#101E33")



# ---------------- parks and trains ----------------

def grad(gid, stops, x2=0, y2=1):
    s = "".join(f'<stop offset="{o}" stop-color="{c}"></stop>' for o, c in stops)
    return f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="{x2}" y2="{y2}">{s}</linearGradient></defs>'



def slides(base_x, top, ground, colors, deck, pool, roof):
    """A water park slide tower (colored roof) with three wide tubes looping down to a splash pool."""
    posts = "".join(f'<path d="M{base_x + dx} {top}V{ground}" stroke="{deck}" stroke-width="3.5"></path>' for dx in (0, 30))
    posts += "".join(f'<path d="M{base_x} {y}L{base_x + 30} {y + 20}M{base_x + 30} {y}L{base_x} {y + 20}" stroke="{deck}" stroke-width="1.4" opacity="0.8"></path>' for y in range(int(top) + 8, int(ground) - 20, 20))
    deckbar = f'<rect x="{base_x - 6}" y="{top - 4}" width="42" height="7" rx="2" fill="{deck}"></rect>'
    roof_ = f'<path d="M{base_x - 10} {top - 4} L{base_x + 15} {top - 24} L{base_x + 40} {top - 4}Z" fill="{roof}"></path>'
    def loop_path(x0, y0, dir_, drop):
        # down and around twice, then out to the pool
        x, y = x0, y0
        d = f"M{x} {y}"
        for k in range(2):
            d += f" C {x + dir_ * 46} {y + 4}, {x + dir_ * 48} {y + drop * 0.5}, {x + dir_ * 6} {y + drop * 0.55}"
            d += f" S {x - dir_ * 18} {y + drop * 0.95}, {x + dir_ * 14} {y + drop}"
            x, y = x + dir_ * 14, y + drop
        return d
    tubes = ""
    specs = [(base_x + 32, top + 4, 1, (ground - top - 20) / 2.2), (base_x - 2, top + 4, -1, (ground - top - 18) / 2.1), (base_x + 15, top + 10, 1, (ground - top - 26) / 2.3)]
    for (x0, y0, dir_, drop), c in zip(specs, colors):
        d = loop_path(x0, y0, dir_, drop)
        tubes += (f'<path d="{d}" stroke="rgba(0,0,0,0.2)" stroke-width="13" fill="none" stroke-linecap="round" transform="translate(1.5 2)"></path>'
                  f'<path d="{d}" stroke="{c}" stroke-width="11" fill="none" stroke-linecap="round"></path>'
                  f'<path d="{d}" stroke="#FFFFFF" stroke-width="2.5" fill="none" opacity="0.45" stroke-linecap="round"></path>')
    water = f'<ellipse cx="{base_x + 15}" cy="{ground + 1}" rx="62" ry="9" fill="{pool}"></ellipse>'
    splash = "".join(f'<circle cx="{base_x + x}" cy="{ground - y}" r="{r}" fill="{pool}" opacity="0.95"></circle>' for x, y, r in [(46, 8, 3.5), (54, 15, 2.5), (-18, 9, 3.5), (-24, 16, 2.5), (30, 10, 3)])
    return posts + deckbar + roof_ + tubes + water + splash




def park():
    """Any amusement park: Ferris wheel, coaster loop, carousel and pennants; the sign says the park's name ({{PLACE}})."""
    sky = grad("pksky", [(0, "#5BA7D9"), (0.75, "#BFE3F2"), (1, "#FCE9C8")])
    spokes = "".join(f'<path d="M95 330 L{95 + 62 * math.cos(a):.1f} {330 + 62 * math.sin(a):.1f}" stroke="#F3EBDA" stroke-width="1.6"></path>' for a in [i * math.pi / 6 for i in range(12)])
    gondolas = "".join(f'<rect x="{95 + 62 * math.cos(a) - 5:.1f}" y="{330 + 62 * math.sin(a):.1f}" width="10" height="9" rx="2" fill="{c}"></rect>'
                       for a, c in zip([i * math.pi / 6 for i in range(12)], ["#C8102E", "#F4B400", "#1D4E89", "#3DAE2B"] * 3))
    pennants = "".join(f'<path d="M{x} {170 + 10 * math.sin(x / 300 * math.pi):.0f} l7 15 l7 -15z" fill="{c}"></path>'
                       for x, c in zip(range(10, 300, 18), ["#C8102E", "#F4B400", "#1D4E89", "#3DAE2B"] * 5))
    loop = ('<path d="M150 430 C 170 380, 190 330, 222 300 C 260 266, 280 320, 252 340 C 226 360, 210 320, 236 300 C 262 282, 290 300, 310 330" '
            'stroke="#C8102E" stroke-width="5" fill="none"></path>'
            + "".join(f'<path d="M{x} {y}V430" stroke="#9AA6B2" stroke-width="2"></path>' for x, y in [(170, 384), (196, 330), (252, 340), (290, 316)]))
    carousel = ('<path d="M160 430 V398 H250 V430" fill="#FCE9C8"></path><path d="M152 398 L205 368 L258 398Z" fill="#C8102E"></path>'
                '<path d="M166 398 L205 376 L244 398" fill="#F4B400"></path><circle cx="205" cy="364" r="4" fill="#F4B400"></circle>'
                + "".join(f'<path d="M{x} 398 V430" stroke="#C9A55A" stroke-width="2"></path>' for x in range(170, 250, 16)))
    sign = ('<g><path d="M72 196 V250 M228 196 V250" stroke="#16324F" stroke-width="5"></path>'
            '<rect x="64" y="200" width="172" height="44" rx="12" fill="#16324F" stroke="#C9A55A" stroke-width="3"></rect>'
            '<text x="150" y="231" text-anchor="middle" font-family="Playfair Display, Georgia, serif" font-weight="700" font-size="{{PLACE_SIZE}}" fill="#F3EBDA">{{PLACE}}</text></g>')
    return svg(f'''{sky}<rect width="300" height="430" fill="url(#pksky)"></rect>
<path d="M0 166 Q150 186 300 166" stroke="#F3EBDA" stroke-width="1.5" fill="none"></path>{pennants}
{sign}
<circle cx="95" cy="330" r="62" stroke="#F3EBDA" stroke-width="3" fill="none"></circle>{spokes}{gondolas}<circle cx="95" cy="330" r="7" fill="#F4B400"></circle>
<path d="M95 330 L66 430 M95 330 L124 430" stroke="#F3EBDA" stroke-width="4"></path>
{loop}{carousel}
<rect y="430" width="300" height="170" fill="#5DA34E"></rect><path d="M0 430 Q150 422 300 432 V438 H0Z" fill="#71B860"></path>''', "#5DA34E")

def _loco(x, y, s=1.0, boiler="#1F1B16", cab="#B3262D", trim="#C9A55A", smoke=True):
    """A friendly large-scale steam locomotive facing right; (x, y) is the rail under its rear wheel."""
    p = []
    p.append(f'<g transform="translate({x} {y}) scale({s})">')
    if smoke:
        p.append('<g fill="#F3EBDA" opacity="0.85"><circle cx="66" cy="-62" r="7"></circle><circle cx="58" cy="-76" r="9"></circle><circle cx="46" cy="-92" r="11"></circle><circle cx="30" cy="-104" r="12"></circle></g>')
    p.append(f'<rect x="0" y="-46" width="26" height="30" rx="2" fill="{cab}"></rect><rect x="-3" y="-50" width="32" height="6" rx="2" fill="{boiler}"></rect>'
             f'<rect x="6" y="-40" width="12" height="10" rx="1.5" fill="#F6E3B0"></rect>'
             f'<rect x="26" y="-38" width="50" height="22" rx="10" fill="{boiler}"></rect>'
             f'<path d="M30 -38 V-16 M44 -38 V-16 M58 -38 V-16" stroke="{trim}" stroke-width="1.6"></path>'
             f'<rect x="62" y="-58" width="9" height="20" fill="{boiler}"></rect><path d="M59 -60 H74 L72 -55 H61Z" fill="{boiler}"></path>'
             f'<path d="M46 -38 a6 6 0 0 1 12 0" fill="{trim}"></path>'
             f'<circle cx="78" cy="-30" r="5" fill="#FFE08A" stroke="{trim}" stroke-width="1.5"></circle>'
             f'<path d="M76 -16 L92 0 H70Z" fill="{cab}"></path>'
             f'<rect x="-4" y="-18" width="82" height="5" fill="#3A332B"></rect>'
             f'<circle cx="12" cy="-8" r="8" fill="{cab}" stroke="{boiler}" stroke-width="2"></circle><circle cx="34" cy="-9" r="9" fill="{cab}" stroke="{boiler}" stroke-width="2"></circle>'
             f'<circle cx="56" cy="-9" r="9" fill="{cab}" stroke="{boiler}" stroke-width="2"></circle><path d="M34 -9 H56" stroke="{trim}" stroke-width="2.4"></path>'
             '</g>')
    return "".join(p)

def garden_train():
    """A garden railroad (train shows, club layouts): a large-scale steam engine and caboose on a wooden trestle among rocks, conifers and flowers."""
    sky = grad("gtsky", [(0, "#9BD0EC"), (1, "#EAF6FB")])
    trestle = "".join(f'<path d="M{x} 386 L{x - 8} 470 M{x} 386 L{x + 8} 470" stroke="#7A5233" stroke-width="2.4"></path>' for x in range(40, 280, 28))
    trestle += "".join(f'<path d="M30 {y} H270" stroke="#7A5233" stroke-width="1.6"></path>' for y in (414, 442))
    ties = "".join(f'<rect x="{x}" y="384" width="5" height="5" fill="#5C3A22"></rect>' for x in range(22, 284, 9))
    caboose = ('<g transform="translate(40 382)"><rect x="0" y="-30" width="40" height="22" rx="2" fill="#C8102E"></rect><rect x="12" y="-40" width="16" height="10" fill="#C8102E"></rect>'
               '<rect x="5" y="-25" width="8" height="8" fill="#F6E3B0"></rect><rect x="27" y="-25" width="8" height="8" fill="#F6E3B0"></rect>'
               '<rect x="-2" y="-8" width="44" height="4" fill="#3A332B"></rect><circle cx="9" cy="-3" r="5" fill="#3A332B"></circle><circle cx="31" cy="-3" r="5" fill="#3A332B"></circle></g>')
    conifer = lambda x, y, h, c: f'<path d="M{x} {y - h} L{x - h * 0.32} {y} H{x + h * 0.32}Z" fill="{c}"></path><rect x="{x - 2}" y="{y}" width="4" height="6" fill="#5C3A22"></rect>'
    flowers = "".join(f'<circle cx="{x}" cy="{y}" r="3" fill="{c}"></circle>' for x, y, c in
                      [(30, 488, "#E5484D"), (42, 494, "#F4B400"), (230, 490, "#E5484D"), (246, 486, "#C77DFF"), (262, 494, "#F4B400"), (120, 500, "#F4B400"), (180, 498, "#E5484D")])
    rocks = '<path d="M0 478 Q30 456 64 470 Q96 448 120 478 Z" fill="#9A9184"></path><path d="M180 480 Q220 452 256 468 Q286 456 300 474 V482 H180Z" fill="#8C8376"></path>'
    return svg(f'''{sky}<rect width="300" height="470" fill="url(#gtsky)"></rect>
{conifer(40, 380, 120, "#2F6B45")}{conifer(262, 372, 140, "#285E3D")}{conifer(214, 380, 80, "#3A7D52")}
<path d="M0 470 H300 V600 H0Z" fill="#6E9F4F"></path>{rocks}
<rect x="30" y="384" width="240" height="4" fill="#5C3A22"></rect>{ties}{trestle}
<path d="M14 388 H286" stroke="#B9B2A6" stroke-width="2"></path>
{caboose}{_loco(94, 382, 1.1)}
{flowers}<path d="M0 520 Q150 506 300 522 V600 H0Z" fill="#5F8F43"></path>''', "#5F8F43")

def trains():
    """Chasing trains: a steam engine on the main line at sunset, a railroad crossing sign in front."""
    sky = grad("trsky", [(0, "#324B7A"), (0.6, "#E58F5B"), (1, "#F7D08A")])
    crossbuck = ('<g transform="translate(232 352)"><path d="M0 0 V110" stroke="#E9E2D2" stroke-width="4"></path>'
                 '<path d="M-26 -14 L26 14 M-26 14 L26 -14" stroke="#F3EBDA" stroke-width="9" stroke-linecap="square"></path>'
                 '<path d="M-26 -14 L26 14 M-26 14 L26 -14" stroke="#1F1B16" stroke-width="1" opacity="0.4"></path>'
                 '<rect x="-14" y="28" width="28" height="12" rx="3" fill="#1F1B16"></rect><circle cx="-7" cy="34" r="4" fill="#E5484D"></circle><circle cx="7" cy="34" r="4" fill="#5A1A1A"></circle></g>')
    ties = "".join(f'<path d="M{x} 438 L{x + 6} 446" stroke="#3A2A1E" stroke-width="3"></path>' for x in range(-4, 304, 10))
    cars = ('<g transform="translate(-22 430)"><rect x="0" y="-30" width="54" height="24" rx="2" fill="#6B3A2A"></rect><rect x="-2" y="-8" width="58" height="4" fill="#2A221C"></rect>'
            '<circle cx="10" cy="-3" r="5" fill="#2A221C"></circle><circle cx="44" cy="-3" r="5" fill="#2A221C"></circle></g>')
    return svg(f'''{sky}<rect width="300" height="440" fill="url(#trsky)"></rect>
<circle cx="200" cy="300" r="34" fill="#FBD38D" opacity="0.9"></circle>
<path d="M0 360 Q60 330 120 352 Q190 318 300 346 V440 H0Z" fill="#3E5A6B" opacity="0.7"></path>
<path d="M0 396 Q90 376 180 392 Q240 380 300 394 V440 H0Z" fill="#2E4A3E"></path>
<path d="M0 434 H300 V600 H0Z" fill="#3A5530"></path>{ties}<path d="M0 436 H300 M0 444 H300" stroke="#C9C2B6" stroke-width="2"></path>
{cars}{_loco(40, 432, 1.3, boiler="#1F1B16", cab="#1F1B16", trim="#C9A55A")}
{crossbuck}''', "#3A5530")



def cruise():
    """A cruise on one of the big modern ships, straight from the side, heading right:
    a raked bow, a block of balcony decks with a sloped front and bridge wings, big yellow lifeboats set into the hull,
    funnels and water slides on top. A palm island ahead on the horizon, gulls overhead."""
    sky = grad("crsky", [(0, "#4FA9DD"), (0.7, "#BFE6F6"), (1, "#FCEBCB")])
    sea = grad("crsea", [(0, "#1E7FB8"), (1, "#0D4C7A")])
    hullg = grad("crhull", [(0, "#FFFFFF"), (1, "#DCE6EE")])
    gulls = "".join(f'<path d="M{x} {y} q5 -6 10 0 q5 -6 10 0" stroke="#FFFFFF" stroke-width="2" fill="none" stroke-linecap="round"></path>'
                    for x, y in [(70, 196), (94, 208), (210, 176)])
    island = ('<path d="M238 342 Q264 326 300 332 V344Z" fill="#E9D3A6"></path><path d="M244 342 Q268 330 300 336 V344 H244Z" fill="#6DB04F"></path>'
              '<path d="M280 336 Q277 316 284 300" stroke="#7A5A3A" stroke-width="3" fill="none"></path>'
              '<path d="M284 300 q-13 -3 -20 4 M284 300 q-10 -10 -20 -9 M284 300 q4 -13 16 -13 M284 300 q13 -3 19 6" stroke="#3F7A3A" stroke-width="3" fill="none" stroke-linecap="round"></path>')
    W, D, T = 380, 336, 300                     # waterline, main deck, top of the decks (lower and shorter)
    stern, bow = 22, 278                        # x of the stern and the tip of the bow
    # hull: square-ish stern on the left, the bow raked forward on the right
    hull = (f'<path d="M{stern} {D} H{bow} L{bow - 26} {W} H{stern + 6} Z" fill="url(#crhull)"></path>'
            f'<path d="M{stern + 6} {W} H{bow - 26} L{bow - 29} {W + 8} H{stern + 9} Z" fill="#16324F"></path>'
            f'<path d="M{stern + 4} {W - 12} H{bow - 22}" stroke="#2E86C1" stroke-width="2.5"></path>')
    hull_clip = f'<clipPath id="crhullclip"><path d="M{stern} {D} H{bow} L{bow - 26} {W} H{stern + 6} Z"></path></clipPath>'
    recess = f'<rect x="{stern + 8}" y="{D}" width="{bow - stern - 30}" height="11" fill="#24384D"></rect>'
    boats = "".join(f'<rect x="{x}" y="{D + 2}" width="17" height="7" rx="3.5" fill="#F4B400" stroke="#C98A00" stroke-width="0.6"></rect>'
                    f'<rect x="{x + 3}" y="{D + 1}" width="11" height="2.5" rx="1.2" fill="#FFFFFF"></rect>' for x in range(stern + 12, bow - 40, 22))
    ports = f'<g clip-path="url(#crhullclip)">' + "".join(f'<rect x="{x}" y="{D + 20}" width="3.5" height="3" rx="1" fill="#1E5C86"></rect>' for x in range(stern + 10, bow - 30, 7)) + '</g>'
    # the decks: one block, its front sloping back from the main deck up to the top (no bulge)
    fb, ft = bow - 30, bow - 46                 # front of the block at the main deck, and at the top
    block_d = f'M{stern + 4} {T} H{ft} L{fb} {D} H{stern + 4} Z'
    block = (f'<clipPath id="crblock"><path d="{block_d}"></path></clipPath>'
             f'<path d="{block_d}" fill="#FFFFFF" stroke="#D3DEE8" stroke-width="0.8"></path>')
    rows = "".join(f'<rect x="{stern + 8}" y="{T + 5 + k * 9}" width="{fb - stern}" height="5.5" fill="{"#3A93CC" if k % 2 == 0 else "#2E86C1"}"></rect>'
                   for k in range(4))
    divs = "".join(f'<path d="M{x} {T + 5}V{T + 5 + 3 * 9 + 5.5}" stroke="#FFFFFF" stroke-width="0.7" opacity="0.75"></path>' for x in range(stern + 14, fb, 6))
    glass = f'<g clip-path="url(#crblock)">{rows}{divs}</g>'
    # bridge wings: a bar across the top front, reaching just past the sloped front
    wings = (f'<rect x="{ft - 40}" y="{T + 1}" width="{48}" height="6" fill="#FFFFFF" stroke="#C9D5E0" stroke-width="0.8"></rect>'
             f'<path d="M{ft - 36} {T + 4} H{ft + 4}" stroke="#16324F" stroke-width="2"></path>')
    rail = f'<path d="M{stern + 6} {T - 3} H{ft - 2}" stroke="#9FC9E6" stroke-width="2"></path>'
    def slide(c, x, h, w):
        return (f'<path d="M{x} {T} C{x - w} {T - h * 0.7:.1f}, {x + w} {T - h * 0.85:.1f}, {x - w * 0.4:.1f} {T - h}" stroke="{c}" stroke-width="3.5" fill="none" stroke-linecap="round"></path>')
    slides = ""                                 # (no rooftop slides: they read as squiggles at this size)
    def funnel(fx):
        return (f'<path d="M{fx} {T} L{fx + 2} {T - 22} H{fx + 16} L{fx + 18} {T} Z" fill="#FFFFFF" stroke="#C9D5E0" stroke-width="0.8"></path>'
                f'<rect x="{fx + 2}" y="{T - 22}" width="14" height="5" fill="#1D4E89"></rect>'
                f'<circle cx="{fx + 9}" cy="{T - 10}" r="2.4" fill="#C9A55A"></circle>')
    funnels = funnel(52) + funnel(76)
    mast = f'<path d="M{ft - 26} {T} V{T - 18} M{ft - 32} {T - 12} H{ft - 20}" stroke="#16324F" stroke-width="2"></path><circle cx="{ft - 26}" cy="{T - 19}" r="2" fill="#C8102E"></circle>'
    # foam hugging the ship: a bow wave curling around the front, and the churn wrapping the stern
    foam = (f'<path d="M{bow - 40} {W - 2} Q{bow - 24} {W - 9} {bow - 20} {W - 1} Q{bow - 12} {W + 3} {bow - 2} {W + 1} Q{bow - 18} {W + 9} {bow - 46} {W + 6}Z" fill="#FFFFFF" opacity="0.95"></path>'
            f'<path d="M{bow - 6} {W + 4} Q{bow + 4} {W + 6} {bow + 10} {W + 3}" stroke="#FFFFFF" stroke-width="2" fill="none" opacity="0.7" stroke-linecap="round"></path>'
            f'<path d="M{stern + 30} {W + 6} Q{stern + 8} {W + 9} {stern + 2} {W + 2} Q{stern - 2} {W - 4} {stern + 6} {W - 4} Q{stern + 2} {W + 1} {stern + 12} {W + 1} Q{stern + 24} {W + 2} {stern + 30} {W + 6}Z" fill="#FFFFFF" opacity="0.95"></path>'
            f'<path d="M{stern - 4} {W + 4} Q{stern - 12} {W + 6} {stern - 14} {W + 2}" stroke="#FFFFFF" stroke-width="2" fill="none" opacity="0.7" stroke-linecap="round"></path>')
    waves = "".join(f'<path d="M{x} {y} q8 -5 16 0 q8 -5 16 0" stroke="#7FC3E8" stroke-width="2" fill="none" opacity="0.7"></path>'
                    for x, y in [(40, 410), (150, 420), (240, 404), (70, 446), (190, 466), (10, 500), (130, 520), (240, 540)])
    return svg(f'''{sky}{sea}{hullg}<defs>{hull_clip}</defs><rect width="300" height="344" fill="url(#crsky)"></rect>
<circle cx="62" cy="214" r="24" fill="#FFD36B"></circle>{gulls}
<rect y="338" width="300" height="262" fill="url(#crsea)"></rect>{island}
{slides}{funnels}{mast}{rail}{block}{glass}{wings}{hull}{recess}{boats}{ports}{foam}{waves}''', "#0D4C7A", par="xMaxYMax slice")


THEMES = {
  "palm": palm_sunday, "goodfriday": good_friday, "easter": resurrection, "reformation": reformation,
  "xmaseve": christmas_eve, "christmas": christmas, "newyear": new_year, "mlk": mlk, "valentine": valentine,
  "presidents": presidents, "mothers": mothers_day, "memorial": memorial, "fathers": fathers_day,
  "july4": july4, "labor": labor_day, "veterans": veterans, "thanksgiving": thanksgiving, "school": school,
  "pattern": pattern, "waterpark": water_park, "vacation": vacation_tall, "beach": vacation_tall, "roadtrip": roadtrip, "flight": airtravel, "trip": trip, "churchglass": church_glass, "camping": camping, "vbs": vbs,
  "park": park, "gardentrain": garden_train, "trains": trains, "cruise": cruise,
}
