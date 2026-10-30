# Art packs

An art pack is a set of pictures for special days, plus the rules that
bring them up. A rule can be a holiday, a church day worked out from Easter,
a word in an event title, the first day of a season, or a picture every
Sunday.

Doorpost only uses packs that are installed and turned on. If a pack is
off or not installed, none of its pictures, words or rules show anywhere:
not on the frame, not in Settings, not in the picture guide.

## The packs

| Pack | Comes with Doorpost? | What's in it |
|---|---|---|
| U.S. holidays | Yes | New Year's Day, MLK Day, Valentine's Day, Presidents' Day, Mother's Day, Memorial Day, Father's Day, the 4th of July, Labor Day, Veterans Day and Thanksgiving, and which ones take over their day by default. |
| Seasons | Yes | The first day of spring, summer, fall and winter, and a snow day. |
| Family basics | Yes | Birthdays (with the person's photo), anniversaries, school days, graduation, trips and vacations, camping, visitors, date night, and the gold pattern used when a day has no picture. |
| Faith | Yes, installed and on (you can turn it off or remove it) | Everything Christian: the church year (Palm Sunday, Good Friday, Resurrection Sunday, Ascension, Pentecost, Reformation Day, Christmas Eve and Christmas Day), church life (VBS, church glass, picnic, mission trip, church camp, Christmas program, fall festival, baptism), a verse on Thanksgiving, bedtime verses on the clock screen, and a picture with a verse every Sunday. |
| Outings | No, install it | Amusement parks (with the park's name on the sign), water parks, trains, the zoo, the aquarium, fairs, hikes, lake days, pumpkin patches, apple picking, Christmas lights and tree farms. |
| Kids' activities | No, install it | Baseball, soccer, football, recitals, school plays, movie nights and Scouts. |

### The Faith pack

The Faith pack comes installed and turned on. It is still a pack like the
optional ones: turn it off, or press **Remove**, in Settings > Art packs, and
it stays that way. To get it back, install it again under **Get more packs**.
It is put in once, the first time the server starts, and never again by
itself. Its Sunday pictures come from five series that take turns, one Sunday each:

- The Lord's Day (52 pictures)
- The Ten Commandments (10)
- The Holy Trinity (7)
- The 1689 Second London Baptist Confession, one picture per chapter (32)
- Through the Bible, one picture per book (66)

Each Sunday picture has a verse and a short note on what the picture shows
and why ("About this picture", when you tap the day). The turns start fresh
on the first Sunday of January 2027. A Sunday that is a holiday (Resurrection
Sunday, or a holiday set to Special) shows the holiday instead, and the
series wait a week.

You can still pick and choose after installing it. Settings > Special days
has a switch for the Sunday pictures and a list of church days to check or
uncheck.

The verses can show in the BSB (the default), the KJV or your own NASB
text. Pick one under **Bible translation** on the same page. See
[bible-translations.md](bible-translations.md).

## Install a pack

1. Open **Settings > Art packs**.
2. Under **Get more packs**, press **Install** next to the pack you want.
3. The frame picks up the new pictures within a minute.

To install a pack someone gave you, use **Install from a zip** on the same
page.

Each pack in the list has a checksum (sha256). Doorpost checks the
download against it before installing anything. Then it unzips the pack
carefully: only `.svg`, `.png`, `.jpg` and `.json` files, no file names that
point outside the pack, nothing over 20 MB. Last, it cleans every drawing:
it removes scripts, event handlers (`onload` and friends), `foreignObject`
and any link to an outside address. The frame never gets a drawing that has
not been through this.

Installed packs are kept in the server's data folder, in `packs/`
(`/data/packs` in the Home Assistant add-on, so they are part of Home
Assistant's backups). Demo mode keeps its own in `packs-demo/`.

## Turn a pack off, or remove it

Every pack has an **On / Off** switch in Settings > Art packs. Off means
none of its pictures or rules are used. The pack stays on disk, so you can
turn it back on.

Installed packs (Faith and any you add) also have **Remove**. The other
packs that come with Doorpost can only be turned off.

Your own settings stay put either way. For example, if you uncheck Good
Friday and later remove and reinstall the Faith pack, Good Friday is still
unchecked.

One thing to know: if you have edited the title words in Settings > Special
days, Doorpost keeps your list as you saved it. A word you kept that
points at a picture from a removed pack shows the gold pattern instead.

## Make your own pack

A pack is a folder with a `pack.json` file and the drawings:

```
my-pack/
  pack.json
  scenes/
    kite.svg
    bonfire.svg
```

Here is a small `pack.json`:

```json
{
  "id": "my-pack",
  "name": "Our outdoor days",
  "version": "1.0.0",
  "priority": 50,
  "description": "Kite day and bonfire night.",
  "license": "CC BY 4.0",
  "preview": "scenes/kite.svg",
  "scenes": {
    "kite": {"title": "Kite day", "script": "Up it goes!", "about": "A red kite over a green hill.", "file": "scenes/kite.svg"},
    "bonfire": {"title": "Bonfire night", "script": "Bonfire!", "file": "scenes/bonfire.svg"}
  },
  "groups": [{"name": "Outdoors", "scenes": ["kite", "bonfire"]}],
  "rules": [
    {"keyword": "Kite", "scene": "kite"},
    {"keyword": "Bonfire", "scene": "bonfire", "picture_only": true}
  ]
}
```

What the parts mean:

- `id`: lowercase letters, numbers and dashes. It can't be the id of a pack
  that comes with Doorpost.
- `priority`: when two packs have a picture with the same name, the higher
  number wins. The packs that come with Doorpost use 10, the optional
  ones 20. Use 50 (the default) to replace one of our pictures with yours.
- `scenes`: each picture. `title` is its name in Settings, `script` is the
  big line on the frame, `about` is the note in the picture guide, and
  `file` is the drawing. Add `"hidden": true` for a picture that should not
  be listed (a wide version of another picture, for example). Add
  `"variants"` to show another of the pack's pictures for part of the year:
  `"variants": [{"scene": "kite-autumn", "from": "09-15", "to": "11-30"}]`
  (month-day, and a range can run past New Year).
- `groups`: how Settings > Special days groups your pictures.
- `rules`: what brings the pictures up (below).

### Rules

| Rule | Example | What it does |
|---|---|---|
| Title word | `{"keyword": "Kite", "scene": "kite"}` | An event with "Kite" in its title takes over its day with this picture. Add `"picture_only": true` to only pick the picture for an event that is already special (starred). `"order"` sets which words are checked first (lower first, default 500). |
| Holiday | `{"holiday": "labor day", "scene": "labor", "script": "Labor Day", "mode": "special"}` | A holiday from the holiday calendar (lowercase name). `mode` is the default: `hide`, `show` or `special`. Can also add a `verse` or set `solemn`. |
| Church day | `{"church": "palm", "name": "Palm Sunday", "easter": -7, "scene": "palm", "script": "Hosanna!", "verse": "...", "default_on": true}` | A day worked out every year: `"easter"` counts days from Easter, or `"date": "12-25"` is a fixed date. |
| Season | `{"season": "fall", "scene": "fall", "name": "First day of fall"}` | The equinox or solstice (`spring`, `summer`, `fall`, `winter`). |
| Every Sunday | `{"weekly": "sunday", "series": "series.json", "script": "The Lord's Day", "label": "..."}` | A picture every Sunday from the series in `series.json` (see the Faith pack for the layout). |
| Clock verses | `{"clock_verses": [["text", "Psalm 4:8"]]}` | Lines for the bedtime clock screen, one per weekday. |

### Drawings

- SVG is best. PNG and JPG work too.
- Draw on a tall canvas: `viewBox="0 0 300 600"` with
  `preserveAspectRatio="xMidYMax slice"`. Keep the main subject between
  y 150 and 420 and x 60 and 240, so it shows on both tall and wide screens.
- Start the file with `<svg xmlns="http://www.w3.org/2000/svg" ...>` so it
  also opens as a picture on its own (the preview in Settings needs this).
- These words in a drawing get filled in on the frame: `{{NAME}}` and
  `{{NAME_SIZE}}` (the birthday person's name and a font size),
  `{{PORTRAIT}}` (their photo), `{{PLACE}}` and `{{PLACE_SIZE}}` (the park
  name).
- The frame is an old Android browser. Plain shapes, gradients, clip paths
  and text all work. Scripts, animation and outside pictures are removed.
- A drawing can show a PNG or JPG from its own pack, such as a logo:
  `<image href="images/logo.png" x="130" y="412" width="40" height="40"/>`.
  The path is inside the pack folder. Anything else in an `<image>` is
  removed.

### Keep your pictures themable

A frame can show pictures as drawn or recolored to match its look
("Pictures: Match the look", see [themes.md](themes.md)). Your pictures
join in for free if you follow three rules:

- Write colors as `fill="#C9A55A"`, `stroke="..."` and `stop-color="..."`
  with six hex digits. Colors inside a `style="..."` or a `<style>` block, or
  written as names (`fill="red"`), stay as drawn.
- Paint the whole background with a first
  `<rect width="100%" height="100%" fill="#...">`. A dark color painted this
  way counts as the background, so a look can change the sky without
  changing dark things drawn on top.
- Give each gradient and clip path an `id` and point at it with `url(#id)`.
  The frame gives each copy of a picture its own ids.

Doorpost sorts each color into a family (background, ink blue, gold, cream,
red and so on) by its shade. When it guesses wrong, name the family in
`pack.json`:

```json
"palette": {"#7A1F5C": "red", "#1B2A3A": "navy"}
```

The families are `night` (background), `navy` (ink blue), `deep`, `gold`,
`paper` (cream and light), `red`, `warm` (orange), `brown`, `green`, `sky`
and `pink`.

### Try it, then share it

Put the folder in `local/packs/` next to the code (create the folder if it
isn't there) and restart the server. See [private-overlay.md](private-overlay.md)
for the rest of `local/`. It shows in Settings > Art packs as
"Your own". When it looks right, zip the folder and install the zip on
another Doorpost with **Install from a zip**.

## For people working on the code

The pictures that come with Doorpost are drawn in Python
(`app/scenes.py`, `app/scenes_family.py`, `app/lordsday_art.py`), with
their names and rules in `app/special.py`, `app/picture_guide.py` and
`app/lordsday.py`. `app/pack_build.py` sorts them into packs.

```bash
python3 scripts/build-pack.py faith    # dist/packs/faith/ and dist/packs/faith-<version>.zip (+ .sha256)
python3 scripts/build-pack.py --all    # every pack, packs/<built-in>/, packs/index.json and packs/previews/
```

Run `--all` after changing any drawing or table. The tests check that
`packs/` and `packs/index.json` match the drawing code. The zips come out
byte for byte the same every time, so their sha256 stays put until a
drawing changes.

`packs/index.json` is the list Settings shows under "Get more packs". Each
entry has an `id`, `name`, `description`, `version`, `url`, `sha256`,
`size`, `pictures` and `preview`. `"default": true` (the Faith pack) means
the server installs it the first time it starts (`seed_defaults` in
`app/packs.py`); after that it is the family's to keep, turn off or remove. A `url` can be an `https://` address (a
release download, for example) or a path under `dist/packs/`. When a path
under `dist/packs/` has no zip yet, the server builds that pack from the
drawing code, so Install works offline in demo mode and on a fresh copy of
the code.

`FRAME_EXTRA_PACKS` (folders separated by `:`) adds more places to read
packs from. The tests use it to run with every pack. Tests of a first start
(Faith put in, removing it sticks) take it away (`tests/test_packs.py`).

## License

The art packs are shared under the
[Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/)
license (CC BY 4.0), separate from the code's MIT license (see `LICENSE`). You can
reuse and change the pictures, including in your own packs, as long as you give credit.
The Bible verses in the Faith pack are short quotations from the Berean
Standard Bible (BSB), which is in the public domain, so they can travel with
the pictures. See [bible-translations.md](bible-translations.md).
