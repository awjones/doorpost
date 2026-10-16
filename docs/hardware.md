# Hardware: picture frames

Doorpost needs a screen that can run one full-screen web page and stay on
all day. This page covers cheap Android picture frames, which is what it was
built for. For other screens (tablets, old iPads, monitors and TVs) see
[screens.md](screens.md).

The steps for taking over a frame are in [setup-guide.md](setup-guide.md#5-take-over-the-frame)
and in Wes Bos's repo,
[github.com/wesbos/photo-frame-dashboard](https://github.com/wesbos/photo-frame-dashboard).

## What has been tested

| Frame | Board inside | Status |
|---|---|---|
| 10.1 inch Android frame, sold as BIUFRAME, model PF1007L | Allwinner A33, Android 6.0.1, 1 GB RAM, 1280 x 800 | **Tested with Doorpost.** Runs it every day after the takeover in the setup guide. |
| 10.1 inch BIUFRAME, model Synergy 10X1 | Rockchip RK3126, Android 6.0.1, 1280 x 800 | Taken over in Wes Bos's repo, with a one-step setup script. **Not tested with Doorpost**, but it gets the same web engine (WebView 106), so it should work. |
| 15 inch Skylight calendar | Rockchip RK3566, Android 12 | Notes in Wes's repo. His unit's Wi-Fi was dead and needed a USB Wi-Fi adapter. **Not tested with Doorpost.** |

Everything else is untested. If you try another frame, notes in an issue help
the next person.

## Brand names are not a hardware check

Frames sold under the same name, in the same box, can have different boards
inside. The listing Wes used now often ships the Allwinner A33 PF1007L board
instead of the Rockchip one. The steps are different for each, and running the
wrong board's script can leave a frame that won't start.

Always identify the board before you change anything: read Settings > About,
then connect a computer and follow the "Identify" step in Wes's repo. This repo
has a read-only helper too:

```
python3 -I scripts/frame-watch.py
```

## What to look for when buying

- **Android version, and whether the web engine can be updated.** Family
  Frame needs a web engine (Android System WebView) at version 106 or later.
  Old frames ship with something much older (ours had 44). On Android 6 it can
  be replaced with root access, as in the guide. If a frame can't be rooted
  and its WebView can't be updated, it won't run Doorpost.
- **1 GB of memory or more.** Doorpost is kept light for 1 GB frames.
  Less than that is untested and likely to struggle.
- **A real USB data port.** Setup needs a computer to talk to the frame over
  USB (ADB). Some frames have a port for power only. Some boards need a USB-A
  to USB-C cable, and get no power or data from USB-C to USB-C.
- **Root or USB debugging already on**, if you can find out before buying.
  That makes the takeover much shorter.
- **Resolution.** 1280 x 800 is the tested size. 1920 x 1080 should work and
  gets sharper photos. See [screens.md](screens.md).
- **A touch screen.** Kids claim chores and parents approve them by tapping.
  Without touch, the frame can still show the calendar and photos, and parents
  can use the phone page.
- **Power.** A plug-in adapter, not a battery. It will be on all day.
- **Mounting.** Wall mount holes or a stand that suits where it will hang.

## Cautions

- **These frames can't be made secure.** The one in Wes's guide had its last
  security update in 2016, and any app on it could get full control without
  asking. Treat the frame as a screen only: no Google, Apple or bank logins on
  it, and keep it on its own network
  ([setup-guide.md](setup-guide.md#4-set-up-your-home-network)).
- **Vendor apps phone home.** The maker's apps talk to servers overseas, and
  on our board one of them could give the maker's server full control of the
  frame. Keep the frame off Wi-Fi until those apps are disabled.
- **Back up before you change anything**, and check the backup. Wes's guide
  shows how for each board.
- **One change at a time**, with the undo written down first. Stop at the
  first thing that doesn't match the guide.
- **Updates from the maker can undo your work.** Once the vendor's updater is
  disabled and the frame can reach only your server, it can't download them.

## After the takeover

What the frame should have when you are done:

- A plain launcher (so you can reach Android settings if you need to).
- Android System WebView 106.
- The Doorpost kiosk app as the Home screen, so it opens after a power cut.
  Hold two fingers still for 1.5 seconds for its menu.
- System animations off.
- The vendor apps and updater disabled.
- Wi-Fi joined to the frame's own network, which reaches only your server.
