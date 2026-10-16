# Birthday portraits

On a family birthday the frame shows the birthday picture with that person's photo in the gold oval and their
name on the banner. Code: `app/portraits.py` (store, face crop, title matching), `app/google_photos.py`,
`scripts/apple-portraits.py`; Settings › Family (one list for parents and kids: names, nicknames, birthdays, the name in
Apple Photos, one photo, and the kid settings). The same photo is a kid's avatar on the frame.

## Which days count

A **birthday date** on the Family page brings the card up by itself, with the age ("Happy 10th birthday, Child 1!"),
and it wins the day over other starred events (they show underneath). Feb 29 birthdays show on Feb 28 in other years.

Calendar events count too, when the title says it's one of ours:

"Child 1's birthday", "Child 1's 10th Birthday", "Child 1 Example's Birthday"
(Apple's Birthdays calendar), "Birthday: Child 1", "Happy birthday, Child 1", "Child 1 turns 10". Names come from
`people` (with their nicknames) and the kids. Anything else with "birthday" in it, like "Birthday party (Buddy)",
stays an ordinary event unless it's starred; starred, it gets the picture with whatever name is in the title.

## Where the photo comes from

1. **Apple Photos** (automatic). The Mac's Favorites sync (`scripts/sync-apple-favorites.sh`, step 5) runs
   `apple-portraits.py`: it asks the frame who needs a portrait (`/api/portraits/wanted`) and finds each person in
   Photos' People ("Name in Apple Photos" from Settings first, several allowed; then an exact name; then a first
   name, only when just one person in Photos has it). It uses the person's **cover photo** (Photos' key photo:
   open the person, choose a photo, Make Key Photo) and where their face is in it. Without a cover, it takes their
   newest photo where they're the only face, facing the camera and big enough for a portrait. It exports the
   original, shrinks it to 1600 px and posts it (`/api/portraits/upload`), only when the pick changed, so
   changing a cover in Photos changes the birthday picture at the next sync.
2. **Google Photos** (by hand). Google's Photos Picker API: Settings opens a picking session, you choose a few
   recent photos of the person and tap Done, and the frame keeps the newest one with a single face (OpenCV's
   face finder) and centers on it. Google doesn't give apps its face groups, so there is no automatic version.
   Setup: a Google Cloud project with the Photos Picker API on, an OAuth client of type Web application with the
   redirect address `<frame https address>/api/google/callback`, then paste the ID and secret in Settings and
   press Connect Google. The same sign-in also covers Google Tasks lists and picking slideshow photos (see
   [providers.md](providers.md)). An app left in "Testing" has to reconnect every 7 days.
3. **Upload** in Settings.

A portrait picked or uploaded by hand is never replaced by the Mac's. Remove it in Settings to go back to
automatic. Kids without a portrait use their face photo from Settings › Kids; anyone else gets a present in the oval.

Portraits are 640×800 JPEGs in `/data/portraits`, with `index.json` (source, date taken, Photos id).
