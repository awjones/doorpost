# Several frames

Settings > Frames holds a profile for each frame in the house (`app/frames.py`):
name, look (Navy & gilt, Quiet night, Bright & playful), home screen (Today, Kids, Clock & today,
Chores), which screens show, which calendars and kids, whether parents can approve chores
there, and optional night hours of its own. Calendars, chores, screen time, lists and photos
are shared by every frame.

Looks come from folders in `themes/`, and each frame also picks how pictures show: **Original**
(as drawn) or **Match the look** (recolored and framed to fit its look). See [themes.md](themes.md),
which also explains how to make a look.

How a frame knows which one it is:

- Open `http://doorpost.local:8090/frame/<id>` on it (Settings shows each address), or
- a new frame in a house with several profiles asks "Hello, new frame" and lists them; picking
  one needs a parent PIN. The choice is remembered on the frame (`localStorage` `ff.frame`).
- The small gear in the top-right corner (parent PIN) switches it later, makes a new profile
  ("A new frame here"), reloads it, or shows its name for 10 seconds.
- A house with one profile (the kitchen) never asks.

Screens: the layout is 800 px on the short side and stretches the long side to the screen's
shape (16:10, 16:9...), tall or wide. Full-HD frames (1920x1080, like most 15.6" and 21.5"
frames) get photos made at 1920x1080 / 1080x1920 (`shape=wide-hd` / `tall-hd`).

Calendars are read every 5 minutes (`calendar_refresh_minutes`). Tapping the top-left corner of a frame has the Pi read them right away (at most once a minute) and the frame pull everything fresh.

## The Kids screen (a playroom frame)

Pick **Kids** as a frame's home screen (Settings > Frames, or "Starts on: Kids" when you make a
new frame from the gear menu). It is made for children who can't read yet, on a frame across
the room. It works on a tall frame (800 x 1280) and a wide one (1280 x 800).

What it shows:

- **A big header**: the day, a large clock, the weather, and a sun or moon for the time of day.
- **What's next today**: picture cards for the rest of today's events (a ball for practice, a
  fork and knife for dinner, a school for school), with the time in big numbers and a dot for each
  kid it's for. Bedtime is always the last card.
- **Each kid's chores**: a column per kid with their face (or number) and today's chores as big
  buttons with a picture. Tapping one marks it "waiting for a grown-up", the same as **I did it**
  on the Chores screen. A parent still approves it. Tap a kid's name to see all their chores.
- **Weekend screen time**: one of the four pictures, shown big, with how many sleeps until the
  weekend and what each kid added. Pick the picture per frame (Settings > Frames > Screen time picture).
- **Bedtime countdown**: for the last two hours before the frame's bedtime (Settings > Frames >
  Bedtime, 8:00 PM unless you change it) the header turns to evening colors and a card counts down,
  with pictures for pajamas, brushing teeth, a story and lights out.
- **Special days**: a countdown card ("2 sleeps until") before a special day, and on the day itself
  its picture takes over the top of the screen.

What it never shows: the server takes these out before anything reaches a kids' frame, so no screen
on it can show them by mistake (`app/kidsview.py`):

- event notes and addresses,
- minutes taken away (from one kid or from everyone) and the "taken away" line of the total,
- garage and door status, and calendar or server errors.

Parent tools stay behind the parent PIN (the **Grown-ups** button, if "Parents can approve chores
here" is on, and the gear in the corner).

In demo mode, `http://localhost:8090/frame/playroom` is a tall playroom frame on the Kids screen
(Bright & playful, bedtime 8:00 PM, night clock from 8:30 PM). Try it with
`FRAME_NOW=2026-10-15T19:40` to see the bedtime countdown, or `FRAME_NOW=2026-10-17T10:00` for a
special day. Add `?layout=wide` to see the wide layout in a normal browser window.
