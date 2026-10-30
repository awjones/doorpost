# Bible translations

The Faith pack shows Bible verses in four places: the Sunday pictures (and
their pop-ups), the church-year days, Thanksgiving, and the bedtime clock.
You can pick which translation those verses use.

The Faith pack's verses are the **Berean Standard Bible (BSB)**, which is
in the public domain. It is the default, and it is built in, so there is
nothing to download or set up.

## Pick a translation

Open **Settings > Special days** and scroll to **Bible translation**. The
card only shows when a pack with verses (the Faith pack) is turned on.

Each translation shows its status, its copyright or credit line, and what
it needs:

| Translation | Status | What it needs |
|---|---|---|
| BSB (Berean Standard Bible) | Built in | Nothing. It is the text inside the Faith pack. The default. |
| KJV (King James Version) | Built in | Nothing. |
| NASB (New American Standard Bible) | Your text | Add your own licensed text, or fetch it with your own API.Bible key. |

The card also shows Psalm 118:24 in each translation, so you can compare.

Changes save right away. The frame picks them up within a minute.

### When a verse isn't there

If a verse is not on hand in the translation you picked, the frame uses the
**BSB**, then the KJV. A verse never disappears. Every verse on the frame
ends with the translation it came from, for example "Psalm 23:1 (KJV)".

### Shortened verses

Many pictures use part of a verse, so the words fit. A shortened verse is
shortened the same way in every translation. For the KJV and the BSB the
Faith pack stores exactly which words of the full verse to keep. For any
other text, Doorpost keeps the words that best match the pack's own
shortened quote.

The pack's quotes are never reworded. Each one is the published BSB
wording, cut to a short piece of the verse; where words in the middle are
left out, the gap is marked with "...". Every quote shows its reference.

## The licensing situation, in plain words

### BSB

The Berean Standard Bible has been in the public domain since April 30,
2023 ([berean.bible/terms.htm](https://berean.bible/terms.htm)). That is
why it can sit inside the Faith pack, which is shared under Creative
Commons (CC BY 4.0). No notice is required, but credit is welcome, so the
card shows:

> Bible quotations from the Berean Standard Bible (BSB), public domain.

Doorpost includes the BSB text of exactly the verses the pictures use, in
`app/bible_data/bsb.json`, from the official plain-text file at
[bereanbible.com/bsb.txt](https://bereanbible.com/bsb.txt).

The BSB asks that text which differs from the official text not use the
Berean name. So a verse shown whole says "(BSB)", and a shortened verse
says "(adapted)" instead.

### KJV

The King James Version is in the public domain in the United States. (In
the United Kingdom it is under Crown copyright.) Doorpost includes the KJV
text of exactly the verses the pictures use, in
`app/bible_data/kjv.json`. It comes from the 1769 Oxford text as published
at [openbible.com/textfiles/kjv.txt](https://openbible.com/textfiles/kjv.txt)
(the "Pure Cambridge Edition"). The square brackets that mark the printed
italics were removed. A sample of verses was checked against a second
source (bible-api.com) and matched word for word, apart from psalm titles,
which this file counts as part of verse 1.

### NASB

The NASB belongs to The Lockman Foundation and is all rights reserved.
Doorpost does not include it. Lockman allows up to 1,000 verses without
asking, with its notice shown in full (with a link to lockman.org) on web
pages and apps:

> Scripture quotations taken from the (NASB®) New American Standard Bible®,
> Copyright © 1960, 1971, 1977, 1995, 2020 by The Lockman Foundation. Used
> by permission. All rights reserved. www.Lockman.org

For the NASB 1995, the years end at 1995. Pick the edition on the card and
the notice changes to match. Lockman's terms:
[lockman.org permission page](https://www.lockman.org/permission-to-quote-copyright-trademark-information/).

Lockman does not offer its own API. There are two ways to add the NASB:

1. **Your own text.** Press **List of verses to fill in** to get a file of
   every reference the pictures use. Put your licensed NASB text next to
   each reference and add the file with **Add your text (JSON)**:

   ```json
   {"Psalm 118:24": "This is the day which the LORD has made...",
    "Lamentations 3:22-23": "..."}
   ```

   Your text is shown as you give it. If you give a whole verse that is
   much longer than the picture's quote, it is shortened to match.
   Doorpost keeps at most 1,000 verses, Lockman's limit.

2. **Your API.Bible key.** API.Bible (American Bible Society) licenses
   the NASB to apps, and Lockman is one of its partners. If your API.Bible
   plan includes the NASB, save your key and the NASB's Bible ID on the card,
   then press **Fetch the verses**. The key stays with the server's other
   secrets and is never shown again. This was built from API.Bible's
   documentation and tested with a stand-in; it has not been tried with a
   real key yet. Check API.Bible's own terms (they may ask you to report
   views).

### Why not the ESV?

Doorpost doesn't include the ESV. Crossway's terms don't allow ESV text in a
Creative Commons release, and Crossway licenses apps only to organizations,
not to individual developers.

## For people working on the code

- `app/bible.py` holds the translations, the notices, the fallback order,
  the shortening, your own text and the API.Bible fetch.
- `app/bible_api.py` is the Settings API. `web/js/bible-admin.js` and
  `web/css/bible-admin.css` draw the card.
- `app/bible_data/quotes.json` lists every quote in the Faith pack with its
  reference, the verses it covers, the BSB text and, for the BSB and KJV,
  which words of the full verse to keep (word positions, split on spaces).
  `bsb.json` and `kjv.json` hold the full text of those verses.
- The Faith pack (version 1.1.0 and later) stores a `passage` next to each
  verse: `ref`, `verses`, `text` (the BSB text, unchanged), `tr` and
  `short`. Older packs without it keep showing their verse as it was.
- To remake the data files, download the two official text files and run:

  ```bash
  python3 scripts/bible/make-quotes.py kjv.txt bsb.txt --review
  python3 scripts/build-pack.py --all
  ```

  Every quote in the drawing code must be an exact piece of its BSB verse,
  or the script stops and says which one. `--review` prints every quote in
  the BSB and the KJV to check by eye. Fix a poor KJV match in
  `scripts/bible/overrides.json` with the exact words to keep, using `...`
  for a gap.
- `tests/test_bsb_quotes.py` checks every quote in the pack against the BSB
  text of its verses (`app/bible_data/bsb.json`). A quote must be one exact
  piece of the verse, or exact pieces in order joined by `...`; only a
  capital first letter, quote marks and the end punctuation may differ.
