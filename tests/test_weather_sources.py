"""Weather sources: NWS in the U.S., Open-Meteo elsewhere, the fallback, and units.
Every call goes through a mocked httpx transport, so nothing touches the network."""
from datetime import datetime

import httpx
import pytest

from app import open_meteo
from app.weather import WeatherService, convert, in_us

NOW = datetime(2026, 10, 15, 16, 12)
US = (39.74, -104.99, "America/Denver")
TORONTO = (43.65, -79.38, "America/Toronto")
LONDON = (51.51, -0.13, "Europe/London")


def _om_payload(temp_unit="celsius"):
    hours = [f"2026-10-15T{h:02d}:00" for h in range(24)] + [f"2026-10-16T{h:02d}:00" for h in range(24)]
    c = [12.0 + (i % 6) * 0.5 for i in range(len(hours))]
    if temp_unit == "fahrenheit":
        c = [x * 9 / 5 + 32 for x in c]
    pop = [10] * len(hours)
    code = [2] * len(hours)
    for i in (20, 21, 22):          # rain this evening
        pop[i], code[i] = 80, 61
    return {
        "current": {"time": "2026-10-15T16:00", "temperature_2m": 13.4 if temp_unit == "celsius" else 56.1,
                    "weather_code": 3, "is_day": 1, "wind_speed_10m": 14.2},
        "hourly": {"time": hours, "temperature_2m": c, "precipitation_probability": pop,
                   "weather_code": code, "is_day": [1 if 7 <= int(t[11:13]) < 19 else 0 for t in hours]},
        "daily": {"time": ["2026-10-15", "2026-10-16", "2026-10-17", "2026-10-18"],
                  "weather_code": [61, 0, 95, 3], "temperature_2m_max": [15.2, 18.0, 17.4, 14.0],
                  "temperature_2m_min": [8.6, 9.1, 10.0, 7.0], "precipitation_probability_max": [80, 0, 60, 10]},
    }


NWS_POINTS = {"properties": {"forecast": "https://api.weather.gov/gridpoints/IND/1,1/forecast",
                             "forecastHourly": "https://api.weather.gov/gridpoints/IND/1,1/forecast/hourly",
                             "observationStations": "https://api.weather.gov/gridpoints/IND/1,1/stations"}}
NWS_FORECAST = {"properties": {"periods": [
    {"startTime": "2026-10-15T06:00:00-04:00", "isDaytime": True, "temperature": 68, "shortForecast": "Partly Sunny"},
    {"startTime": "2026-10-15T18:00:00-04:00", "isDaytime": False, "temperature": 50, "shortForecast": "Mostly Clear"},
    {"startTime": "2026-10-16T06:00:00-04:00", "isDaytime": True, "temperature": 71, "shortForecast": "Sunny"},
]}}
NWS_HOURLY = {"properties": {"periods": [
    {"startTime": "2026-10-15T16:00:00-04:00", "temperature": 63, "isDaytime": True, "shortForecast": "Partly Sunny",
     "windSpeed": "5 to 10 mph", "probabilityOfPrecipitation": {"value": 10}},
    {"startTime": "2026-10-15T17:00:00-04:00", "temperature": 61, "isDaytime": True, "shortForecast": "Partly Sunny",
     "windSpeed": "10 mph", "probabilityOfPrecipitation": {"value": 20}},
]}}


class Fake:
    """A mocked weather.gov and Open-Meteo. `nws` is "ok", "down" (500s) or "outside" (404 for the point)."""

    def __init__(self, nws="ok"):
        self.nws = nws
        self.calls = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request.url)
        host, path = request.url.host, request.url.path
        if host == "api.open-meteo.com":
            return httpx.Response(200, json=_om_payload(request.url.params["temperature_unit"]))
        if host == "api.weather.gov":
            if self.nws == "down":
                return httpx.Response(500, json={"detail": "busy"})
            if path.startswith("/points/"):
                if self.nws == "outside":
                    return httpx.Response(404, json={"title": "Data Unavailable For Requested Point"})
                return httpx.Response(200, json=NWS_POINTS)
            if path.endswith("/forecast"):
                return httpx.Response(200, json=NWS_FORECAST)
            if path.endswith("/forecast/hourly"):
                return httpx.Response(200, json=NWS_HOURLY)
            if path.endswith("/stations"):
                return httpx.Response(200, json={"features": []})
        return httpx.Response(404)

    def hosts(self):
        return [u.host for u in self.calls]


def _svc(place, fake, **config):
    lat, lon, tz = place
    return WeatherService(lat, lon, "test", http=httpx.Client(transport=httpx.MockTransport(fake)),
                          config=config, timezone=tz)


def test_us_location_uses_nws_in_fahrenheit():
    fake = Fake()
    s = _svc(US, fake)
    w = s.get(NOW)
    assert set(fake.hosts()) == {"api.weather.gov"}
    assert s.label() == "National Weather Service"
    assert w["temp"] == 63 and w["high"] == 68 and w["low"] == 50
    assert w["units"] == {"temp": "F", "wind": "mph", "wind_label": "mph"} and w["wind"] == 10
    assert w["days"][0]["name"] == "Today"


def test_london_uses_open_meteo_in_celsius():
    fake = Fake()
    s = _svc(LONDON, fake)
    w = s.get(NOW)
    assert fake.hosts() == ["api.open-meteo.com"]       # never asks the U.S. service
    assert fake.calls[0].params["temperature_unit"] == "celsius"
    assert fake.calls[0].params["wind_speed_unit"] == "kmh"
    assert fake.calls[0].params["timezone"] == "Europe/London"
    assert w["source"] == "open-meteo" and w["units"]["temp"] == "C" and w["units"]["wind_label"] == "km/h"
    assert (w["temp"], w["text"], w["icon"], w["wind"]) == (13, "Cloudy", "cloud", 14)
    assert (w["high"], w["low"]) == (15, 9)
    assert [d["name"] for d in w["days"]] == ["Today", "Friday", "Saturday"]
    assert [d["icon"] for d in w["days"]] == ["rain", "sun", "storm"]
    assert w["hours"][0]["label"] == "Now" and w["hours"][1]["label"] == "5 PM" and len(w["hours"]) == 6
    assert w["rain"] == 80 and w["phrase"] == "Rain likely (80%)"
    assert w["note"] == "Rain likely 8 PM – 11 PM (80%)"


def test_toronto_open_meteo_even_though_inside_the_us_box():
    fake = Fake()
    w = _svc(TORONTO, fake).get(NOW)
    assert fake.hosts() == ["api.open-meteo.com"] and w["units"]["temp"] == "C"


def test_nws_down_falls_back_to_open_meteo_and_keeps_fahrenheit():
    fake = Fake(nws="down")
    s = _svc(US, fake)
    w = s.get(NOW)
    assert fake.hosts() == ["api.weather.gov", "api.open-meteo.com"]
    assert s.error is None and s.label() == "Open-Meteo"
    assert w["units"]["temp"] == "F" and fake.calls[-1].params["temperature_unit"] == "fahrenheit"
    assert w["temp"] == 56


def test_nws_outside_coverage_is_remembered():
    """A U.S. time zone but a point NWS doesn't cover: switch to Open-Meteo and metric for good."""
    fake = Fake(nws="outside")
    s = _svc((45.0, -75.0, "America/New_York"), fake)
    w = s.get(NOW)
    assert w["source"] == "open-meteo" and w["units"]["temp"] == "C" and not s.is_us()
    s.fetched_at = None
    s.get(NOW)
    assert fake.hosts()[-1] == "api.open-meteo.com" and fake.hosts().count("api.weather.gov") == 1


def test_nws_only_reports_the_error():
    fake = Fake(nws="down")
    s = _svc(US, fake, source="nws")
    assert s.get(NOW) is None and "500" in s.error
    assert "api.open-meteo.com" not in fake.hosts()


def test_open_meteo_chosen_in_the_us():
    fake = Fake()
    w = _svc(US, fake, source="open-meteo").get(NOW)
    assert fake.hosts() == ["api.open-meteo.com"] and w["units"]["temp"] == "F"


def test_celsius_with_nws():
    fake = Fake()
    w = _svc(US, fake, temp="C", wind="kmh").get(NOW)
    assert w["source"] == "nws"
    assert (w["temp"], w["high"], w["low"]) == (17, 20, 10)
    assert w["hours"][0]["temp"] == 17 and w["days"][1]["high"] == 22
    assert w["wind"] == 16 and w["units"]["wind_label"] == "km/h"


def test_fahrenheit_chosen_abroad():
    fake = Fake()
    w = _svc(LONDON, fake, temp="F", wind="mph").get(NOW)
    assert fake.calls[0].params["temperature_unit"] == "fahrenheit" and w["units"]["wind"] == "mph"


def test_cached_for_15_minutes():
    fake = Fake()
    s = _svc(LONDON, fake)
    s.get(NOW)
    s.get(NOW.replace(minute=25))
    assert len(fake.calls) == 1
    s.get(NOW.replace(minute=28))
    assert len(fake.calls) == 2


def test_wmo_codes_map_to_the_frame_icons():
    icons = {"sun", "moon", "partly", "cloud", "fog", "rain", "snow", "storm"}
    assert all(icon in icons for _text, icon in open_meteo.WMO.values())
    assert open_meteo.describe(0, is_day=False) == ("Clear", "moon")
    assert open_meteo.describe(2, is_day=False)[1] == "moon"
    assert open_meteo.describe(75)[1] == "snow" and open_meteo.describe(99)[1] == "storm"
    assert open_meteo.describe(45)[1] == "fog" and open_meteo.describe(None)[1] == "cloud"


@pytest.mark.parametrize("place,expected", [(US, True), (TORONTO, False), (LONDON, False),
                                            ((21.31, -157.86, "Pacific/Honolulu"), True),
                                            ((51.51, -0.13, "America/New_York"), False)])
def test_in_us(place, expected):
    lat, lon, tz = place
    assert in_us(tz, lat, lon) is expected


def test_demo_weather_follows_the_celsius_setting(demo_env):
    from app import demo
    from app.config import load_settings, read_store, write_store
    from app.main import Services
    store = read_store(True)
    store["weather"] = {"source": "auto", "temp": "C", "wind": "kmh"}
    write_store(store, True)
    s = Services(load_settings())
    w = s.weather_now(NOW)
    assert w["temp"] == 17 and w["high"] == 20 and w["units"]["wind_label"] == "km/h" and w["wind"] == 13
    assert demo.DEMO_WEATHER["temp"] == 62          # the sample itself is untouched
    assert len(w["hours"]) == 6 and w["note"] == demo.DEMO_WEATHER["note"]


def test_convert_round_trip_keeps_shape():
    w = {"temp": 62, "high": 68, "low": 49, "wind": 8, "hours": [{"temp": 60}], "days": [{"high": 70, "low": None}],
         "units": {"temp": "F", "wind": "mph"}}
    c = convert(w, "C", "kmh")
    assert c["days"][0]["low"] is None and c["hours"][0]["temp"] == 16
    assert set(c) == set(w)


def test_weather_display_choices_saved_and_sent(client_factory=None):
    """Settings > General: wind placement and the °F/°C letter reach the frame's weather."""
    from app.admin import _weather_choices
    out = _weather_choices({"weather_show_wind": "off", "weather_unit_letter": "yes"}, {})
    assert out["show_wind"] == "off" and out["unit_letter"] == "yes"
    assert _weather_choices({}, {})["show_wind"] == "panel"
    assert _weather_choices({}, {})["unit_letter"] == "no"
    import pytest
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        _weather_choices({"weather_show_wind": "sometimes"}, {})


def test_frame_weather_carries_display_choices(demo_env):
    from app.config import load_settings, read_store, write_store
    from app.main import Services
    s = Services(load_settings())
    assert s.weather_now(NOW)["display"] == {"wind": "panel", "letter": False}   # defaults: 62°, wind on the panel
    store = read_store(True)
    store["weather"] = {"source": "auto", "temp": "C", "wind": "kmh", "show_wind": "everywhere", "unit_letter": "yes"}
    write_store(store, True)
    w = Services(load_settings()).weather_now(NOW)
    assert w["display"] == {"wind": "everywhere", "letter": True} and w["units"]["temp"] == "C"
