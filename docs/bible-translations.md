# Bible translations

The Faith pack shows Bible verses in four places: the Sunday pictures (and
their pop-ups), the church-year days, Thanksgiving, and the bedtime clock.
You can pick which translation those verses use.

**This is an open decision.** Which translation the public release should
use has not been settled. The ESV stays the default for now, while the
question of permission from Crossway is worked out (see below).

## Pick a translation

Open **Settings > Special days** and scroll to **Bible translation**. The
card only shows when a pack with verses (the Faith pack) is turned on.

Each translation shows its status, its copyright or credit line, and what
it needs:

| Translation | Status | What it needs |
|---|---|---|
| ESV (English Standard Version) | Built in | Nothing. It is the text inside the Faith pack. The default. |
| KJV (King James Version) | Built in | Nothing. It is also the fallback. |
| BSB (Berean Standard Bible) | Download | Press **Download BSB** once. |
| NASB (New American Standard Bible) | Your text | Add your own licensed text, or fetch it with your own API.Bible key. |

The card also shows Psalm 118:24 in each translation, so you can compare.

Changes save right away. The frame picks them up within a minute.

### When a verse isn't there

If a verse is not on hand in the translation you picked, the frame uses the
**KJV**, then the text inside the pack. A verse never disappears. Every
verse on the frame ends with the translation it came from, for example
"Psalm 23:1 (KJV)".

### Shortened verses

Many pictures use part of a verse, so the words fit. A shortened verse is
shortened the same way in every translation. For the KJV and the BSB the
Faith pack stores exactly which words of the full verse to keep. For any
other text, Doorpost keeps the words that best match the pack's own
shortened quote.

## The licensing situation, in plain words

### ESV

The ESV belongs to Crossway. Its text is all rights reserved. Crossway lets
people quote up to 500 verses without asking, with this notice:

> Scripture quotations are from the ESV® Bible (The Holy Bible, English
> Standard Version®), © 2001 by Crossway, a publishing ministry of Good News
> Publishers. ESV Text Edition: 2025. The ESV text may not be quoted in any
> publication made available to the public by a Creative Commons license.
> The ESV may not be translated in whole or in part into any other language.
> Used by permission. All rights reserved.

The art packs are shared under Creative Commons (CC BY 4.0). The notice
itself rules that out for ESV text. Crossway also lists "digital artwork"
as something that needs written permission. So a public release with the
ESV inside the Faith pack needs written permission from Crossway first.

How to ask:

1. Fill in Crossway's digital permission form:
   [crossway.org/permissions/digital](https://www.crossway.org/permissions/digital/).
2. Describe the project as a free, open-source family picture frame. About
   174 verses, shown one at a time beside original drawings. Not sold.
3. Say that some verses are shortened to fit the pictures (the form asks
   whether you plan to edit the text).
4. Expect that Crossway may ask for the verse text to be kept apart from
   the Creative Commons license, with its own "all rights reserved" notice.

More about the ESV: [esv.org](https://www.esv.org).

A likely long-term path is the **ESV API** at
[api.esv.org](https://api.esv.org/). It is free for non-commercial use.
Each family would get their own key, and the frame would fetch the verses
from Crossway at run time instead of shipping them inside the pack. This is
not built yet. It would work like the NASB key below, and the stored
shortening would be worked out from the pack's ESV quotes.

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

### BSB

The Berean Standard Bible has been in the public domain since April 30,
2023 ([berean.bible/terms.htm](https://berean.bible/terms.htm)). No notice
is required, but credit is welcome, so the card shows:

> Bible quotations from the Berean Standard Bible (BSB), public domain.

**Download BSB** gets the official plain-text file from
[bereanbible.com/bsb.txt](https://bereanbible.com/bsb.txt) (about 4 MB),
keeps only the verses the pictures use, and saves them in the data folder
(`bible/bsb.json`). **Remove** deletes that file; you can download it
again any time.

The BSB asks that text which differs from the official text not use the
Berean name. So a verse shown whole says "(BSB)", and a shortened verse
says "(adapted)" instead.

Demo mode does not go online. It uses a small sample of the BSB file
(`app/bible_data/bsb-sample.txt`), which covers the bedtime clock, the
church year, Thanksgiving and the Sundays from September to December 2026.

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

## For people working on the code

- `app/bible.py` holds the translations, the notices, the fallback order,
  the shortening, the BSB download, your own text and the API.Bible fetch.
- `app/bible_api.py` is the Settings API. `web/js/bible-admin.js` and
  `web/css/bible-admin.css` draw the card.
- `app/bible_data/quotes.json` lists every quote in the Faith pack with its
  reference, the verses it covers, the ESV text and, for the KJV and BSB,
  which words of the full verse to keep (word positions, split on spaces).
- The Faith pack (version 1.1.0 and later) stores a `passage` next to each
  verse: `ref`, `verses`, `text` (the ESV text, unchanged), `tr` and
  `short`. Older packs without it keep showing their verse as it was.
- To remake the data files, download the two official text files and run:

  ```bash
  python3 scripts/bible/make-quotes.py kjv.txt bsb.txt --review
  python3 scripts/build-pack.py --all
  ```

  `--review` prints every quote in all three translations to check by eye.
  Fix a poor match in `scripts/bible/overrides.json` with the exact words
  to keep, using `...` for a gap.
