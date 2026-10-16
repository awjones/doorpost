# Screens: sizes, orientation and other options

Doorpost was built and tested on one screen: a 10.1 inch, 1280 x 800
Android picture frame. Everything else on this page is either how the layout
works (true for any screen) or advice for screens nobody has tested yet. Each
part says which.

For picture frames in particular, see [hardware.md](hardware.md).

![How Doorpost picks a wide or tall layout, then four screen sizes drawn to scale with resolution, viewing distance, layout and a caution for each.](img/screen-sizes.svg)

## Wide or tall: how the layout fits a screen

This part is how the code works, on any screen.

- The page lays itself out at **800 pixels on the short side**. The long side
  stretches to match the screen's shape, from 1200 to 1440 pixels. Then the
  whole page is scaled to fill the screen.
  - A 16:10 screen (1280 x 800) gets a 1280 x 800 layout, shown 1 to 1.
  - A 16:9 screen (1920 x 1080) gets a 1422 x 800 layout, scaled up.
  - A 4:3 screen gets a 1200 x 800 layout with thin bands at the top and
    bottom.
- If the screen is **taller than it is wide** (by 5% or more), the page uses
  the **tall** layout instead: 800 wide by 1200 to 1440 tall. The page adds the
  class `vert` to the body, and every screen (Today, Chores, Calendar and the
  rest) has its own tall arrangement.
- Turning a frame on its side switches layouts by itself. To force one, add
  `?layout=tall` or `?layout=wide` to the frame's address.
- Photos are cropped on the brain for the frame's shape. Screens 1700 pixels
  or more across get sharper HD photos (1920 x 1080). Focal points keep the
  important part of each photo in view on both shapes; see
  [photos.md](photos.md#focal-points-wide-and-tall-frames).
- The gear in the top-right corner of a frame (parent PIN) shows the screen's
  size and shape.

## Sizes

| Size | Typical resolution | Read it from | Layout | Status |
|---|---|---|---|---|
| 7 inch | 1024 x 600, or 720 x 1280 tall (Raspberry Pi Touch Display 2) | 1 to 3 ft | Wide, scaled down (tall if upright) | Untested |
| 10.1 inch | 1280 x 800 | 2 to 6 ft | Wide, 1 to 1 (tall on its side) | **Tested** |
| 13 to 15.6 inch | 1920 x 1080 | 4 to 10 ft | Wide, scaled up, HD photos | Untested |
| 21.5 inch and up | 1920 x 1080 or more | 6 to 15 ft | Wide, scaled up, HD photos | Untested |

Distances are rough guides for reading the calendar comfortably. Photos and the
clock read from farther away. A small screen in a big kitchen is the most
common letdown, so stand where people will read it and hold up something the
same size before you buy.

## Cautions

Check these before you buy any screen.

- **Web engine version.** Doorpost needs a browser engine at least as new
  as Chrome 106. On Android this is Android System WebView. Old picture frames
  ship with far older versions and need the engine replaced (see
  [hardware.md](hardware.md)). If it can't be upgraded, the screen won't work.
- **Memory.** 1 GB of RAM or more. The page is kept light for 1 GB frames.
- **A real USB data port, with ADB.** Needed to set up a picture frame. Some
  frames only take power through their port.
- **Resolution vs layout.** Anything from 1024 x 600 to 4K will lay out, but
  text on a 7 inch, 1024 x 600 screen is small, and very wide shapes (21:9)
  leave bands at the edges.
- **Touch or no touch.** Without touch, the frame still shows the calendar,
  weather and photos, but kids can't claim chores on it. Parents can still
  use the phone page.
- **Viewing distance and font size.** Text size is fixed by the layout, so a
  bigger screen means bigger text. Match the size to the room (table above).
- **Always on: power, burn-in and backlight.** The screen is on all day. LCD
  panels rarely burn in, but a static image can leave a faint ghost, and
  backlights fade with hours. OLED screens (some TVs) burn in much faster and
  are a poor fit. The slideshow after 5 idle minutes and the dim night clock
  help. Turning the backlight fully off overnight is done on the frame (Wes's
  kiosk app has a motion-sensor option), not by Doorpost.
- **Brightness at night.** From 10 PM to 6 AM the page shows a dim clock and
  tomorrow's first event. Change the hours in Settings. A bright screen in a
  dark hallway is still noticeable, so try it at night before you mount it.
- **Mounting and heat.** Leave space behind it for air. Keep it out of direct
  sun and away from the stove and heat vents. Plan the power cable route
  before drilling.
- **Vendor apps that phone home.** Cheap frames and smart TVs run the maker's
  apps, which talk to the maker's servers. Disable them if you can, and always
  put the screen on its own network that can reach only your server
  ([setup-guide.md](setup-guide.md#4-set-up-your-home-network)).

## Other screens you can use (all untested)

None of these have been tested with Doorpost. They should work if they
meet the cautions above. If you try one, please share what happened.

### A newer Android tablet

Most Android tablets from the last several years have an up-to-date Chrome and
WebView, so they need no rooting or engine swap.

- Use a **kiosk browser** app (Fully Kiosk Browser is a popular one; some
  features need a paid license) to open your server's address full screen and
  start it at power-on. Or use the Doorpost kiosk app from `kiosk/`.
- Use Android's **screen pinning** (Settings > Security) to keep it on one app.
- Turn off the tablet's own sleep timer, or let the kiosk app keep it awake.
- Keep it plugged in. Tablets that sit at 100% charge for months can wear out
  or swell their batteries. Some tablets have a setting to stop charging at
  80% or 85%; turn it on if yours does.
- No logins on it. Put it on the frame's network.

### An old iPad

An old iPad can work as a kitchen screen. How old matters: the page needs a
reasonably modern Safari, so an iPad that still gets iPadOS 15 or later is a
safer bet than one stuck on an older version.

- Open your server's address in Safari, then use **Share > Add to Home
  Screen** so it opens full screen.
- Turn on **Guided Access** (Settings > Accessibility > Guided Access), open
  the page, and triple-click the side or Home button to lock the iPad to it.
- Set **Auto-Lock** to Never (Settings > Display & Brightness).
- The same battery advice applies: keep it plugged in and watch for swelling.

### A monitor or TV with a mini PC

For 21.5 inches and up, a computer monitor (or a TV) with a small PC behind it
is often simpler than a big Android frame.

- Any small PC or a Raspberry Pi can run Chromium in kiosk mode, for example
  `chromium --kiosk http://192.168.1.50:8090/`, and start it at login.
- A monitor plus a separate USB touch panel is fiddly; most of these setups are
  look-only, with parents using the phone page.
- TVs: prefer a plain monitor. TVs often run their own apps that phone home,
  and OLED TVs burn in.
- Use the screen's own power schedule or a smart plug to turn it off overnight.

### A Raspberry Pi touch screen

The Raspberry Pi Touch Display 2 (7 inch, 720 x 1280, portrait) on a separate
Pi running Chromium in kiosk mode would get the tall layout. It is small for a
kitchen; it suits a desk, nightstand or kids' room. Don't run the screen on the
same Pi as Home Assistant OS, which has no desktop to show it.
