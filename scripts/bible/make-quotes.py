"""Make app/bible_data/ from the official public-domain text files (run by hand, rarely; docs/bible-translations.md).

    python3 scripts/bible/make-quotes.py KJV.txt BSB.txt [--review]

KJV.txt: https://openbible.com/textfiles/kjv.txt (King James Bible, Pure Cambridge Edition, public domain)
BSB.txt: https://bereanbible.com/bsb.txt         (Berean Standard Bible, official file, public domain)

Writes:
  app/bible_data/quotes.json     every quote in the Faith pack: reference, the verses it covers, the BSB text the
                                 pack ships, and per translation which words of the full verse the quote keeps
  app/bible_data/bsb.json        the BSB text of exactly those verses (built in)
  app/bible_data/kjv.json        the KJV text of exactly those verses (built in)

Each pack quote must be an exact excerpt of the BSB verse (app/bible.py exact_keep). The KJV word ranges are
found by matching the quote against the KJV verse (app/bible.py align), then fixed by hand in
scripts/bible/overrides.json where the match is off.
--review prints every quote in both translations to check by eye.
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
BSB_SOURCE = ("Berean Standard Bible, from https://bereanbible.com/bsb.txt (the official plain-text file). "
              "Public domain since April 30, 2023 (https://berean.bible/terms.htm).")


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
        full = " ".join(bsb_all[v] for v in verses)
        keep = bible.exact_keep(text, full)
        if not keep:
            raise SystemExit(f"{ref}: {text!r} is not word for word from the BSB: {full!r}")
        short = {"bsb": {"words": len(full.split()), "keep": keep}}
        full = " ".join(kjv_all[v] for v in verses)
        fix = over.get(f"{key[0]}|{text}", {}).get("kjv")
        short["kjv"] = {"words": len(full.split()), "keep": phrase_ranges(fix, full) if fix else bible.align(text, full)}
        quotes.append({"ref": key[0], "text": text, "verses": verses, "short": short})
    (OUT / "quotes.json").write_text(json.dumps({"about": "Every Bible quote in the Faith pack. 'short': which words of the "
                                                 "full verse (split on spaces) each translation's quote keeps. Made by "
                                                 "scripts/bible/make-quotes.py.", "quotes": quotes},
                                                indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    want = []
    for q in quotes:
        want += [v for v in q["verses"] if v not in want]
    for name, source, src in (("bsb", BSB_SOURCE, bsb_all), ("kjv", KJV_SOURCE, kjv_all)):
        (OUT / f"{name}.json").write_text(json.dumps({"code": name, "source": source, "verses": {v: src[v] for v in want}},
                                                    indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    bible._quotes_cache.clear()
    print(f"{len(quotes)} quotes, {len(want)} verses")
    if "--review" in args:
        b = bible.Bible("kjv", {"kjv": kjv_all, "bsb": bsb_all})
        for q in quotes:
            p = {**q, "tr": "bsb"}
            print(f"\n{q['ref']}\n  BSB {q['text']}")
            t, cite, _c = b.show(p)
            print(f"  KJV {t}   [{cite}]  {q['short']['kjv']['keep']}/{q['short']['kjv']['words']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
