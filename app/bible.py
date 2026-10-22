"""Bible translations for the verses the art packs show (docs/bible-translations.md).

The Faith pack keeps each verse as a reference plus the text it ships (BSB) and, for the translations we know,
which words of the full verse its shortened quote keeps (a "passage", built by app/pack_build.py from
app/bible_data/quotes.json). The verse TEXT for each translation comes from translation sources:

    bsb    built in: the text inside the pack, and app/bible_data/bsb.json (the default; public domain)
    kjv    built in: app/bible_data/kjv.json, the referenced verses only (public domain)
    nasb   the family's own licensed text (a JSON import), or fetched with their own API.Bible key

Every place a verse shows (Sunday pictures, church-year days, Thanksgiving, the bedtime clock) asks
`show(passage)` here. It tries the chosen translation, then BSB, then KJV, then the pack's own text, so a verse
never disappears. A shortened quote stays shortened the same way: the pack's word ranges for that translation,
or, for a translation without ranges, the closest match to the pack's own (shortened) text.

Only public-domain text ships with Doorpost; anything under copyright is the family's own to add.
"""
from __future__ import annotations

import difflib
import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from . import config as _cfg

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(__file__).resolve().parent / "bible_data"
KJV_FILE = DATA / "kjv.json"
BSB_FILE = DATA / "bsb.json"
QUOTES_FILE = DATA / "quotes.json"
APIBIBLE_URL = "https://rest.api.bible/v1/bibles/{bible}/verses/{verse}"
MAX_IMPORT = 1024 * 1024
MAX_IMPORT_VERSES = 1000   # Lockman: no more than 1,000 NASB verses stored in an electronic system

# ---------------- the 66 books (names as in the official BSB and KJV text files) and USFM codes ----------------

BOOKS = [
    ("Genesis", "GEN"), ("Exodus", "EXO"), ("Leviticus", "LEV"), ("Numbers", "NUM"), ("Deuteronomy", "DEU"),
    ("Joshua", "JOS"), ("Judges", "JDG"), ("Ruth", "RUT"), ("1 Samuel", "1SA"), ("2 Samuel", "2SA"), ("1 Kings", "1KI"),
    ("2 Kings", "2KI"), ("1 Chronicles", "1CH"), ("2 Chronicles", "2CH"), ("Ezra", "EZR"), ("Nehemiah", "NEH"),
    ("Esther", "EST"), ("Job", "JOB"), ("Psalm", "PSA"), ("Proverbs", "PRO"), ("Ecclesiastes", "ECC"),
    ("Song of Solomon", "SNG"), ("Isaiah", "ISA"), ("Jeremiah", "JER"), ("Lamentations", "LAM"), ("Ezekiel", "EZK"),
    ("Daniel", "DAN"), ("Hosea", "HOS"), ("Joel", "JOL"), ("Amos", "AMO"), ("Obadiah", "OBA"), ("Jonah", "JON"),
    ("Micah", "MIC"), ("Nahum", "NAM"), ("Habakkuk", "HAB"), ("Zephaniah", "ZEP"), ("Haggai", "HAG"),
    ("Zechariah", "ZEC"), ("Malachi", "MAL"), ("Matthew", "MAT"), ("Mark", "MRK"), ("Luke", "LUK"), ("John", "JHN"),
    ("Acts", "ACT"), ("Romans", "ROM"), ("1 Corinthians", "1CO"), ("2 Corinthians", "2CO"), ("Galatians", "GAL"),
    ("Ephesians", "EPH"), ("Philippians", "PHP"), ("Colossians", "COL"), ("1 Thessalonians", "1TH"),
    ("2 Thessalonians", "2TH"), ("1 Timothy", "1TI"), ("2 Timothy", "2TI"), ("Titus", "TIT"), ("Philemon", "PHM"),
    ("Hebrews", "HEB"), ("James", "JAS"), ("1 Peter", "1PE"), ("2 Peter", "2PE"), ("1 John", "1JN"), ("2 John", "2JN"),
    ("3 John", "3JN"), ("Jude", "JUD"), ("Revelation", "REV"),
]
USFM = dict(BOOKS)
_BOOK_KEY = {n.lower(): n for n, _c in BOOKS}
_BOOK_KEY.update({"psalms": "Psalm", "song of songs": "Song of Solomon", "revelations": "Revelation"})
ONE_CHAPTER = {"Obadiah", "Philemon", "2 John", "3 John", "Jude"}
REF_RE = re.compile(r"^\s*((?:[123]\s)?[A-Za-z][A-Za-z ]*?)\s+(\d+)(?::(\d+)(?:\s*[-–—]\s*(\d+))?)?\s*$")


def parse_ref(ref: str) -> list[str]:
    """'Lamentations 3:22–23' -> ['Lamentations 3:22', 'Lamentations 3:23']; 'Jude 3' -> ['Jude 1:3']. [] if not a verse."""
    m = REF_RE.match(str(ref or ""))
    if not m:
        return []
    book = _BOOK_KEY.get(re.sub(r"\s+", " ", m.group(1)).lower())
    if not book:
        return []
    ch, v1, v2 = m.group(2), m.group(3), m.group(4)
    if v1 is None:
        if book not in ONE_CHAPTER:
            return []   # a whole chapter isn't a quote
        ch, v1 = "1", ch
    a, b = int(v1), int(v2 or v1)
    if b < a or b - a > 20:
        return []
    return [f"{book} {int(ch)}:{v}" for v in range(a, b + 1)]


def canon(ref: str) -> str:
    """One spelling for a reference: 'Psalms 150:6' -> 'Psalm 150:6', 'Numbers 6:24-25' -> 'Numbers 6:24-25'."""
    vs = parse_ref(ref)
    if not vs:
        return str(ref or "").strip()
    return vs[0] if len(vs) == 1 else f"{vs[0]}-{vs[-1].rsplit(':', 1)[1]}"


# ---------------- the translations ----------------

NASB_NOTICE = {
    "2020": ("Scripture quotations taken from the (NASB®) New American Standard Bible®, Copyright © 1960, 1971, 1977, 1995, "
             "2020 by The Lockman Foundation. Used by permission. All rights reserved. www.Lockman.org"),
    "1995": ("Scripture quotations taken from the (NASB®) New American Standard Bible®, Copyright © 1960, 1971, 1977, 1995 "
             "by The Lockman Foundation. Used by permission. All rights reserved. www.Lockman.org"),
}

TRANSLATIONS = {
    "bsb": {"abbr": "BSB", "name": "Berean Standard Bible", "kind": "builtin",
            "notice": "Bible quotations from the Berean Standard Bible (BSB), public domain.",
            "note": "Built in, and the default: it is the text inside the Faith pack. The BSB asks that changed text "
                    "not carry its name, so a shortened verse is marked “adapted” instead of “BSB”.",
            "links": [["berean.bible", "https://berean.bible/terms.htm"]]},
    "kjv": {"abbr": "KJV", "name": "King James Version", "kind": "builtin",
            "notice": "King James Version, public domain in the United States.",
            "note": "Built in. (In the United Kingdom the KJV is under Crown copyright.)",
            "links": []},
    "nasb": {"abbr": "NASB", "name": "New American Standard Bible", "kind": "yours",
             "notice": NASB_NOTICE["2020"],
             "note": "The Lockman Foundation's NASB is all rights reserved and isn't included. Add your own licensed "
                     "text (a file of verses), or fetch the verses with your own API.Bible key if your plan includes "
                     "the NASB. The notice above must stay with the text.",
             "links": [["lockman.org", "https://www.lockman.org"],
                       ["Lockman permission terms", "https://www.lockman.org/permission-to-quote-copyright-trademark-information/"]]},
}
DEFAULT = "bsb"
FALLBACK = ("bsb", "kjv")   # then the pack's own text


# ---------------- words: shortening a verse the way the pack's quote is shortened ----------------

_ARCHAIC = {"hath": "has", "thee": "you", "thou": "you", "thy": "your", "thine": "your", "ye": "you", "unto": "to",
            "doth": "does", "shalt": "shall", "saith": "says", "art": "are", "hast": "have", "wilt": "will",
            "cometh": "comes", "believeth": "believes", "giveth": "gives", "keepeth": "keeps", "loveth": "loves",
            "shineth": "shining", "lord's": "lords", "lord": "lord", "ghost": "spirit"}


def _norm(w: str) -> str:
    w = re.sub(r"[^\w']", "", w.lower().replace("’", "'")).strip("'")
    return _ARCHAIC.get(w, w)


def segments(text: str) -> list[str]:
    """A quote split at its gaps ('Every good gift... coming down' -> two parts)."""
    return [s.strip() for s in re.split(r"\s*(?:\.\.\.|…)\s*", text) if s.strip()]


def align(quote: str, full: str, reach: int = 2) -> list[list[int]]:
    """Which words of `full` (split on spaces) best match each part of `quote`, in order: [[start, end], ...].
    `reach`: how many more words it may take to finish the phrase (2 for the reviewed ranges, 3 at run time)."""
    words = [_norm(w) for w in full.split()]
    n = len(words)
    out, pos = [], 0
    parts = segments(quote) or [quote]
    for k, seg in enumerate(parts):
        q = [_norm(w) for w in seg.split()]
        m = len(q)
        best, best_score = None, -1.0
        # leave room for the parts still to come
        last = n - (len(parts) - k - 1)
        for i in range(pos, max(pos, last)):
            for j in range(i + max(1, m // 2), min(last, i + 2 * m + 3) + 1):
                sm = difflib.SequenceMatcher(None, q, words[i:j], autojunk=False)
                score = sm.ratio() - 0.002 * (j - i)
                if score > best_score:
                    best, best_score = [i, j], score
        if best is None:
            return [[0, n]]
        # finish the phrase: run on to the next comma or full stop when it is at most `reach` words away
        raw = full.split()
        if not re.search(r"[,.;:!?’”]$", raw[best[1] - 1]):
            for j in range(best[1], min(last, best[1] + reach)):
                if re.search(r"[,.;:!?’”]$", raw[j]) or j + 1 == n:
                    best = [best[0], j + 1]
                    break
        out.append(best)
        pos = best[1]
    return out


def excerpt(full: str, keep: list) -> str:
    words = full.split()
    parts = []
    for a, b in keep:
        seg = " ".join(words[int(a):int(b)]).strip()
        if parts:
            parts[-1] = parts[-1].rstrip(",;:.—–- ")
        parts.append(seg)
    return "... ".join(p for p in parts if p)


def tidy(text: str) -> str:
    """Quote marks off (the frame adds its own), a capital first letter, and end punctuation."""
    t = re.sub(r"[“”\"]", "", text or "").strip()
    # a single quote cut in half: an opening ‘ with no closing ’ after it, or a closing ’ (after . , ! ?) with no ‘
    closing = re.compile(r"(?<=[.,!?;:])’")
    if "‘" in t and not closing.search(t[t.index("‘"):]):
        t = t.replace("‘", "")
    if "‘" not in t:
        t = closing.sub("", t)
    t = re.sub(r"\s+", " ", t).strip().lstrip(",;:—–- ").rstrip(",;:—–- ")
    if t and t[0].islower():
        t = t[0].upper() + t[1:]
    if t and not re.search(r"[.!?][’”]?$", t):
        t += "."
    return t


def is_whole(keep: list, n: int) -> bool:
    return len(keep) == 1 and int(keep[0][0]) == 0 and int(keep[0][1]) >= n


def _plain(w: str) -> str:
    return w.lower().strip(".,;:!?“”‘’\"'()—–- ")


def exact_keep(quote: str, full: str) -> Optional[list]:
    """The word ranges of `full` that `quote` is made of, word for word and in order ('...' marks a gap), or None
    when the quote isn't an exact excerpt. Only a capital first letter, quote marks and punctuation at the ends of
    words may differ."""
    words = [_plain(w) for w in full.split()]
    out, pos = [], 0
    for seg in segments(quote):
        want = [_plain(w) for w in seg.split()]
        for i in range(pos, len(words) - len(want) + 1):
            if words[i:i + len(want)] == want:
                out.append([i, i + len(want)])
                pos = i + len(want)
                break
        else:
            return None
    return out or None


# ---------------- the sources ----------------

def bible_dir(demo: bool) -> Path:
    return _cfg.DATA_DIR / ("bible-demo" if demo else "bible")


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


_quotes_cache: dict = {}


def quotes() -> list[dict]:
    """app/bible_data/quotes.json: every verse the built-in pictures quote, with its word ranges per translation."""
    if "q" not in _quotes_cache:
        _quotes_cache["q"] = _read_json(QUOTES_FILE).get("quotes", [])
    return _quotes_cache["q"]


def passage_for(text: str, ref: str, tr: str = DEFAULT) -> Optional[dict]:
    """The passage the pack stores for a quote from the drawing code's tables (app/pack_build.py)."""
    key = (canon(ref), text)
    for q in quotes():
        if (q["ref"], q["text"]) == key:
            return {"ref": ref, "verses": q["verses"], "text": text, "tr": tr, "short": q.get("short", {})}
    vs = parse_ref(ref)
    return {"ref": ref, "verses": vs, "text": text, "tr": tr, "short": {}} if vs else None


def verse_list() -> list[str]:
    """Every single verse the built-in pictures quote (what a fetch keeps)."""
    seen: list[str] = []
    for q in quotes():
        for v in q["verses"]:
            if v not in seen:
                seen.append(v)
    return seen


class Bible:
    """The family's choice and the verse text on hand. `show` gives the words and the citation for a passage."""

    def __init__(self, choice: str = DEFAULT, sources: Optional[dict] = None, as_is: Optional[dict] = None, nasb_edition: str = "2020"):
        self.choice = choice if choice in TRANSLATIONS else DEFAULT   # an old saved choice (the ESV) lands on the BSB
        self.sources = sources or {}        # code: {"Psalm 23:1": "full verse text"}
        self.as_is = as_is or {}            # code: {"Psalm 118:24": "text to show as given"} (your own text)
        self.nasb_edition = nasb_edition

    def order(self) -> list[str]:
        out = [self.choice]
        for c in FALLBACK:
            if c not in out:
                out.append(c)
        return out

    def _text(self, code: str, p: dict) -> Optional[tuple[str, bool]]:
        """(text, shortened) in translation `code`, or None when it isn't on hand."""
        own = (p.get("text") or "").strip()
        rule = (p.get("short") or {}).get(code)
        if code == str(p.get("tr") or "").lower() and own:
            return own, bool(rule) and not is_whole(rule.get("keep") or [], int(rule.get("words", 0)))
        given = self.as_is.get(code, {}).get(canon(p.get("ref", "")))
        if given:
            if own and len(given.split()) > 1.5 * len(own.split()) + 3:
                keep = align(own, given, 3)
                return excerpt(given, keep), not is_whole(keep, len(given.split()))
            return given, False
        src = self.sources.get(code) or {}
        verses = p.get("verses") or parse_ref(p.get("ref", ""))
        if not verses or not all(src.get(v) for v in verses):
            return None
        full = " ".join(src[v].strip() for v in verses)
        n = len(full.split())
        if rule and int(rule.get("words", -1)) == n and rule.get("keep"):
            keep = rule["keep"]
        elif own:
            keep = align(own, full, 3)   # no ranges for this text: shorten it the way the pack's own quote is
        else:
            keep = [[0, n]]
        return excerpt(full, keep), not is_whole(keep, n)

    def show(self, p: dict) -> tuple[str, str, str]:
        """(text, citation, code) for passage p: 'This is the day...', 'Psalm 118:24 (KJV)', 'kjv'."""
        ref = str(p.get("ref") or "")
        for code in self.order() + [str(p.get("tr") or "").lower()]:
            got = self._text(code, p) if code else None
            if got:
                text, short = got
                tag = TRANSLATIONS.get(code, {}).get("abbr") or code.upper()
                if code == "bsb" and short:
                    tag = "adapted"      # the BSB asks that changed text not carry its name
                return tidy(text), (f"{ref} ({tag})" if tag else ref), code
        return tidy(p.get("text") or ""), ref, ""

    def line(self, p: Optional[dict], fallback: str = "") -> str:
        """The verse as one line for a picture: '“Text.” Psalm 23:1 (KJV)'."""
        if not p or not (p.get("text") or p.get("verses")):
            return fallback
        text, cite, _code = self.show(p)
        return f"“{text}” {cite}" if text else fallback

    def notice(self, code: str) -> str:
        if code == "nasb":
            return NASB_NOTICE.get(self.nasb_edition, NASB_NOTICE["2020"])
        return TRANSLATIONS.get(code, {}).get("notice", "")


# ---------------- the family's choice and the files on disk ----------------

_state_lock = threading.Lock()
_state: dict = {"key": None, "bible": None}


def _files(demo: bool) -> dict:
    return {"nasb": bible_dir(demo) / "nasb.json"}


def settings_of(demo: bool) -> dict:
    return dict(_cfg.read_store(demo).get("bible") or {})


def current(demo: bool) -> Bible:
    """The Bible to show verses with, read again only when the choice or an added file changes."""
    files = _files(demo)
    sp = _cfg.store_path(demo)
    key = (demo, str(_cfg.DATA_DIR), sp.stat().st_mtime_ns if sp.exists() else 0,
           tuple(p.stat().st_mtime_ns if p.exists() else 0 for p in files.values()))
    with _state_lock:
        if _state["key"] != key:
            cfg = settings_of(demo)
            sources = {"bsb": _read_json(BSB_FILE).get("verses", {}), "kjv": _read_json(KJV_FILE).get("verses", {})}
            as_is = {}
            for code, path in files.items():
                data = _read_json(path)
                if data.get("as_is"):
                    as_is[code] = data.get("verses", {})
                elif data.get("verses"):
                    sources[code] = data["verses"]
            _state["bible"] = Bible(str(cfg.get("translation") or DEFAULT), sources, as_is, str(cfg.get("nasb_edition") or "2020"))
            _state["key"] = key
        return _state["bible"]


def status(demo: bool) -> list[dict]:
    """Settings > Special days > Bible translation: each translation, what's on hand and its notice."""
    b = current(demo)
    files = _files(demo)
    out = []
    for code, t in TRANSLATIONS.items():
        data = _read_json(files[code]) if code in files else {}
        n = len(data.get("verses", {}))
        if code == "bsb":
            state, label = "built-in", "Built in (in the Faith pack)"
        elif code == "kjv":
            state, label = "built-in", "Built in"
        else:
            key_set = bool((_cfg.read_store(demo).get("secrets") or {}).get("apibible_key"))
            if n:
                state = "yours"
                label = f"Your text added ({n} verses)" if data.get("as_is") else f"Fetched with your API.Bible key ({n} verses)"
            else:
                state, label = ("key", "Key added, verses not fetched yet") if key_set else ("needs-text", "Needs your licensed text")
        out.append({"code": code, "abbr": t["abbr"], "name": t["name"], "kind": t["kind"], "state": state, "label": label,
                    "chosen": b.choice == code, "notice": b.notice(code), "note": t["note"], "links": t["links"],
                    "when": data.get("when", ""), "source": data.get("source", "")})
    return out


# ---------------- the official plain-text files (scripts/bible/make-quotes.py) ----------------

LINE_RE = re.compile(r"^((?:[123] )?[A-Z][A-Za-z ]+?) (\d+):(\d+)\t(.+)$")


def parse_plain(text: str, want: Optional[set] = None) -> dict:
    """The official BSB (and KJV) plain-text layout, 'Genesis 1:1<TAB>In the beginning...', to {ref: text}."""
    out = {}
    for line in text.splitlines():
        m = LINE_RE.match(line.lstrip("﻿").rstrip())
        if not m:
            continue
        book = _BOOK_KEY.get(m.group(1).lower())
        if not book:
            continue
        ref = f"{book} {int(m.group(2))}:{int(m.group(3))}"
        if want is None or ref in want:
            out[ref] = m.group(4).strip()
    return out


def wanted_verses(extra: Optional[list] = None) -> set:
    """The built-in pictures' verses, plus any other verses the turned-on packs quote."""
    want = set(verse_list())
    for v in extra or []:
        want.update(parse_ref(v))
    return want


def _save_source(demo: bool, code: str, data: dict) -> None:
    d = bible_dir(demo)
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / f"{code}.json.tmp"
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(d / f"{code}.json")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def remove(demo: bool, code: str) -> None:
    p = _files(demo).get(code)
    if p and p.exists():
        p.unlink()


# ---------------- the NASB: your own text, or your API.Bible key ----------------

def import_text(demo: bool, code: str, raw: bytes) -> int:
    """A JSON file of verse text keyed by reference: {"Psalm 23:1": "text", ...} (or {"verses": {...}}).
    The text is shown as given; a whole verse that is much longer than the picture's quote is shortened to match."""
    if code != "nasb":
        raise ValueError("Only the NASB takes your own text.")
    if len(raw) > MAX_IMPORT:
        raise ValueError("That file is over 1 MB.")
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError):
        raise ValueError("That isn't a JSON file. It should look like {\"Psalm 23:1\": \"The Lord is my shepherd...\"}.")
    if isinstance(data, dict) and isinstance(data.get("verses"), dict):
        data = data["verses"]
    if not isinstance(data, dict):
        raise ValueError("The file should be one list of \"reference\": \"text\" pairs.")
    verses = {}
    for k, v in data.items():
        if not isinstance(v, str) or not v.strip() or not parse_ref(str(k)):
            continue
        verses[canon(str(k))] = re.sub(r"\s+", " ", v).strip()[:600]
    if not verses:
        raise ValueError("No verses found. Use references like \"Psalm 23:1\" or \"Lamentations 3:22-23\".")
    if len(verses) > MAX_IMPORT_VERSES:
        raise ValueError(f"That's {len(verses)} verses; the limit is {MAX_IMPORT_VERSES}.")
    _save_source(demo, code, {"code": code, "source": "your file", "when": _now(), "as_is": True, "verses": verses})
    return len(verses)


def template() -> dict:
    """The references to fill in for your own text, each with the shortened quote the picture uses (BSB wording)."""
    out = {}
    for q in quotes():
        out.setdefault(q["ref"], q["text"])
    return out


def fetch_apibible(demo: bool, key: str, bible_id: str, code: str = "nasb", extra: Optional[list] = None) -> int:
    """Fetch the verses the pictures use from API.Bible with the family's own key and Bible ID (their plan must
    include the translation). Saves them like an added file. Not in demo mode."""
    if demo:
        raise ValueError("Fetching with a key is off in demo mode.")
    if not key or not re.match(r"^[A-Za-z0-9_-]{6,80}$", bible_id or ""):
        raise ValueError("Add your API.Bible key and the Bible ID for the NASB first.")
    import httpx
    verses = {}
    with httpx.Client(timeout=20, headers={"api-key": key}) as c:
        for ref in sorted(wanted_verses(extra)):
            book, cv = ref.rsplit(" ", 1)
            ch, v = cv.split(":")
            r = c.get(APIBIBLE_URL.format(bible=bible_id, verse=f"{USFM[book]}.{ch}.{v}"),
                      params={"content-type": "text", "include-notes": "false", "include-titles": "false",
                              "include-chapter-numbers": "false", "include-verse-numbers": "false",
                              "include-verse-spans": "false"})
            if r.status_code in (401, 403):
                raise ValueError("API.Bible didn't accept that key, or your plan doesn't include this Bible.")
            if r.status_code == 404:
                continue
            r.raise_for_status()
            text = re.sub(r"\s+", " ", str((r.json().get("data") or {}).get("content") or "")).strip()
            text = re.sub(r"^\[?\d+\]?\s*", "", text)
            if text:
                verses[ref] = text
    if not verses:
        raise ValueError("API.Bible sent back no verses.")
    _save_source(demo, code, {"code": code, "source": "API.Bible (your key)", "when": _now(), "verses": verses})
    return len(verses)
