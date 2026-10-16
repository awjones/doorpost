# Doorpost

The dashboard for the kitchen picture frame: today's schedule, the family
calendar, chores that earn weekend screen time, and a photo slideshow.

## Where things are

- **Settings**: the *Doorpost* item in the Home Assistant sidebar (admins
  only). Calendars, photos, kids (with face photos), chores, screen time,
  house status, display, and each parent's PIN are all set there.
- **The frame**: point the frame's kiosk browser at
  `http://<this Home Assistant's address>:8090/`
- **Parent phone page**: `http://<address>:8090/parent` (signs in with your own PIN):
  screen time, chores and the log.
- **Photos folder**: `/media/family_frame`. Drop photos in with the Samba
  share (`media` share, `family_frame` folder), with Home Assistant's Media
  browser, or with the Upload box in Settings.

## First-time setup

1. Open **Doorpost** from the sidebar.
2. **Parent PINs**: one for each parent, so the screen time log says who.
3. **Calendars**: paste each Google calendar's *Secret address in iCal format*,
   then press **Check**.
4. **Kids**: add a face photo for each kid.
5. **Display & clock**: set the house's latitude and longitude for the weather.
6. **House status**: tick the garage door and front door lock.

## Network

Only the frame needs port 8090. If your router supports it, put the frame on
its own IoT network and allow it to reach exactly this machine on TCP 8090,
nothing else.

## Backups

Home Assistant backups include this add-on's settings, which hold the
calendar addresses, plus the chore history and the screen time log. Treat
backup files as private.
