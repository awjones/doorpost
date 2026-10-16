# Storage

Settings > Overview has a **Storage** card. It shows how full the server's disk
is and what Doorpost keeps on it. Settings > Frames shows what each frame
reports about itself.

## What uses space

Everything lives on the server, in two folders:

- **The data folder** (`data/`, or `/data` in the Home Assistant add-on).
- **The photos folder** (`photos/`, or `/media/family_frame` in the add-on).
  When this is on a different disk, the card shows that disk too.

| Line on the card | What it is |
|---|---|
| Photos | Your slideshow photos: uploads and the Mac's Favorites sync. Photos from a Google or iCloud shared album are not kept here. |
| Prepared photos | Each photo cropped to the frame's size, so the frame never has to resize anything. |
| Special-day photos | Pictures uploaded in Settings > Special days. |
| Profile photos | Kids' faces and birthday portraits. |
| Art packs | Downloaded special-day picture packs. |
| Database and settings | Chores, screen time, focal points and your settings. Small. |
| Calendar copies and logs | Recent copies of your calendars. Small, and read again every few minutes. |

Folder sizes are counted in the background and kept for five minutes, so a big
photo library doesn't slow down the Settings page.

## Warnings

A disk shows amber under **Needs attention** when it has less than 15% or
less than 2 GB free. It turns red under 5% or 500 MB. A full disk can stop
Doorpost from saving chores and settings, so act on amber.

## How to free space

1. **Clear prepared photos.** The button is on the Storage card. It removes
   only the cropped copies. Your photos, focal points and settings are not
   touched. The server makes each copy again the next time it is shown, so
   the slideshow may be slower for a while.
2. **Remove photos you don't need** in Settings > Photos, or delete them from
   the photos folder.
3. **Move the photos to a bigger disk.** Set `FRAME_PHOTOS_DIR` to a folder on
   a USB drive or a network share, then copy the photos there. In the add-on,
   the photos folder is Home Assistant's media folder, which can live on a
   bigger drive (Settings > System > Storage in Home Assistant).
4. **Home Assistant backups** include the add-on's data folder. Old backups
   can fill the disk faster than Doorpost does.

## Why the frame stores almost nothing

The frame is a screen. It runs one web page that asks the server for what to
show. Calendar addresses, logins, PINs and your photo library stay on the
server. The page keeps only which frame profile it is. If a frame is lost or
replaced, nothing private is on it.

Each frame sends a small report every five minutes: screen size, browser
version, how much the page itself stores, memory, and how long the last photo
took to load. Settings > Frames shows it under **This frame's device**.

A web page cannot see the frame's own disk. So the frame's free space is not
shown. A kiosk app could add it later: if the page finds
`window.FamilyFrameKiosk.deviceStorage()` returning
`{"total": bytes, "free": bytes}`, it sends that as `device_storage`, and the
warnings cover the frame too. Page storage is only reported when the frame
uses an https address, because browsers share it only on secure pages.
