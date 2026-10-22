"""Every quote in the Faith pack is the published BSB wording: a trimmed excerpt, never a paraphrase.

The rule (docs/bible-translations.md, "Shortened verses"): a quote is one exact, contiguous piece of the verse(s),
or several exact pieces in order joined by an ellipsis ("..." or "…") where words are left out. Allowed on top of
that: a capital first letter on a piece, and dropping or adding punctuation at the end of a piece. Curly and
straight quote marks count as the same. Changed words, reordered words, added words or the wrong verse fail.

app/bible_data/bsb.json holds the BSB text of exactly the verses the pack uses, from the official file at
bereanbible.com (scripts/bible/make-quotes.py). If a picture needs a new verse, remake it with that script.
"""
import json
import re

import pytest

from app import bible as B
from app import pack_build as pb

BSB = json.loads(B.BSB_FILE.read_text(encoding="utf-8"))["verses"]
GAP = re.compile(r"\s*(?:\.\.\.|…)\s*")


def _norm(s: str) -> str:
    s = s.replace("’", "'").replace("‘", "'").replace("“", "").replace("”", "")
    return re.sub(r"\s+", " ", s).strip()


def bsb_excerpt_problem(text: str, verses: list) -> str:
    """'' when `text` is a faithful BSB excerpt of `verses`; otherwise what is wrong."""
    missing = [v for v in verses if v not in BSB]
    if missing:
        return f"no stored BSB text for {missing} (remake app/bible_data/bsb.json)"
    full = _norm(" ".join(BSB[v] for v in verses))
    pos = 0
    for piece in GAP.split(_norm(text)):
        piece = piece.strip().rstrip(".,;:!?")
        if not piece:
            continue
        first = re.escape(piece[0])
        if piece[0].isalpha():
            first = f"[{re.escape(piece[0].lower())}{re.escape(piece[0].upper())}]"
        m = re.compile(r"(?<![\w'])" + first + re.escape(piece[1:]) + r"(?!\w)").search(full, pos)
        if not m:
            return f"{piece!r} is not the BSB wording (in order) of: {full}"
        pos = m.end()
    return ""


def test_the_rule():
    v = ["Matthew 13:46"]
    assert bsb_excerpt_problem("When he found one very precious pearl... sold all he had", v) == ""
    assert bsb_excerpt_problem("When he found one very precious pearl … sold all he had.", v) == ""
    assert bsb_excerpt_problem("When he found one very precious pearl, he sold all", v)        # added word
    assert bsb_excerpt_problem("Sold all he had... when he found one very precious pearl", v)  # out of order
    assert bsb_excerpt_problem("When he found one very precious pea", v)                       # cut inside a word
    assert bsb_excerpt_problem("Cast all your anxieties on Him", ["1 Peter 5:7"])               # word changed
    assert bsb_excerpt_problem("On finding one pearl of great value", v)                       # another translation
    # app/bible.py's own matcher agrees
    full = BSB["Matthew 13:46"]
    assert B.exact_keep("When he found one very precious pearl... sold all he had", full)
    assert B.exact_keep("On finding one pearl of great value", full) is None


def _all_quotes():
    seen = []
    for text, ref in pb.faith_quotes():
        if (text, ref) not in seen:
            seen.append((text, ref))
    return seen


def test_stored_text_covers_every_verse_and_nothing_else():
    used = {v for text, ref in _all_quotes() for v in B.parse_ref(ref)}
    assert used == set(BSB)


@pytest.mark.parametrize("text,ref", _all_quotes(), ids=lambda x: x if len(str(x)) < 30 else None)
def test_every_pack_quote_is_exact_bsb(text, ref):
    verses = B.parse_ref(ref)
    assert verses, ref
    problem = bsb_excerpt_problem(text, verses)
    assert not problem, f"{ref}: {problem}"


def test_stored_quotes_match_the_drawing_code():
    """app/bible_data/quotes.json (what the translation picker uses) carries the same BSB text as the pack."""
    stored = {(q["ref"], q["text"]) for q in json.loads(B.QUOTES_FILE.read_text(encoding="utf-8"))["quotes"]}
    assert stored == {(B.canon(r), t) for t, r in _all_quotes()}
    for ref, text in stored:
        assert not bsb_excerpt_problem(text, B.parse_ref(ref)), ref
