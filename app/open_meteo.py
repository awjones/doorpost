"""Weather anywhere in the world from Open-Meteo (https://open-meteo.com).

Free for non-commercial use, no API key, no account. The data is licensed
CC BY 4.0, so Settings and the docs carry the line "Weather data by
Open-Meteo.com". One call returns everything the frame shows; WeatherService
caches it, so a frame makes about 100 calls a day (the free limit is 10,000).

The answer is boiled down to the same shape as the National Weather Service
summary in app/weather.py, so the frame doesn't care which source it came from.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

import httpx

API = "https://api.open-meteo.com/v1/forecast"
ATTRIBUTION = "Weather data by Open-Meteo.com (CC BY 4.0)"

# WMO weather interpretation codes (the table at the bottom of open-meteo.com/en/docs)
# -> the words the frame shows and the frame's icon. "partly" and "sun" turn into "moon" at night.
WMO = {
    0: ("Clear", "sun"),
    1: ("Mostly clear", "sun"),
    2: ("Partly cloudy", "partly"),
    3: ("Cloudy", "cloud"),
    45: ("Fog", "fog"),
    48: ("Freezing fog", "fog"),
    51: ("Light drizzle", "rain"),
    53: ("Drizzle", "rain"),
    55: ("Heavy drizzle", "rain"),
    56: ("Freezing drizzle", "rain"),
    57: ("Freezing drizzle", "rain"),
    61: ("Light rain", "rain"),
    63: ("Rain", "rain"),
    65: ("Heavy rain", "rain"),
    66: ("Freezing rain", "rain"),
    67: ("Freezing rain", "rain"),
    71: ("Light snow", "snow"),
    73: ("Snow", "snow"),
    75: ("Heavy snow", "snow"),
    77: ("Snow grains", "snow"),
    80: ("Rain showers", "rain"),
    81: ("Rain showers", "rain"),
    82: ("Heavy rain showers", "rain"),
    85: ("Snow showers", "snow"),
    86: ("Heavy snow showers", "snow"),
    95: ("Thunderstorms", "storm"),
    96: ("Thunderstorms with hail", "storm"),
    99: ("Thunderstorms with hail", "storm"),
}


def describe(code: Optional[int], is_day: bool = True) -> tuple[str, str]:
    """A WMO code -> (words, icon)."""
    text, icon = WMO.get(int(code) if code is not None else -1, ("", "cloud"))
    if not is_day and icon in ("sun", "partly"):
        icon = "moon"
    return text, icon


def fetch(http: httpx.Client, lat: float, lon: float, timezone: str, temp: str, wind: str) -> dict:
    """One call for current conditions, 4 days of hours and 3 days, in the units asked for."""
    r = http.get(API, params={
        "latitude": f"{lat:.4f}", "longitude": f"{lon:.4f}",
        "current": "temperature_2m,weather_code,is_day,wind_speed_10m",
        "hourly": "temperature_2m,precipitation_probability,weather_code,is_day",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "temperature_unit": "fahrenheit" if temp == "F" else "celsius",
        "wind_speed_unit": "mph" if wind == "mph" else "kmh",
        "timezone": timezone or "auto",
        "forecast_days": 4,
    })
    r.raise_for_status()
    return r.json()


def _int(v) -> Optional[int]:
    return None if v is None else int(round(v))


def as_periods(data: dict, now: datetime) -> list[dict]:
    """Open-Meteo's hourly columns as rows shaped like NWS hourly periods (from this hour on),
    so the hour strip and rain note code is shared."""
    h = data.get("hourly") or {}
    this_hour = now.strftime("%Y-%m-%dT%H:00")
    out = []
    for i, t in enumerate(h.get("time") or []):
        if t < this_hour:
            continue
        is_day = bool((h.get("is_day") or [1] * (i + 1))[i])
        text, icon = describe((h.get("weather_code") or [None] * (i + 1))[i], is_day)
        out.append({"startTime": t, "temperature": _int((h.get("temperature_2m") or [None] * (i + 1))[i]),
                    "isDaytime": is_day, "shortForecast": text, "icon": icon,
                    "probabilityOfPrecipitation": {"value": (h.get("precipitation_probability") or [None] * (i + 1))[i]}})
    return out


def summarize(data: dict, now: datetime, temp: str, wind: str) -> dict:
    """Boil an Open-Meteo answer down to what the frame shows (same shape as weather.summarize)."""
    from .weather import DOW_LONG, _pop, hours_ahead, rain_note, rain_phrase

    hourly = as_periods(data, now)
    cur = data.get("current") or {}
    is_day = bool(cur.get("is_day", 1))
    text, icon = describe(cur.get("weather_code"), is_day)
    d = data.get("daily") or {}
    days = []
    for i, day in enumerate((d.get("time") or [])[:3]):
        if day < now.date().isoformat():
            continue
        dtext, dicon = describe((d.get("weather_code") or [None] * (i + 1))[i], True)
        date_ = datetime.fromisoformat(day).date()
        days.append({"name": "Today" if date_ == now.date() else DOW_LONG[date_.weekday()], "date": day,
                     "high": _int((d.get("temperature_2m_max") or [None] * (i + 1))[i]),
                     "low": _int((d.get("temperature_2m_min") or [None] * (i + 1))[i]),
                     "text": dtext, "rain": int((d.get("precipitation_probability_max") or [0] * (i + 1))[i] or 0),
                     "icon": dicon})
    today = now.date().isoformat()
    rest_of_day = [h for h in hourly if h["startTime"][:10] == today] or hourly[:12]
    rain = max((_pop(h) for h in rest_of_day), default=0)
    first = days[0] if days and days[0]["date"] == today else {}
    temp_now = _int(cur.get("temperature_2m"))
    if temp_now is None and hourly:
        temp_now = hourly[0]["temperature"]
    return {
        "temp": temp_now,
        "text": text,
        "high": first.get("high"),
        "low": first.get("low"),
        "rain": rain,
        "icon": icon,
        "phrase": rain_phrase(rain),
        "hours": hours_ahead(hourly),
        "days": days,
        "note": rain_note(hourly, now),
        "wind": _int(cur.get("wind_speed_10m")),
        "units": {"temp": temp, "wind": wind},
        "source": "open-meteo",
    }
