"""Special days: one day on the calendar gets a full-panel picture.

Three ways a day becomes special:
  1. Our own events: a title that starts with ⭐ (or "#special" in the notes), or a
     title that contains one of the "words" from Settings > Special days.
     A "photo: <name>" line in the notes picks the picture.
  2. U.S. holidays from Google's public holiday calendar, each set to
     Hide / Show (a small line on the day) / Special (takes over the day).
  3. The church year, worked out here every year (no calendar or list to keep up):
     Easter by the standard formula, Palm Sunday, Good Friday, Ascension and
     Pentecost counted from it; Christmas Eve, Christmas Day and Reformation Day fixed.
  4. The first day of each season (equinoxes and solstices, worked out here), on quiet days only.

A birthday shows the person's own portrait (app/portraits.py) with their name on the banner.

A real photo uploaded in Settings beats the built-in drawing of the same name.

The pictures and the rules that bring them up (which holidays, the church-year dates, title words, the
seasons, the Sunday series) come from the turned-on art packs (app/packs.py). The tables in this file are
the source the packs are made from (scripts/build-pack.py); at run time SpecialDays reads the packs.
"""
from __future__ import annotations

import io
import logging
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import httpx
import icalendar
from PIL import Image, ImageOps

log = logging.getLogger(__name__)

US_HOLIDAYS_URL = "https://calendar.google.com/calendar/ical/en.usa%23holiday%40group.v.calendar.google.com/public/basic.ics"
MODES = ("hide", "show", "special")
MAX_UPLOAD = 40 * 1024 * 1024

from .scenes_family import NAMES as FAMILY_NAMES, PICTURE_ONLY, THEMES as FAMILY_THEMES, WORDS as FAMILY_WORDS  # noqa: E402

# Every drawing the packs are made from (app/pack_build.py). At run time: the turned-on packs' scenes.
THEMES = {"palm", "goodfriday", "easter", "reformation", "xmaseve", "christmas", "newyear", "mlk", "valentine",
          "presidents", "mothers", "memorial", "fathers", "july4", "labor", "veterans", "thanksgiving", "school",
          "pattern", "park", "gardentrain", "trains", "cruise", "waterpark", "vacation", "camping", "vbs", "beach", "roadtrip", "flight", "trip", "churchglass"} | set(FAMILY_THEMES)

# The script line on our own special days, by look.
FAMILY_SCRIPT = {"park": "Park day!",
                 "gardentrain": "All aboard!", "trains": "Train chasing!", "cruise": "Bon voyage!", "waterpark": "Splash day!", "vacation": "Vacation!",
                 "school": "School's out!", "camping": "Camp out!", "vbs": "VBS week!",
                 "beach": "Vacation!", "roadtrip": "Road trip!", "flight": "Up, up and away!", "trip": "Vacation!", "churchglass": "Lord's Day",
                 **{k: v[1] for k, v in FAMILY_NAMES.items()}}

# ---------------- church year ----------------

CHURCH = [
    # key, name, (days from Easter | (month, day)), look, script, verse, solemn, on by default
    ("palm", "Palm Sunday", -7, "palm", "Hosanna!", "“Blessed is He who comes in the name of the Lord!” Mark 11:9", False, False),
    ("goodfriday", "Good Friday", -2, "goodfriday", "It is finished", "John 19:30", True, True),
    ("easter", "Resurrection Sunday", 0, "easter", "He is risen!", "“He is not here; He has risen.” Matthew 28:6", False, True),
    ("ascension", "Ascension Day", 39, "pattern", "He ascended", "“He was taken up, and a cloud hid Him from their sight.” Acts 1:9", False, False),
    ("pentecost", "Pentecost Sunday", 49, "pattern", "Pentecost", "“And they were all filled with the Holy Spirit.” Acts 2:4", False, False),
    ("reformation", "Reformation Day", (10, 31), "reformation", "Sola Scriptura", "“The righteous will live by faith.” Romans 1:17", False, True),
    ("xmaseve", "Christmas Eve", (12, 24), "xmaseve", "Christmas Eve", "“The Light shines in the darkness.” John 1:5", False, True),
    ("christmas", "Christmas Day", (12, 25), "christmas", "Merry Christmas!", "“For unto us a child is born.” Isaiah 9:6", False, True),
]
CHURCH_DEFAULTS = {c[0]: c[7] for c in CHURCH}
# Google's holiday calendar also lists these; the church year shows them instead (once).
GOOGLE_HANDLED_BY_CHURCH = {"easter sunday": "easter", "christmas eve": "xmaseve", "christmas day": "christmas"}


def easter(year: int) -> date:
    """Western Easter Sunday (the anonymous Gregorian algorithm)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    return date(year, month, (h + l - 7 * m + 114) % 31 + 1)


def church_days(year: int) -> list[dict]:
    e = easter(year)
    out = []
    for key, name, when, look, script, verse, solemn, _ in CHURCH:
        d = e + timedelta(days=when) if isinstance(when, int) else date(year, *when)
        out.append({"key": key, "name": name, "date": d, "look": look, "script": script, "verse": verse,
                    "solemn": solemn, "icon": "cross"})
    return out


# ---------------- U.S. holidays ----------------

HOLIDAY_LOOKS = {
    # normalized name: (look, script, solemn, verse)
    "new year's day": ("newyear", "Happy New Year!", False, ""),
    "martin luther king jr. day": ("mlk", "Remember", True, ""),
    "valentine's day": ("valentine", "Be mine", False, ""),
    "presidents' day": ("presidents", "Presidents' Day", False, ""),
    "mother's day": ("mothers", "Happy Mother's Day!", False, ""),
    "memorial day": ("memorial", "We remember", True, ""),
    "father's day": ("fathers", "Happy Father's Day!", False, ""),
    "independence day": ("july4", "Happy 4th!", False, ""),
    "labor day": ("labor", "Labor Day", False, ""),
    "veterans day": ("veterans", "Thank you", True, ""),
    "thanksgiving day": ("thanksgiving", "Give thanks", False, "“Give thanks to the LORD, for He is good.” Psalm 107:1"),
}
DEFAULT_MODES = {
    "new year's day": "special", "mother's day": "special", "memorial day": "special", "father's day": "special",
    "independence day": "special", "veterans day": "special", "thanksgiving day": "special",
    "halloween": "hide", "black friday": "hide", "tax day": "hide", "st. patrick's day": "hide",
    "cinco de mayo": "hide", "easter monday": "hide", "columbus day": "hide",
}
DEFAULT_WORDS = [{"word": "Water park", "look": "waterpark"}, {"word": "Waterpark", "look": "waterpark"},
                 {"word": "Last day of school", "look": "school"}, {"word": "VBS", "look": "vbs"},
                 {"word": "Vacation Bible School", "look": "vbs"}, {"word": "Camping", "look": "camping"},
                 {"word": "Campout", "look": "camping"}, {"word": "Camporee", "look": "camping"},
                 {"word": "Road trip", "look": "roadtrip"}, {"word": "Flight", "look": "flight"}, {"word": "Fly to", "look": "flight"},
                 # amusement parks: the park picture with the park's name on its sign. Add your own parks' names
                 # in Settings > Special days; the picture's sign shows the name from the event title or location.
                 {"word": "Amusement park", "look": "park"}, {"word": "Theme park", "look": "park"},
                 # trains: club layouts and train shows, and chasing the real ones
                 {"word": "Train show", "look": "gardentrain"},
                 {"word": "Garden railroad", "look": "gardentrain"}, {"word": "Garden railway", "look": "gardentrain"},
                 {"word": "Train chase", "look": "trains"}, {"word": "Chase trains", "look": "trains"}, {"word": "Railfan", "look": "trains"},
                 {"word": "Cruise", "look": "cruise"},
                 # family milestones, kids' activities, Scouts, church life, outings, visitors (app/scenes_family.py)
                 *[{"word": w, "look": k, **({"picture_only": True} if w in PICTURE_ONLY else {})} for w, k in FAMILY_WORDS],
                 # first match wins: these come last, so VBS, park names and the rest win over them
                 {"word": "Beach", "look": "beach"}, {"word": "Vacation", "look": "trip"}]
GENERIC_PARK_WORDS = {"amusement park", "theme park"}


# ---------------- seasons ----------------

SEASONS = [("spring", "First day of spring", (2451623.80984, 365242.37404, 0.05169, -0.00411, -0.00057)),
           ("summer", "First day of summer", (2451716.56767, 365241.62603, 0.00325, 0.00888, -0.00030)),
           ("fall", "First day of fall", (2451810.21715, 365242.01767, -0.11575, 0.00337, 0.00078)),
           ("winter", "First day of winter", (2451900.05952, 365242.74049, -0.06223, -0.00823, 0.00032))]


def season_days(year: int, tz: str = "America/New_York") -> dict:
    """{date: (look, name)}: the equinoxes and solstices (Meeus' mean formulas, within an hour or so) on the local calendar."""
    y = (year - 2000) / 1000
    out = {}
    for key, name, c in SEASONS:
        jd = c[0] + c[1] * y + c[2] * y ** 2 + c[3] * y ** 3 + c[4] * y ** 4
        when = datetime(2000, 1, 1, 12, tzinfo=ZoneInfo("UTC")) + timedelta(days=jd - 2451545.0)
        out[when.astimezone(ZoneInfo(tz)).date()] = (key, name)
    return out


def default_words() -> list[dict]:
    """The title words from the turned-on art packs (Settings > Special days starts from these)."""
    from .packs import current
    return current().words


def norm(name: str) -> str:
    """'Presidents’ Day' -> "presidents' day"; '(substitute)' days share their holiday's setting."""
    n = name.replace("’", "'").replace("‘", "'").lower()
    return re.sub(r"\s*\(substitute\)\s*$", "", n).strip()


def is_substitute(name: str) -> bool:
    return "(substitute)" in name.lower()


class HolidayFeed:
    """Google's public 'Holidays in the United States' calendar, read once a day and cached on disk."""

    def __init__(self, url: str, cache: Path, http: Optional[httpx.Client] = None):
        self.url = url
        self.cache = cache
        self.http = http or httpx.Client(timeout=20, follow_redirects=True)
        self.days: list[dict] = []
        self.error: Optional[str] = None
        self.read_at: Optional[datetime] = None
        if cache.exists():
            self._parse(cache.read_bytes())

    def refresh(self, force: bool = False) -> None:
        if not self.url:
            self.days, self.error = [], None
            return
        if not force and self.read_at and datetime.now() - self.read_at < timedelta(hours=20):
            return
        try:
            if self.url.startswith("file:") or not re.match(r"^https?://", self.url):
                data = Path(self.url.removeprefix("file:")).read_bytes()
            else:
                r = self.http.get(self.url)
                r.raise_for_status()
                data = r.content
            if b"BEGIN:VCALENDAR" not in data[:200]:
                raise ValueError("that address didn't return a calendar")
            self._parse(data)
            self.cache.parent.mkdir(parents=True, exist_ok=True)
            self.cache.write_bytes(data)
            self.error = None
        except Exception as exc:
            log.warning("holiday calendar refresh failed: %s", exc)
            self.error = str(exc)[:200]
        self.read_at = datetime.now()

    def _parse(self, data: bytes) -> None:
        cal = icalendar.Calendar.from_ical(data)
        out = []
        for ev in cal.walk("VEVENT"):
            d = ev.get("DTSTART").dt
            d = d.date() if isinstance(d, datetime) else d
            name = str(ev.get("SUMMARY", "")).strip()
            if name:
                out.append({"date": d, "name": name, "observance": "observance" in str(ev.get("DESCRIPTION", "")).lower()})
        out.sort(key=lambda h: h["date"])
        self.days = out


# ---------------- our own events ----------------

STAR = re.compile(r"^\s*(?:⭐|🌟|★)️?\s*")
PHOTO_LINE = re.compile(r"(?im)^\s*photo\s*:\s*([\w .-]+?)\s*$")
SPECIAL_TAG = re.compile(r"(?i)#special\b")
PLAIN = {"none", "off", "no", "plain"}   # "photo: none" in the notes: not special, no picture


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40]


def plain_text(description: str) -> str:
    """Google sends a description with any formatting as HTML (<br>, <b>, &nbsp;): back to plain lines."""
    import html
    d = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>", "\n", description or "")
    d = re.sub(r"<[^>]+>", "", d)
    return html.unescape(d).replace("\xa0", " ").replace("\r", "")


def flag_event(title: str, description: str, words: list[dict], people: Optional[list] = None) -> tuple[str, Optional[str], str]:
    """(clean title, look or None when not special, notes without the flag lines).
    Special when: a star starts the title, #special is in the description, a "photo: <name>" line
    is in the description, or a word from Settings > Special days is in the title ("photo: none" turns all of
    that off for one event). A "picture only" word
    just picks the picture when the event is special some other way."""
    look: Optional[str] = None
    special = False
    clean = title
    description = plain_text(description)
    if STAR.match(title):
        clean, special = STAR.sub("", title, count=1).strip(), True
    if SPECIAL_TAG.search(description or ""):
        special = True
    m = PHOTO_LINE.search(description or "")
    if m and slug(m.group(1)) in PLAIN:
        # "photo: none": keep this one an ordinary event, whatever its title or star says
        return STAR.sub("", title, count=1).strip(), None, PHOTO_LINE.sub("", SPECIAL_TAG.sub("", description or "")).strip()
    if m:
        look, special = slug(m.group(1)), True   # asking for a picture means "make this special"
    hint = None
    if people is not None:
        from .portraits import is_family_birthday
        if is_family_birthday(clean, people):   # one of ours: always the birthday picture
            special, look = True, look or "birthday"
    for w in words or []:
        word = str(w.get("word", "")).strip()
        if word and re.search(r"(?i)\b" + re.escape(word) + r"\b", clean):
            wlook = slug(str(w.get("look") or "")) or None
            # "Soccer": the picture for a starred game, not every practice. A birthday word only counts by itself
            # for one of ours (people given); a friend's party just gets the picture if it's starred.
            if w.get("picture_only") or (wlook == "birthday" and people is not None):
                hint = hint or wlook
                continue
            special = True
            look = look or wlook
            break
    look = look or hint
    notes = PHOTO_LINE.sub("", SPECIAL_TAG.sub("", description or "")).strip()
    return clean, ((look or "") if special else None), notes


# ---------------- pictures for special days ----------------

def save_picture(folder: Path, name: str, data: bytes) -> str:
    """Keep an uploaded picture (no bigger than 1400 px) under a short name the notes can use."""
    if len(data) > MAX_UPLOAD:
        raise ValueError("That picture is over 40 MB.")
    key = slug(name)
    if not key:
        raise ValueError("Give the picture a name, like holiday-world.")
    try:
        im = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    except Exception:
        raise ValueError("That isn't a picture this frame can read (JPEG, PNG or WebP).")
    im.thumbnail((1400, 1400), Image.LANCZOS)
    folder.mkdir(parents=True, exist_ok=True)
    im.save(folder / f"{key}.jpg", "JPEG", quality=86)
    return key


def list_pictures(folder: Path) -> list[str]:
    return sorted(p.stem for p in folder.glob("*.jpg")) if folder.exists() else []


# ---------------- putting it together ----------------

class SpecialDays:
    def __init__(self, cfg: dict, holidays: HolidayFeed, pictures: Path, people: Optional[list] = None,
                 portrait=None, tz: str = "America/New_York", packs=None):
        from .packs import current
        self.packs = packs or current()   # the turned-on art packs: pictures and rules
        self.cfg = cfg
        self.holidays = holidays
        self.pictures = pictures
        self.people = people or []          # app/portraits.people_of(settings)
        self.portrait = portrait or (lambda person: None)   # person dict -> picture URL or None
        self.tz = tz
        self.seasons = bool(cfg.get("seasons", True))   # the first day of each season, on quiet days
        self._season_cache: dict[int, dict] = {}
        self.church_defaults = self.packs.church_defaults()
        self.church_on = {k: bool((cfg.get("church") or {}).get(k, v)) for k, v in self.church_defaults.items()}
        self.modes = dict(self.packs.holiday_modes(), **{norm(k): v for k, v in (cfg.get("holiday_modes") or {}).items() if v in MODES})
        self.handled_by_church = self.packs.replaced_holidays()
        self.countdown_days = int(cfg.get("countdown_days", 7))
        self.sundays = bool(cfg.get("sundays", True))  # a Lord's Day picture every Sunday (app/lordsday.py)
        self._church_cache: dict[int, dict[date, dict]] = {}
        self._special_dates: Optional[set] = None

    @property
    def words(self) -> list[dict]:
        w = self.cfg.get("words")
        return self.packs.words if w is None else w

    def mode(self, name: str) -> str:
        m = self.modes.get(norm(name), "show")
        if is_substitute(name) and m == "special":
            return "show"  # the day off shows as a plain line; the holiday itself gets the picture
        return m

    def park_name(self, ev: dict) -> str:
        """What the park picture's sign says: the park named in the title (a word from Settings), else where it is."""
        for w in self.words:
            word = str(w.get("word", ""))
            if w.get("look") == "park" and word.lower() not in GENERIC_PARK_WORDS:
                m = re.search(r"(?i)\b" + re.escape(word) + r"\b", ev["title"])
                if m:
                    return m.group(0)
        where = (ev.get("where") or "").split(",")[0].strip()
        return (where or ev["title"])[:28]

    def picture(self, look: str, d: Optional[date] = None) -> tuple[str, Optional[str]]:
        """(drawing to use, photo URL or None). With a day, a scene's seasonal variant (pack.json "variants") counts."""
        key = slug(look or "")
        photo = f"special/{key}.jpg" if key and (self.pictures / f"{key}.jpg").exists() else None
        scenes = self.packs.scenes
        drawing = key if key in scenes else key.replace("-", "") if key.replace("-", "") in scenes else "pattern"
        return self.packs.variant(drawing, d), photo  # "water-park" and "waterpark" both find the water park drawing

    def _church(self, d: date) -> Optional[dict]:
        if d.year not in self._church_cache:
            self._church_cache[d.year] = {c["date"]: c for c in self.packs.church_days(d.year)}
        c = self._church_cache[d.year].get(d)
        return c if c and self.church_on.get(c["key"]) else None

    def _family_birthday(self, d: date) -> Optional[dict]:
        for p in self.people:
            b = p.get("birthday") or ""
            try:
                born = date.fromisoformat(b)
            except ValueError:
                continue
            m, dd = born.month, born.day
            if (m, dd) == (2, 29) and not (d.year % 4 == 0 and (d.year % 100 or d.year % 400 == 0)):
                dd = 28   # a leap-day birthday shows on Feb 28 in other years
            if (d.month, d.day) != (m, dd) or d.year < born.year:
                continue
            age = d.year - born.year
            nth = f"{age}{'th' if 10 <= age % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(age % 10, 'th')} " if age else ""
            theme, photo = self.picture("birthday")
            return {"kind": "birthday", "key": f"birthday-{p['slug']}", "title": f"{p['name']}'s {nth}birthday".replace("  ", " "),
                    "script": f"Happy {nth}birthday, {p['name']}!", "theme": theme, "photo": photo, "name": p["name"],
                    "portrait": self.portrait(p), "icon": "star", "solemn": False, "verse": "", "lines": [], "span": [0, 1]}
        return None

    def holiday_sunday(self, d: date) -> bool:
        """A church-year day or a holiday set to Special: it takes the day, and the Sunday pictures wait a week."""
        if self._church(d):
            return True
        if self._special_dates is None:
            self._special_dates = {h["date"] for h in self.holidays.days
                                   if norm(h["name"]) not in self.handled_by_church and self.mode(h["name"]) == "special"}
        return d in self._special_dates

    def holidays_on(self, d: date) -> list[dict]:
        return [h for h in self.holidays.days if h["date"] == d and norm(h["name"]) not in self.handled_by_church]

    def for_day(self, d: date, events: list[dict], today: date) -> tuple[Optional[dict], list[str]]:
        """The day's special (or None) and the holiday names to show as small lines."""
        special = None
        own = next((e for e in events if e.get("look") is not None), None)
        # A family birthday (Settings > Family) is that person's day: it wins over other starred events, which
        # show underneath. A calendar event for the same birthday is used as is.
        bday = self._family_birthday(d)
        if bday and own and own.get("look") != "birthday":
            own = None
        if own:
            theme, photo = self.picture(own["look"], d)
            lines = [own["time"] if own["all_day"] else own["time"] + (" – " + own["end_time"] if own.get("end_time") else "")]
            if own.get("where"):
                lines.append(own["where"])
            special = {"kind": "event", "key": own.get("uid") or own["title"], "uid": own.get("uid"), "title": own["title"],
                       "script": self.packs.script(theme) or "Special day!", "theme": theme, "photo": photo,
                       "icon": "star", "solemn": False, "verse": "", "lines": lines, "span": own.get("span", [0, 1])}
            if theme == "park":
                special["place"] = self.park_name(own)
                special["place_from_where"] = bool(own.get("where")) and special["place"] == own["where"].split(",")[0].strip()[:28]
            if theme == "birthday":
                from .portraits import birthday_name, match_person
                who = match_person(own["title"], self.people)
                special["name"] = birthday_name(own["title"], self.people)
                special["portrait"] = self.portrait(who) if who else None
                special["script"] = f"Happy birthday, {special['name']}!" if special["name"] else "Happy birthday!"
        if special is None:   # a birthday from Settings > Family, with no calendar event needed
            special = bday
        church = self._church(d)
        if special is None and church:
            theme, photo = self.picture(church["key"] if (self.pictures / f"{church['key']}.jpg").exists() else church["look"])
            special = {"kind": "church", "key": "church-" + church["key"], "title": church["name"], "script": church["script"],
                       "theme": theme, "photo": photo, "icon": "cross", "solemn": church["solemn"], "verse": church["verse"],
                       "lines": [], "span": [0, 1]}
        shown = []
        for h in self.holidays_on(d):
            m = self.mode(h["name"])
            if m == "special" and special is None:
                n = norm(h["name"])
                look, script, solemn, verse = self.packs.holiday_looks().get(n, ("pattern", "Special day", False, ""))
                theme, photo = self.picture(slug(n) if (self.pictures / f"{slug(n)}.jpg").exists() else look)
                special = {"kind": "holiday", "key": "holiday-" + slug(n), "title": h["name"], "script": script,
                           "theme": theme, "photo": photo, "icon": None if solemn else "star", "solemn": solemn,
                           "verse": verse, "lines": [], "span": [0, 1]}
            elif m != "hide":
                shown.append(h["name"])
        if church and special and special["kind"] != "church":
            shown.insert(0, church["name"])
        if special is None and self.seasons and not (d.weekday() == 6 and self.sundays and self.packs.weekly):
            if d.year not in self._season_cache:
                self._season_cache[d.year] = season_days(d.year, self.tz)
            season = self._season_cache[d.year].get(d)
            if season and season[0] in self.packs.seasons:
                theme, photo = self.picture(season[0])
                special = {"kind": "season", "key": "season-" + season[0], "title": season[1], "script": self.packs.script(season[0]) or season[1],
                           "theme": theme, "photo": photo, "icon": None, "solemn": False, "verse": "", "lines": [], "span": [0, 1]}
        ld = self.packs.sunday(d, self.holiday_sunday) if special is None and d.weekday() == 6 and self.sundays else None
        if ld:  # the weekly picture (the faith pack's Lord's Day series) comes last
            special = {"kind": "sunday", "key": f"sunday-{d.isoformat()}", "title": ld["title"], "script": ld["script"],
                       "theme": "pattern", "photo": None, "svg": ld["svg"], "icon": "cross", "solemn": False,
                       "verse": ld["verse"], "about": ld["about"], "lines": [f"{ld['series']} · {ld['n']} of {ld['count']}"],
                       "span": [0, 1]}
        if special:
            n = (d - today).days
            special["countdown"] = ("" if special["solemn"] or special["kind"] in ("sunday", "season") or n < 0 else
                                    "Today!" if n == 0 else "Tomorrow!" if n == 1 else f"In {n} days")
            special["days_until"] = n
        return special, shown

    def settings_view(self, today: date) -> dict:
        """What Settings > Special days lists: the next year of Google holidays and the church year."""
        seen, google = set(), []
        for h in self.holidays.days:
            n = norm(h["name"])
            if h["date"] < today or h["date"] > today + timedelta(days=366) or n in seen:
                continue
            if n in self.handled_by_church or is_substitute(h["name"]):
                continue
            seen.add(n)
            google.append({"key": n, "name": h["name"].replace("’", "'"), "date": h["date"].isoformat(),
                           "observance": h["observance"], "mode": self.modes.get(n, "show")})
        church = []
        for y in (today.year, today.year + 1):
            for c in self.packs.church_days(y):
                if today <= c["date"] and c["key"] not in {x["key"] for x in church}:
                    church.append({"key": c["key"], "name": c["name"], "date": c["date"].isoformat(),
                                   "on": self.church_on[c["key"]]})
        church.sort(key=lambda c: c["date"])
        from .picture_guide import guide_from_packs
        themes = self.packs.visible_scenes()
        return {"google": google, "church": church, "words": self.words, "countdown_days": self.countdown_days, "sundays": self.sundays,
                "seasons": self.seasons, "look_names": {k: self.packs.title(k) for k in themes},
                "has_sundays": bool(self.packs.weekly), "sunday_label": (self.packs.weekly or {}).get("label") or "A picture every Sunday",
                "has_seasons": bool(self.packs.seasons), "has_church": bool(self.packs.church),
                "groups": guide_from_packs(self.packs, self.words),
                "holiday_url": self.holidays.url, "holiday_error": self.holidays.error,
                "holiday_count": len([h for h in self.holidays.days if today <= h["date"] <= today + timedelta(days=366)]),
                "pictures": list_pictures(self.pictures), "themes": sorted(themes - {"pattern"})}
