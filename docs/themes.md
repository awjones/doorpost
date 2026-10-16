# Looks

A look is how a frame is dressed: its colors, fonts and the small touches
that go with them. Each frame picks its own look in **Settings > Frames**.
Doorpost comes with these, in this order:

| Look | Made for |
|---|---|
| Navy & gilt | The kitchen. Navy band, gold trim, warm paper. |
| Quiet night | A bedroom. Dark and dim. |
| Bright & playful | A playroom. Big type, bright colors, round corners. |
| Kids room | A playroom. Sunny sky, big friendly pictures. |
| Light | Warm paper, classic type. |
| Modern | White cards, bold type, one bright color. |
| Illuminated | Parchment, red rubrics, a gilded initial. |
| Gilt binding | Navy leather and gold tooling. |
| Open almanac | Two facing pages on a dark desk. |
| Glass View | Glass panels over the family photo. |
| Mica View | Soft tinted layers, a dock at the bottom. |
| Tonal View | One color, soft shapes. |

Bright & playful and Kids room are kids' looks (see
[Looks for kids' frames](#looks-for-kids-frames)).

## Pictures: Original or Match the look

Each frame also has a **Pictures** setting, in Settings > Frames:

- **Original** shows the special-day pictures, Sunday pictures and screen
  time pictures as they were drawn. This is the default.
- **Match the look** recolors them to fit the frame's look and puts the
  look's frame (border and corners) around them. Quiet night makes them dim
  and soft. Bright & playful makes them brighter. Navy & gilt changes little,
  since the pictures were drawn in its colors.

Nothing is redrawn. The frame swaps colors as it shows each picture, so
turning it back to Original shows the pictures exactly as drawn.

## Make a look

A look is a folder in `themes/`, named for its id:

```
themes/
  harbor/
    theme.json
    theme.css
    fonts/            (only if it uses fonts of its own)
```

To keep a look private, put the folder in `local/themes/` instead. A look
there with the same id as one in `themes/` replaces it. Restart the server
after adding a new look folder. Changes to a look's theme.json, theme.css
and theme.js show on the next check without a restart: the server reads them
again when their files change, and `/themes.css` gets a new version.

### theme.json

```json
{
 "id": "harbor",
 "name": "Harbor",
 "blurb": "Sea blue and white",
 "order": 40,
 "kind": "both",
 "swatches": ["#0F4C75", "#FFFFFF", "#F2A541"],
 "fonts": {"serif": "Georgia, serif"},
 "new_frame": {"home": "today"},
 "art": {
  "palette": {"night": "#0F4C75", "gold": "#F2A541", "paper": "#FFFFFF"},
  "filter": "saturate(0.9)",
  "frame": {"border": "3px solid #F2A541", "border-radius": "16px"}
 }
}
```

What the parts mean:

- `id`: lowercase letters, numbers and dashes. It must match the folder name.
- `name` and `blurb`: shown in Settings > Frames and on the frame's own menu.
- `order`: where it sits in the list (lower first). Give each look its own
  number. The looks that come with Doorpost use 10 to 110, in steps of 10
  (Bright & playful's kids' room cousin uses 35); a test checks no two share one.
- `kind`: `wide`, `tall` or `both`, for frames hung that way.
- `swatches`: a few colors shown next to the name in Settings.
- `fonts`: any of `serif` (headings), `sans` (body text) and `script` (the
  handwritten lines). Leave out the ones you don't change.
- `new_frame`: what a new frame with this look starts on. `home` is `today`,
  `kids`, `clock` or `chores`. `screens` is an optional list of screens.
- `art`: what **Match the look** does (below).
- `options`, `background` and `kids`: see below.
- `words`, `date_style`, `monogram` and `picture_fit`: see
  [Hooks for looks](#hooks-for-looks).
- `"enabled": false` hides a look while you work on it. `"default": true`
  makes it the look new frames get when none is picked.

### theme.css

Every rule starts with `body.look-<id>`, so the look only changes frames that
use it:

```css
body.look-harbor { --paper: #F4F8FB; --navy: #0F4C75; --gilt: #F2A541; }
body.look-harbor .band { border-bottom: 4px solid var(--gilt); }
```

Most of a look is the color settings at the top of `web/css/frame.css`
(`--paper`, `--card`, `--ink`, `--navy`, `--gilt` and the rest). Start by
changing those, then add rules for the parts you want to look different.
A test checks that every rule in a shipped look starts with its
`body.look-<id>`.

To use a font of your own, put the `.woff2` file in the look's `fonts/`
folder and point at it from theme.css:

```css
@font-face { font-family: "Harbor Sans"; src: url(fonts/harbor-sans.woff2) format("woff2"); }
```

The frame is an old Android browser (Chrome 106). Plain CSS works. Don't use
CSS nesting, `:has()`, or colors with 8 hex digits.

### The art palette

**Match the look** sorts every color in the pictures into a family. A look
gives one color for each family it wants to change:

| Family | What it is |
|---|---|
| `night` | The dark sky or wall behind a picture |
| `navy` | Dark blue things drawn on top (a book, a coat) |
| `deep` | The darkest shadows |
| `gold` | Gold, yellow and gilt trim |
| `paper` | Cream, white and light things |
| `red` | Red |
| `warm` | Orange |
| `brown` | Brown and wood |
| `green` | Green |
| `sky` | Lighter blues |
| `pink` | Pink |

Each color moves to the look's color for its family, but keeps its shade: a
light gold stays lighter than a dark gold. A family you leave out keeps its
colors as drawn.

- `filter`: an optional finishing touch for the whole picture, made of
  `brightness()`, `contrast()`, `saturate()`, `sepia()`, `grayscale()`,
  `hue-rotate()` and `opacity()`.
- `frame`: an optional border around each picture's panel: `border`,
  `border-radius`, `box-shadow`, `outline` and `outline-offset`.

### Options

A look can offer a few settings of its own, like how frosted its glass is or
its main color. Each frame keeps its own choices. They show in Settings >
Frames, under the look, once that look is picked.

```json
"options": {
 "frost": {"label": "Glass", "type": "range", "min": 0, "max": 100, "default": 60,
           "presets": {"Frosted": 100, "Balanced": 60, "Clear": 0}},
 "seed": {"label": "Color", "type": "color", "default": "#2F7A68",
          "swatches": ["#2F7A68", "#16324F", "#8A3B5C"]},
 "reduce_effects": {"label": "Reduce glass effects on this frame", "type": "bool", "default": false},
 "background": {"label": "Background", "type": "choice",
                "choices": [["slideshow", "Photo slideshow"], ["one", "One photo"], ["favorite", "Today's favorite"]]}
}
```

There are four kinds:

| type | Settings shows | Extra fields |
|---|---|---|
| `range` | a slider, with a button for each preset | `min`, `max`, `step`, `presets` |
| `color` | round swatches and a color picker | `swatches` |
| `bool` | a checkbox | |
| `choice` | a drop-down list | `choices`, a list of `["value", "Label"]` |

Each option can also have a `help` line (up to 300 letters; Settings wraps
it). A `range` option can add `"preview": "readouts"` and a `readouts` map
of labels to CSS variables its theme.js `derive` returns, like
`{"Blur": "--harbor-ro-blur", "Tint": "--harbor-ro-tint"}`. Settings then
shows those values under the slider and updates them as it moves, so a
parent sees what the slider does before saving. Up to 6. Names are lowercase letters,
numbers and underscores. A look can offer up to 12. A saved value that no
longer fits (say the range changed) goes back to the default.

On the frame, each option becomes something theme.css can use:

- numbers and colors become a CSS variable on `body`: `--opt-frost: 60`,
  `--opt-seed: #2F7A68`. An underscore in the name becomes a dash.
- on/off and choices become an attribute on `body`:
  `data-opt-reduce-effects="1"`, `data-opt-background="favorite"`. On/off
  also sets `--opt-reduce-effects: 1` or `0`.

```css
body.look-harbor .card { opacity: calc(0.6 + var(--opt-frost) / 250); }
body.look-harbor[data-opt-reduce-effects="1"] .card { box-shadow: none; }
```

### theme.js (optional)

Chrome 106 can't mix colors in CSS, so a look that builds colors from an
option does it in a small script. Put `theme.js` in the look's folder. The
frame loads every look's script in one file, `/themes.js`. Write plain old
JavaScript: `var` and `function`, no `=>`, no backtick strings.

```js
FrameLooks.register('harbor', {
  // Runs when the frame's look or options change. Return more CSS variables.
  derive: function (options) {
    var t = FrameLooks.tones(options.seed);
    return { '--harbor-band': t[30], '--harbor-tint': t[95], '--paper': t[98] };
  },
  // Runs after every screen is drawn. Only add decoration: class names or
  // empty elements. Never change the words or the buttons.
  decorate: function (ctx) {
    // ctx: { screen: 'today', root: <the screen's element>, layout: 'wide' or 'tall',
    //        kids: true on a Kids frame or a kids' look, options: {...}, look: 'harbor',
    //        today: '2026-10-15', family: 'Our Family', initial: 'F' }
    FrameLooks.ensure(ctx.root, 'harbor-rail');   // adds <div class="harbor-rail"> once
  }
});
```

Helpers on `FrameLooks`:

- `tones(hex)`: a scale of one color from black to white. Keys are 0, 5,
  10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 98, 99 and 100. 40 is about the
  color's own strength, 90 and up are tints for backgrounds.
- `mix(a, b, w)`: a color part way from `a` to `b` (`w` from 0 to 1).
- `rgba(hex, alpha)`: the color with see-through, for CSS.
- `shift(hex, hue, sat, light)`: turn the hue (degrees) and add to
  saturation and lightness (0 to 1).
- `ensure(parent, className, tag)`: adds a decorative element once and gives
  it back. Running decorate again never adds a second one.

A screen is often drawn again with the same content, and sometimes it is
left as it was. Write `decorate` so running it twice does no harm. If a
script fails, the frame logs it and carries on without it.

### A photo behind every screen

`"background": "photo"` in theme.json puts the slideshow photo full screen
behind every screen. The look's theme.css decides how dim it is and makes
the cards see-through:

```css
body.look-harbor { --look-photo-dim: 0.35; }   /* 0 is the photo as it is, 1 is black */
body.look-harbor .card { background: rgba(255, 255, 255, 0.7); }
```

The photo is the frame's own crop of it (wide or tall, around the focal
point). It moves along with the slideshow. If the look has a `choice`
option named `background`, its values change that: `slideshow` (the
default), `one` (stays on one photo) or `favorite` (one photo a day).
`body` gets the class `look-photo` while the photo shows. Demo mode makes a
drawn landscape for its photos folder when it is empty.

### Looks for kids' frames

`"kids": true` means the look was made for a kids' frame. Settings lists it
first for a frame whose home screen is Kids. A frame using such a look gets
the same narrowed data as the Kids screen, whatever its home screen: no
event notes or addresses, no address on a special day, no taken-away
minutes, no house status. That covers the Today ribbon, the calendar, the
day pop-ups and paging the calendar. Its nav also gets a **Grown-ups**
button for the parent PIN, and the PIN pad leaves out the list of waiting
chores. The Kids screen is styled the
same way as the rest: `body.look-<id> .kv-...` rules win over
`web/css/kids.css`. One kids.css rule uses `!important` (the bedtime bubble),
so match it with `!important` if your look changes it.

### Checklist for a new look

Open the demo (`FRAME_DEMO=1`) and look at each of these, on a wide frame
and a tall one:

- Today, with each flip-panel tab (Chores, Groceries, Weather, Screen time)
- Chores
- Screen Time, with each of its four pictures
- Calendar: Week, Next days and Month
- A special day, and the day pop-up from the calendar
- Lists, and adding to a list
- Photos
- Night clock
- The PIN pad, and the parent panel behind it
- The Kids home screen (the Playroom frame)
- Settings > Frames: its swatches and options
- Pictures set to Match the look: every color family in `art.palette`
- With each preset of each option, and with every on/off option on

## Hooks for looks

The screens carry a few spare pieces a look can use. Each is hidden or
looks the same as before until a look turns it on, so the other looks never
notice.

### The family initial

Every monogram (`.mono`) has the family's letter in it: a `data-initial`
attribute and an `<i class="mono-i">` inside. The letter is the first letter
of the family name's last word ("The Example Family" gives E), unless
Settings > General has a **Family initial**. It reaches the frame as
`initial`.

`"monogram": "initial"` in theme.json shows the letter, typeset, in place of
the drawn monogram everywhere. Style it with `--mono-font` and
`--mono-color`, or with rules for `.mono-i`. A band's monogram takes its size
from `--mono-w` (no `!important` needed).

### Words

`"words"` in theme.json changes a few bits of wording. Leave out any you
don't change.

| Key | Without a look's words | Where |
|---|---|---|
| `today_title` | Today | the Today card's heading |
| `tomorrow` | Tomorrow | the line under the Today card, the night clock |
| `next_prefix` | Next | the "Next · 1 hr" pill |
| `things_count` | `{words}` | "six things" by the heading; `{n}` is the number, `{words}` the number in words |
| `chores_title` | `{name}’s Chores` | the Chores heading |
| `kids_hi` | `Hi, {name}!` | the Chores heading on a kids' look |
| `pin_title`, `pin_sub` | Parent tools, Enter the parent PIN. | the PIN pad |
| `kids_grownups` | Grown-ups | the PIN button on a kids' look |
| `night_title`, `night_sub` | (none) | lines above and below the night clock's date |
| `tod_morning`, `tod_afternoon`, `tod_evening` | Good morning, ... | the time of day under the clock (below) |

`"date_style": "long"` writes the date as "Thursday, the Fifteenth of
October" in the headers, the photo panel, the bedroom clock and the night
clock. `"short"` (the default) is "Thursday · October 15".

### Slots

| Slot | What it is | Shown |
|---|---|---|
| `.clock .tod` | the time of day under the Today clock | hidden |
| `.ribbon .rb-count` (`.rb-n`, `.rb-unit`) | the countdown's number and "days" | hidden |
| `.ribbon .rb-sub .rb-date`, `.rb-lines` | the date line and the time, as two pieces | shown |
| `.ribbon .rb-icon`, `.rb-more` | the day's icon, and "Details >" | hidden |
| `.day-tag` | "Today" in today's day header and month cell | hidden |
| `.week-panel` | around the seven days of Week and Next 7 days | `display: contents` |
| `.ktile .kbar` (`--kpct`), `.ktile .kwbadge` | a kid tile's progress bar, and "1 waiting" (or "Almost!", class `almost`, with one chore left) | hidden |
| `.ktile.all-done`, `.ktile.has-waiting` | classes on the kid tiles | |
| `.chore.todo` / `.waiting` / `.done` | a class on each chore row | |
| `#screen-night .ap`, `.nwx` | AM/PM, and the weather, on the night clock | hidden |
| `.grownups` | the Grown-ups button in a kids' look's nav | kids' looks |

The ribbon also has `data-days` (0 is today). Colors the app used to write
into `style=""` are CSS variables now, so a look needs no `!important`:

- a chore's minutes medal: `--medal-bg`, else the kid's tint (`--kt`; `--kc`
  is the kid's color);
- an event on Week: `--ce-bg`, else its calendar's tint (`--ct`);
- an empty day in the Chores mini bars: `--minibar-empty`;
- a band's monogram size: `--mono-w`.

A very busy day on Week shows what fits and "and 3 more". On a short
3-day weather panel the cards drop their words, then their pictures
(classes `.tight` and `.tighter` on `.wdays`), so no line is cut off.

### Screen time pictures

The drawings use CSS variables for their colors and fonts, with the colors
as drawn as the fallback. A look can recolor them in Original mode:

| Variable | Drawn as |
|---|---|
| `--draw-card` | #FFFDF8, the light pictures' paper |
| `--draw-navy` | #16324F, the dark pictures' sky, and ink |
| `--draw-gilt`, `--draw-gilt-soft`, `--draw-gilt-dim` | #C9A55A, #B9A06E, #8C7A4E |
| `--draw-line`, `--draw-soft` | #E2D8C3 (the ring's track), #5E5547 (small text) |
| `--draw-red`, `--draw-extra` | #C8102E, #8FA3B8 |
| `--draw-<HEX>` | any other drawn color, like `--draw-F3E9D2` (the rocket) |
| `--draw-serif`, `--draw-sans` | the drawings' two fonts |

On a frame set to Match the look, the art palette still recolors them; a
`--draw-` value wins over it. Put the `--draw-` values under
`body.look-<id>.pics-original` to change Original only.

`"picture_fit": {"wide": "slice", "tall": "meet"}` decides how a picture fits
its panel: `meet` shows all of it, `slice` fills the panel and trims the
edges. Those two are the default. The picture always starts below the
title and the picture buttons, so they never cover it.

### Match the look from theme.js

A look whose colors come from an option (a seed color) can recolor the
pictures to match: `derive` returns `art`, one color per family, the same
families as `art.palette`:

```js
derive: function (o) {
  var t = FrameLooks.tones(o.seed);
  return { '--paper': t[98], art: { night: t[20], navy: t[30], paper: t[95], green: t[40] } };
}
```

On a frame set to Match the look, every drawn color in those families moves
to the new color, keeping its shade, the same way `art.palette` works. A
family left out keeps the theme.json palette.

## Settings look

Settings and the parent phone page can wear any look too. Pick it in
**Settings > Overview > Settings look**:

- one of the looks, shown with its swatches. Navy & gilt is the default.
- **Match a frame**: pick a frame. Settings then follows that frame's look
  and its options (a Tonal View color, a Modern accent, how frosted Glass
  is). Change the frame and Settings changes with it.
- **Use it on the phone page too** (on by default). Off keeps the phone page
  plain.

At the bottom of each page is a line like "Settings look: Glass View. Use
plain". **Use plain**, or `?look=plain` at the end of the address, always
shows the plain Navy style.

### Safe by design

A look can't break Settings. Four rules make sure of it:

1. **Tokens, not rules.** A look gives a short list of values (below).
   `web/css/admin-look.css` and the pages' own styles turn them into every
   card, field, switch and button. Every look styles the same controls in
   the same places.
2. **A readability check.** The server works out the values and checks them
   before a page gets them. Body text and button text need 4.5:1 contrast
   (the usual standard). Small labels and the focus ring need 3:1. A look
   that fails is not used: the page shows Navy & gilt, the footer says the
   look couldn't be used safely, and the server log says which pair failed.
   A test checks every look with every option preset.
3. **Decoration only.** A look's `admin.css` can add borders, shadows,
   background pictures and gradients, fonts and letter shapes. It can't
   hide, move or cover anything. The server takes out anything else before
   the page gets it, and a test fails if a shipped `admin.css` tries.
4. **Fallbacks.** A look that is removed or turned off, or a matched frame
   that is gone, gives Navy & gilt. If anything goes wrong while dressing a
   page, the page opens in the plain style.

### The admin block in theme.json

```json
"admin": {
 "tokens": {
  "paper": "var(--paper)", "card": "var(--card)", "ink": "var(--ink)",
  "soft": "var(--soft)", "line": "var(--line)",
  "accent": "readable($accent, #FFFFFF, 4.6)", "accent_ink": "#FFFFFF",
  "danger": "var(--red)", "ok": "var(--green)",
  "head_bg": "mix($accent, #FFFFFF, 0.88)", "head_ink": "var(--ink)",
  "font_display": "var(--serif)", "font_body": "var(--sans)",
  "radius": "8px", "shadow": "none"
 }
}
```

These 15 are needed:

| Token | What it is |
|---|---|
| `paper` | the page behind the cards (solid) |
| `card` | cards (can be see-through, like `rgba(255, 255, 255, 0.8)`) |
| `ink`, `soft` | text, and quieter text |
| `line` | borders |
| `accent`, `accent_ink` | buttons and picked things, and the text on them |
| `danger`, `ok` | warnings in red, and "done" in green |
| `head_bg`, `head_ink` | the header band and its text |
| `font_display`, `font_body` | headings, and everything else |
| `radius`, `shadow` | card corners, and the card shadow |

A look can also set these. Left out, each is made from the ones above:
`tile` (fills inside cards), `line_soft`, `muted`, `label` (small labels),
`note`, `rule` (decorative lines and rings), `head_soft` (the small line in
the header), `head_rule` (the line under the header), `field` and
`field_ink` (inputs), `link`, `track` (an off switch), `warn` and `warn_bg`,
`ok_bg`, `danger_bg`, `danger_ink`, `focus` (the focus ring),
`font_script` (the name in the header) and `pill` (round button ends;
`0px` for square).

A value can be:

- a color (`#16324F`, `rgba(...)`), a size (`14px`) or a font list;
- `var(--paper)`: the look's own frame color, from its `body.look-<id>`
  rule in theme.css, its theme.json fonts, or `web/css/frame.css`;
- `$accent`: one of the look's options, as the frame (or the default) has it;
- `@card`: another token;
- `mix(a, b, 0.2)`, `tone(a, 40)`, `shift(a, 0, 0, -0.1)`, `alpha(a, 0.8)`:
  the same color math as `FrameLooks` in theme.js;
- `lstar(a, auto, 40)`: Tonal View's own tones (the color's hue at a
  lightness the eye sees as 40);
- `readable(a, b)`: color `a`, made darker (or lighter) until it reads on
  `b`. Use it for a color that comes from an option, so a pale pick still
  gives readable buttons;
- `best(bg, a, b)`: whichever of `a` and `b` reads better on `bg`.

A number can be `0.8`, an option (`$frost`), or `lerp($frost, 0.86, 0.62)`
(an option from 0 to 100, mapped onto two numbers).

`"photo": true` puts the family photo behind the page, softened by
`"photo_wash"` (a see-through color over it). Glass View uses this.

### admin.css

`themes/<id>/admin.css` is optional. Every rule starts with
`body.admin-look-<id>`:

```css
body.admin-look-harbor .aband { border-bottom: 4px double var(--a-head-rule); }
body.admin-look-harbor .card > h2 { color: var(--a-accent); font-style: italic; }
```

What it can set:

- borders, corners, `box-shadow`, `text-shadow`;
- `background-image` (gradients, or a picture in the look's own folder),
  with its size, position and repeat;
- `font-family`, `font-style`, `font-weight`, `letter-spacing`,
  `text-transform`, `font-variant` and the like;
- `font-size` on headings only (h1, h2, h3, `.script`, `.kicker`), 12px to
  44px. Form text keeps its size;
- `color`, but only as a text token: `var(--a-ink)`, `var(--a-soft)`,
  `var(--a-link)`, `var(--a-accent)`, `var(--a-danger)`, `var(--a-ok)` or
  `var(--a-muted)`;
- `backdrop-filter` with `blur()`, `saturate()` or `brightness()`;
- on `::before` and `::after` only: `content` (a short ornament),
  `display: block` or `inline-block`, a size, margins and
  `background-color`;
- `@media (max-width: ...)` or `(min-width: ...)` around rules.

Never allowed: `display: none`, `visibility`, `position`, `opacity`,
`z-index`, `transform`, `pointer-events`, `clip`, `order`, `float`,
`inset`, `!important` and `@import`. The tokens are CSS variables named
`--a-<token>`, with dashes (`--a-head-rule`). Options are there too, as
`--opt-<name>` for numbers and colors and `data-opt-<name>` on `body` for
on/off and choices, like on the frame. The look's own fonts (its theme.css
`@font-face` rules) come along.

### Checking a Settings look

Open `/admin`, `/admin/frames`, `/admin/calendars`, `/admin/modules` and
`/parent` (on a phone, or a narrow window) with the look picked. Then:

- run the tests (`tests/test_admin_looks.py` checks every look with every
  option preset, and every `admin.css`);
- with each preset of each option, use **Match a frame** on a frame set to
  it;
- tab through a page: the focus ring has to show on every control.

## For people working on the code

- `app/themes.py` finds the looks (and finds them again when their files
  change) and puts them together into one file, `/themes.css`. The frame loads it with a version
  number, like its other files, so a changed look reaches the frame on its
  next check.
- `app/admin_looks.py` works out and checks a look's Settings tokens, cleans its
  `admin.css`, and dresses `/admin` and `/parent` (`app/admin_looks_api.py`
  has the setting). See [Settings look](#settings-look).
- `app/artcolor.py` sorts colors into families and works out each look's
  colors.
- `web/js/looks.js` is `FrameLooks`: it sets the option variables, runs each
  look's `derive` and `decorate`, and shows the photo behind the screens.
  `web/js/app.js` calls it in three places (a new look or options, after each
  screen is drawn, and a new photo).
- `web/js/look-options.js` draws the options in Settings > Frames. Saved
  values live in each frame's profile as `look_options: {look id: {...}}`
  and reach the frame in `/api/frame` as `frame.look_options`,
  `frame.look_background` and `frame.look_kids`.
- `web/js/app.js` (`artMatch`) swaps the colors on a frame set to Match the
  look. Each copy of a picture also gets its own ids, so two copies on one
  page never share a gradient.
- Art packs can name the family of their own colors. See
  [art-packs.md](art-packs.md).
