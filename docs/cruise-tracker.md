# Cruise ship tracker

Follow a family member's cruise ship on the frame for the days of the trip. Kids
can see where the ship is right now, which port is next, the way it has sailed
so far, and a replay of the whole trip.

It's a module, off by default. Turn it on in **Settings > Modules**, then fill
in **Settings > Cruise ship tracker**. It only shows between the trip's dates,
so it can stay on all year and come back for the next trip.

## What the frame shows

- A **tab** named for the trip (for example "Where's Grandma?") and a map panel
  first on the Today screen, only between the dates you set.
- The **map**: the Caribbean, the Gulf of Mexico and the Bahamas, with
  latitude and longitude lines, the ports of call, the line the ship has sailed,
  a crosshair where it was last heard, and a dashed line for the likely way to
  the next port.
- **In port or at sea**, in words: "In port · Nassau · sails 5 PM", or "At sea,
  on the way to Falmouth".
- A **replay**: when the map opens, the crosshair sails every position saved so
  far, with the day and time on its tag. Sailing runs at about 2.5 seconds a day,
  and a long stay in port is cut to a short pause. Tap **Replay** to watch it
  again.
- **How far is Mom?**: a button on the map (named for whoever's on board). It
  zooms out until the house and the ship both show, draws a line between them
  with the miles as the crow flies, holds a few seconds, then zooms back in. Tap
  it again to come back sooner; tap **Replay** and it zooms back in and replays.
  The house is the weather location in **Settings > General**; without one, the
  button doesn't show. The land north of the Caribbean map is
  `web/img/north.svg` (see `scripts/make-caribbean-map.py`).

## Setting it up

1. **The trip**: a name for the frame, who's on board (how the map labels
   them), and the first and last day to show it.
2. **The ship**: its name and its page on [CruiseMapper](https://www.cruisemapper.com).
   Search for the ship there and paste the page's address, which looks like
   `https://www.cruisemapper.com/ships/<Ship-Name>-<number>`. The ship's MMSI
   (its 9-digit radio number, on the same page) is only needed for the backup
   source below.
3. **Ports of call**: one row per stop, with the day and the arrive and sail
   times from the cruise planner. Days without a row show as "At sea".

## Where the position comes from

Every large ship broadcasts its position over AIS radio. The tracker reads the
ship's public CruiseMapper page, which shows the latest AIS position and how old
it is. It checks about once an hour, day and night, at a slightly different
minute each time, and identifies itself as Doorpost when it asks. CruiseMapper's
robots.txt allows these pages. Only the ship's public position is fetched;
nothing about your family leaves the house.

Out at sea, the latest position can be a few hours old. The crosshair then stays
where the ship was last heard and says when ("Last heard 6:51 AM"). On a port day,
once the scheduled arrival has passed, it shows the ship in port. If nothing has
been heard for a day, the map estimates from the itinerary and says so.

**Backup:** if CruiseMapper can't be read and you've saved a free
[AISStream.io](https://aisstream.io) key (and the MMSI), the tracker listens to
AISStream instead. Its receivers are volunteers' stations on land, so it often
misses a ship, even in port.

**Repeats:** while the ship is out of range, CruiseMapper keeps showing the
same old report ("last reported 3 hours ago"). That isn't counted as a new
hearing, so "Last heard" keeps its real time.

**Probably about here:** when the ship hasn't been heard for a few hours, a
faint second crosshair labeled "probably about here" sails on from where it was
last heard. It follows the likely way to the next port, at the speed that gets
the ship there on time (6 to 22 knots). It stops short of the port. When a real
position comes in, the guess goes away.

## A phone on board

Out at sea, a phone on board often knows where the ship is long before any
tracking site does. Its GPS works with no signal, and the ship's Wi-Fi (even a
messaging-only plan) can send a text home. The tracker can use a phone's
position in three ways. Whichever position is newest wins, and the map says
where it came from ("Last heard 2:29 PM · Mom's phone").

**1. Texted home by a Shortcut.** This needs only iMessage on the phone. On the
traveler's iPhone, in the Shortcuts app:

1. New shortcut, named "Ship spot". Add **Get Current Location**.
2. Add **Text** and type `Ship spot: `, then insert **Current Location ›
   Latitude**, a comma and a space, and **Current Location › Longitude**.
3. Add **Send Message**: the Text, to the person at home. Turn off **Show When
   Run**.
4. Automation tab › **+** › **Time of Day**. Pick a time, then **Run
   Immediately** (and turn off **Notify When Run**), then pick the shortcut.
   iOS has no "every 30 minutes", so add one automation per time you want (for
   example every 2 hours from 6 AM to 10 PM). Tapping the shortcut sends one
   anytime.

At home, `mac/trip-phone-relay.py` reads the new "Ship spot" messages from that
phone in Messages on a Mac and passes them to the frame. Its settings file, the
Full Disk Access it needs, and a crontab line to run it every 5 minutes are at
the top of the script. It reads only messages from the addresses you list, and
keeps only the ones that start "Ship spot".

**2. From Home Assistant.** If the phone shows up in Home Assistant, as a
`device_tracker` from the Home Assistant app or from the iCloud (Find My)
integration, put its name in **Settings > Cruise ship tracker > The ship**. The
tracker looks at it every 5 minutes. The iCloud integration only sees the
devices of the Apple Account you sign in with and its Family Sharing group, not
people who share their location with you in Find My.

**3. By hand.** Under **The ship**, type a position you saw (on a tracking site,
or in a text) and when.

Positions can also be posted by any other tool: `POST /api/trip/fix` with
`{"lat": .., "lon": .., "at": "<ISO time with zone>"}` and the upload key in
`X-Upload-Token`.

## The likely way to the next port

The dashed line and the itinerary estimates follow open water through the
straits and passages cruise ships use (the Florida Straits, the Providence
Channels, the Crooked Island and Windward Passages, the Yucatán Channel and
more), and go around the land and the shallow banks. It's a best guess, not the
ship's actual plan. The routing lives in `app/searoute.py`.

## Keeping the route

Every position is saved with its time, and with when the ship arrived when it
sat in one place over several checks. Under **The ship**, two buttons download
the whole trip:

- **The route (GeoJSON)**: the route line, every position (time, speed,
  source) and the ports of call. It opens in Google Earth, QGIS, geojson.io and
  most mapping or animation tools.
- **The positions (CSV)**: the same positions as a spreadsheet.

The positions are in `data/trip-track.json`. Changing the ship sets the old line
aside as `data/trip-track-<mmsi>.json` instead of deleting it.

## Limits

- The map covers about 8° to 33° north and 58° to 98° west. A ship outside it
  is drawn at the edge.
- CruiseMapper isn't an official feed. If its page changes, checks fail with a
  message in Settings, and the map falls back to the itinerary until the reader
  is fixed (`parse_cruisemapper` in `app/trip.py`).
