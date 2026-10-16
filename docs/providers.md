# Apple, Google, or neither

Doorpost does not make you pick one company. Each feature works with an
Apple account, a Google account, or no account at all. This page shows, for
each feature, what each way needs.

The short version: anything Google offers through a web service runs on the
Doorpost server by itself. Some Apple data (Reminders, the Photos library)
has no web service at all, so it needs a Mac that stays on to pass it along.

| Feature | Apple way | Google way | No-account way | Extra computer needed | Status |
|---|---|---|---|---|---|
| **Lists** (groceries, to-dos) | Apple Reminders, through the small Doorpost Lists helper on a Mac ([lists.md](lists.md)) | Google Tasks, read by the server every minute ([lists.md](lists.md)) | Leave lists off; the Lists screen stays hidden | Apple: a Mac that stays on, because Apple has no web service for Reminders. Google: none | Apple: built. Google: built here |
| **Photos** (slideshow) | iCloud Shared Album with Public Website on (a link), or Favorites from Apple Photos ([photos.md](photos.md)) | Google Photos shared album (a link), or photos you pick by hand in Google Photos ([photos.md](photos.md)) | Upload in Settings, or drop files in the photos folder | Apple Favorites: a Mac with the Photos library, because Apple has no web service for Photos. Shared albums and Google picks: none | Shared albums, Favorites, uploads: built. Google picks for the slideshow: built here |
| **Profile photos** (the circle on chore tiles and birthday cards) | The Mac's photo sync finds the newest photo where only that person's face shows ([birthdays.md](birthdays.md)) | Pick a few photos of the person in Google Photos; the frame keeps the newest one with one face | Upload a photo in Settings > Family | Apple: a Mac with the Photos library. Google: none | Built |
| **Calendar** | See [calendars.md](calendars.md) | See [calendars.md](calendars.md) | See [calendars.md](calendars.md) | See [calendars.md](calendars.md) | See [calendars.md](calendars.md) |
| **Weather** | Apple WeatherKit | Google Weather API | The U.S. National Weather Service inside the U.S., and Open-Meteo everywhere else (both free, no key) ([weather.md](weather.md)) | None | No-account way: built, worldwide. Settings > General picks the source and the units (°F or °C, mph or km/h). Apple and Google: not built. WeatherKit needs a paid Apple Developer membership and signing keys, and Google's Weather API needs a Google Cloud billing account. Each family would have to pay or add billing just to get what the free services already give. |
| **House status** (garage door, locks) | Apple Home (HomeKit) | Google Home | Home Assistant on your home network | Home Assistant (often the same box that runs Doorpost) | Built through Home Assistant only. Apple Home has no web service at all; only Apple devices can talk to it. Google Home's developer tools are for phone apps, and its server API (Device Access) covers only Nest devices and has a sign-up fee. Home Assistant can read both Apple Home and Google Nest devices, so Doorpost reads Home Assistant |

## One Google sign-in for everything

Google Tasks, picking slideshow photos and picking profile photos all share one
Google sign-in. Set it up once, from any of these pages: Settings > Lists,
Settings > Photos or Settings > Family. The steps:

1. At console.cloud.google.com, make a project. Turn on the **Google Tasks API**
   and the **Photos Picker API** (only the ones you'll use).
2. Under **Google Auth Platform**, set it up as **External**. Add the scopes
   `tasks` and `photospicker.mediaitems.readonly`, and add your Google account
   as a test user (or publish the app).
3. Make an **OAuth client** of type **Web application**. Its redirect address is
   shown in Settings: `<your frame's https address>/api/google/callback`. Google
   only accepts https addresses here (or localhost), so this needs the frame's
   outside address, for example through Cloudflare Tunnel.
4. Paste the client ID and secret into Settings, save, and press **Connect Google**.

If you connected Google before one of these features existed, Settings shows an
**Allow Google Tasks** (or **Allow Google Photos**) button. It adds that part to
the same sign-in without undoing the rest.

The sign-in is kept on the server in `google.json` inside the data folder. The
client secret and the sign-in never go back to the browser. **Disconnect
Google** removes the sign-in at Google and on the server.

An app left in Google's "Testing" mode loses its sign-in after 7 days. To avoid
reconnecting every week, publish the app in Google Cloud. It can stay
unverified for your own family; Google then shows an "unverified app" warning
when you connect, which you can click past.

## Demo mode

Demo mode shows every choice with sample data and no accounts. Settings > Lists
has sample Apple Reminders lists and sample Google Tasks lists. Settings > Photos
shows the Google picker button, which explains that the demo doesn't connect to
Google.
