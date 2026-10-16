"""Make app/bible_data/ from the official public-domain text files (run by hand, rarely; docs/bible-translations.md).

    python3 scripts/bible/make-quotes.py KJV.txt BSB.txt [--review]

KJV.txt: https://openbible.com/textfiles/kjv.txt (King James Bible, Pure Cambridge Edition, public domain)
BSB.txt: https://bereanbible.com/bsb.txt         (Berean Standard Bible, official file, public domain)

Writes:
  app/bible_data/quotes.json     every quote in the Faith pack: reference, the verses it covers, the ESV text the
                                 pack ships, and per translation which words of the full verse the quote keeps
  app/bible_data/kjv.json        the KJV text of exactly those verses (built in)
  app/bible_data/bsb-sample.txt  a small cut of the BSB file for demo mode and the tests (not the whole file)

The word ranges are found by matching the ESV quote against each translation's full verse
(app/bible.py align), then fixed by hand in scripts/bible/overrides.json where the match is off.
--review prints every quote in all three translations to check by eye.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
from app import bible, pack_build  # noqa: E402

OUT = ROOT / "app" / "bible_data"
OVERRIDES = HERE / "overrides.json"
KJV_SOURCE = ("King James Version (1769 Oxford text), from https://openbible.com/textfiles/kjv.txt "
              "(Pure Cambridge Edition, text courtesy of BibleProtector.com). Public domain in the United States. "
              "Square brackets (the printed italics) removed.")
# Verses the demo's BSB sample carries: the church year, Thanksgiving, the bedtime clock, and the Sundays
# around the demo dates (October to December 2026).
SAMPLE_REFS = ["Psalm 4:8", "Psalm 121:3", "Lamentations 3:22", "Lamentations 3:23", "Matthew 11:28", "Psalm 118:24",
               "1 Peter 5:7", "Numbers 6:24", "Numbers 6:25", "Mark 11:9", "Matthew 28:6", "Acts 1:9", "Acts 2:4",
               "Romans 1:17", "John 1:5", "Isaiah 9:6", "Psalm 107:1", "Romans 6:4", "2 John 1:4", "Jude 1:3",
               "Exodus 20:15", "John 3:8", "1 Corinthians 11:26", "3 John 1:4", "1 Peter 2:24", "Exodus 20:16",
               "Isaiah 6:3", "John 11:25", "Jude 1:24", "Exodus 20:17", "2 Corinthians 13:14", "Revelation 20:12",
               "Revelation 21:5"]


def read(path):
    return bible.parse_plain(Path(path).read_text(encoding="utf-8-sig"))


def clean_kjv(t):
    return re.sub(r"\s+", " ", t.replace("[", "").replace("]", "")).strip()


def phrase_ranges(phrase, full):
    """'the words kept ... more words' (exact words from the full verse) -> word ranges."""
    words = full.split()
    out, pos = [], 0
    for seg in bible.segments(phrase):
        want = seg.split()
        for i in range(pos, len(words) - len(want) + 1):
            if words[i:i + len(want)] == want:
                out.append([i, i + len(want)])
                pos = i + len(want)
                break
        else:
            raise SystemExit(f"override not found: {seg!r} in {full!r}")
    return out


def main(args):
    if len(args) < 2:
        print(__doc__)
        return 1
    kjv_all = {k: clean_kjv(v) for k, v in read(args[0]).items()}
    bsb_all = read(args[1])
    over = json.loads(OVERRIDES.read_text()) if OVERRIDES.exists() else {}
    quotes, seen = [], set()
    for text, ref in pack_build.faith_quotes():
        key = (bible.canon(ref), text)
        if key in seen:
            continue
        seen.add(key)
        verses = bible.parse_ref(ref)
        assert verses, ref
        short = {}
        for code, src in (("kjv", kjv_all), ("bsb", bsb_all)):
            full = " ".join(src[v] for v in verses)
            fix = over.get(f"{key[0]}|{text}", {}).get(code)
            keep = phrase_ranges(fix, full) if fix else bible.align(text, full)
            short[code] = {"words": len(full.split()), "keep": keep}
        quotes.append({"ref": key[0], "text": text, "verses": verses, "short": short})
    (OUT / "quotes.json").write_text(json.dumps({"about": "Every Bible quote in the Faith pack. 'short': which words of the "
                                                 "full verse (split on spaces) each translation's quote keeps. Made by "
                                                 "scripts/bible/make-quotes.py.", "quotes": quotes},
                                                indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    want = []
    for q in quotes:
        want += [v for v in q["verses"] if v not in want]
    (OUT / "kjv.json").write_text(json.dumps({"code": "kjv", "source": KJV_SOURCE, "verses": {v: kjv_all[v] for v in want}},
                                             indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    sample = ["The Holy Bible, Berean Standard Bible, BSB is produced in cooperation with Bible Hub, Discovery Bible, unfoldingWord, "
              "Bible Aquifer, OpenBible.com, and the Berean Bible Translation Committee. \t",
              "This text of God's Word has been dedicated to the public domain. Free resources and databases are available at BereanBible.com.\t",
              "Verse\tBerean Standard Bible",
              "(A small sample of https://bereanbible.com/bsb.txt for Doorpost demo mode and tests.)\t"]
    sample += [f"{v}\t{bsb_all[v]}" for v in SAMPLE_REFS]
    (OUT / "bsb-sample.txt").write_text("\n".join(sample) + "\n", encoding="utf-8")
    bible._quotes_cache.clear()
    print(f"{len(quotes)} quotes, {len(want)} verses")
    if "--review" in args:
        b = bible.Bible("kjv", {"kjv": kjv_all, "bsb": bsb_all})
        for q in quotes:
            p = {**q, "tr": "esv"}
            print(f"\n{q['ref']}\n  ESV {q['text']}")
            for code in ("kjv", "bsb"):
                b.choice = code
                t, cite, _c = b.show(p)
                print(f"  {code.upper()} {t}   [{cite}]  {q['short'][code]['keep']}/{q['short'][code]['words']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
