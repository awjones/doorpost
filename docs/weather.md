# Weather

The frame shows the weather now, the next few hours, three days, and a note
when rain is coming. It gets this from one of two free services. Neither
needs an account or a key.

| Source | Where it works | Notes |
|---|---|---|
| U.S. National Weather Service (weather.gov) | The 50 states and U.S. territories | Asks for a contact in the `WEATHER_USER_AGENT` setting in `.env`. |
| Open-Meteo (open-meteo.com) | Anywhere in the world | Free for non-commercial use, which a family frame is. The data is CC BY 4.0, so we credit it in Settings and here. |

## Picking the source

Settings > General has three choices under **Weather from**:

- **Automatic** (the default). Inside the U.S. the frame uses the National
  Weather Service. Anywhere else it uses Open-Meteo. If the U.S. service is
  down or says it has no forecast for your spot, the frame uses Open-Meteo
  instead, so the weather keeps showing.
- **U.S. National Weather Service**: only that service. If it fails, the frame
  keeps the last reading and Settings > Overview shows the error.
- **Open-Meteo**: only Open-Meteo, even inside the U.S.

The frame decides "inside the U.S." from your time zone and your latitude and
longitude, both in Settings > General. Set both for your house.

## Units

**Temperature** is Fahrenheit or Celsius. **Wind** is mph or km/h. Automatic
means °F and mph in the U.S., and °C and km/h everywhere else. The frame shows
the wind on the Weather panel, with its unit.

## How often it asks

The frame asks for new weather every 15 minutes, about 100 times a day.
Open-Meteo's free limit is 10,000 a day, so one home is far under it. If a
request fails, the frame keeps the last good reading and tries again in about
five minutes.

## Demo mode

Demo mode shows sample weather and never goes online. It still follows the
units you pick, so you can see the frame in Celsius.

## Credit

Weather data outside the U.S. by [Open-Meteo.com](https://open-meteo.com/),
under the Creative Commons Attribution 4.0 license (CC BY 4.0).

## What the frame shows

Two more choices in Settings > General:

- **Show °F or °C on the frame.** No (the default) shows `62°`. Yes shows `62°F` or `17°C` on the big temperatures (Today, the Weather panel, the clock and the kids' screen). Highs and lows stay short (`H 66°`).
- **Show wind.** On the Weather panel (the default), on the Weather panel and the top of Today, or Off.

To switch between Fahrenheit and Celsius, use **Temperature** in the same card.
