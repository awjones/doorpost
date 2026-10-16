# Setting up the frame

New to this? Start with the step-by-step [setup guide](setup-guide.md), which
explains each step below in plain words, and [hardware.md](hardware.md) for
which frames work.

The frame hardware work (rooting, removing the vendor app, installing the
kiosk) follows Wes Bos's repo, github.com/wesbos/photo-frame-dashboard. For a
BIUFRAME 10.1", start with `scripts/biuframe-setup.sh check`, which is
read-only. Follow the repo's rules: back up before any write, change one thing
at a time, and stop at the first mismatch.

That listing now often ships the Allwinner A33 PF1007L board instead
(`docs/pf1007l-start-here.md` in Wes's repo). To see which board you have,
run the read-only watcher, then plug the frame in:

```
python3 -I scripts/frame-watch.py
```

Keep the frame off Wi-Fi until its vendor app is disabled.

## 1. Point the kiosk at this server

In Wes's `dashboard/kiosk/` app, set:

```
DEFAULT_URL = "http://<server-ip>:8090/"
```

Give the server a fixed address with a DHCP reservation in your router so this
URL never changes.

The page lays itself out at 1280×800 and scales to fit any screen, so the
frame's exact resolution doesn't matter.

## 2. Lock the frame's network down

This step is what keeps family data from going to the frame's maker.

1. In your router, create an **IoT** network (its own VLAN or guest network) and put the frame's Wi-Fi on it.
2. Add firewall rules for that network:
   - **Allow** frame to `<server-ip>` TCP **8090**
   - **Allow** DNS/DHCP to the gateway
   - **Block** everything else, including the internet and the main LAN
3. Check it: on the frame, `http://<server-ip>:8090/` loads, and any public
   website does not.

The frame never needs the internet. Fonts, the family mark, photos and all data
come from the server.

## 3. Things the frame's browser can't do

The frame's WebView is Chrome 106. The frame page already avoids these, so
keep avoiding them when changing it:

- No 8-digit hex colors (`#RRGGBBAA`): use `rgba()`.
- No CSS nesting and no `:has()`.
- Keep it light: there's 1 GB of RAM. No big libraries, and data is polled
  every 30 seconds rather than kept on a live connection.

## 4. Screen on and off

- The page itself switches to the photo slideshow after 5 idle minutes, and
  to the dim night clock from 10 PM to 6 AM (`night` in `config/frame.yaml`).
- Turning the backlight fully off overnight, and waking on motion, is done on
  the frame (Wes's kiosk app with the motion sensor GPIO), not by this server.

## 5. Placement checklist

- A USB-C power outlet within reach
- Not in direct sun (the screen is only so bright)
- Kid height for tapping "I did it", adult height for reading the calendar.
  Most kitchens compromise at about chest height.
