"""Make art packs from the Python drawing code (app/scenes.py, app/scenes_family.py, app/lordsday_art.py).

The drawing code and the tables in app/special.py, app/picture_guide.py and app/lordsday.py are the
source. This module sorts them into packs and writes each one as a folder (pack.json, scenes/*.svg and,
for the faith pack, series.json with series/*.svg) and as a zip. scripts/build-pack.py is the command
line for it; the server also uses it to make a downloadable pack when its zip isn't on disk yet.

Packs (docs/art-packs.md):
  built in:  holidays-us, seasons, family-basics   (written to packs/<id>/ in the repo)
  optional:  faith, outings, kids-activities        (zips in dist/packs/, listed in packs/index.json)
             faith is "default": installed and turned on the first time the server starts (app/packs.py seed_defaults)
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION = "1.0.0"
VERSIONS = {"faith": "1.2.0"}   # 1.1.0: each verse also carries its reference and shortening (Bible translations)
                               # 1.1.1: every verse is exact ESV wording (trimmed excerpts, gaps marked "...")
                               # 1.2.0: the verses are the BSB (public domain), exact wording, gaps marked "..."
LICENSE = "CC BY 4.0"
BUILT_IN = ("holidays-us", "seasons", "family-basics")
OPTIONAL = ("faith", "outings", "kids-activities")
DEFAULT_ON = ("faith",)   # downloadable, but installed and on the first time Doorpost starts (removable)
ZIP_TIME = (2026, 1, 1, 0, 0, 0)   # fixed, so the same drawings always make the same zip (and sha256)

# Which picture-guide groups go in which pack (app/picture_guide.py GROUPS).
PACK_GROUPS = {
    "faith": ["Church year", "Church life"],
    "holidays-us": ["U.S. holidays"],
    "seasons": ["Seasons"],
    "family-basics": ["Family days", "Trips and vacations", "Family milestones", "Visitors and evenings"],
    "outings": ["Parks and water parks", "Trains", "Outings"],
    "kids-activities": ["Kids' activities", "Scouts"],
}
EXTRA_SCENES = {"family-basics": {"vacation": {}, "vacation-wide": {"hidden": True}}}   # not listed in a group
CATCH_ALL = ("beach", "vacation")   # general title words: checked after every other word (first match wins)

INFO = {
    "faith": ("Faith", "The church year (Palm Sunday through Christmas), church life pictures, a verse on Thanksgiving, "
              "bedtime verses on the clock, and a picture with a verse every Sunday from five series: the Lord's Day, "
              "the Ten Commandments, the Trinity, the 1689 Confession and the books of the Bible."),
    "holidays-us": ("U.S. holidays", "Pictures for New Year's Day, Memorial Day, the 4th of July, Thanksgiving and the "
                    "other U.S. holidays, and which ones take over their day by default."),
    "seasons": ("Seasons", "The first day of spring, summer, fall and winter, and a snow day."),
    "family-basics": ("Family basics", "Birthdays, anniversaries, school days, graduation, trips and vacations, "
                      "visitors and date night, plus the gold pattern used when a day has no picture."),
    "outings": ("Outings", "Amusement and water parks, trains, the zoo, the aquarium, fairs, hikes, lake days, "
                "pumpkin patches, apple picking and Christmas lights."),
    "kids-activities": ("Kids' activities", "Game days (baseball, soccer, football), recitals, school plays, "
                        "movie nights and Scouts."),
}

# A Bible verse on the bedtime clock screen, one per weekday (faith pack only).
CLOCK_VERSES = [
    ["I will lie down and sleep in peace, for You alone, O LORD, make me dwell in safety.", "Psalm 4:8"],
    ["He will not allow your foot to slip; your Protector will not slumber.", "Psalm 121:3"],
    ["Because of the loving devotion of the LORD we are not consumed, for His mercies never fail. They are new every morning.", "Lamentations 3:22–23"],
    ["Come to Me, all you who are weary and burdened, and I will give you rest.", "Matthew 11:28"],
    ["This is the day that the LORD has made; we will rejoice and be glad in it.", "Psalm 118:24"],
    ["Cast all your anxiety on Him, because He cares for you.", "1 Peter 5:7"],
    ["The LORD bless you and keep you; may the LORD cause His face to shine upon you.", "Numbers 6:24–25"],
]

QUOTED = re.compile(r"^“(.+)” (.+)$")


def split_verse(line: str) -> tuple:
    """'“He is risen.” Matthew 28:6' -> ('He is risen.', 'Matthew 28:6'); a bare reference -> ('', 'John 19:30')."""
    m = QUOTED.match(line or "")
    return (m.group(1), m.group(2)) if m else ("", (line or "").strip())


def faith_quotes() -> list:
    """Every Bible quote in the Faith pack, as (text, reference), in pack order (app/bible.py, docs/bible-translations.md)."""
    from . import lordsday as L
    from . import special as sp
    out = [(it["verse"], it["ref"]) for s in L.SERIES for it in s["items"]]
    out += [split_verse(c[5]) for c in sp.CHURCH]
    out += [split_verse(v[3]) for v in sp.HOLIDAY_LOOKS.values() if v[3]]
    out += [(t, r) for t, r in CLOCK_VERSES]
    return [(t, r) for t, r in out if t]


def passage(text: str, ref: str):
    """The verse as the pack stores it: reference, the verses it covers, the BSB text it ships and, per translation,
    which words of the full verse the shortened quote keeps (app/bible_data/quotes.json)."""
    from . import bible
    return bible.passage_for(text, ref, "bsb") if text else None


BARE_AMP = re.compile(r"&(?!(?:#\d+|#x[0-9a-fA-F]+|[a-zA-Z][a-zA-Z0-9]*);)")


def svg_file_text(svg: str) -> str:
    """A drawing as a stand-alone .svg file: the SVG namespace (so it also opens as an image) and no bare '&'."""
    if "xmlns=" not in svg[:300]:
        svg = svg.replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" ', 1)
    return BARE_AMP.sub("&amp;", svg)


def _drawings() -> dict:
    from . import scenes as sc
    from . import scenes_family as sf
    out = {k: f for k, f in {**sc.THEMES, **sf.THEMES}.items()}
    out["vacation-wide"] = sc.vacation_wide
    return out


def _scene_meta() -> dict:
    """Name, script line, write-up and 'comes up by itself' note for every built-in drawing."""
    from . import picture_guide as pg
    from .scenes_family import NAMES as FAMILY_NAMES
    from .special import FAMILY_SCRIPT
    names = {**pg.NAMES, **{k: v[0] for k, v in FAMILY_NAMES.items()}}
    meta = {}
    for k in _drawings():
        m = {"title": names.get(k, k)}
        if FAMILY_SCRIPT.get(k):
            m["script"] = FAMILY_SCRIPT[k]
        if pg.ABOUT.get(k):
            m["about"] = pg.ABOUT[k]
        if pg.AUTOMATIC.get(k):
            m["auto"] = pg.AUTOMATIC[k]
        meta[k] = m
    meta["vacation"]["title"] = "Vacation"
    meta["vacation-wide"]["title"] = "Vacation (wide)"
    return meta


def pack_of_scene() -> dict:
    from . import picture_guide as pg
    owner = {}
    for pid, groups in PACK_GROUPS.items():
        for name, keys in pg.GROUPS:
            if name in groups:
                for k in keys:
                    owner[k] = pid
        for k in EXTRA_SCENES.get(pid, {}):
            owner[k] = pid
    return owner


def _rules(pid: str, owner: dict) -> list:
    from . import special as sp
    rules: list = []
    if pid == "holidays-us":
        for name, (look, script, solemn, _verse) in sp.HOLIDAY_LOOKS.items():
            r = {"holiday": name, "scene": look, "script": script, "solemn": solemn}
            if name in sp.DEFAULT_MODES:
                r["mode"] = sp.DEFAULT_MODES[name]
            rules.append(r)
        rules += [{"holiday": n, "mode": m} for n, m in sp.DEFAULT_MODES.items() if n not in sp.HOLIDAY_LOOKS]
    if pid == "faith":
        replaces = {}
        for gname, key in sp.GOOGLE_HANDLED_BY_CHURCH.items():
            replaces.setdefault(key, []).append(gname)
        for key, name, when, look, script, verse, solemn, on in sp.CHURCH:
            r = {"church": key, "name": name}
            if isinstance(when, int):
                r["easter"] = when
            else:
                r["date"] = f"{when[0]:02d}-{when[1]:02d}"
            r.update({"scene": look, "script": script, "verse": verse, "solemn": solemn, "default_on": on})
            if passage(*split_verse(verse)):
                r["passage"] = passage(*split_verse(verse))
            if key in replaces:
                r["replaces"] = replaces[key]
            rules.append(r)
        for name, (_look, _script, _solemn, verse) in sp.HOLIDAY_LOOKS.items():
            if verse:   # the Thanksgiving verse: added on top of the U.S. holidays pack's picture
                rules.append({"holiday": name, "verse": verse, "passage": passage(*split_verse(verse))})
        rules.append({"weekly": "sunday", "series": "series.json", "script": "The Lord's Day",
                      "label": "Lord’s Day picture every Sunday"})
        rules.append({"clock_verses": CLOCK_VERSES, "passages": [passage(t, r) for t, r in CLOCK_VERSES]})
    if pid == "seasons":
        for key, name, _c in sp.SEASONS:
            rules.append({"season": key, "scene": key, "name": name})
    words = sp.DEFAULT_WORDS
    for i, w in enumerate(words):
        if owner.get(w["look"]) != pid:
            continue
        r = {"keyword": w["word"], "scene": w["look"], "order": 900 + i if w["word"].lower() in CATCH_ALL else i}
        if w.get("picture_only"):
            r["picture_only"] = True
        rules.append(r)
    return rules


def _series(folder: Path) -> dict:
    from . import lordsday as L
    out = {"start": L.START.isoformat(), "series": []}
    for si, s in enumerate(L.SERIES):
        items = []
        for i, it in enumerate(s["items"]):
            rel = f"series/{s['key']}-{i + 1:02d}.svg"
            (folder / rel).write_text(svg_file_text(L._picture(si, i)), encoding="utf-8")
            items.append({"title": it["title"], "verse": it["verse"], "ref": it["ref"], "about": it["about"], "file": rel,
                          "passage": passage(it["verse"], it["ref"])})
        out["series"].append({"key": s["key"], "name": s["name"], "items": items})
    return out


def build(pid: str, out_dir: Path) -> Path:
    """Write the pack folder out_dir/<pid>/ (replacing what was there). Returns the folder."""
    from . import picture_guide as pg
    if pid not in INFO:
        raise ValueError(f"unknown pack {pid!r}; known: {', '.join(INFO)}")
    folder = Path(out_dir) / pid
    if folder.exists():
        shutil.rmtree(folder)
    (folder / "scenes").mkdir(parents=True)
    owner = pack_of_scene()
    draw, meta = _drawings(), _scene_meta()
    scenes = {}
    for k in sorted(k for k, p in owner.items() if p == pid):
        (folder / "scenes" / f"{k}.svg").write_text(svg_file_text(draw[k]()), encoding="utf-8")
        scenes[k] = {**meta[k], **EXTRA_SCENES.get(pid, {}).get(k, {}), "file": f"scenes/{k}.svg"}
    groups = [{"name": name, "order": i, "scenes": keys} for i, (name, keys) in enumerate(pg.GROUPS) if name in PACK_GROUPS[pid]]
    name, desc = INFO[pid]
    preview = {"faith": "easter", "holidays-us": "july4", "seasons": "fall", "family-basics": "birthday",
               "outings": "park", "kids-activities": "baseball"}[pid]
    manifest = {"id": pid, "name": name, "version": version_of(pid), "priority": 10 if pid in BUILT_IN else 20,
                "description": desc, "license": LICENSE, "preview": f"scenes/{preview}.svg",
                "groups": groups, "scenes": scenes, "rules": _rules(pid, owner),
                "slots": ["NAME", "NAME_SIZE", "PORTRAIT", "PLACE", "PLACE_SIZE"] if pid in ("family-basics", "outings") else []}
    if pid == "faith":
        (folder / "series").mkdir()
        (folder / "series.json").write_text(json.dumps(_series(folder), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (folder / "pack.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return folder


def make_zip(folder: Path, zip_path: Path) -> str:
    """Zip a pack folder (files under '<id>/'), the same bytes every time. Returns its sha256."""
    folder = Path(folder)
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as z:
        for p in sorted(x for x in folder.rglob("*") if x.is_file()):
            info = zipfile.ZipInfo(f"{folder.name}/{p.relative_to(folder).as_posix()}", ZIP_TIME)
            info.external_attr = 0o644 << 16
            z.writestr(info, p.read_bytes())
    return hashlib.sha256(zip_path.read_bytes()).hexdigest()


def version_of(pid: str) -> str:
    return VERSIONS.get(pid, VERSION)


def zip_name(pid: str) -> str:
    return f"{pid}-{version_of(pid)}.zip"


def build_zip(pid: str, dist: Path, work: Path) -> tuple[Path, str]:
    """Build the pack in `work` and zip it to dist/<id>-<version>.zip. Returns (zip path, sha256)."""
    folder = build(pid, work)
    z = Path(dist) / zip_name(pid)
    return z, make_zip(folder, z)


def index_entry(pid: str, folder: Path, sha: str, size: int) -> dict:
    m = json.loads((folder / "pack.json").read_text(encoding="utf-8"))
    pictures = len(m["scenes"])
    if (folder / "series.json").exists():
        pictures += sum(len(s["items"]) for s in json.loads((folder / "series.json").read_text(encoding="utf-8"))["series"])
    return {"id": pid, "name": m["name"], "description": m["description"], "version": m["version"],
            "url": f"dist/packs/{zip_name(pid)}", "sha256": sha, "size": size, "pictures": pictures,
            "license": m["license"], "preview": f"previews/{pid}.svg", **({"default": True} if pid in DEFAULT_ON else {})}
