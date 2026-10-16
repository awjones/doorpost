# Setup guide: start to finish

This guide is for someone who has never run a home server. It is long because
it spells out every step, not because the steps are hard. You can do most of it
with an AI assistant (ChatGPT, Claude, Gemini or similar) sitting beside you.
The last section shows how.

Plan on an evening for the server and the network, and a second evening for
the picture frame.

Other guides:

- [hardware.md](hardware.md): which picture frames work and what to watch for.
- [screens.md](screens.md): screen sizes, wide or tall, and other screens you can use.
- [frame-setup.md](frame-setup.md): the frame steps in short form.

## 1. Get the parts

![The kit: picture frame, a small always-on computer or a Home Assistant box, router, a parent's phone, an optional Mac and cables. Below, six numbered steps show how information moves.](img/parts-and-flow.svg)

You need three things:

1. **A picture frame.** A cheap 10.1 inch Android frame is what this was built
   and tested on. Read [hardware.md](hardware.md) before you buy one, because
   frames that look the same can have different insides.
2. **The brain.** One small computer that stays on all the time. Pick one:
   - A **Raspberry Pi 4 or 5** with 2 GB of memory or more, its own power
     supply, and a 32 GB or larger microSD card (an SSD lasts longer).
   - The **Home Assistant** box you already have, if you have one. Family
     Frame runs on it as an add-on.
   - Any other computer that never sleeps, such as an old laptop or a Mac mini.
3. **Your home Wi-Fi router.** It works best if it can make a separate Wi-Fi
   network and give a device a fixed address. Most routers sold in the last
   few years can.

Nice to have:

- **A phone for each parent.** The phone page is a web page, so there is no app
  to install.
- **A Mac**, only if you want Apple Photos Favorites or Apple Reminders lists
  on the frame.
- **Cables.** A USB data cable to connect a computer to the frame during setup.
  Some frames need a USB-A to USB-C cable; a USB-C to USB-C cable gave our
  frame no power and no data. The cable in the box is often power only. A cable
  that already syncs a phone is a safe bet.

### How the parts talk to each other

Follow the numbers in the picture above:

1. The brain reads your calendars, the weather and any shared photo albums
   from the internet.
2. It crops the photos to fit and builds the finished page.
3. The frame asks the brain for that page every 30 seconds. That is all the
   frame does.
4. When a child taps **I did it** on the frame, the tap goes to the brain.
5. A parent approves the chore, on the frame with a PIN or from a phone.
6. If you use a Mac, it sends Apple Photos Favorites and Reminders lists to
   the brain on a schedule.

Nothing private lives on the frame. If it breaks or is stolen, no passwords or
calendar addresses go with it.

## 2. Try it in demo mode first

Before you buy anything, you can run Doorpost on a laptop with made-up data.
Follow "Try it in demo mode" in the [README](../README.md#try-it-in-demo-mode).
It takes about five minutes and shows you every screen.

## 3. Install it on the brain

Follow "Install options" in the [README](../README.md#install-options):

- **Option 1** if you run Home Assistant. Settings then live in the Home
  Assistant sidebar.
- **Option 2** for a Raspberry Pi or any other always-on computer.

When it is running, open `http://<brain address>:8090/admin` from a laptop on
your home Wi-Fi and set it up: your location, the family members, calendars
(each calendar's private iCal address), chores and a PIN for each parent.

## 4. Set up your home network

![Your router runs the home Wi-Fi, with the brain at a fixed address, and a separate frame Wi-Fi that can reach only the brain on port 8090. Four steps, a check, and three prompts to ask an AI assistant.](img/network-setup.svg)

These two router settings keep the frame useful and private. The example
address below is `192.168.1.50`. Yours will be different; your router shows it.

1. **Give the brain a fixed address.** In your router's app or web page, find
   the brain in the list of connected devices and choose "reserve address",
   "fixed IP" or "DHCP reservation". The name differs by brand. Now the
   brain's address never changes, so the frame can always find it.
2. **Make a separate Wi-Fi network for the frame.** This may be called a VLAN,
   an IoT network or a guest network. Give it its own name and password.
3. **Allow one door.** Add rules so devices on the frame network can reach
   only the brain's address on TCP port 8090 (plus DNS and DHCP, which every
   device needs to join a network). Block everything else, including the
   internet and your main network. Some guest networks can't make an
   exception like this. If yours can't, ask your AI assistant what your
   router can do instead.
4. **Away from home (optional).** If you want the phone page when you are out,
   use a tunnel with a sign-in, such as Cloudflare Tunnel with Cloudflare
   Access. See "Sign-in from outside the house" in the README. Never open port
   8090 to the whole internet.

**Check it.** Once the frame is on its Wi-Fi, `http://192.168.1.50:8090/`
should load on it and any public website should not.

The frame never needs the internet. Fonts, pictures and all data come from the
brain.

## 5. Take over the frame

![Credit to Wes Bos's repo and video, the two board types it covers, then seven steps we used to take over our frame, with a warning to stop if anything does not match.](img/inspiration-and-takeover.svg)

Doorpost started from Wes Bos's
[photo-frame-dashboard](https://github.com/wesbos/photo-frame-dashboard) and
his video, [https://www.youtube.com/watch?v=ZLycoUMltNI](https://www.youtube.com/watch?v=ZLycoUMltNI).
His repo is the guide for this part. It is written so an AI assistant can
follow it with you, and it covers two board types:

- **Rockchip "BIUFRAME"** (RK3126, Android 6.0.1). USB debugging is on out
  of the box and one setup script does the work.
- **Allwinner A33 "PF1007L"** (Android 6.0.1). This board now often ships
  inside the same-looking frame. It usually needs more steps.

Here is what we did on our frame, a PF1007L. Every step that changed the frame
waited for a yes, one change at a time, with the way to undo it written down
first.

1. **Identify the board.** Read Settings > About on the frame and connect it
   to a computer with a USB data cable. Wes's repo and `scripts/frame-watch.py`
   here (read-only) tell you which board you have. Nothing changes yet.
2. **Back it up.** Copy the frame's storage to a computer and check the copy
   before changing anything.
3. **Turn off the vendor apps, and keep the frame offline until then.** The
   maker's app on our board could give the maker's server a root shell (full
   control of the frame) as soon as it was online. So the frame stayed off
   Wi-Fi until those apps were disabled.
4. **Update the web engine.** Android System WebView went from version 44 to
   106. Doorpost needs 106. The old copy was kept so it can be put back.
5. **Install the kiosk.** A plain launcher, plus the Doorpost kiosk app
   (in `kiosk/`, built from Wes's) set as the Home screen, so it opens by
   itself after a power cut. Turn system animations off so screens change
   cleanly.
6. **Point it at your server.** Set the kiosk's address to your brain, such as
   `http://192.168.1.50:8090/`, before you build it (see `kiosk/README.md`).
7. **Lock the network.** Join the frame to its own Wi-Fi from step 4 above.
   Now it can go online.

Ours already had root ADB (full USB access) turned on. Many PF1007L frames
don't, and need extra steps from Wes's guide, sometimes with a spare microSD
card.

**Stop if anything doesn't match.** A different model name, chip, size or
checksum means you have a different frame than the guide expects. Stop and ask
in Wes's repo rather than guessing. A wrong write can leave a frame that won't
start.

## 6. Photos and focal points

Add photos in **Settings > Photos**: upload them, drop them in a folder, or link
a Google Photos or iCloud shared album. A Mac can send Apple Photos Favorites.
Details are in [photos.md](photos.md).

Wide and tall frames cut off different parts of a photo. Tap a photo in
Settings > Photos to mark what matters, and every frame keeps that part in
view. [photos.md](photos.md#focal-points-wide-and-tall-frames) shows how.

## 7. Hang it

- Near a power outlet, out of direct sun, away from the stove.
- About chest height is a good middle ground between kids tapping chores and
  adults reading the calendar.
- [screens.md](screens.md) covers viewing distance, night brightness and heat.

## Using an AI assistant to help

An AI assistant is a good partner for this project. It can explain each step,
translate it to your router's screens, and read error messages with you. Some
tips:

- **Give it the source.** Paste the link to this repo and to Wes's repo, or
  paste the section you are on. Ask it to follow the guide, not to improvise.
- **Tell it what you have.** Your router's brand and model, your computer
  (Mac, Windows or Linux), and what the frame's Settings > About screen says.
- **Ask it to explain before you run anything.** "What does this command do,
  and does it change anything?" is always a fair question.
- **Never paste secrets into a chat.** That means passwords, calendar secret
  addresses, tokens and PINs. Type those straight into Settings yourself.
- **For the frame, keep Wes's rules.** Back up first. One change at a time.
  Stop at the first thing that doesn't match.
- **If an assistant can run commands on your computer** (some can), have it
  ask before every command that changes the frame, and say no if you are not
  sure.

### Prompts you can copy

Fill in the blanks. Swap `192.168.1.50` for your brain's address.

Getting started:

```
I want to set up Doorpost, a self-hosted family dashboard for a picture
frame. Please read the README and docs/setup-guide.md from the repo and walk me
through it one step at a time. I have a ___ (Raspberry Pi 4 / Home Assistant
box / old laptop) and a ___ router. Ask me before assuming anything.
```

Installing on Home Assistant:

```
I run Home Assistant on a ___. Walk me through installing Doorpost as a
local add-on using "Option 1" in its README. Explain the Samba share step in
plain words. Don't ask me to paste any passwords into this chat.
```

The router:

```
My router is a ___. How do I make a separate Wi-Fi network that can only
reach 192.168.1.50 port 8090?
```

```
How do I give the computer called ___ a fixed address (a DHCP reservation) on
my ___ router?
```

```
How can I check that a device on my frame Wi-Fi reaches 192.168.1.50:8090 and
nothing else?
```

The frame:

```
I have a cheap Android picture frame. Settings > About says: ___. Using Wes
Bos's guide at github.com/wesbos/photo-frame-dashboard, help me find out which
board it has. Only run read-only checks for now, and stop if anything doesn't
match the guide.
```

```
Before we change anything on the frame, walk me through making a verified
backup of it, the way Wes Bos's guide describes for my board.
```

When something breaks:

```
Doorpost shows this error: ___. Here is what I did just before: ___.
What does it mean, and what is the smallest safe thing to try first?
```
