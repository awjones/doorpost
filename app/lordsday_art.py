"""Lord's Day pictures: five series of inline SVG drawings (52 Lord's Day, the Ten Commandments,
the Trinity, the 1689 Confession chapters, the books of the Bible). Signs and objects only:
never a picture of Christ, the Father or the Spirit. Portrait viewBox 0 0 300 600, art in y 150-420.
Words and meanings that go with them are in app/lordsday.py."""
import math

from .scenes import DIM, SKY, C, G, R, star5, stars_sky, svg


SUNDAYS = [
 ("The Lord's Day", "Sunrise over the church door", "This is the day that the LORD has made", "Psalm 118:24"),
 ("Sola Scriptura", "Open Bible in light", "All Scripture is God-breathed", "2 Timothy 3:16"),
 ("Sola Fide", "Shield of faith", "Justified through faith, we have peace with God", "Romans 5:1"),
 ("Sola Gratia", "A gift, freely given", "By grace you have been saved through faith", "Ephesians 2:8"),
 ("Solus Christus", "Empty cross", "There is one mediator between God and men", "1 Timothy 2:5"),
 ("Soli Deo Gloria", "Crown with rays", "To Him be the glory forever!", "Romans 11:36"),
 ("Believer's Baptism", "Still river, ripples", "Buried with Him in baptism", "Colossians 2:12"),
 ("The Lord's Supper", "Bread and cup", "Do this in remembrance of Me", "Luke 22:19"),
 ("Preach the Word", "Pulpit with open Bible", "Preach the word; be prepared in season and out of season", "2 Timothy 4:2"),
 ("A Lamp to My Feet", "Oil lamp on a path", "Your word is a lamp to my feet", "Psalm 119:105"),
 ("A Mighty Fortress", "Stone fortress on a rock", "God is our refuge and strength", "Psalm 46:1"),
 ("The Lord Is My Shepherd", "Shepherd's crook and sheep", "The LORD is my shepherd; I shall not want", "Psalm 23:1"),
 ("Anchor of Hope", "Anchor and rope", "We have this hope as an anchor for the soul, firm and secure", "Hebrews 6:19"),
 ("The Vine", "Grapevine and branches", "I am the vine and you are the branches", "John 15:5"),
 ("A City on a Hill", "Lit town on a hilltop", "A city on a hill cannot be hidden", "Matthew 5:14"),
 ("The Rock", "Cleft in the rock", "The LORD is my rock, my fortress", "Psalm 18:2"),
 ("Living Water", "Spring in the desert", "The water I give him will become in him a fount of water", "John 4:14"),
 ("Bread of Life", "Loaves and basket", "I am the bread of life", "John 6:35"),
 ("The Ark", "Ark on the waters", "A few people, only eight souls, were saved through water", "1 Peter 3:20"),
 ("The Door", "Open door, light inside", "I am the gate. If anyone enters through Me, he will be saved", "John 10:9"),
 ("The Armor of God", "Helmet, shield and sword", "Put on the full armor of God", "Ephesians 6:11"),
 ("Sword of the Spirit", "Sword over the Bible", "The sword of the Spirit, which is the word of God", "Ephesians 6:17"),
 ("The Rainbow", "Rainbow over the hills", "I have set My rainbow in the clouds", "Genesis 9:13"),
 ("Covenant of Grace", "Sealed scroll", "I will be their God, and they will be My people", "Jeremiah 31:33"),
 ("The Heavens Declare", "Sun, moon and stars", "The heavens declare the glory of God", "Psalm 19:1"),
 ("Providence", "A sparrow", "Not one of them will fall to the ground apart from the will of your Father", "Matthew 10:29"),
 ("The Harvest", "Ripe wheat field", "The harvest is plentiful, but the workers are few", "Matthew 9:37"),
 ("Go and Make Disciples", "Globe and compass", "Go and make disciples of all nations", "Matthew 28:19"),
 ("The Mustard Seed", "Seed and great tree", "The kingdom of heaven is like a mustard seed", "Matthew 13:31"),
 ("Pearl of Great Price", "One pearl", "When he found one very precious pearl... sold all he had", "Matthew 13:46"),
 ("Salt and Light", "Salt cellar and candle", "You are the salt of the earth", "Matthew 5:13"),
 ("Built on the Rock", "House on a rock", "A wise man who built his house on the rock", "Matthew 7:24"),
 ("The Narrow Gate", "Gate and narrow path", "Small is the gate and narrow the way that leads to life", "Matthew 7:14"),
 ("Psalms and Hymns", "Open hymnal, notes", "Sing psalms, hymns, and spiritual songs", "Colossians 3:16"),
 ("Prayer", "Incense rising from a bowl", "May my prayer be set before You like incense", "Psalm 141:2"),
 ("The Gathered Church", "Lit church on the Lord's Day", "Let us not neglect meeting together", "Hebrews 10:25"),
 ("Elders and Deacons", "Shepherd's crook and basin", "With the overseers and deacons", "Philippians 1:1"),
 ("Chosen in Him", "Book of names", "He chose us in Him before the foundation of the world", "Ephesians 1:4"),
 ("Robe of Righteousness", "White robe", "He has clothed me with garments of salvation and wrapped me in a robe of righteousness", "Isaiah 61:10"),
 ("No Condemnation", "Broken chains", "There is now no condemnation", "Romans 8:1"),
 ("Adopted", "Home with lit windows", "You received the Spirit of adoption to sonship", "Romans 8:15"),
 ("The Refiner's Fire", "Silver in the crucible", "He will sit as a refiner and purifier of silver", "Malachi 3:3"),
 ("Run the Race", "Track and laurel wreath", "Let us run with endurance the race set out for us", "Hebrews 12:1"),
 ("Crown of Life", "Gold crown", "He will receive the crown of life", "James 1:12"),
 ("The Trumpet", "Trumpet and clouds", "With the trumpet of God", "1 Thessalonians 4:16"),
 ("Tree of Life", "Tree by the river", "On either side of the river stood a tree of life", "Revelation 22:2"),
 ("The Law of the Lord", "Two stone tablets", "The Law of the LORD is perfect, reviving the soul", "Psalm 19:7"),
 ("A Sabbath Rest", "Still waters, green pasture", "There remains, then, a Sabbath rest for the people of God", "Hebrews 4:9"),
 ("Repent and Believe", "Signpost turning home", "Repent and believe in the gospel!", "Mark 1:15"),
 ("The Faith Delivered", "The 1689 Confession", "Contend earnestly for the faith entrusted once for all to the saints", "Jude 3"),
 ("The Burden Rolled Away", "Pilgrim's burden at the cross", "He Himself bore our sins in His body on the tree", "1 Peter 2:24"),
 ("New Every Morning", "Sunrise over the fields", "His mercies never fail. They are new every morning", "Lamentations 3:22–23"),
]
assert len(SUNDAYS) == 52 and len({s[0] for s in SUNDAYS}) == 52

def sola_scriptura():
    rays = "".join(f'<path d="M150 330 L{150+math.cos(math.radians(a))*190:.0f} {330+math.sin(math.radians(a))*190:.0f}" stroke="{G}" stroke-width="4" opacity="0.35"></path>' for a in range(200, 345, 15))
    return svg(f'''{rays}<circle cx="150" cy="330" r="60" fill="{G}" opacity="0.18"></circle>
<path d="M60 340 Q105 318 150 340 Q195 318 240 340 L240 400 Q195 380 150 400 Q105 380 60 400Z" fill="{C}" stroke="#8B4F24" stroke-width="3"></path>
<path d="M150 340 V400" stroke="#8B4F24" stroke-width="3"></path>{"".join(f'<path d="M{x} {352+i*10} h{w}" stroke="{DIM}" stroke-width="2"></path>' for i in range(4) for x, w in [(76, 58), (164, 58)])}
<path d="M144 396 L144 432 L150 426 L156 432 L156 396Z" fill="{R}"></path><rect y="440" width="300" height="160" fill="#10263D"></rect>''', "#16324F")

def baptism():
    ripples = "".join(f'<ellipse cx="150" cy="380" rx="{r}" ry="{r*0.28:.0f}" fill="none" stroke="{C}" stroke-width="2" opacity="{0.8 - i*0.12:.2f}"></ellipse>' for i, r in enumerate((18, 40, 64, 90, 118)))
    reeds = "".join(f'<path d="M{x} 360 q{d} -40 {d*1.5:.0f} -80" stroke="#3F7A5A" stroke-width="4" fill="none"></path>' for x, d in [(22, 4), (34, -3), (270, -4), (282, 3), (258, 2)])
    return svg(f'''<defs><linearGradient id="bp" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#16324F"></stop><stop offset="0.55" stop-color="#E0B66A"></stop></linearGradient></defs>
<rect width="300" height="600" fill="url(#bp)"></rect><circle cx="150" cy="320" r="46" fill="{G}"></circle>
<path d="M0 330 Q80 300 150 322 Q220 300 300 330 V600 H0Z" fill="#2E5E58"></path><rect y="340" width="300" height="260" fill="#1F4E6B"></rect>{ripples}{reeds}''', "#16324F")

def supper():
    return svg(f'''{stars_sky(SKY[:6], G)}<circle cx="150" cy="300" r="110" fill="{G}" opacity="0.12"></circle>
<path d="M30 400 H270 L290 440 H10Z" fill="{C}"></path><path d="M10 440 H290 V452 H10Z" fill="#D9C9A6"></path>
<path d="M70 398 C70 360 90 346 120 346 C150 346 166 360 166 398Z" fill="#B07A40"></path><path d="M84 370 q14 -10 28 0 M106 362 q14 -10 28 0 M128 370 q14 -10 28 0" stroke="#7A4A1E" stroke-width="3" fill="none"></path>
<path d="M184 300 Q184 346 214 352 Q244 346 244 300Z" fill="#C9A55A" stroke="#8C6A2A" stroke-width="2"></path><ellipse cx="214" cy="300" rx="30" ry="7" fill="#7A1E2B" stroke="#8C6A2A" stroke-width="2"></ellipse><rect x="210" y="351" width="8" height="34" fill="#C9A55A"></rect><ellipse cx="214" cy="388" rx="22" ry="7" fill="#C9A55A" stroke="#8C6A2A" stroke-width="2"></ellipse><path d="M194 310 Q196 336 210 344" stroke="#F0D98C" stroke-width="3" fill="none" opacity="0.7"></path>''', "#16324F")

def fortress():
    battl = lambda x, w: "".join(f'<rect x="{x + i*14}" y="-12" width="9" height="12" fill="#8A8170"></rect>' for i in range(w))
    return svg(f'''{stars_sky(SKY[:7])}<path d="M20 430 Q60 360 150 350 Q240 360 280 430Z" fill="#4A4038"></path>
<g transform="translate(0 0)"><rect x="70" y="260" width="160" height="100" fill="#8A8170"></rect><g transform="translate(70 260)">{battl(0, 12)}</g>
<rect x="50" y="220" width="44" height="140" fill="#9A9080"></rect><g transform="translate(50 220)">{battl(0, 3)}</g>
<rect x="206" y="220" width="44" height="140" fill="#9A9080"></rect><g transform="translate(206 220)">{battl(0, 3)}</g>
<path d="M134 360 V318 A16 16 0 0 1 166 318 V360Z" fill="#2A1E15"></path>
<path d="M72 200 V172 M228 200 V172" stroke="{C}" stroke-width="2"></path><path d="M72 172 l20 7 l-20 7Z M228 172 l20 7 l-20 7Z" fill="{R}"></path>
<rect x="66" y="250" width="12" height="18" rx="6" fill="#2A1E15"></rect><rect x="222" y="250" width="12" height="18" rx="6" fill="#2A1E15"></rect></g>
<rect y="430" width="300" height="170" fill="#10263D"></rect>''', "#16324F")

def anchor():
    return svg(f'''<rect y="380" width="300" height="220" fill="#1F4E6B"></rect>
<path d="M0 390 q25 -10 50 0 t50 0 t50 0 t50 0 t50 0 t50 0" stroke="{C}" stroke-width="2" fill="none" opacity="0.5"></path>
<circle cx="150" cy="200" r="16" fill="none" stroke="{G}" stroke-width="7"></circle><rect x="144" y="214" width="12" height="160" fill="{G}"></rect>
<rect x="112" y="240" width="76" height="11" rx="5" fill="{G}"></rect>
<path d="M88 320 Q96 380 150 380 Q204 380 212 320" stroke="{G}" stroke-width="12" fill="none" stroke-linecap="round"></path>
<path d="M76 330 L88 306 L102 330Z M198 330 L212 306 L224 330Z" fill="{G}"></path>
<path d="M150 184 C110 150, 90 220, 120 250 S 200 280, 186 330" stroke="#B9A06E" stroke-width="3" fill="none" stroke-dasharray="6 4"></path>''', "#16324F")

def tablets():
    nums = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
    txt = "".join(f'<text x="{x}" y="{y}" text-anchor="middle" font-family="Playfair Display, serif" font-size="18" font-weight="600" fill="#5A4636">{n}</text>'
                  for (x, y), n in zip([(100, 280 + i*30) for i in range(5)] + [(200, 280 + i*30) for i in range(5)], nums))
    return svg(f'''<circle cx="150" cy="320" r="120" fill="{G}" opacity="0.14"></circle>
<path d="M58 410 V250 A42 42 0 0 1 142 250 V410Z" fill="#B8AE9A" stroke="#7A7060" stroke-width="3"></path>
<path d="M158 410 V250 A42 42 0 0 1 242 250 V410Z" fill="#B8AE9A" stroke="#7A7060" stroke-width="3"></path>{txt}
<rect y="420" width="300" height="180" fill="#3A3448"></rect>''', "#2A2638")

def pilgrim():
    return svg(f'''<defs><linearGradient id="pg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#16324F"></stop><stop offset="0.7" stop-color="#C98A4A"></stop></linearGradient></defs>
<rect width="300" height="600" fill="url(#pg)"></rect>
<path d="M0 420 L120 250 Q150 230 180 250 L300 420 V600 H0Z" fill="#3F7A5A"></path>
<rect x="146" y="170" width="8" height="84" fill="{C}"></rect><rect x="126" y="192" width="48" height="8" fill="{C}"></rect>
<path d="M200 410 V380 A22 22 0 0 1 244 380 V410Z" fill="#1F1B16"></path><path d="M188 412 Q222 360 256 412Z" fill="none" stroke="#5A4C3E" stroke-width="6"></path>
<path d="M150 256 C 140 300, 190 330, 212 392" stroke="#E8D3A0" stroke-width="6" fill="none" stroke-dasharray="3 7" stroke-linecap="round"></path>
<g transform="translate(206 368) rotate(28)"><rect x="-16" y="-12" width="32" height="24" rx="6" fill="#7A5A3A"></rect><path d="M-16 0 H16 M0 -12 V12" stroke="#5A3A22" stroke-width="3"></path></g>
<path d="M60 420 Q120 380 150 300" stroke="#E8D3A0" stroke-width="10" fill="none" stroke-linecap="round" opacity="0.8"></path>''', "#16324F")

def confession():
    return svg(f'''{stars_sky(SKY[:8], G)}<circle cx="150" cy="320" r="110" fill="{G}" opacity="0.12"></circle>
<rect x="84" y="220" width="132" height="180" rx="6" fill="#4A2A1A" stroke="{G}" stroke-width="3"></rect><rect x="96" y="232" width="108" height="156" rx="4" fill="none" stroke="{G}" stroke-width="1.5"></rect>
<text x="150" y="292" text-anchor="middle" font-family="Playfair Display, serif" font-size="15" font-weight="600" fill="{G}">CONFESSION</text>
<text x="150" y="312" text-anchor="middle" font-family="Playfair Display, serif" font-size="12" fill="{G}">OF FAITH</text>
<text x="150" y="356" text-anchor="middle" font-family="Playfair Display, serif" font-size="34" font-weight="700" fill="{G}">1689</text>
<path d="M226 230 C250 260 246 330 214 384" stroke="{C}" stroke-width="3" fill="none"></path><path d="M226 230 C214 262 222 300 232 318 C 244 290 246 256 226 230Z" fill="{C}"></path>
<rect y="410" width="300" height="190" fill="#10263D"></rect>''', "#16324F")

N, BR, GR, DG, BL, SK = "#16324F", "#7A5A3A", "#3F7A5A", "#2F6B3A", "#2E8FB8", "#5E9AC6"
_gid = [0]
def grad(top, bottom, stop=1.0):
    _gid[0] += 1; i = f"sg{_gid[0]}"
    return (f'<defs><linearGradient id="{i}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{top}"></stop>'
            f'<stop offset="{stop}" stop-color="{bottom}"></stop></linearGradient></defs><rect width="300" height="600" fill="url(#{i})"></rect>')
def ground(y, col): return f'<path d="M0 {y} Q150 {y-22} 300 {y} V600 H0Z" fill="{col}"></path>'
def rays(cx, cy, r, a0=0, a1=360, step=20, w=4, op=0.35, col=G):
    return "".join(f'<path d="M{cx} {cy} L{cx+math.cos(math.radians(a))*r:.0f} {cy+math.sin(math.radians(a))*r:.0f}" stroke="{col}" stroke-width="{w}" opacity="{op}"></path>' for a in range(a0, a1, step))
def glow(cx, cy, r, op=0.16): return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{G}" opacity="{op}"></circle>'
def sheep(x, y, s=1):
    return (f'<g transform="translate({x} {y}) scale({s})"><ellipse cx="0" cy="0" rx="22" ry="14" fill="{C}"></ellipse>'
            f'<circle cx="-12" cy="-6" r="9" fill="{C}"></circle><circle cx="10" cy="-8" r="9" fill="{C}"></circle><ellipse cx="22" cy="-2" rx="7" ry="6" fill="#2A2A2E"></ellipse>'
            f'<path d="M-12 12 v8 M12 12 v8" stroke="#2A2A2E" stroke-width="3"></path></g>')
def house(x, y, w, col=C, roof=R, lit=True):
    win = G if lit else "#7FA7D9"
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{w*0.7:.0f}" fill="{col}"></rect><path d="M{x-6} {y} L{x+w/2:.0f} {y-w*0.45:.0f} L{x+w+6} {y}Z" fill="{roof}"></path>'
            f'<rect x="{x+w*0.15:.0f}" y="{y+w*0.18:.0f}" width="{w*0.2:.0f}" height="{w*0.18:.0f}" fill="{win}"></rect><rect x="{x+w*0.65:.0f}" y="{y+w*0.18:.0f}" width="{w*0.2:.0f}" height="{w*0.18:.0f}" fill="{win}"></rect>'
            f'<rect x="{x+w*0.4:.0f}" y="{y+w*0.36:.0f}" width="{w*0.2:.0f}" height="{w*0.34:.0f}" fill="{BR}"></rect>')
def cross(x, y, h, col=C):
    w = h * 0.1
    return f'<rect x="{x-w/2:.1f}" y="{y}" width="{w:.1f}" height="{h}" fill="{col}"></rect><rect x="{x-h*0.3:.1f}" y="{y+h*0.22:.1f}" width="{h*0.6:.1f}" height="{w:.1f}" fill="{col}"></rect>'
def church(x, y, s=1, lit=True):
    return (f'<g transform="translate({x} {y}) scale({s})"><rect x="-50" y="-60" width="100" height="70" fill="{C}"></rect><path d="M-58 -60 L0 -100 L58 -60Z" fill="{R}"></path>'
            f'<rect x="-11" y="-130" width="22" height="40" fill="{C}"></rect><path d="M-16 -128 L0 -150 L16 -128Z" fill="{R}"></path>{cross(0, -178, 26, G)}'
            f'<path d="M-12 10 V-18 A12 12 0 0 1 12 -18 V10Z" fill="{G if lit else BR}"></path>'
            f'<rect x="-38" y="-46" width="14" height="18" fill="{G if lit else "#7FA7D9"}"></rect><rect x="24" y="-46" width="14" height="18" fill="{G if lit else "#7FA7D9"}"></rect></g>')
def book(cx, cy, w=180, col=C, edge="#8B4F24"):
    h = w / 2
    return (f'<path d="M{cx-h} {cy} Q{cx-h/2} {cy-22} {cx} {cy} Q{cx+h/2} {cy-22} {cx+h} {cy} L{cx+h} {cy+60} Q{cx+h/2} {cy+40} {cx} {cy+60} Q{cx-h/2} {cy+40} {cx-h} {cy+60}Z" fill="{col}" stroke="{edge}" stroke-width="3"></path>'
            f'<path d="M{cx} {cy} V{cy+60}" stroke="{edge}" stroke-width="3"></path>'
            + "".join(f'<path d="M{x} {cy+12+i*10} h{h-24}" stroke="{DIM}" stroke-width="2"></path>' for i in range(4) for x in (cx-h+14, cx+10)))
def flame(x, y, s=1):
    return (f'<g transform="translate({x} {y}) scale({s})"><path d="M0 0 Q-16 -22 -4 -46 Q0 -30 6 -38 Q18 -18 0 0Z" fill="#E07A2A"></path>'
            f'<path d="M0 0 Q-8 -14 -1 -28 Q4 -18 8 -22 Q10 -8 0 0Z" fill="{G}"></path></g>')
NIGHT = lambda: stars_sky(SKY)

def lords_day():
    return svg(grad(N, "#E0A85A", 0.75) + glow(150, 330, 70, 0.6) + rays(150, 330, 200, 190, 350, 16, 4, 0.3) + ground(380, DG) + church(150, 380, 1.0), N)
def sola_fide():
    darts = "".join(f'<g transform="translate({x} {y}) rotate({a})"><path d="M0 0 h40" stroke="{BR}" stroke-width="3"></path><path d="M40 -5 l10 5 l-10 5z" fill="#8A8170"></path></g>' for x, y, a in [(30, 230, 20), (240, 260, 160), (40, 380, -15)])
    return svg(NIGHT() + glow(150, 300, 110) + '<path d="M150 200 L230 228 V300 Q230 370 150 410 Q70 370 70 300 V228Z" fill="#8C6A2A" stroke="#C9A55A" stroke-width="6"></path>'
               + cross(150, 240, 120, C) + darts, N)
def sola_gratia():
    return svg(grad(N, "#2E4A7A") + rays(150, 320, 170, 0, 360, 24, 3, 0.25) + glow(150, 320, 90)
               + f'<rect x="90" y="300" width="120" height="100" rx="6" fill="{R}"></rect><rect x="82" y="282" width="136" height="26" rx="5" fill="#A80E26"></rect>'
               + f'<rect x="142" y="282" width="16" height="118" fill="{G}"></rect><path d="M150 282 C120 240 96 270 150 282 C204 270 180 240 150 282Z" fill="none" stroke="{G}" stroke-width="8"></path>', N)
def solus_christus():
    return svg(grad("#1B1A21", "#C98A4A", 0.8) + rays(150, 260, 220, 0, 360, 18, 5, 0.22) + glow(150, 260, 60, 0.5) + ground(400, "#2A2A2E") + cross(150, 200, 200, "#E8D3A0"), "#1B1A21")
def soli_deo_gloria():
    return svg(grad(N, "#24406B") + rays(150, 300, 200, 0, 360, 12, 3, 0.3) + glow(150, 300, 100, 0.25)
               + f'<text x="150" y="335" text-anchor="middle" font-family="Pinyon Script, cursive" font-size="62" fill="{G}">S.D.G.</text>'
               + f'<path d="M80 360 h140" stroke="{G}" stroke-width="2"></path>', N)
def preach():
    return svg(grad(N, "#3A2A1E") + glow(150, 300, 110, 0.2)
               + f'<path d="M96 300 H204 L196 420 H104Z" fill="#7A4A1E" stroke="#5A3A22" stroke-width="3"></path><rect x="88" y="290" width="124" height="14" fill="#5A3A22"></rect>'
               + f'<path d="M150 302 V418" stroke="#5A3A22" stroke-width="2"></path>' + book(150, 252, 120)
               + f'<rect y="420" width="300" height="180" fill="#2A1E15"></rect>', N)
def lamp():
    stones = "".join(f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{rx*0.35:.0f}" fill="#8A8170"></ellipse>' for x, y, rx in [(150, 476, 34), (126, 444, 24), (160, 418, 18)])
    return svg(NIGHT() + glow(170, 320, 100, 0.25) + ground(420, "#1F2A22") + stones
               + f'<path d="M92 344 Q86 312 120 306 L196 306 Q232 306 226 328 L212 330 Q206 350 160 360 Q100 362 92 344Z" fill="#B07A40"></path>'
               + f'<ellipse cx="140" cy="314" rx="22" ry="6" fill="#5A3A22"></ellipse><path d="M92 330 Q66 330 72 312 Q78 300 96 312" stroke="#B07A40" stroke-width="7" fill="none"></path>'
               + flame(222, 324, 1.2), N)


def shepherd():
    return svg(grad("#1F4A6E", "#9FC8E0", 0.7) + ground(380, "#5E9A4A") + sheep(90, 380, 1.1) + sheep(170, 400, 1.2) + sheep(230, 372, 0.9)
               + f'<path d="M150 420 V230 Q150 196 180 196 Q206 196 206 222 Q206 240 190 240" stroke="#7A4A1E" stroke-width="8" fill="none" stroke-linecap="round"></path>', "#7FB8D9")
def vine():
    grapes = lambda x, y: "".join(f'<circle cx="{x+dx}" cy="{y+dy}" r="9" fill="#5B2A6E"></circle>' for dx, dy in [(0, 0), (16, 0), (8, 14), (-8, 14), (24, 14), (0, 28), (16, 28), (8, 42)])
    leaf = lambda x, y, a: f'<path transform="translate({x} {y}) rotate({a})" d="M0 0 Q20 -26 40 0 Q20 26 0 0Z" fill="{GR}"></path>'
    return svg(grad("#2A3B33", "#4A5A3A") + f'<path d="M20 200 C 90 160, 210 160, 280 210" stroke="{BR}" stroke-width="10" fill="none"></path>'
               + f'<path d="M80 180 C 70 230 90 260 84 300 M200 176 C 214 220 196 250 206 290" stroke="{BR}" stroke-width="6" fill="none"></path>'
               + grapes(70, 300) + grapes(196, 290) + leaf(40, 200, -20) + leaf(120, 168, 10) + leaf(230, 190, 30) + leaf(150, 220, 70) + ground(440, "#2F3A28"), "#2A3B33")
def city_hill():
    houses = "".join(house(x, y, w, C, R) for x, y, w in [(84, 300, 40), (132, 280, 44), (184, 300, 38), (110, 330, 34), (166, 326, 36)])
    return svg(NIGHT() + glow(150, 300, 120, 0.2) + '<path d="M0 420 Q150 260 300 420Z" fill="#26405A"></path>' + houses + '<rect y="418" width="300" height="182" fill="#162A40"></rect>', N)
def the_rock():
    return svg(grad("#4A6E8A", "#C9B48A") + '<path d="M30 430 L70 270 L130 230 L190 250 L250 300 L280 430Z" fill="#7A6E62"></path>'
               + '<path d="M130 230 L150 330 L140 430" stroke="#4A4038" stroke-width="10" fill="none"></path><path d="M70 270 L110 300 M190 250 L210 320" stroke="#5A5048" stroke-width="5"></path>'
               + ground(440, "#5E5040"), "#4A6E8A")
def living_water():
    return svg(grad("#3A2E4A", "#E0A85A", 0.6) + '<path d="M0 360 Q150 330 300 360 V600 H0Z" fill="#C9A06A"></path><path d="M150 280 L110 360 H190Z" fill="#8A7060"></path><path d="M120 300 L90 360 H150Z" fill="#7A6050"></path>'
               + f'<path d="M150 330 C 140 380, 200 400, 170 460 S 140 560, 150 600" stroke="{BL}" stroke-width="22" fill="none"></path>'
               + f'<path d="M150 330 C 140 380, 200 400, 170 460" stroke="#BFE3F2" stroke-width="4" fill="none"></path>'
               + "".join(f'<path d="M{x} 360 q-6 -30 0 -60 q6 30 0 60" fill="{GR}"></path>' for x in (100, 112, 206, 218)), "#E8B86A")
def bread_life():
    loaf = lambda x, y: f'<ellipse cx="{x}" cy="{y}" rx="30" ry="16" fill="#C08A4A"></ellipse><path d="M{x-16} {y-4} q8 -6 16 0 M{x} {y-6} q8 -6 16 0" stroke="#8A5A2A" stroke-width="2" fill="none"></path>'
    return svg(NIGHT() + glow(150, 320, 110, 0.18) + f'<path d="M70 330 H230 L212 410 H88Z" fill="#B08A50"></path>'
               + "".join(f'<path d="M{70+i*16} 330 L{88+i*12} 410" stroke="#8A6A3A" stroke-width="2"></path>' for i in range(11))
               + loaf(110, 316) + loaf(160, 306) + loaf(196, 320) + loaf(134, 296) + loaf(176, 288) + '<rect y="420" width="300" height="180" fill="#10263D"></rect>', N)
def ark():
    waves = "".join(f'<path d="M{x} {y} q15 -8 30 0 q15 8 30 0" stroke="{C}" stroke-width="2" fill="none" opacity="0.5"></path>' for x, y in [(10, 400), (130, 420), (220, 396), (60, 440)])
    return svg(grad("#3A4A5E", "#6A8AA0") + f'<rect y="360" width="300" height="240" fill="#2E5A78"></rect>' + waves
               + f'<path d="M40 340 H260 L236 380 H64Z" fill="#7A4A1E"></path><rect x="90" y="290" width="120" height="50" fill="#9A6A3A"></rect><path d="M80 290 L150 256 L220 290Z" fill="#5A3A22"></path>'
               + f'<rect x="138" y="304" width="24" height="16" fill="{G}"></rect>', "#3A4A5E")
def the_door():
    return svg(NIGHT() + f'<path d="M150 600 L120 430 H180Z" fill="{G}" opacity="0.25"></path><rect x="90" y="220" width="120" height="210" fill="#3A2A1E"></rect>'
               + f'<rect x="102" y="232" width="96" height="198" fill="#FFF3D1"></rect>' + glow(150, 330, 120, 0.25)
               + f'<path d="M102 232 L60 250 V448 L102 430Z" fill="#7A4A1E"></path><circle cx="72" cy="344" r="4" fill="{G}"></circle>' + '<rect y="430" width="300" height="170" fill="#162A40"></rect>', N)
def armor():
    return svg(grad(N, "#2E4A7A") + glow(150, 300, 120, 0.15)
               + f'<path d="M110 220 Q110 180 150 180 Q190 180 190 220 V250 H170 V230 H130 V250 H110Z" fill="#9AA4AE" stroke="#5E6A74" stroke-width="3"></path><path d="M150 176 V150" stroke="{R}" stroke-width="10"></path>'
               + f'<path d="M150 270 L206 290 V336 Q206 380 150 406 Q94 380 94 336 V290Z" fill="#8C6A2A" stroke="{G}" stroke-width="5"></path>'
               + f'<g transform="rotate(30 230 330)"><rect x="226" y="220" width="8" height="150" fill="#C9D2DA"></rect><rect x="210" y="364" width="40" height="8" fill="{G}"></rect><rect x="226" y="372" width="8" height="26" fill="{BR}"></rect></g>', N)
def sword_spirit():
    return svg(grad(N, "#24406B") + rays(150, 250, 180, 200, 340, 14, 3, 0.25) + book(150, 360, 200)
               + f'<rect x="144" y="170" width="12" height="170" fill="#D9E0E6"></rect><path d="M144 170 L150 150 L156 170Z" fill="#D9E0E6"></path>'
               + f'<rect x="118" y="336" width="64" height="10" fill="{G}"></rect><rect x="145" y="346" width="10" height="26" fill="{BR}"></rect>', N)
def rainbow():
    cols = ["#C8102E", "#E07A2A", "#E8B21E", "#5E9A4A", "#2E8FB8", "#5B3E9A"]
    arcs = "".join(f'<path d="M{20+i*10} 400 A{130-i*10} {130-i*10} 0 0 1 {280-i*10} 400" stroke="{c}" stroke-width="10" fill="none"></path>' for i, c in enumerate(cols))
    return svg(grad("#1F4A6E", "#BFD7EA", 0.7) + arcs + ground(410, "#5E9A4A") + '<path d="M0 450 Q150 420 300 450 V600 H0Z" fill="#4A8A3A"></path>', "#4A6E8A")
def covenant():
    return svg(NIGHT() + glow(150, 310, 100, 0.2) + f'<rect x="80" y="230" width="140" height="170" fill="{C}"></rect>'
               + f'<rect x="70" y="214" width="160" height="22" rx="11" fill="#D9C9A6"></rect><rect x="70" y="394" width="160" height="22" rx="11" fill="#D9C9A6"></rect>'
               + "".join(f'<path d="M98 {256+i*16} h{104 if i % 3 else 70}" stroke="{DIM}" stroke-width="2"></path>' for i in range(7))
               + f'<circle cx="190" cy="372" r="18" fill="{R}"></circle><path d="M180 388 l-6 22 l14 -10 l6 12 l2 -22" fill="{R}"></path>' + star5(190, 372, 8, "#7A0A1E"), N)
def heavens():
    return svg(NIGHT() + stars_sky([(x, y, r) for x, y, r in [(60, 330, 1.4), (240, 360, 1.2), (180, 300, 1), (90, 400, 1.3)]])
               + f'<circle cx="90" cy="230" r="40" fill="{G}"></circle>' + rays(90, 230, 70, 0, 360, 30, 3, 0.5)
               + f'<circle cx="214" cy="280" r="34" fill="{C}"></circle><circle cx="228" cy="270" r="30" fill="{N}"></circle>'
               + star5(160, 360, 10, C) + star5(250, 210, 7, C) + star5(70, 340, 6, C) + '<path d="M0 440 Q150 410 300 440 V600 H0Z" fill="#10263D"></path>', N)
def providence():
    return svg(grad("#1F4A6E", "#BFD7EA", 0.7) + f'<path d="M0 300 C 100 290, 180 320, 300 280" stroke="{BR}" stroke-width="8" fill="none"></path>'
               + "".join(f'<path transform="translate({x} {y}) rotate({a})" d="M0 0 Q14 -14 28 0 Q14 14 0 0Z" fill="{GR}"></path>' for x, y, a in [(40, 296, -30), (90, 292, 20), (230, 290, -20), (260, 282, 30)])
               + f'<g transform="translate(150 286)"><ellipse cx="0" cy="0" rx="26" ry="18" fill="#8A6A4A"></ellipse><circle cx="20" cy="-12" r="11" fill="#8A6A4A"></circle>'
               + f'<path d="M30 -12 l10 3 l-10 3z" fill="{G}"></path><circle cx="23" cy="-14" r="2" fill="#1F1B16"></circle><path d="M-24 4 l-22 10 l4 -14z" fill="#6A4A2A"></path>'
               + f'<path d="M-6 6 Q4 14 14 4" fill="#C9B49A"></path><path d="M-4 18 v10 M6 18 v10" stroke="#5A3A22" stroke-width="2"></path></g>', "#9FC8E0")
def harvest():
    wheat = "".join(f'<path d="M{x} 440 q-3 -40 {(x%7)-3} -{70+(x%5)*8}" stroke="{G}" stroke-width="2" fill="none"></path><ellipse cx="{x+(x%7)-3}" cy="{368-(x%5)*8}" rx="4" ry="11" fill="{G}"></ellipse>' for x in range(14, 290, 11))
    return svg(grad("#4A6E8A", "#E0B66A") + f'<circle cx="220" cy="260" r="40" fill="{G}"></circle>' + ground(380, "#8A7A3A") + wheat
               + f'<path d="M60 250 Q100 200 140 240" stroke="#9AA4AE" stroke-width="7" fill="none"></path><path d="M60 250 L40 300" stroke="{BR}" stroke-width="7"></path>', "#4A6E8A")
def disciples():
    meridians = "".join(f'<ellipse cx="150" cy="300" rx="{r}" ry="90" fill="none" stroke="{C}" stroke-width="2" opacity="0.6"></ellipse>' for r in (30, 60, 90))
    return svg(NIGHT() + f'<circle cx="150" cy="300" r="90" fill="{BL}"></circle>'
               + f'<path d="M100 250 Q120 236 140 250 Q150 280 128 296 Q110 290 100 250Z M170 300 Q196 290 210 310 Q200 350 176 356 Q164 330 170 300Z" fill="#5E9A4A"></path>'
               + meridians + f'<path d="M60 300 H240" stroke="{C}" stroke-width="2" opacity="0.6"></path>'
               + f'<g transform="translate(222 392)"><circle r="26" fill="#2A2A2E" stroke="{G}" stroke-width="3"></circle><path d="M0 -20 L5 0 L0 20 L-5 0Z" fill="{G}"></path><path d="M-20 0 L0 -4 L20 0 L0 4Z" fill="{C}"></path></g>', N)
def mustard():
    birds = "".join(f'<path d="M{x} {y} q6 -6 12 0 q6 -6 12 0" stroke="#1F1B16" stroke-width="2" fill="none"></path>' for x, y in [(70, 200), (200, 180), (230, 230)])
    return svg(grad("#1F4A6E", "#BFD7EA", 0.7) + ground(410, "#5E9A4A") + f'<path d="M150 410 C 146 360 156 330 150 290" stroke="{BR}" stroke-width="14" fill="none"></path>'
               + "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{GR}"></circle>' for x, y, r in [(150, 250, 60), (100, 280, 40), (200, 280, 42), (120, 220, 36), (182, 214, 38)])
               + birds + f'<circle cx="60" cy="440" r="5" fill="#C9A55A"></circle><path d="M40 470 h40" stroke="{C}" stroke-width="2"></path>', "#9FC8E0")
def pearl():
    return svg(grad("#16324F", "#1F5E7A") + glow(150, 320, 100, 0.2)
               + f'<path d="M70 360 Q150 420 230 360 Q150 380 70 360Z" fill="#C9B9A6"></path><path d="M70 356 Q150 250 230 356 Q150 330 70 356Z" fill="#D9CDBE"></path>'
               + "".join(f'<path d="M150 {300} L{90+i*20} 354" stroke="#B0A090" stroke-width="2"></path>' for i in range(7))
               + f'<circle cx="150" cy="364" r="20" fill="#F7F3EA"></circle><circle cx="144" cy="358" r="6" fill="#FFFFFF"></circle>' + ground(450, "#E0CDA0"), "#16324F")
def salt_light():
    return svg(NIGHT() + glow(200, 290, 70, 0.3)
               + f'<path d="M70 300 Q70 280 96 280 Q122 280 122 300 L130 400 H62Z" fill="#E6E0D6"></path><rect x="74" y="270" width="44" height="12" rx="4" fill="#9AA4AE"></rect>'
               + "".join(f'<circle cx="{x}" cy="{y}" r="2" fill="#FFFFFF"></circle>' for x, y in [(84, 330), (100, 348), (92, 370), (108, 320)])
               + f'<rect x="186" y="320" width="28" height="80" fill="{C}"></rect>' + flame(200, 318, 1.1)
               + f'<path d="M168 400 H232 L222 412 H178Z" fill="{G}"></path><rect y="412" width="300" height="188" fill="#10263D"></rect>', N)
def built_rock():
    rain = "".join(f'<path d="M{x} {y} l-6 18" stroke="#9FC2D9" stroke-width="2"></path>' for x in range(20, 300, 24) for y in (160, 220))
    return svg(grad("#3A4A5E", "#5E6E80") + rain + f'<path d="M50 440 L90 360 L210 350 L250 440Z" fill="#7A6E62"></path>' + house(100, 300, 100, C, R)
               + f'<rect y="440" width="300" height="160" fill="#2E5A78"></rect>', "#3A4A5E")
def narrow_gate():
    return svg(grad("#2A3B33", "#E0B66A", 0.9) + glow(150, 260, 80, 0.5) + f'<path d="M60 430 V260 A90 90 0 0 1 240 260 V430 H200 V270 A50 50 0 0 0 100 270 V430Z" fill="#8A8170"></path>'
               + f'<path d="M100 270 A50 50 0 0 1 200 270" stroke="#6A6058" stroke-width="3" fill="none"></path><path d="M150 600 L136 430 H164Z" fill="#E8D3A0"></path>'
               + f'<path d="M0 430 H300 V600 H0Z" fill="#2F4A2A" opacity="0.6"></path>', "#2A3B33")
def psalms():
    notes = "".join(f'<g transform="translate({x} {y})"><ellipse cx="0" cy="0" rx="8" ry="6" transform="rotate(-20)" fill="{G}"></ellipse><path d="M7 -2 V-30" stroke="{G}" stroke-width="3"></path></g>' for x, y in [(80, 250), (120, 210), (190, 230), (230, 190), (160, 180)])
    return svg(grad(N, "#24406B") + notes + book(150, 330, 200) + "".join(f'<path d="M{x} {354+i*12} q12 -6 24 0 q12 6 24 0" stroke="#5A4636" stroke-width="1.5" fill="none"></path>' for i in range(3) for x in (64, 162)), N)
def prayer():
    smoke = f'<path d="M150 330 C 120 290, 180 260, 150 220 S 130 160, 160 130" stroke="{C}" stroke-width="6" fill="none" opacity="0.5" stroke-linecap="round"></path>'
    return svg(NIGHT() + glow(150, 300, 90, 0.2) + smoke + f'<path d="M100 340 H200 Q196 380 150 384 Q104 380 100 340Z" fill="{G}"></path><rect x="132" y="384" width="36" height="12" fill="{DIM}"></rect><rect x="118" y="396" width="64" height="8" rx="3" fill="{DIM}"></rect>'
               + '<rect y="420" width="300" height="180" fill="#10263D"></rect>', N)
def gathered():
    lanterns = "".join(f'<circle cx="{x}" cy="{y}" r="4" fill="{G}"></circle>' + glow(x, y, 10, 0.4) for x, y in [(40, 440), (70, 452), (230, 446), (260, 440), (110, 470), (196, 466)])
    return svg(NIGHT() + ground(410, "#1F2A22") + church(150, 410, 1.05) + lanterns, N)
def elders_deacons():
    return svg(grad(N, "#2E4A7A") + glow(150, 310, 110, 0.15)
               + f'<path d="M100 420 V230 Q100 196 130 196 Q156 196 156 222 Q156 240 140 240" stroke="#7A4A1E" stroke-width="8" fill="none" stroke-linecap="round"></path>'
               + f'<path d="M160 380 H260 Q256 412 210 414 Q164 412 160 380Z" fill="#9AA4AE"></path><path d="M184 340 q10 -30 22 0 q8 40 -2 44" stroke="{C}" stroke-width="10" fill="none"></path>'
               + '<rect y="420" width="300" height="180" fill="#10263D"></rect>', N)
def chosen():
    names = "".join(f'<path d="M{x} {y} h{w}" stroke="#5A4636" stroke-width="2"></path>' for x, y, w in [(84, 296, 50), (84, 312, 42), (84, 328, 54), (84, 344, 38), (164, 296, 48), (164, 312, 54), (164, 328, 40), (164, 344, 50)])
    return svg(NIGHT() + glow(150, 310, 110, 0.25) + book(150, 280, 190, "#F3EBDA", "#7A4A1E") + names
               + f'<path d="M150 340 L150 420 L142 410 L134 420 V340" fill="{R}"></path>' + star5(150, 220, 12, G), N)
def robe():
    return svg(grad(N, "#2E4A7A") + glow(150, 300, 110, 0.2) + f'<path d="M120 200 Q150 186 180 200" stroke="#8A8170" stroke-width="5" fill="none"></path><path d="M150 186 V176" stroke="#8A8170" stroke-width="4"></path>'
               + f'<path d="M110 206 L190 206 L230 260 L206 276 L196 254 L204 420 H96 L104 254 L94 276 L70 260Z" fill="#FFFFFF"></path>'
               + f'<path d="M110 206 L150 250 L190 206" stroke="{G}" stroke-width="5" fill="none"></path><path d="M96 410 H204" stroke="{G}" stroke-width="6"></path>', N)
def no_condemnation():
    link = lambda x, y, a: f'<rect x="{x}" y="{y}" width="34" height="20" rx="10" fill="none" stroke="#9AA4AE" stroke-width="7" transform="rotate({a} {x+17} {y+10})"></rect>'
    return svg(grad("#1B1A21", "#E0B66A", 0.85) + rays(150, 420, 260, 190, 350, 14, 5, 0.25)
               + link(40, 300, -10) + link(70, 306, 20) + link(100, 300, -10) + link(176, 306, 10) + link(206, 300, -20) + link(232, 310, 10)
               + f'<path d="M136 296 l8 18 M164 296 l-6 20" stroke="#9AA4AE" stroke-width="6"></path>' + ground(420, "#3A3448"), "#1B1A21")
def adopted():
    return svg(NIGHT() + ground(420, "#1F2A22") + house(90, 300, 120, C, R) + glow(150, 340, 90, 0.18)
               + f'<path d="M150 250 C 130 226 104 246 150 274 C 196 246 170 226 150 250Z" fill="{R}"></path>', N)
def refiner():
    return svg(NIGHT() + f'<path d="M96 300 H204 L196 360 Q150 380 104 360Z" fill="#5A5048"></path><ellipse cx="150" cy="300" rx="54" ry="10" fill="#D9E0E6"></ellipse>'
               + flame(120, 410, 1.3) + flame(150, 414, 1.6) + flame(182, 410, 1.3) + f'<path d="M96 414 H204" stroke="#5A3A22" stroke-width="8"></path>'
               + '<rect y="420" width="300" height="180" fill="#10263D"></rect>', N)
def run_race():
    lanes = "".join(f'<path d="M{-40+i*40} 600 C {40+i*30} 460, {200-i*10} 420, {320} {380+i*8}" stroke="{C}" stroke-width="3" fill="none" opacity="0.8"></path>' for i in range(5))
    leaves = "".join(f'<ellipse cx="{150+math.cos(math.radians(a))*54:.0f}" cy="{250+math.sin(math.radians(a))*54:.0f}" rx="6" ry="13" transform="rotate({a+90} {150+math.cos(math.radians(a))*54:.0f} {250+math.sin(math.radians(a))*54:.0f})" fill="{GR}"></ellipse>' for a in list(range(100, 260, 18)) + list(range(-80, 80, 18)))
    return svg(grad("#4A6E8A", "#E0B66A") + '<path d="M0 380 Q150 350 300 380 V600 H0Z" fill="#B0563A"></path>' + lanes + leaves, "#4A6E8A")
def crown_life():
    return svg(grad(N, "#24406B") + glow(150, 310, 100, 0.2) + f'<ellipse cx="150" cy="400" rx="96" ry="22" fill="#5B2A6E"></ellipse>'
               + f'<path d="M96 380 L90 290 L122 330 L150 270 L178 330 L210 290 L204 380Z" fill="{G}" stroke="#8C6A2A" stroke-width="3"></path>'
               + "".join(f'<circle cx="{x}" cy="{y}" r="7" fill="{c}"></circle>' for x, y, c in [(90, 288, R), (150, 268, BL), (210, 288, R), (150, 356, GR)]), N)
def trumpet():
    def cloud(x, y, s): return f'<g transform="translate({x} {y}) scale({s})" fill="{C}" opacity="0.9"><ellipse rx="34" ry="16"></ellipse><ellipse cx="24" cy="-9" rx="22" ry="15"></ellipse><ellipse cx="-22" cy="-5" rx="18" ry="12"></ellipse></g>'
    return svg(grad("#16324F", "#E0B66A", 0.9) + rays(150, 250, 260, 0, 360, 15, 4, 0.2) + cloud(70, 380, 1.3) + cloud(230, 360, 1.1) + cloud(150, 420, 1.6)
               + f'<g transform="rotate(-25 150 260)"><rect x="70" y="252" width="130" height="12" rx="5" fill="{G}"></rect><path d="M196 248 L250 222 V294 L196 268Z" fill="{G}"></path><rect x="60" y="248" width="14" height="20" fill="{G}"></rect></g>', "#16324F")
def tree_life():
    fruit = "".join(f'<circle cx="{x}" cy="{y}" r="7" fill="{R}"></circle>' for x, y in [(110, 230), (180, 220), (150, 270), (200, 270), (96, 280), (140, 200)])
    return svg(grad("#1F4A6E", "#BFD7EA", 0.7) + '<path d="M0 420 Q150 400 300 420 V600 H0Z" fill="#5E9A4A"></path>'
               + f'<path d="M150 600 C 120 520, 190 470, 160 420" stroke="{BL}" stroke-width="30" fill="none"></path>'
               + f'<path d="M150 410 C 146 360 156 320 150 290" stroke="{BR}" stroke-width="16" fill="none"></path>'
               + "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{GR}"></circle>' for x, y, r in [(150, 250, 64), (100, 270, 40), (200, 266, 44)]) + fruit, "#9FC8E0")
def sabbath_rest():
    return svg(grad("#2E4A7A", "#E0A85A", 0.9) + f'<circle cx="210" cy="300" r="36" fill="{G}"></circle>' + '<path d="M0 330 Q150 300 300 330 V600 H0Z" fill="#4E8A4A"></path>'
               + f'<ellipse cx="150" cy="400" rx="130" ry="30" fill="#5E9AC6"></ellipse><path d="M70 396 h40 M170 408 h50" stroke="{C}" stroke-width="2" opacity="0.6"></path>'
               + sheep(80, 350, 0.8) + sheep(220, 356, 0.7), "#2E4A7A")
def repent():
    return svg(NIGHT() + ground(420, "#1F2A22") + house(196, 340, 70, C, R)
               + f'<rect x="96" y="250" width="8" height="180" fill="{BR}"></rect><path d="M104 262 H170 L186 276 L170 290 H104Z" fill="#B08A50"></path><path d="M96 310 H40 L24 324 L40 338 H96Z" fill="#8A6A3A"></path>'
               + f'<path d="M100 600 C 110 520, 180 470, 220 400" stroke="#E8D3A0" stroke-width="10" fill="none" stroke-dasharray="4 10" stroke-linecap="round"></path>', N)
def new_morning():
    return svg(grad("#2E4A7A", "#E8B86A", 0.7) + f'<circle cx="150" cy="350" r="56" fill="{G}"></circle>' + rays(150, 350, 220, 190, 350, 12, 4, 0.35)
               + '<path d="M0 360 Q150 330 300 360 V600 H0Z" fill="#5E9A4A"></path>'
               + "".join(f'<path d="M{x} 600 L150 360" stroke="#4A8A3A" stroke-width="3"></path>' for x in range(-150, 460, 60)), "#2E4A7A")

# ---------- Ten Commandments ----------
def numeral(n, x=150, y=208):
    return f'<text x="{x}" y="{y}" text-anchor="middle" font-family="Playfair Display, serif" font-size="30" font-weight="700" fill="{G}">{n}</text>'
def c1():  # fallen idol
    return svg(NIGHT() + numeral("I") + ground(420, "#3A3448") + f'<rect x="60" y="370" width="70" height="40" fill="#8A8170" transform="rotate(-12 95 390)"></rect>'
               + f'<circle cx="190" cy="396" r="22" fill="#9A9080"></circle><rect x="150" y="300" width="40" height="90" fill="#8A8170" transform="rotate(68 170 345)"></rect>'
               + f'<path d="M210 370 l14 -10 M220 380 l16 -4" stroke="#6A6058" stroke-width="4"></path>' + glow(150, 300, 90, 0.15), N)
def c2():  # tools laid down by uncarved stone
    return svg(grad(N, "#2E4A7A") + numeral("II") + f'<path d="M80 420 L96 300 Q150 280 204 300 L220 420Z" fill="#9A9080"></path>'
               + f'<g transform="rotate(-20 110 400)"><rect x="60" y="400" width="80" height="8" fill="#9AA4AE"></rect><path d="M140 396 l20 8 l-20 8z" fill="#9AA4AE"></path></g>'
               + f'<g transform="rotate(15 220 410)"><rect x="200" y="380" width="12" height="60" fill="{BR}"></rect><rect x="186" y="372" width="40" height="22" rx="4" fill="#7A5A3A"></rect></g>'
               + '<rect y="430" width="300" height="170" fill="#10263D"></rect>', N)
def c3():  # hallowed
    return svg(NIGHT() + numeral("III") + glow(150, 310, 110, 0.2) + f'<rect x="70" y="250" width="160" height="130" fill="{C}"></rect>'
               + f'<rect x="60" y="236" width="180" height="20" rx="10" fill="#D9C9A6"></rect><rect x="60" y="374" width="180" height="20" rx="10" fill="#D9C9A6"></rect>'
               + f'<text x="150" y="324" text-anchor="middle" font-family="Pinyon Script, cursive" font-size="44" fill="#8C6A2A">Hallowed</text>', N)
def c4():  # seven days, one lit
    tiles = "".join(f'<rect x="{62+i*26}" y="290" width="22" height="40" rx="5" fill="{G if i == 0 else "#2E4A7A"}" stroke="{C}" stroke-width="1.5"></rect>'
                    f'<text x="{73+i*26}" y="316" text-anchor="middle" font-family="Libre Franklin, sans-serif" font-size="12" font-weight="700" fill="{N if i == 0 else C}">{d}</text>' for i, d in enumerate("SMTWTFS"))
    return svg(grad(N, "#24406B") + numeral("IV") + rays(73, 310, 100, 0, 360, 30, 3, 0.3) + tiles + ground(420, "#10263D"), N)
def c5():  # roots and home
    roots = "".join(f'<path d="M150 400 Q{150+d} {440+abs(d)/3:.0f} {150+d*1.6:.0f} {470}" stroke="{BR}" stroke-width="5" fill="none"></path>' for d in (-60, -30, 0, 30, 60))
    return svg(grad("#1F4A6E", "#BFD7EA", 0.7) + numeral("V") + '<path d="M0 400 Q150 384 300 400 V600 H0Z" fill="#6A5040"></path>' + roots
               + f'<path d="M150 400 C 146 360 156 340 150 320" stroke="{BR}" stroke-width="16" fill="none"></path>'
               + "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{GR}"></circle>' for x, y, r in [(150, 286, 52), (106, 306, 34), (194, 304, 36)]) + house(206, 354, 46, C, R), "#9FC8E0")
def c6():  # sword to plowshare
    return svg(grad("#4A6E8A", "#E0B66A") + numeral("VI") + ground(400, "#6A5040")
               + "".join(f'<path d="M0 {420+i*24} Q150 {400+i*24} 300 {420+i*24}" stroke="#5A4030" stroke-width="3" fill="none"></path>' for i in range(5))
               + f'<path d="M110 360 L200 300 L214 316 L130 380Z" fill="#9AA4AE"></path><path d="M200 300 Q240 300 236 340 L214 316Z" fill="#7A8490"></path>'
               + f'<path d="M110 360 L60 400" stroke="{BR}" stroke-width="8"></path>', "#4A6E8A")
def c7():  # two rings
    return svg(grad(N, "#2E4A7A") + numeral("VII") + glow(150, 310, 100, 0.2)
               + f'<circle cx="128" cy="320" r="44" fill="none" stroke="{G}" stroke-width="12"></circle><circle cx="172" cy="320" r="44" fill="none" stroke="#E6CF8A" stroke-width="12"></circle>'
               + f'<path d="M150 284 A44 44 0 0 1 172 276" stroke="{G}" stroke-width="12" fill="none"></path>' + star5(150, 250, 8, C), N)
def c8():  # level scales
    return svg(NIGHT() + numeral("VIII") + f'<rect x="146" y="240" width="8" height="160" fill="{G}"></rect><rect x="70" y="250" width="160" height="7" fill="{G}"></rect>'
               + "".join(f'<path d="M{x} 254 L{x-22} 330 M{x} 254 L{x+22} 330" stroke="{G}" stroke-width="2"></path><path d="M{x-30} 330 H{x+30} Q{x} 350 {x-30} 330Z" fill="{G}"></path>' for x in (80, 220))
               + f'<rect x="120" y="400" width="60" height="10" fill="{G}"></rect><rect y="420" width="300" height="180" fill="#10263D"></rect>', N)
def c9():  # plumb line
    bricks = "".join(f'<rect x="{30+(r%2)*16+c*32}" y="{230+r*20}" width="30" height="18" fill="#9A7A60"></rect>' for r in range(10) for c in range(3))
    return svg(grad("#1F4A6E", "#BFD7EA", 0.7) + numeral("IX", 232) + bricks + f'<path d="M190 232 H240" stroke="{BR}" stroke-width="6"></path>'
               + f'<path d="M200 232 V380" stroke="{C}" stroke-width="2"></path><path d="M192 380 L208 380 L200 404Z" fill="{G}"></path>' + ground(440, "#5E9A4A"), "#4A6E8A")
def c10():  # daily bread, contentment
    return svg(grad(N, "#3A2A1E") + numeral("X") + glow(150, 330, 90, 0.2)
               + f'<path d="M86 340 H214 Q208 400 150 404 Q92 400 86 340Z" fill="#8A6A4A"></path>'
               + f'<ellipse cx="150" cy="330" rx="46" ry="20" fill="#C08A4A"></ellipse><path d="M126 326 q10 -8 20 0 M150 322 q10 -8 20 0" stroke="#8A5A2A" stroke-width="2" fill="none"></path>'
               + '<rect y="420" width="300" height="180" fill="#2A1E15"></rect>', N)

DRAW = {"The Lord's Day": lords_day, "Sola Scriptura": sola_scriptura, "Sola Fide": sola_fide, "Sola Gratia": sola_gratia,
        "Solus Christus": solus_christus, "Soli Deo Gloria": soli_deo_gloria, "Believer's Baptism": baptism, "The Lord's Supper": supper,
        "Preach the Word": preach, "A Lamp to My Feet": lamp, "A Mighty Fortress": fortress, "The Lord Is My Shepherd": shepherd,
        "Anchor of Hope": anchor, "The Vine": vine, "A City on a Hill": city_hill, "The Rock": the_rock, "Living Water": living_water,
        "Bread of Life": bread_life, "The Ark": ark, "The Door": the_door, "The Armor of God": armor, "Sword of the Spirit": sword_spirit,
        "The Rainbow": rainbow, "Covenant of Grace": covenant, "The Heavens Declare": heavens, "Providence": providence, "The Harvest": harvest,
        "Go and Make Disciples": disciples, "The Mustard Seed": mustard, "Pearl of Great Price": pearl, "Salt and Light": salt_light,
        "Built on the Rock": built_rock, "The Narrow Gate": narrow_gate, "Psalms and Hymns": psalms, "Prayer": prayer,
        "The Gathered Church": gathered, "Elders and Deacons": elders_deacons, "Chosen in Him": chosen, "Robe of Righteousness": robe,
        "No Condemnation": no_condemnation, "Adopted": adopted, "The Refiner's Fire": refiner, "Run the Race": run_race,
        "Crown of Life": crown_life, "The Trumpet": trumpet, "Tree of Life": tree_life, "The Law of the Lord": tablets,
        "A Sabbath Rest": sabbath_rest, "Repent and Believe": repent, "The Faith Delivered": confession,
        "The Burden Rolled Away": pilgrim, "New Every Morning": new_morning}

COMMANDMENTS = [
 ("No Other Gods", "A fallen idol", "You shall have no other gods before Me", "Exodus 20:3", c1),
 ("No Carved Image", "Carving tools laid down", "You shall not make for yourself an idol", "Exodus 20:4", c2),
 ("Hallowed Be His Name", "“Hallowed” on a scroll", "You shall not take the name of the LORD your God in vain", "Exodus 20:7", c3),
 ("Remember the Sabbath", "Seven days, the first one lit", "Remember the Sabbath day by keeping it holy", "Exodus 20:8", c4),
 ("Honor Father and Mother", "Deep roots and a home", "Honor your father and mother", "Exodus 20:12", c5),
 ("You Shall Not Murder", "Sword beaten into a plowshare", "You shall not murder", "Exodus 20:13", c6),
 ("Faithful in Marriage", "Two wedding rings", "You shall not commit adultery", "Exodus 20:14", c7),
 ("You Shall Not Steal", "Honest, level scales", "You shall not steal", "Exodus 20:15", c8),
 ("Speak the Truth", "A plumb line by a true wall", "You shall not bear false witness against your neighbor", "Exodus 20:16", c9),
 ("Content with Daily Bread", "Bread enough for today", "You shall not covet", "Exodus 20:17", c10),
]


def T(x, y, txt, size=18, col=G, fam="Playfair Display, serif", w=600, anchor="middle"):
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="{fam}" font-size="{size}" font-weight="{w}" fill="{col}">{txt}</text>'
def label(txt, y=432, col=G):
    return f'<text x="150" y="{y}" text-anchor="middle" font-family="Libre Franklin, sans-serif" font-size="12" font-weight="700" letter-spacing="3" fill="{col}">{txt.upper()}</text>'

# ---------------- the Trinity ----------------
def shield_trinity(cx=150, cy=300, s=1.0, bg="#16324F"):
    """The old Shield of the Trinity: words only. Outer sides say "is not", the lines to the center say "is"."""
    P = {"F": (cx - 72 * s, cy - 54 * s), "S": (cx + 72 * s, cy - 54 * s), "H": (cx, cy + 70 * s), "G": (cx, cy)}
    out = [f'<path d="M{P["F"][0]:.1f} {P["F"][1]:.1f} L{P["S"][0]:.1f} {P["S"][1]:.1f} L{P["H"][0]:.1f} {P["H"][1]:.1f}Z" fill="none" stroke="{G}" stroke-width="3"></path>']
    out += [f'<path d="M{P["G"][0]:.1f} {P["G"][1]:.1f} L{P[k][0]:.1f} {P[k][1]:.1f}" stroke="{G}" stroke-width="2"></path>' for k in "FSH"]
    def word(a, b, txt, t=0.5, off=0.0):
        (x1, y1), (x2, y2) = P[a], P[b]
        x, y = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
        ang = math.degrees(math.atan2(y2 - y1, x2 - x1))
        if ang > 90: ang -= 180
        if ang < -90: ang += 180
        nx, ny = -(y2 - y1), (x2 - x1)
        L = math.hypot(nx, ny); nx, ny = nx / L, ny / L
        if off and (x - P["G"][0]) * nx + (y - P["G"][1]) * ny < 0:  # outer labels sit outside the triangle
            nx, ny = -nx, -ny
        x += nx * abs(off); y += ny * abs(off)
        return (f'<text x="{x:.1f}" y="{y:.1f}" transform="rotate({ang:.1f} {x:.1f} {y:.1f})" text-anchor="middle" dominant-baseline="middle" '
                f'font-family="Playfair Display, serif" font-style="italic" font-size="{11 * s:.1f}" fill="#E3D3A8" stroke="{bg}" stroke-width="{4 * s:.1f}" paint-order="stroke">{txt}</text>')
    out += [word("F", "S", "is not", off=-9 * s), word("S", "H", "is not", off=-9 * s), word("H", "F", "is not", off=-9 * s)]
    out += [word("G", k, "is", 0.55) for k in "FSH"]
    for k, name in (("F", "Father"), ("S", "Son"), ("H", "Spirit"), ("G", "God")):
        x, y = P[k]
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{25 * s:.1f}" fill="#24406B" stroke="{G}" stroke-width="3"></circle>'
                   + T(x, y + 4 * s, name, 11 * s, C, "Libre Franklin, sans-serif", 700))
    return "".join(out)
def tri_one(): return svg(grad(N, "#24406B") + rays(150, 300, 200, 0, 360, 15, 3, 0.25) + glow(150, 300, 80, 0.35) + T(150, 316, "ONE", 52) + label("Deuteronomy 6:4", 420, "#B9A06E"), N)
def tri_three(): return svg(grad(N, "#24406B") + shield_trinity() + label("The Shield of the Trinity", 420, "#B9A06E"), N)
def tri_father(): return svg(grad("#0E1D2B", "#2E4A7A") + rays(150, 130, 340, 50, 131, 8, 5, 0.3) + glow(150, 150, 60, 0.4)
                             + "".join(star5(x, y, r, C) for x, y, r in [(70, 260, 8), (230, 280, 10), (150, 360, 7), (100, 380, 6), (210, 400, 6)]) + label("Father of lights", 432, "#B9A06E"), N)
def tri_son(): return svg(grad(N, "#24406B") + glow(150, 300, 100, 0.2) + T(108, 330, "Α", 96) + T(196, 330, "Ω", 96) + label("Alpha and Omega", 420, "#B9A06E"), N)
def tri_spirit():
    grass = "".join(f'<path d="M{x} 440 q{18 + (x % 5) * 3} -40 {38 + (x % 7) * 3} -{80 + (x % 4) * 10}" stroke="{G}" stroke-width="2.5" fill="none"></path>' for x in range(0, 300, 12))
    wind = "".join(f'<path d="M{x} {y} q30 -14 60 0 t60 0" stroke="{C}" stroke-width="2.5" fill="none" opacity="0.55"></path>' for x, y in [(20, 250), (90, 290), (40, 330), (130, 220)])
    return svg(grad("#1E3B30", "#4A6A3A") + wind + grass + label("The wind blows", 470, "#E3D3A8"), "#1E3B30")
def tri_holy(): return svg(grad(N, "#24406B") + glow(150, 300, 110, 0.25) + T(150, 260, "Holy", 50, G, "Pinyon Script, cursive", 400) + T(150, 318, "Holy", 50, G, "Pinyon Script, cursive", 400) + T(150, 376, "Holy", 50, G, "Pinyon Script, cursive", 400), N)
def tri_benediction():
    return svg(grad(N, "#24406B") + f'<rect x="64" y="226" width="172" height="164" fill="{C}"></rect><rect x="54" y="212" width="192" height="18" rx="9" fill="#D9C9A6"></rect><rect x="54" y="386" width="192" height="18" rx="9" fill="#D9C9A6"></rect>'
               + T(150, 268, "Grace", 26, "#8C6A2A") + T(150, 314, "Love", 26, "#8C6A2A") + T(150, 360, "Fellowship", 26, "#8C6A2A"), N)
TRINITY = [
 ("One God", "One light; the word ONE", "Hear, O Israel: The LORD our God, the LORD is One", "Deuteronomy 6:4", tri_one),
 ("Three Persons", "The Shield of the Trinity (words only)", "In the name of the Father and of the Son and of the Holy Spirit", "Matthew 28:19", tri_three),
 ("God the Father", "Light from above, the Father of lights", "Every good and perfect gift... coming down from the Father of the heavenly lights", "James 1:17", tri_father),
 ("God the Son", "Alpha and Omega", "I am the Alpha and the Omega, the First and the Last", "Revelation 22:13", tri_son),
 ("God the Holy Spirit", "Wind in the grass", "The wind blows where it wishes... So it is with everyone born of the Spirit", "John 3:8", tri_spirit),
 ("Holy, Holy, Holy", "Holy three times", "Holy, holy, holy is the LORD of Hosts", "Isaiah 6:3", tri_holy),
 ("Grace, Love, Fellowship", "The benediction on a scroll", "The grace of the Lord Jesus Christ, and the love of God, and the fellowship of the Holy Spirit", "2 Corinthians 13:14", tri_benediction),
]

# ---------------- emblem kit (center 150,300) ----------------
def ring(col): return f'<circle cx="150" cy="300" r="92" fill="{col}" opacity="0.12"></circle><circle cx="150" cy="300" r="92" fill="none" stroke="{G}" stroke-width="2" opacity="0.6"></circle>'
E = {}
def em(name):
    def deco(f): E[name] = f; return f
    return deco
@em("bible")
def _(): return book(150, 280, 170)
@em("shield3")
def _(): return shield_trinity(150, 300, 0.85, "#3A2418")
@em("decree")
def _(): return (f'<rect x="96" y="236" width="108" height="130" fill="{C}"></rect>' + "".join(f'<path d="M110 {256+i*14} h80" stroke="{DIM}" stroke-width="2"></path>' for i in range(6))
                 + f'<circle cx="182" cy="350" r="18" fill="{R}"></circle>' + star5(182, 350, 8, "#7A0A1E"))
@em("creation")
def _(): return (f'<circle cx="150" cy="320" r="56" fill="{BL}"></circle><path d="M110 300 Q130 290 150 304 Q160 330 136 344 Q118 336 110 300Z M160 330 Q186 320 196 340 Q186 364 168 362Z" fill="#5E9A4A"></path>'
                 + f'<circle cx="214" cy="236" r="22" fill="{G}"></circle>' + rays(214, 236, 40, 0, 360, 30, 2, 0.6) + star5(88, 236, 8, C))
@em("steps")
def _(): return "".join(f'<ellipse cx="{x}" cy="{y}" rx="9" ry="14" fill="{C}" transform="rotate({a} {x} {y})"></ellipse><circle cx="{x+d}" cy="{y-18}" r="4" fill="{C}"></circle>' for x, y, a, d in [(120, 380, -10, -2), (156, 340, 10, 2), (126, 296, -10, -2), (160, 254, 10, 2)])
@em("fruit")
def _(): return (f'<path d="M150 254 Q118 250 112 290 Q110 340 150 346 Q190 340 188 290 Q182 250 150 254Z" fill="{R}"></path><path d="M180 280 a12 12 0 1 1 0 24" fill="#24406B"></path>'
                 + f'<path d="M150 254 Q152 238 160 230" stroke="{BR}" stroke-width="4" fill="none"></path><path d="M100 380 Q150 360 200 380" stroke="#5E5040" stroke-width="5" fill="none"></path>'
                 + "".join(f'<path d="M{x} 378 l-6 -10 M{x} 378 l6 -10" stroke="#5E5040" stroke-width="3"></path>' for x in (112, 140, 168, 194)))
@em("stars")
def _(): return "".join(star5(x, y, r, C if (x + y) % 3 else G) for x, y, r in [(150, 300, 12), (110, 250, 7), (196, 262, 8), (90, 330, 6), (210, 340, 7), (130, 370, 5), (178, 380, 6), (150, 226, 6), (232, 300, 5), (72, 280, 5)])
@em("ladder")
def _(): return glow(150, 220, 40, 0.5) + f'<path d="M126 400 L138 210 M174 400 L162 210" stroke="{G}" stroke-width="5"></path>' + "".join(f'<path d="M{127+i*1.3:.0f} {390-i*24} H{173-i*1.3:.0f}" stroke="{G}" stroke-width="4"></path>' for i in range(8))
@em("cage")
def _(): return (f'<path d="M96 380 V280 Q96 240 136 240 H164 Q204 240 204 280 V380Z" fill="none" stroke="{G}" stroke-width="3"></path>' + "".join(f'<path d="M{x} 246 V380" stroke="{G}" stroke-width="2"></path>' for x in (116, 136, 164, 184))
                 + f'<path d="M150 240 V230" stroke="{G}" stroke-width="3"></path><rect x="140" y="300" width="30" height="40" fill="#24406B"></rect>'
                 + f'<g transform="translate(224 248)"><path d="M0 0 q-14 -16 -28 -4 q14 -4 28 4 q-6 -18 10 -24 q-2 14 -10 24z" fill="{C}"></path></g>')
@em("crossroads")
def _(): return f'<rect x="146" y="240" width="8" height="150" fill="{BR}"></rect><path d="M154 252 H210 L224 264 L210 276 H154Z M146 292 H90 L76 304 L90 316 H146Z" fill="#B08A50"></path><path d="M60 400 L150 390 L240 400" stroke="#8A8170" stroke-width="4" fill="none"></path>'
@em("fold")
def _(): return f'<path d="M80 390 V320 H220 V390" fill="none" stroke="{BR}" stroke-width="6"></path><path d="M80 344 H220 M80 368 H220" stroke="{BR}" stroke-width="3"></path><rect x="136" y="318" width="28" height="74" fill="#24406B"></rect>' + sheep(150, 290, 0.9)
@em("justify")
def _(): return (f'<rect x="146" y="240" width="8" height="150" fill="{G}"></rect><path d="M74 262 L226 238" stroke="{G}" stroke-width="6"></path>'
                 + f'<path d="M82 262 L64 320 M82 262 L100 320" stroke="{G}" stroke-width="2"></path><path d="M58 320 H106 Q82 336 58 320Z" fill="{G}"></path>' + cross(82, 284, 30, C)
                 + f'<path d="M218 238 L200 296 M218 238 L236 296" stroke="{G}" stroke-width="2"></path><path d="M194 296 H242 Q218 312 194 296Z" fill="{G}"></path><rect x="120" y="390" width="60" height="9" fill="{G}"></rect>')
@em("key")
def _(): return f'<circle cx="150" cy="250" r="30" fill="none" stroke="{G}" stroke-width="10"></circle><rect x="144" y="278" width="12" height="110" fill="{G}"></rect><rect x="156" y="350" width="24" height="10" fill="{G}"></rect><rect x="156" y="372" width="18" height="10" fill="{G}"></rect>'
@em("grow")
def _(): return (f'<path d="M150 400 C 146 350 156 320 150 250" stroke="#5E9A4A" stroke-width="6" fill="none"></path>' + "".join(f'<path transform="translate(150 {y}) rotate({a})" d="M0 0 Q20 -18 40 0 Q20 18 0 0Z" fill="#5E9A4A"></path>' for y, a in [(360, -20), (330, 200), (300, -30), (275, 210)])
                 + f'<circle cx="150" cy="244" r="12" fill="{R}"></circle><path d="M100 400 H200" stroke="#6A5040" stroke-width="8"></path>')
@em("tent")
def _(): return "".join(star5(x, y, 5, C) for x, y in [(90, 230), (150, 214), (210, 236), (120, 256), (186, 262)]) + f'<path d="M80 390 L150 290 L220 390Z" fill="#B08A50"></path><path d="M150 290 L136 390 H164Z" fill="#5A3A22"></path><path d="M60 390 H240" stroke="#6A5040" stroke-width="5"></path>'
@em("uturn")
def _(): return f'<path d="M110 400 V300 A40 40 0 0 1 190 300 V340" stroke="#E8D3A0" stroke-width="16" fill="none" stroke-linecap="round"></path><path d="M172 334 L190 366 L208 334Z" fill="#E8D3A0"></path>' + glow(190, 380, 26, 0.5)
@em("basket")
def _(): return (f'<path d="M86 320 H214 L198 392 H102Z" fill="#B08A50"></path>' + "".join(f'<path d="M{90+i*14} 322 L{104+i*11} 392" stroke="#8A6A3A" stroke-width="2"></path>' for i in range(9))
                 + "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{c}"></circle>' for x, y, r, c in [(112, 306, 16, R), (144, 298, 18, "#E07A2A"), (178, 306, 16, R), (130, 286, 12, "#5E9A4A"), (164, 284, 13, "#E8B21E")]))
@em("summit")
def _(): return f'<path d="M50 400 L150 236 L250 400Z" fill="#5A6A7A"></path><path d="M150 236 L132 266 L150 260 L166 270Z" fill="{C}"></path><path d="M150 236 V200" stroke="{C}" stroke-width="3"></path><path d="M150 200 l26 8 l-26 8Z" fill="{R}"></path><path d="M90 400 C 120 360, 110 320, 140 280" stroke="#E8D3A0" stroke-width="5" fill="none" stroke-dasharray="4 6"></path>'
@em("seal")
def _(): return f'<path d="M84 250 H216 V370 H84Z" fill="{C}"></path><path d="M84 250 L150 310 L216 250" fill="none" stroke="#C9B49A" stroke-width="3"></path><circle cx="150" cy="320" r="24" fill="{R}"></circle>' + star5(150, 320, 11, "#7A0A1E")
@em("tablets")
def _(): return ''.join(f'<path d="M{x} 390 V280 A32 32 0 0 1 {x+64} 280 V390Z" fill="#B8AE9A" stroke="#7A7060" stroke-width="3"></path>' for x in (82, 154)) + "".join(f'<path d="M{x+12} {300+i*16} h40" stroke="#7A7060" stroke-width="3"></path>' for x in (82, 154) for i in range(5))
@em("sandals")
def _(): return f'<path d="M50 400 L120 300 L170 340 L250 260 V400Z" fill="#5A6A7A"></path>' + "".join(f'<g transform="translate({x} {y}) rotate({a})"><ellipse rx="14" ry="30" fill="#8B4F24"></ellipse><path d="M-14 -10 L14 6 M14 -10 L-14 6" stroke="#5A3A22" stroke-width="3"></path></g>' for x, y, a in [(126, 300, -20), (166, 330, 15)])
@em("yoke")
def _(): return f'<path d="M70 300 Q110 270 140 300" stroke="#8B4F24" stroke-width="14" fill="none"></path><path d="M164 296 Q196 266 230 296" stroke="#8B4F24" stroke-width="14" fill="none" transform="rotate(14 196 290)"></path><path d="M90 300 V350 M120 300 V352 M180 306 V356 M212 310 V360" stroke="#5A3A22" stroke-width="5"></path><path d="M146 286 l8 18 l-10 6" stroke="{G}" stroke-width="3" fill="none"></path>'
@em("church")
def _(): return church(150, 400, 0.9)
@em("pledge")
def _(): return f'<rect x="88" y="240" width="124" height="150" fill="{C}"></rect>' + T(150, 290, "Yes", 34, "#8C6A2A", "Pinyon Script, cursive", 400) + "".join(f'<path d="M104 {314+i*14} h92" stroke="{DIM}" stroke-width="2"></path>' for i in range(3)) + f'<path d="M168 370 l-10 30 l14 -8 l8 12 l2 -32" fill="{R}"></path><circle cx="176" cy="366" r="16" fill="{R}"></circle>'
@em("capitol")
def _(): return f'<path d="M80 300 L150 262 L220 300Z" fill="{C}"></path><rect x="80" y="300" width="140" height="10" fill="{C}"></rect>' + "".join(f'<rect x="{x}" y="312" width="10" height="70" fill="{C}"></rect>' for x in (88, 110, 132, 158, 180, 202)) + f'<rect x="70" y="382" width="160" height="10" fill="{C}"></rect>'
@em("rings")
def _(): return f'<circle cx="130" cy="310" r="38" fill="none" stroke="{G}" stroke-width="11"></circle><circle cx="170" cy="310" r="38" fill="none" stroke="#E6CF8A" stroke-width="11"></circle>'
@em("churchrock")
def _(): return f'<path d="M60 410 L90 330 L210 320 L240 410Z" fill="#7A6E62"></path>' + church(150, 330, 0.75)
@em("table")
def _(): return f'<rect x="60" y="330" width="180" height="14" fill="#8B4F24"></rect><path d="M74 344 V400 M226 344 V400" stroke="#5A3A22" stroke-width="7"></path>' + "".join(f'<circle cx="{x}" cy="324" r="9" fill="{C}"></circle>' for x in (84, 116, 148, 180, 212)) + f'<ellipse cx="150" cy="316" rx="22" ry="10" fill="#C08A4A"></ellipse>'
@em("ordinances")
def _(): return "".join(f'<ellipse cx="96" cy="350" rx="{r}" ry="{r*0.3:.0f}" fill="none" stroke="{C}" stroke-width="2" opacity="{0.9-i*0.2:.1f}"></ellipse>' for i, r in enumerate((10, 24, 40))) + f'<ellipse cx="96" cy="350" rx="44" ry="14" fill="{BL}" opacity="0.4"></ellipse>' + f'<ellipse cx="180" cy="364" rx="26" ry="12" fill="#C08A4A"></ellipse><path d="M196 290 Q196 322 214 326 Q232 322 232 290Z" fill="{G}"></path><rect x="211" y="326" width="6" height="30" fill="{G}"></rect><ellipse cx="214" cy="358" rx="16" ry="5" fill="{G}"></ellipse>'
@em("water")
def _(): return f'<rect x="58" y="330" width="184" height="70" rx="30" fill="{BL}"></rect>' + "".join(f'<ellipse cx="150" cy="350" rx="{r}" ry="{r*0.3:.0f}" fill="none" stroke="{C}" stroke-width="2" opacity="{0.9-i*0.18:.1f}"></ellipse>' for i, r in enumerate((14, 34, 56, 78)))
@em("supper")
def _(): return f'<ellipse cx="114" cy="352" rx="40" ry="18" fill="#C08A4A"></ellipse><path d="M96 346 q10 -8 20 0 M116 342 q10 -8 20 0" stroke="#8A5A2A" stroke-width="2" fill="none"></path><path d="M168 280 Q168 326 196 332 Q224 326 224 280Z" fill="{G}"></path><ellipse cx="196" cy="280" rx="28" ry="6" fill="#7A1E2B"></ellipse><rect x="192" y="332" width="8" height="34" fill="{G}"></rect><ellipse cx="196" cy="370" rx="20" ry="6" fill="{G}"></ellipse>'
@em("tomb")
def _(): return glow(150, 340, 60, 0.4) + f'<path d="M60 400 Q60 280 160 280 Q240 284 240 400Z" fill="#5A4C3E"></path><path d="M122 400 V346 A28 28 0 0 1 178 346 V400Z" fill="#FFF3D1"></path><circle cx="222" cy="372" r="28" fill="#776654"></circle>'
@em("books")
def _(): return glow(150, 300, 80, 0.4) + book(150, 300, 150) + f'<path d="M78 252 L118 236 L118 290 L78 306Z" fill="{C}" stroke="#8B4F24" stroke-width="2"></path><path d="M222 252 L182 236 L182 290 L222 306Z" fill="{C}" stroke="#8B4F24" stroke-width="2"></path>'

CONFESSION = [
 ("Of the Holy Scriptures", "bible", "The word of our God stands forever", "Isaiah 40:8"),
 ("Of God and of the Holy Trinity", "shield3", "Hear, O Israel: The LORD our God, the LORD is One", "Deuteronomy 6:4"),
 ("Of God's Decree", "decree", "Who works out everything by the counsel of His will", "Ephesians 1:11"),
 ("Of Creation", "creation", "In the beginning God created the heavens and the earth", "Genesis 1:1"),
 ("Of Divine Providence", "steps", "A man’s heart plans his course, but the LORD determines his steps", "Proverbs 16:9"),
 ("Of the Fall of Man, of Sin, and of the Punishment Thereof", "fruit", "Sin entered the world through one man", "Romans 5:12"),
 ("Of God's Covenant", "stars", "Look to the heavens and count the stars", "Genesis 15:5"),
 ("Of Christ the Mediator", "ladder", "There is one mediator between God and men", "1 Timothy 2:5"),
 ("Of Free Will", "crossroads", "No one can come to Me unless the Father who sent Me draws him", "John 6:44"),
 ("Of Effectual Calling", "fold", "He calls his own sheep by name and leads them out", "John 10:3"),
 ("Of Justification", "justify", "Justified freely by His grace", "Romans 3:24"),
 ("Of Adoption", "key", "No longer a slave, but a son; and since you are a son, you are also an heir", "Galatians 4:7"),
 ("Of Sanctification", "grow", "Grow in the grace and knowledge of our Lord", "2 Peter 3:18"),
 ("Of Saving Faith", "tent", "By faith Abraham... obeyed and went, without knowing where he was going", "Hebrews 11:8"),
 ("Of Repentance unto Life and Salvation", "uturn", "God has granted even the Gentiles repentance unto life", "Acts 11:18"),
 ("Of Good Works", "basket", "Created in Christ Jesus to do good works", "Ephesians 2:10"),
 ("Of the Perseverance of the Saints", "summit", "He who began a good work in you will carry it on to completion", "Philippians 1:6"),
 ("Of the Assurance of Grace and Salvation", "seal", "That you may know that you have eternal life", "1 John 5:13"),
 ("Of the Law of God", "tablets", "The Law of the LORD is perfect, reviving the soul", "Psalm 19:7"),
 ("Of the Gospel and the Extent of Its Grace", "sandals", "How beautiful are the feet of those who bring good news!", "Romans 10:15"),
 ("Of Christian Liberty and Liberty of Conscience", "yoke", "It is for freedom that Christ has set us free", "Galatians 5:1"),
 ("Of Religious Worship and the Sabbath Day", "church", "His worshipers must worship Him in spirit and in truth", "John 4:24"),
 ("Of Lawful Oaths and Vows", "pledge", "Simply let your ‘Yes’ be ‘Yes,’ and your ‘No,’ ‘No.’", "Matthew 5:37"),
 ("Of the Civil Magistrate", "capitol", "Everyone must submit himself to the governing authorities", "Romans 13:1"),
 ("Of Marriage", "rings", "They will become one flesh", "Genesis 2:24"),
 ("Of the Church", "churchrock", "I will build My church", "Matthew 16:18"),
 ("Of the Communion of Saints", "table", "They devoted themselves... to the fellowship, to the breaking of bread", "Acts 2:42"),
 ("Of Baptism and the Lord's Supper", "ordinances", "Go and make disciples... baptizing them", "Matthew 28:19"),
 ("Of Baptism", "water", "We were therefore buried with Him through baptism into death", "Romans 6:4"),
 ("Of the Lord's Supper", "supper", "You proclaim the Lord’s death until He comes", "1 Corinthians 11:26"),
 ("Of the State of Man after Death and the Resurrection", "tomb", "I am the resurrection and the life", "John 11:25"),
 ("Of the Last Judgment", "books", "And books were opened", "Revelation 20:12"),
]
def confession_scene(n, key):
    return svg(grad("#2A1810", "#4A2A1A") + f'<rect x="18" y="140" width="264" height="300" rx="10" fill="none" stroke="{G}" stroke-width="2" opacity="0.7"></rect>'
               + T(150, 180, f"CHAPTER {n}", 14, "#B9A06E", "Libre Franklin, sans-serif", 700) + ring("#C9A55A") + E[key]() + label("1689 Confession", 430, "#B9A06E"), "#2A1810")

# ---------------- the books of the Bible ----------------
SECTIONS = [("The Law", "#1E3B30", 5), ("History", "#3A2418", 12), ("Poetry & Wisdom", "#3A2448", 5), ("Major Prophets", "#4A1A1E", 5),
            ("Minor Prophets", "#2A3448", 12), ("Gospels", "#16324F", 4), ("History of the Church", "#16424A", 1), ("Paul's Letters", "#1F2A5A", 13),
            ("General Letters", "#2E3A22", 8), ("Prophecy", "#3A2E10", 1)]
def bb(name):
    def deco(f): E["b:" + name] = f; return f
    return deco
@bb("Genesis")
def _(): return E["creation"]()
@bb("Exodus")
def _(): return f'<path d="M60 240 Q90 300 70 400 H120 Q110 320 124 240Z" fill="{BL}"></path><path d="M240 240 Q210 300 230 400 H180 Q190 320 176 240Z" fill="{BL}"></path><path d="M124 240 H176 L180 400 H120Z" fill="#E8D3A0"></path>' + "".join(f'<path d="M{x} {y} q8 -6 16 0" stroke="{C}" stroke-width="2" fill="none"></path>' for x, y in [(74, 280), (88, 330), (196, 300), (206, 350)])
@bb("Leviticus")
def _(): return "".join(f'<rect x="{96+c*36}" y="{390-r*26}" width="34" height="24" fill="#9A9080"></rect>' for r in range(3) for c in range(3)) + flame(150, 312, 1.8)
@bb("Numbers")
def _(): return "".join(f'<ellipse cx="{150 + (i % 2) * 8 - 4}" cy="{220 + i * 18}" rx="{26 - i}" ry="13" fill="{C}" opacity="0.85"></ellipse>' for i in range(6)) + "".join(f'<path d="M{x-28} 400 L{x} 350 L{x+28} 400Z" fill="#B08A50"></path>' for x in (90, 150, 210))
@bb("Deuteronomy")
def _(): return E["tablets"]()
@bb("Joshua")
def _(): return "".join(f'<rect x="{70+i*32}" y="{330+(i%2)*14}" width="30" height="{70-(i%2)*14}" fill="#9A8A70" transform="rotate({(-1)**i*8} {85+i*32} 380)"></rect>' for i in range(5)) + f'<path d="M100 262 Q150 214 208 246 L220 230 L228 280 L204 268 Q150 242 108 276Z" fill="#E6CF8A" stroke="#8C6A2A" stroke-width="2"></path>'
@bb("Judges")
def _(): return f'<path d="M110 330 Q100 380 130 396 H170 Q200 380 190 330Z" fill="#B0563A"></path><rect x="186" y="250" width="10" height="110" fill="{BR}" transform="rotate(14 190 300)"></rect>' + flame(204, 254, 1.4)
@bb("Ruth")
def _(): return "".join(f'<path d="M150 400 Q{150+d*0.4:.0f} 320 {150+d} {230+abs(d)*0.6:.0f}" stroke="{G}" stroke-width="3" fill="none"></path><ellipse cx="{150+d}" cy="{224+abs(d)*0.6:.0f}" rx="6" ry="16" fill="{G}" transform="rotate({d*0.5:.0f} {150+d} {224+abs(d)*0.6:.0f})"></ellipse>' for d in range(-60, 61, 15)) + f'<path d="M126 350 H174" stroke="#8C6A2A" stroke-width="8"></path>'
@bb("1 Samuel")
def _(): return f'<path d="M100 240 Q150 320 200 240" stroke="#B08A50" stroke-width="5" fill="none"></path><ellipse cx="150" cy="290" rx="20" ry="12" fill="#8B4F24"></ellipse>' + "".join(f'<circle cx="{x}" cy="{y}" r="9" fill="#9A9080"></circle>' for x, y in [(110, 380), (136, 386), (162, 380), (188, 388), (214, 382)])
@bb("2 Samuel")
def _(): return f'<path d="M96 370 L90 280 L122 320 L150 260 L178 320 L210 280 L204 370Z" fill="{G}" stroke="#8C6A2A" stroke-width="3"></path>' + "".join(f'<circle cx="{x}" cy="{y}" r="6" fill="{c}"></circle>' for x, y, c in [(90, 278, R), (150, 258, BL), (210, 278, R)])
@bb("1 Kings")
def _(): return f'<path d="M70 290 L150 240 L230 290Z" fill="{G}"></path><rect x="76" y="290" width="148" height="100" fill="{C}"></rect><rect x="96" y="304" width="18" height="86" fill="{G}"></rect><rect x="186" y="304" width="18" height="86" fill="{G}"></rect><rect x="130" y="320" width="40" height="70" fill="#5A3A22"></rect>'
@bb("2 Kings")
def _(): return f'<circle cx="150" cy="320" r="54" fill="none" stroke="{G}" stroke-width="8"></circle><circle cx="150" cy="320" r="10" fill="{G}"></circle>' + "".join(f'<path d="M150 320 L{150+math.cos(math.radians(a))*54:.0f} {320+math.sin(math.radians(a))*54:.0f}" stroke="{G}" stroke-width="5"></path>' for a in range(0, 360, 45)) + flame(100, 270, 1.2) + flame(200, 270, 1.2) + flame(150, 250, 1.4)
@bb("1 Chronicles")
def _(): return f'<rect x="80" y="236" width="140" height="150" fill="{C}"></rect>' + f'<path d="M150 260 V300 M110 300 H190 M110 300 V330 M190 300 V330 M90 330 H130 M170 330 H210 M90 330 V360 M130 330 V360 M170 330 V360 M210 330 V360" stroke="#8C6A2A" stroke-width="3" fill="none"></path>' + "".join(f'<circle cx="{x}" cy="{y}" r="6" fill="#8C6A2A"></circle>' for x, y in [(150, 256), (90, 364), (130, 364), (170, 364), (210, 364)])
@bb("2 Chronicles")
def _(): return f'<rect x="90" y="300" width="120" height="66" fill="{G}" stroke="#8C6A2A" stroke-width="3"></rect><rect x="84" y="292" width="132" height="12" fill="#E6CF8A"></rect><path d="M60 340 H240" stroke="#8B4F24" stroke-width="7"></path>' + glow(150, 280, 70, 0.3)
@bb("Ezra")
def _(): return f'<rect x="60" y="270" width="180" height="100" fill="{C}"></rect><rect x="48" y="256" width="24" height="128" rx="12" fill="#8B4F24"></rect><rect x="228" y="256" width="24" height="128" rx="12" fill="#8B4F24"></rect>' + "".join(f'<path d="M80 {290+i*14} h140" stroke="{DIM}" stroke-width="2"></path>' for i in range(5))
@bb("Nehemiah")
def _(): return "".join(f'<rect x="{50+(r%2)*20+c*40}" y="{390-r*24}" width="38" height="22" fill="#9A7A60"></rect>' for r in range(4) for c in range(5) if 50+(r%2)*20+c*40 < 230) + f'<path d="M180 260 L230 230" stroke="#9AA4AE" stroke-width="6"></path><path d="M180 260 L170 280" stroke="{BR}" stroke-width="6"></path><path d="M90 250 L120 280 L140 250Z" fill="#9AA4AE"></path>'
@bb("Esther")
def _(): return f'<rect x="146" y="240" width="8" height="160" fill="{G}" transform="rotate(-20 150 320)"></rect><circle cx="178" cy="248" r="14" fill="{G}"></circle>' + f'<path d="M86 370 L80 320 L100 340 L116 310 L132 340 L152 320 L146 370Z" fill="{G}"></path>'
@bb("Job")
def _(): return f'<g fill="#7A8490"><ellipse cx="150" cy="260" rx="70" ry="30"></ellipse><ellipse cx="110" cy="276" rx="40" ry="22"></ellipse><ellipse cx="196" cy="276" rx="40" ry="22"></ellipse></g><path d="M156 290 L136 330 H156 L140 376 L184 316 H162 L176 290Z" fill="{G}"></path>' + "".join(f'<path d="M{x} 300 l-6 18" stroke="#9FC2D9" stroke-width="2"></path>' for x in range(96, 220, 18))
@bb("Psalms")
def _(): return f'<path d="M100 400 V250 Q100 220 130 230 Q210 260 214 400Z" fill="none" stroke="{G}" stroke-width="8"></path>' + "".join(f'<path d="M{110+i*14} {244+i*6} V396" stroke="{C}" stroke-width="2"></path>' for i in range(7))
@bb("Proverbs")
def _(): return "".join(f'<path transform="translate({x} {y})" d="M0 -18 L16 -9 V9 L0 18 L-16 9 V-9Z" fill="{G}" stroke="#8C6A2A" stroke-width="2"></path>' for x, y in [(118, 270), (150, 270), (182, 270), (102, 298), (134, 298), (166, 298), (198, 298), (118, 326), (150, 326), (182, 326), (134, 354), (166, 354)])
@bb("Ecclesiastes")
def _(): return f'<path d="M110 236 H190 M110 396 H190" stroke="{BR}" stroke-width="8"></path><path d="M118 240 Q118 300 150 316 Q182 300 182 240Z M118 392 Q118 332 150 316 Q182 332 182 392Z" fill="none" stroke="{C}" stroke-width="3"></path><path d="M126 252 Q150 270 174 252 Q166 290 150 306Z M126 392 Q150 360 174 392Z" fill="{G}"></path>'
@bb("Song of Solomon")
def _(): return f'<path d="M150 400 C 146 360 152 330 150 300" stroke="#5E9A4A" stroke-width="5" fill="none"></path><path transform="translate(150 350) rotate(-40)" d="M0 0 Q20 -18 40 0 Q20 18 0 0Z" fill="#5E9A4A"></path>' + "".join(f'<path transform="translate(150 300) rotate({a})" d="M0 0 Q-14 -30 0 -56 Q14 -30 0 0Z" fill="{C}"></path>' for a in (-50, -25, 0, 25, 50)) + f'<circle cx="150" cy="300" r="7" fill="{G}"></circle>'
@bb("Isaiah")
def _(): return f'<path d="M80 380 L180 280 M100 396 L196 292" stroke="#9AA4AE" stroke-width="6"></path><circle cx="190" cy="282" r="16" fill="#E07A2A"></circle><circle cx="190" cy="282" r="8" fill="{G}"></circle>' + glow(190, 282, 30, 0.5)
@bb("Jeremiah")
def _(): return f'<ellipse cx="150" cy="380" rx="90" ry="16" fill="#5A3A22"></ellipse><path d="M110 372 Q102 320 130 300 Q118 280 136 266 H164 Q182 280 170 300 Q198 320 190 372Z" fill="#B0563A"></path><path d="M126 266 H174" stroke="#8A3A22" stroke-width="5"></path>'
@bb("Lamentations")
def _(): return f'<circle cx="150" cy="390" r="50" fill="{G}" opacity="0.8"></circle><rect x="40" y="390" width="220" height="40" fill="#2A3448"></rect><path d="M150 230 Q124 280 132 300 Q150 320 168 300 Q176 280 150 230Z" fill="#9FC2D9"></path>'
@bb("Ezekiel")
def _(): return "".join(f'<ellipse cx="150" cy="310" rx="{rx}" ry="{ry}" fill="none" stroke="{G}" stroke-width="5" transform="rotate({a} 150 310)"></ellipse>' for rx, ry, a in [(70, 70, 0), (70, 30, 60), (70, 30, -60)]) + "".join(f'<circle cx="{150+math.cos(math.radians(a))*70:.0f}" cy="{310+math.sin(math.radians(a))*70:.0f}" r="5" fill="{C}"></circle>' for a in range(0, 360, 30))
@bb("Daniel")
def _(): return f'<circle cx="150" cy="306" r="70" fill="#B07A30"></circle><circle cx="150" cy="312" r="46" fill="#D9A050"></circle><circle cx="132" cy="300" r="5" fill="#1F1B16"></circle><circle cx="168" cy="300" r="5" fill="#1F1B16"></circle><path d="M142 326 L150 334 L158 326Z" fill="#5A3A22"></path><path d="M150 334 V342 M150 342 Q140 350 132 344 M150 342 Q160 350 168 344" stroke="#5A3A22" stroke-width="3" fill="none"></path>'
@bb("Hosea")
def _(): return "".join(f'<ellipse cx="{x}" cy="{y}" rx="16" ry="6" fill="#C9D2DA" stroke="#8A9AA6" stroke-width="2"></ellipse>' for x, y in [(110, 380), (110, 370), (110, 360), (140, 384), (140, 374)]) + "".join(f'<path d="M{x} 380 Q{x+4} 330 {x+12} 280" stroke="{G}" stroke-width="3" fill="none"></path><ellipse cx="{x+12}" cy="274" rx="5" ry="13" fill="{G}"></ellipse>' for x in (176, 192, 208))
@bb("Joel")
def _(): return f'<g fill="#7A8490"><ellipse cx="150" cy="250" rx="70" ry="28"></ellipse><ellipse cx="110" cy="264" rx="40" ry="20"></ellipse><ellipse cx="196" cy="264" rx="40" ry="20"></ellipse></g>' + "".join(f'<path d="M{x} {y} l-5 16" stroke="#9FC2D9" stroke-width="3"></path>' for x in range(90, 220, 16) for y in (296, 330, 364)) + f'<path d="M60 400 Q150 384 240 400" stroke="#5E9A4A" stroke-width="10" fill="none"></path>'
@bb("Amos")
def _(): return E["basket"]()
@bb("Obadiah")
def _(): return f'<path d="M60 410 L110 260 L170 240 L230 410Z" fill="#6A5E52"></path><path d="M110 250 Q150 210 200 240 Q170 236 150 250 Q134 236 110 250Z" fill="#3A2A1E"></path><path d="M120 224 L150 210 L180 224" stroke="{C}" stroke-width="3" fill="none"></path>'
@bb("Jonah")
def _(): return f'<path d="M70 320 Q120 250 200 290 L240 260 L232 310 L246 350 L204 326 Q120 380 70 320Z" fill="#5E7A90"></path><circle cx="100" cy="310" r="5" fill="#1F1B16"></circle><path d="M80 330 Q100 336 120 326" stroke="#1F1B16" stroke-width="3" fill="none"></path>' + "".join(f'<path d="M{x} 390 q12 -6 24 0" stroke="{C}" stroke-width="2" fill="none"></path>' for x in (60, 110, 160, 210))
@bb("Micah")
def _(): return "".join(house(x, y, w, "#D9C9A6", "#8B4F24", True) for x, y, w in [(84, 350, 40), (134, 340, 44), (186, 352, 38)]) + f'<path d="M150 214 L156 248 L190 254 L156 260 L150 294 L144 260 L110 254 L144 248Z" fill="{G}"></path>'
@bb("Nahum")
def _(): return f'<path d="M110 400 V280 H190 V400Z" fill="#8A8170"></path>' + "".join(f'<rect x="{110+i*18}" y="266" width="12" height="16" fill="#8A8170"></rect>' for i in range(5)) + f'<path d="M136 400 V350 A14 14 0 0 1 164 350 V400Z" fill="#2A1E15"></path>' + "".join(f'<path d="M{x} {y} q15 -8 30 0 q15 8 30 0" stroke="{BL}" stroke-width="5" fill="none"></path>' for x, y in [(30, 400), (190, 396), (40, 380)])
@bb("Habakkuk")
def _(): return f'<path d="M120 400 L130 250 H170 L180 400Z" fill="#9A9080"></path><path d="M116 250 H184 V232 H116Z" fill="#7A7060"></path>' + "".join(f'<rect x="{116+i*18}" y="220" width="12" height="14" fill="#7A7060"></rect>' for i in range(4)) + f'<rect x="142" y="270" width="16" height="22" fill="{G}"></rect>' + star5(220, 220, 8, C)
@bb("Zephaniah")
def _(): return house(100, 330, 100, C, R) + "".join(f'<g transform="translate({x} {y})"><ellipse cx="0" cy="0" rx="8" ry="6" transform="rotate(-20)" fill="{G}"></ellipse><path d="M7 -2 V-28" stroke="{G}" stroke-width="3"></path></g>' for x, y in [(96, 270), (130, 236), (176, 250), (214, 226)])
@bb("Haggai")
def _(): return "".join(f'<rect x="{60+c*46}" y="{380-r*30}" width="44" height="28" fill="{"#C9A55A" if (r, c) == (0, 0) else "#9A9080"}"></rect>' for r in range(3) for c in range(4) if c >= r) + T(82, 400, "1", 16, "#5A4636")
@bb("Zechariah")
def _(): return (f'<rect x="146" y="290" width="8" height="100" fill="{G}"></rect><path d="M100 290 Q100 330 150 330 Q200 330 200 290" stroke="{G}" stroke-width="6" fill="none"></path><path d="M120 290 Q120 312 150 312 Q180 312 180 290" stroke="{G}" stroke-width="5" fill="none"></path><rect x="120" y="388" width="60" height="8" fill="{G}"></rect>'
                 + "".join(flame(x, 286, 0.6) for x in (100, 120, 150, 180, 200)) + "".join(f'<circle cx="{x}" cy="260" r="26" fill="{GR}"></circle><rect x="{x-3}" y="280" width="6" height="110" fill="{BR}"></rect>' for x in (56, 244)))
@bb("Malachi")
def _(): return f'<circle cx="150" cy="380" r="50" fill="{G}"></circle>' + rays(150, 380, 150, 190, 350, 10, 5, 0.6) + '<rect x="40" y="380" width="220" height="40" fill="#2A3448"></rect>'
@bb("Matthew")
def _(): return f'<path d="M96 380 L90 300 L122 336 L150 280 L178 336 L210 300 L204 380Z" fill="{G}" stroke="#8C6A2A" stroke-width="3"></path><path d="M150 214 L156 240 L182 246 L156 252 L150 278 L144 252 L118 246 L144 240Z" fill="{C}"></path>'
@bb("Mark")
def _(): return f'<rect x="132" y="300" width="36" height="90" fill="#8B4F24"></rect><path d="M110 390 H190" stroke="#5A3A22" stroke-width="7"></path><path d="M140 300 Q140 260 150 254 Q160 260 160 300Z" fill="#E8D3A0"></path>' + flame(150, 256, 1.3) + glow(150, 240, 50, 0.4)
@bb("Luke")
def _(): return f'<path d="M80 340 H220 L200 390 H100Z" fill="#8B4F24"></path><path d="M80 340 Q150 300 220 340" fill="{G}"></path><path d="M100 390 L86 410 M200 390 L214 410" stroke="#5A3A22" stroke-width="6"></path><path d="M150 210 L155 236 L180 240 L155 244 L150 270 L145 244 L120 240 L145 236Z" fill="{C}"></path>'
@bb("John")
def _(): return rays(150, 300, 120, 0, 360, 15, 3, 0.5) + glow(150, 300, 50, 0.6) + f'<rect x="138" y="300" width="24" height="90" fill="{C}"></rect>' + flame(150, 298, 1.3)
@bb("Acts")
def _(): return f'<path d="M80 360 H220 L200 392 H100Z" fill="#7A4A1E"></path><rect x="146" y="230" width="6" height="130" fill="#5A3A22"></rect><path d="M152 236 Q206 290 152 346Z" fill="{C}"></path><path d="M146 246 Q104 296 146 340Z" fill="#E6E0D6"></path>' + "".join(f'<path d="M{x} 402 q12 -6 24 0" stroke="{C}" stroke-width="2" fill="none"></path>' for x in (60, 120, 180))
@bb("Romans")
def _(): return f'<path d="M80 400 V290 A70 70 0 0 1 220 290 V400 H190 V296 A40 40 0 0 0 110 296 V400Z" fill="#B8AE9A"></path>' + book(150, 330, 70)
@bb("1 Corinthians")
def _(): return f'<path d="M150 380 C 70 320 80 250 120 250 C 140 250 150 266 150 278 C 150 266 160 250 180 250 C 220 250 230 320 150 380Z" fill="{R}"></path>' + T(150, 326, "13", 26, C)
@bb("2 Corinthians")
def _(): return glow(150, 280, 60, 0.5) + f'<path d="M116 280 Q100 330 120 380 H180 Q200 330 184 280Z" fill="#B0563A"></path><rect x="124" y="268" width="52" height="14" fill="#8A3A22"></rect><path d="M150 268 L120 220 M150 268 L150 210 M150 268 L180 220" stroke="{G}" stroke-width="4"></path>'
@bb("Galatians")
def _(): return E["yoke"]()
@bb("Ephesians")
def _(): return "".join(f'<rect x="{80+c*48}" y="{360-r*34}" width="46" height="32" fill="#9A9080"></rect>' for r in range(3) for c in range(3) if not (r == 0 and c == 0)) + f'<rect x="80" y="360" width="46" height="32" fill="{G}"></rect>' + cross(103, 364, 24, "#5A4636")
@bb("Philippians")
def _(): return f'<path d="M110 250 H190 Q190 320 150 330 Q110 320 110 250Z" fill="{G}"></path><path d="M110 262 Q84 262 86 286 Q90 304 116 300 M190 262 Q216 262 214 286 Q210 304 184 300" stroke="{G}" stroke-width="6" fill="none"></path><rect x="142" y="330" width="16" height="36" fill="{G}"></rect><rect x="118" y="366" width="64" height="16" fill="{G}"></rect>'
@bb("Colossians")
def _(): return E["b:2 Samuel"]() + "".join(star5(x, y, 6, C) for x, y in [(80, 240), (220, 240), (150, 220)])
@bb("1 Thessalonians")
def _(): return rays(150, 230, 150, 0, 180, 12, 4, 0.4) + glow(150, 230, 40, 0.6) + f'<g fill="{C}" opacity="0.9"><ellipse cx="150" cy="330" rx="70" ry="24"></ellipse><ellipse cx="104" cy="344" rx="40" ry="18"></ellipse><ellipse cx="200" cy="344" rx="40" ry="18"></ellipse></g>'
@bb("2 Thessalonians")
def _(): return f'<rect x="70" y="360" width="160" height="16" fill="#8B4F24"></rect><path d="M84 376 V404 M216 376 V404" stroke="#5A3A22" stroke-width="7"></path><rect x="140" y="250" width="12" height="100" fill="{BR}" transform="rotate(30 146 300)"></rect><rect x="150" y="244" width="50" height="22" rx="4" fill="#7A8490" transform="rotate(30 146 300)"></rect>'
@bb("1 Timothy")
def _(): return f'<rect x="120" y="250" width="60" height="140" fill="#C9C2B0"></rect>' + "".join(f'<path d="M{x} 254 V386" stroke="#9A9282" stroke-width="3"></path>' for x in (132, 144, 156, 168)) + f'<rect x="110" y="236" width="80" height="16" fill="#C9C2B0"></rect><rect x="104" y="390" width="92" height="14" fill="#C9C2B0"></rect>'
@bb("2 Timothy")
def _(): return "".join(f'<ellipse cx="{150+math.cos(math.radians(a))*60:.0f}" cy="{300+math.sin(math.radians(a))*60:.0f}" rx="7" ry="15" transform="rotate({a+90} {150+math.cos(math.radians(a))*60:.0f} {300+math.sin(math.radians(a))*60:.0f})" fill="{GR}"></ellipse>' for a in list(range(110, 260, 16)) + list(range(-70, 80, 16))) + book(150, 290, 80)
@bb("Titus")
def _(): return f'<path d="M40 380 Q150 340 260 380 V420 H40Z" fill="{BL}"></path><path d="M80 380 Q100 330 150 326 Q200 330 220 380Z" fill="#5E9A4A"></path>' + church(150, 360, 0.45)
@bb("Philemon")
def _(): return E["seal"]() + f'<path d="M210 360 a14 14 0 1 1 0 0.1 M232 380 a14 14 0 1 1 0 0.1" stroke="#9AA4AE" stroke-width="5" fill="none"></path>'
@bb("Hebrews")
def _(): return glow(150, 300, 70, 0.5) + f'<path d="M70 230 H146 L140 300 L148 340 L138 400 H70Z" fill="#7A1E2B"></path><path d="M230 230 H156 L162 290 L152 330 L164 400 H230Z" fill="#2E4A7A"></path><rect x="64" y="222" width="172" height="10" fill="{G}"></rect>'
@bb("James")
def _(): return f'<ellipse cx="150" cy="290" rx="54" ry="70" fill="#C9D2DA" stroke="{G}" stroke-width="8"></ellipse><path d="M120 260 Q140 240 160 250" stroke="#FFFFFF" stroke-width="5" fill="none"></path><rect x="144" y="360" width="12" height="40" fill="{G}"></rect>'
@bb("1 Peter")
def _(): return "".join(f'<rect x="{x}" y="{y}" width="{w}" height="30" rx="6" fill="{c}"></rect>' for x, y, w, c in [(70, 370, 70, "#9A9080"), (144, 370, 86, "#8A8170"), (86, 336, 60, "#A89E8A"), (150, 336, 66, "#9A9080"), (110, 302, 80, "#8A8170")])
@bb("2 Peter")
def _(): return f'<rect x="40" y="320" width="220" height="100" fill="#0E1520"></rect>' + glow(150, 260, 50, 0.5) + f'<path d="M150 214 L158 252 L196 260 L158 268 L150 306 L142 268 L104 260 L142 252Z" fill="{C}"></path>' + f'<rect x="96" y="352" width="22" height="36" fill="{C}"></rect>' + flame(107, 352, 0.9)
@bb("1 John")
def _(): return rays(150, 300, 120, 0, 360, 20, 3, 0.4) + E["b:1 Corinthians"]().replace(T(150, 326, "13", 26, C), "")
@bb("2 John")
def _(): return E["steps"]() + f'<path d="M84 230 H136 V266 H84Z" fill="{C}"></path><path d="M84 230 L110 252 L136 230" stroke="#C9B49A" stroke-width="2" fill="none"></path>'
@bb("3 John")
def _(): return E["b:Zephaniah"]().split("<g")[0] + f'<rect x="140" y="360" width="20" height="40" fill="{G}"></rect>' + glow(150, 380, 30, 0.6)
@bb("Jude")
def _(): return f'<path d="M150 240 L206 260 V306 Q206 350 150 376 Q94 350 94 306 V260Z" fill="#2E4A7A" stroke="{G}" stroke-width="5"></path>' + star5(150, 306, 22, G)
@bb("Revelation")
def _(): return glow(150, 300, 100, 0.4) + f'<rect x="70" y="260" width="160" height="120" fill="#E6CF8A"></rect>' + "".join(f'<path d="M{x} 380 V330 A12 12 0 0 1 {x+24} 330 V380Z" fill="#F7F3EA"></path>' for x in (84, 138, 192)) + "".join(f'<rect x="{70+i*20}" y="248" width="12" height="14" fill="#E6CF8A"></rect>' for i in range(8)) + f'<path d="M150 380 C 140 400 160 410 150 430" stroke="{BL}" stroke-width="10" fill="none"></path>'

BOOKS = [
 ("Genesis", "In the beginning God created the heavens and the earth", "1:1", "Creation"),
 ("Exodus", "The LORD will fight for you; you need only to be still", "14:14", "The Red Sea parted"),
 ("Leviticus", "Be holy, because I am holy", "11:44", "The altar fire"),
 ("Numbers", "The LORD bless you and keep you", "6:24", "Tents and the pillar of cloud"),
 ("Deuteronomy", "You shall love the LORD your God with all your heart", "6:5", "The two tablets"),
 ("Joshua", "As for me and my house, we will serve the LORD!", "24:15", "Jericho's walls and the ram's horn"),
 ("Judges", "Everyone did what was right in his own eyes", "21:25", "Gideon's jar and torch"),
 ("Ruth", "Your people will be my people, and your God will be my God", "1:16", "A sheaf of barley"),
 ("1 Samuel", "The LORD sees the heart", "16:7", "David's sling and five stones"),
 ("2 Samuel", "Your throne will be established forever", "7:16", "David's crown"),
 ("1 Kings", "The LORD, He is God! The LORD, He is God!", "18:39", "Solomon's temple"),
 ("2 Kings", "Those who are with us are more than those who are with them", "6:16", "Chariot of fire"),
 ("1 Chronicles", "Give thanks to the LORD, for He is good", "16:34", "The family scroll"),
 ("2 Chronicles", "If My people... humble themselves and pray", "7:14", "The ark of the covenant"),
 ("Ezra", "Ezra had set his heart to study the Law of the LORD", "7:10", "The scroll of the Law"),
 ("Nehemiah", "The joy of the LORD is your strength", "8:10", "The wall, the trowel and the sword"),
 ("Esther", "For such a time as this?", "4:14", "The golden scepter"),
 ("Job", "I know that my Redeemer lives", "19:25", "The whirlwind"),
 ("Psalms", "Let everything that has breath praise the LORD!", "150:6", "The harp"),
 ("Proverbs", "The fear of the LORD is the beginning of knowledge", "1:7", "The honeycomb"),
 ("Ecclesiastes", "To everything there is a season", "3:1", "The hourglass"),
 ("Song of Solomon", "I am a rose of Sharon, a lily of the valley", "2:1", "The lily"),
 ("Isaiah", "He was pierced for our transgressions", "53:5", "The coal from the altar"),
 ("Jeremiah", "Like clay in the potter’s hand, so are you in My hand", "18:6", "The potter's wheel"),
 ("Lamentations", "His mercies never fail", "3:22", "A tear and the dawn"),
 ("Ezekiel", "I will give you a new heart", "36:26", "Wheels within wheels"),
 ("Daniel", "My God sent His angel and shut the mouths of the lions", "6:22", "The lion"),
 ("Hosea", "I will heal their apostasy; I will freely love them", "14:4", "Silver and barley"),
 ("Joel", "Return to the LORD your God. For He is gracious", "2:13", "The rain"),
 ("Amos", "Let justice roll on like a river", "5:24", "A basket of summer fruit"),
 ("Obadiah", "The kingdom will belong to the LORD", "1:21", "The eagle's rock"),
 ("Jonah", "Salvation is from the LORD!", "2:9", "The great fish"),
 ("Micah", "To act justly, to love mercy, and to walk humbly with your God?", "6:8", "Bethlehem and the star"),
 ("Nahum", "The LORD is good, a stronghold in the day of distress", "1:7", "The stronghold"),
 ("Habakkuk", "The righteous will live by faith", "2:4", "The watchtower"),
 ("Zephaniah", "He will rejoice over you with gladness", "3:17", "Singing over the home"),
 ("Haggai", "Consider carefully your ways", "1:5", "The foundation stone"),
 ("Zechariah", "Not by might nor by power, but by My Spirit", "4:6", "The lampstand and the olive trees"),
 ("Malachi", "The sun of righteousness will rise with healing in its wings", "4:2", "The rising sun"),
 ("Matthew", "Where is the One who has been born King of the Jews?", "2:2", "Crown and star"),
 ("Mark", "The Son of Man did not come to be served, but to serve", "10:45", "The lamp on its stand"),
 ("Luke", "She gave birth to her firstborn, a Son... and laid Him in a manger", "2:7", "The manger"),
 ("John", "In the beginning was the Word", "1:1", "Light in the darkness"),
 ("Acts", "You will be My witnesses... to the ends of the earth", "1:8", "Paul's ship"),
 ("Romans", "I am not ashamed of the gospel", "1:16", "The Roman arch and the Word"),
 ("1 Corinthians", "And now these three remain: faith, hope, and love", "13:13", "Love, chapter 13"),
 ("2 Corinthians", "We have this treasure in jars of clay", "4:7", "The jar of clay"),
 ("Galatians", "It is for freedom that Christ has set us free", "5:1", "The broken yoke"),
 ("Ephesians", "Christ Jesus Himself as the cornerstone", "2:20", "The cornerstone"),
 ("Philippians", "I press on toward the goal to win the prize", "3:14", "The prize"),
 ("Colossians", "In Him all things hold together", "1:17", "The crown over all"),
 ("1 Thessalonians", "So we will always be with the Lord", "4:17", "Light above the clouds"),
 ("2 Thessalonians", "Do not grow weary in well-doing", "3:13", "The workbench"),
 ("1 Timothy", "The church of the living God, the pillar and foundation of the truth", "3:15", "The pillar"),
 ("2 Timothy", "I have fought the good fight, I have finished the race", "4:7", "The laurel and the Word"),
 ("Titus", "The grace of God has appeared, bringing salvation to everyone", "2:11", "Church on the island"),
 ("Philemon", "No longer as a slave, but... as a beloved brother", "1:16", "The letter and broken shackles"),
 ("Hebrews", "The new and living way opened for us through the curtain", "10:20", "The curtain torn"),
 ("James", "Be doers of the word, and not hearers only", "1:22", "The mirror"),
 ("1 Peter", "You also, like living stones, are being built into a spiritual house", "2:5", "Living stones"),
 ("2 Peter", "A lamp shining in a dark place, until the day dawns and the morning star rises", "1:19", "The morning star"),
 ("1 John", "God is love", "4:8", "Love in the light"),
 ("2 John", "Walking in the truth", "1:4", "Footsteps and a letter"),
 ("3 John", "No greater joy than to hear that my children are walking in the truth", "1:4", "The open door"),
 ("Jude", "To Him who is able to keep you from stumbling", "1:24", "The shield"),
 ("Revelation", "Behold, I make all things new", "21:5", "The city with gates of pearl"),
]
assert len(BOOKS) == 66 and all(("b:" + b[0]) in E for b in BOOKS)
def section_of(i):
    n = 0
    for name, col, count in SECTIONS:
        if i < n + count: return name, col
        n += count
def book_scene(i):
    name, col = section_of(i)
    return svg(grad(col, "#0E1520", 1.2) + ring(G) + E["b:" + BOOKS[i][0]]() + label(name, 430, "#E3D3A8"), col)
