# Modules: turn parts of the frame on and off

Doorpost has a small core that is always on, and modules you can turn on or
off in **Settings > Modules**. Turn on only what your family uses. A module
that is off disappears from every frame, from the phone page and from
Settings.

![A small core surrounded by modules that turn on or off, plus art packs](img/modules.svg)

## What is always on

- The frame itself: its screens, the clock, the night clock and the gear menu.
- The calendar (Today, the week, the next 7 days and the month).
- Settings, the family list and the parent PINs.

## The modules

| Module | What it does | What it needs |
|---|---|---|
| **Weather** | Now, today and the next 3 days on the Today screen. | Your town or ZIP code. No account. |
| **Chores** | Kids tap "I did it"; a parent approves on the frame or a phone. | Nothing extra. |
| **Screen time** | Approved chores fill a weekend pool of minutes. | Chores turned on. |
| **Photos** | A slideshow when the frame sits idle. | Photos you upload, a shared album, or a photos folder. |
| **Profile photos** | Faces on the chore buttons and birthday cards, instead of a colored initial. | A photo of each person. |
| **Lists** | Groceries and to-dos you can check off or add to on the frame. | A Mac for Apple Reminders, or Google Tasks. |
| **Home Assistant** | Garage, doors and locks in the line at the bottom of the frame. | Home Assistant on your home network. |
| **Special days** | Holidays and starred events take over their day with a picture and a countdown. | An art pack (Holidays comes installed). |
| **Lord's Day pictures** | A picture, a verse and a short note every Sunday. | The Faith art pack, and Special days on. Only listed when the Faith pack is installed. |
| **Sign in from anywhere** | The parent page and Settings away from home, through Cloudflare Access. | A Cloudflare account and your own web address. |
| **Multiple frames** | Give each screen in the house its own look and screens. | A second frame. |
| **Kids view** | A picture-first home screen for a playroom frame. | Nothing extra. Best on its own frame. |

Each card in Settings > Modules shows a short status line, such as how many
photos are in the slideshow or "Not set up yet".

## Turning a module off

When you turn a module off:

- Its tabs, panels and pieces of the Today screen leave every frame. A kids
  frame with Chores off just shows no chore buttons.
- Its Settings page leaves the menu.
- Its addresses stop answering. A Mac helper that sends Reminders or photos
  gets "not found" until the module is on again.
- Its background work stops. For example, with Photos off the server stops
  looking for new photos.
- **Needs attention** on the Overview page stops asking about it.

Nothing is deleted. Your chores, lists, photos, logs and settings stay saved.
Turn the module back on and everything comes back as it was.

## Modules that need another module

Screen time needs Chores. Lord's Day pictures need Special days.

- Turning Screen time on also turns Chores on.
- Turning Chores off rests Screen time too. Its switch stays on and its card
  says "Waiting for Chores". Turn Chores back on and Screen time comes back.

## New setups and older setups

- A new setup starts with Weather, Chores, Screen time, Photos, Profile
  photos, Special days and Lord's Day pictures on. Lists, Home Assistant, Sign
  in from anywhere, Multiple frames and Kids view start off.
- A setup from before modules existed keeps what it already uses: Lists is on
  if lists are picked, Home Assistant is on if it is turned on there, Multiple
  frames is on if there is more than one frame, and so on.
- Demo mode turns everything on.

## Multiple frames and Kids view

With **Multiple frames** off, every frame shows the first frame in Settings >
Frames. Your other frames stay saved. Turn the module back on to use them
again. The "A new frame here" button on the frame's gear menu only shows when
the module is on.

With **Kids view** off, a frame whose home screen was Kids shows Today
instead. Its Kids setting stays saved for when you turn the module back on.

## For developers

The list of modules lives in `app/modules.py`, one small entry per module:
its id, name, description, what it needs, whether it starts on, which modules
it needs, its frame screens and Today pieces, its Settings pages, and the
addresses it owns. The settings store keeps `modules: {id: true or false}`.

- Every request passes a check (`module_guard` in `app/main.py`) that answers
  404 when the address belongs to a module that is off. New routes can also
  use `Depends(enabled("id"))`.
- `/api/frame` includes `modules`, the list that is on. The frame page, the
  kids view and the phone page read it and leave out what is off.
- `tests/test_modules.py` turns each module off and checks the frame's data,
  its addresses and the Settings menu, then turns it back on.
