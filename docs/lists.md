# Lists (Apple Reminders or Google Tasks)

The frame shows lists you pick in **Settings > Lists**. They can come from
Apple Reminders, Google Tasks, both, or neither. It starts with any list called
Groceries, and any other list can be turned on there later. Items can be
checked off and added on the frame; they show up on everyone's phone within
about a minute.

| | Apple Reminders | Google Tasks |
|---|---|---|
| Needs | A Mac that stays on, with the Doorpost Lists helper | A Google sign-in (one-time setup, see [providers.md](providers.md)) |
| Extra computer | Yes, the Mac. Apple has no web service for Reminders | No. The Doorpost server talks to Google itself |
| How often | Every 30 seconds while the Mac is awake | Every minute, and right away after a change on the frame |
| Items added on the frame | Get the note "Added on the frame" in Reminders | Get the note "Added on the frame" in Google Tasks |

To use neither, leave every list unchecked. The Lists screen then stays hidden.

## Google Tasks

1. Set up the Google sign-in once (the steps are in Settings and in
   [providers.md](providers.md)). Turn on the **Google Tasks API** in your Google
   Cloud project.
2. In **Settings > Lists**, press **Connect Google** (or **Allow Google Tasks**
   if Google is already connected for photos).
3. Your task lists appear under **From Google Tasks**. Check the ones the frame
   should show, then **Save lists**. **Check now** reads Google right away.

How it behaves:

- The server reads the names of all your task lists, and the tasks on the
  lists you turned on. Turn off **Use Google Tasks** to stop it.
- Tasks checked off in the last two days show under "Done today". Older ones are
  left out.
- If Google can't be reached, the frame keeps the last list and holds anything
  added or checked off, then sends it when Google answers again.
- Subtasks show as ordinary items. Due dates aren't shown.
- Code: `app/google_tasks.py` (the Google side) and `app/lists.py` (what the
  frame shows). Google's list ids get a `gtasks:` prefix on the frame.

## Apple Reminders

Apple has no web service for Reminders, so a small helper on the Mac does the
passing back and forth:

- `mac/lists-helper/main.swift` is the helper. Every 30 seconds it sends the chosen lists to
  `POST /api/lists/sync` (with the same upload key as the Favorites sync, from the Keychain
  item "Doorpost upload token") and writes the frame's changes into Reminders.
- `mac/install-lists-helper.sh` builds it into `~/Applications/Doorpost Lists.app` and adds
  the LaunchAgent `org.doorpost.frame-lists`. Log: `~/Library/Logs/doorpost-lists.log`.
- The first run asks for Reminders permission (System Settings > Privacy & Security > Reminders).
  Rebuilding changes the app's signature, so macOS asks again; only rebuild when the Swift changes.

How it behaves:

- If the Mac is asleep or off, the frame keeps the last list and holds anything added or
  checked off, then catches up when the Mac is back. Settings says so after 10 minutes.
- If the same item changes on the frame and in Reminders before they sync, the newer change wins.

## Both

- Each list remembers where it came from. The Mac's check-in never touches
  Google lists, and the Google read never touches Reminders lists.
- "Store sections" (Produce, Dairy & eggs, Bakery...) are worked out from each item's name
  (`app/lists.py`). Neither Reminders nor Google Tasks shares grocery sections with
  other apps, and neither says who added an item.
