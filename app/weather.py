"""Current conditions, the next few hours and the next three days.

Two sources, both free with no API key:
- the U.S. National Weather Service (api.weather.gov), inside the U.S. only. NWS asks
  for a descriptive User-Agent.
- Open-Meteo (app/open_meteo.py), anywhere in the world, free for non-commercial use.

Settings > General picks the source: Automatic (NWS inside the U.S., Open-Meteo
elsewhere, and Open-Meteo whenever NWS fails), or one of the two. Units are
Fahrenheit or Celsius and mph or km/h; Automatic means F and mph in the U.S.,
C and km/h elsewhere. Results are cached for 15 minutes; on failure the last
good reading is kept.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from typing import Optional

import httpx

from . import open_meteo

log = logging.getLogger(__name__)
API = "https://api.weather.gov"
SOURCES = ("auto", "nws", "open-meteo")
TEMP_UNITS = ("auto", "F", "C")
WIND_UNITS = ("auto", "mph", "kmh")
SHOW_WIND = ("panel", "everywhere", "off")   # where the frame shows wind
UNIT_LETTER = ("no", "yes")                  # 62° or 62°F on the frame
WIND_LABEL = {"mph": "mph", "kmh": "km/h"}

# Time zones used in the U.S. and its territories (where NWS forecasts).
_US_ZONES = {
    "America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles", "America/Phoenix",
    "America/Anchorage", "America/Juneau", "America/Sitka", "America/Yakutat", "America/Nome",
    "America/Metlakatla", "America/Adak", "America/Boise", "America/Detroit", "America/Menominee",
    "America/Puerto_Rico", "America/St_Thomas", "Pacific/Honolulu", "Pacific/Guam", "Pacific/Saipan",
    "Pacific/Pago_Pago", "EST5EDT", "CST6CDT", "MST7MDT", "PST8PDT",
}
# Rough boxes (south, north, west, east) around the 50 states and territories.
_US_BOXES = [
    (24.0, 49.5, -125.0, -66.5),    # lower 48
    (51.0, 71.5, -180.0, -129.0),   # Alaska
    (18.5, 22.5, -161.0, -154.5),   # Hawaii
    (17.5, 18.6, -67.5, -64.5),     # Puerto Rico and the U.S. Virgin Islands
    (13.0, 21.0, 144.0, 146.5),     # Guam and the Northern Mariana Islands
    (-14.6, -11.0, -171.5, -168.0),  # American Samoa
]


def in_us(timezone: Optional[str], lat: Optional[float], lon: Optional[float]) -> bool:
    """A good guess at "this house is in the U.S.": a U.S. time zone and a spot inside the U.S. boxes.
    (The box for the lower 48 also covers parts of Canada and Mexico; their time zones rule them out,
    and NWS saying "not ours" settles the rest.)"""
    tz = timezone or ""
    if not (tz in _US_ZONES or tz.startswith(("America/Indiana/", "America/Kentucky/", "America/North_Dakota/", "US/"))):
        return False
    if lat is None or lon is None:
        return True
    return any(s <= lat <= n and w <= lon <= e for s, n, w, e in _US_BOXES)


def icon_for(text: str, is_day: bool = True) -> str:
    t = (text or "").lower()
    if "thunder" in t:
        return "storm"
    if any(w in t for w in ("snow", "sleet", "flurr", "ice")):
        return "snow"
    if any(w in t for w in ("rain", "shower", "drizzle")):
        return "rain"
    if any(w in t for w in ("fog", "haze", "smoke")):
        return "fog"
    if "partly" in t or "mostly sunny" in t or "mostly clear" in t:
        return "partly" if is_day else "moon"
    if "cloud" in t or "overcast" in t:
        return "cloud"
    return "sun" if is_day else "moon"


def c_to_f(c: Optional[float]) -> Optional[int]:
    return None if c is None else round(c * 9 / 5 + 32)


def f_to_c(f: Optional[float]) -> Optional[int]:
    return None if f is None else round((f - 32) * 5 / 9)


def kmh_to_mph(k: Optional[float]) -> Optional[int]:
    return None if k is None else round(k / 1.609344)


def mph_to_kmh(m: Optional[float]) -> Optional[int]:
    return None if m is None else round(m * 1.609344)


def convert(w: Optional[dict], temp: str, wind: str) -> Optional[dict]:
    """A weather summary in other units (the frame's labels follow w["units"])."""
    if not w:
        return w
    have = w.get("units") or {"temp": "F", "wind": "mph"}
    out = dict(w)
    if have.get("temp") != temp:
        t = f_to_c if temp == "C" else c_to_f
        for k in ("temp", "high", "low"):
            out[k] = t(w.get(k))
        out["hours"] = [{**h, "temp": t(h.get("temp"))} for h in w.get("hours") or []]
        out["days"] = [{**d, "high": t(d.get("high")), "low": t(d.get("low"))} for d in w.get("days") or []]
    if have.get("wind") != wind and w.get("wind") is not None:
        out["wind"] = mph_to_kmh(w["wind"]) if wind == "kmh" else kmh_to_mph(w["wind"])
    out["units"] = {"temp": temp, "wind": wind, "wind_label": WIND_LABEL[wind]}
    return out


class WeatherService:
    """The frame's weather. `config` is Settings > General's weather choices:
    {"source": auto|nws|open-meteo, "temp": auto|F|C, "wind": auto|mph|kmh}."""

    CACHE = timedelta(minutes=15)

    def __init__(self, lat: Optional[float], lon: Optional[float], user_agent: str,
                 http: Optional[httpx.Client] = None, config: Optional[dict] = None,
                 timezone: Optional[str] = None):
        self.lat, self.lon = lat, lon
        self.timezone = timezone
        self.config = dict(config or {})
        self.http = http or httpx.Client(timeout=15, headers={"User-Agent": user_agent,
                                                              "Accept": "application/geo+json"})
        self._points: Optional[dict] = None
        self._nws_covers: Optional[bool] = None   # False once NWS says "not a U.S. location"
        self.current: Optional[dict] = None
        self.fetched_at: Optional[datetime] = None
        self.error: Optional[str] = None
        self.source_used: Optional[str] = None

    @classmethod
    def from_settings(cls, settings, http: Optional[httpx.Client] = None) -> "WeatherService":
        return cls(settings.latitude, settings.longitude, settings.weather_user_agent, http=http,
                   config=getattr(settings, "weather", None) or {}, timezone=settings.timezone)

    def same_setup(self, other: "WeatherService") -> bool:
        return (self.lat, self.lon, self.timezone, self.config) == (other.lat, other.lon, other.timezone, other.config)

    # ---- choices ----
    def source(self) -> str:
        s = self.config.get("source") or "auto"
        return s if s in SOURCES else "auto"

    def is_us(self) -> bool:
        return self._nws_covers is not False and in_us(self.timezone, self.lat, self.lon)

    def units(self) -> tuple[str, str]:
        us = self.is_us()
        t = self.config.get("temp") or "auto"
        w = self.config.get("wind") or "auto"
        return (t if t in ("F", "C") else ("F" if us else "C"),
                w if w in ("mph", "kmh") else ("mph" if us else "kmh"))

    def label(self) -> str:
        """For Settings: which source the frame is using right now."""
        return {"nws": "National Weather Service", "open-meteo": "Open-Meteo"}.get(self.source_used or "", "")

    # ---- reading ----
    def get(self, now: datetime) -> Optional[dict]:
        if self.lat is None or self.lon is None:
            self.error = "Set the latitude and longitude in Settings > General"
            return None
        if self.fetched_at and now - self.fetched_at < self.CACHE:
            return self.current
        try:
            self.current = self._fetch(now)
            self.fetched_at = now
            self.error = None
        except Exception as exc:
            log.warning("weather fetch failed: %s", exc)
            self.error = str(exc)[:200]
            self.fetched_at = now - timedelta(minutes=10)  # retry in ~5 min
        return self.current

    def _fetch(self, now: datetime) -> dict:
        src = self.source()
        if src == "auto" and not self.is_us():
            src = "open-meteo"
        if src in ("nws", "auto"):
            try:
                return self._nws(now)
            except Exception as exc:
                if src == "nws":
                    raise
                log.info("NWS failed (%s); using Open-Meteo", exc)
        return self._open_meteo(now)

    def _open_meteo(self, now: datetime) -> dict:
        temp, wind = self.units()
        data = open_meteo.fetch(self.http, self.lat, self.lon, self.timezone or "auto", temp, wind)
        self.source_used = "open-meteo"
        w = open_meteo.summarize(data, now, temp, wind)
        w["units"]["wind_label"] = WIND_LABEL[wind]
        return w

    def _json(self, url: str) -> dict:
        r = self.http.get(url)
        r.raise_for_status()
        return r.json()

    def _nws(self, now: datetime) -> dict:
        if self._points is None:
            try:
                self._points = self._json(f"{API}/points/{self.lat:.4f},{self.lon:.4f}")["properties"]
                self._nws_covers = True
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:   # "Unable to provide data for requested point"
                    self._nws_covers = False
                raise
        p = self._points
        forecast = self._json(p["forecast"])["properties"]["periods"]
        hourly = self._json(p["forecastHourly"])["properties"]["periods"]
        w = summarize(forecast, hourly, self._observation(p), now)
        self.source_used = "nws"
        return convert(w, *self.units())

    def _observation(self, p: dict) -> Optional[dict]:
        try:
            stations = self._json(p["observationStations"])["features"]
            if not stations:
                return None
            sid = stations[0]["properties"]["stationIdentifier"]
            return self._json(f"{API}/stations/{sid}/observations/latest")["properties"]
        except Exception as exc:
            log.info("no observation: %s", exc)
            return None


def _wind_mph(obs: Optional[dict], hourly: list[dict]) -> Optional[int]:
    """Wind now: the station's reading (km/h) or the first forecast hour ("5 to 10 mph")."""
    v = ((obs or {}).get("windSpeed") or {}).get("value")
    if v is not None:
        return kmh_to_mph(v)
    nums = re.findall(r"\d+", (hourly[0].get("windSpeed") or "") if hourly else "")
    return int(nums[-1]) if nums else None


def summarize(forecast: list[dict], hourly: list[dict], obs: Optional[dict], now: datetime) -> dict:
    """Boil NWS responses down to what the frame shows."""
    today = now.date().isoformat()
    first = forecast[0] if forecast else {}
    high = low = None
    for per in forecast[:3]:
        if per.get("isDaytime") and per["startTime"][:10] == today and high is None:
            high = per.get("temperature")
        if not per.get("isDaytime") and low is None:
            low = per.get("temperature")
    rest_of_day = [h for h in hourly if h["startTime"][:10] == today] or hourly[:12]
    rain = max(((h.get("probabilityOfPrecipitation") or {}).get("value") or 0) for h in rest_of_day) \
        if rest_of_day else 0
    temp = c_to_f(((obs or {}).get("temperature") or {}).get("value"))
    text = (obs or {}).get("textDescription") or ""
    if temp is None and hourly:
        temp = hourly[0].get("temperature")
    if not text and hourly:
        text = hourly[0].get("shortForecast", "")
    is_day = bool(hourly[0].get("isDaytime", True)) if hourly else True
    return {
        "temp": temp,
        "text": text or first.get("shortForecast", ""),
        "high": high,
        "low": low,
        "rain": int(rain),
        "icon": icon_for(text or first.get("shortForecast", ""), is_day),
        "phrase": rain_phrase(int(rain)),
        "hours": hours_ahead(hourly),
        "days": next_days(forecast, now, high),
        "note": rain_note(hourly, now),
        "wind": _wind_mph(obs, hourly),
        "units": {"temp": "F", "wind": "mph"},
        "source": "nws",
    }


DOW_LONG = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _pop(p: dict) -> int:
    return int(((p.get("probabilityOfPrecipitation") or {}).get("value")) or 0)


def _hour_label(start: str) -> str:
    h = int(start[11:13])
    return "midnight" if h == 0 else "noon" if h == 12 else f"{h % 12} {'AM' if h < 12 else 'PM'}"


def _own_icon(v) -> str:
    """One of our icon names. The weather service's hourly periods carry a web address in "icon" instead, which
    the frame can't load (it has no internet), so that one is worked out from the forecast text."""
    return v if isinstance(v, str) and v and "/" not in v else ""


def hours_ahead(hourly: list[dict], n: int = 6) -> list[dict]:
    """The Home screen's weather strip: now and the next few hours."""
    out = []
    for i, h in enumerate(hourly[:n]):
        out.append({"label": "Now" if i == 0 else _hour_label(h["startTime"]).replace("midnight", "12 AM").replace("noon", "12 PM"),
                    "temp": h.get("temperature"), "rain": _pop(h),
                    "icon": _own_icon(h.get("icon")) or icon_for(h.get("shortForecast", ""), bool(h.get("isDaytime", True)))})
    return out


def next_days(forecast: list[dict], now: datetime, today_high=None, n: int = 3) -> list[dict]:
    """Today and the next two days: high, low, sky and chance of rain (NWS gives day and night halves)."""
    by_day: dict[str, dict] = {}
    for per in forecast:
        day = per["startTime"][:10]
        if not per.get("isDaytime") and day not in by_day and day > now.date().isoformat():
            continue  # a night that belongs to the day before
        d = by_day.setdefault(day, {"day": None, "night": None})
        d["day" if per.get("isDaytime") else "night"] = d["day" if per.get("isDaytime") else "night"] or per
    out = []
    for day in sorted(by_day)[:n]:
        dd, nn = by_day[day]["day"], by_day[day]["night"]
        main = dd or nn or {}
        date_ = datetime.fromisoformat(day).date()
        text = short_text(main.get("shortForecast", ""))
        name = ("Today" if dd else "Tonight") if date_ == now.date() else DOW_LONG[date_.weekday()]
        out.append({"name": name, "date": day,
                    "high": dd.get("temperature") if dd else today_high if date_ == now.date() else None,
                    "low": nn.get("temperature") if nn else None, "text": text,
                    "rain": max(_pop(dd or {}), _pop(nn or {})), "icon": icon_for(text, True)})
    return out


def short_text(t: str) -> str:
    """'Isolated Showers And Thunderstorms then Scattered Showers' -> 'Isolated showers and thunderstorms'."""
    t = (t or "").split(" then ")[0].strip()
    return t[:1].upper() + t[1:].lower() if t else t


def rain_note(hourly: list[dict], now: datetime) -> Optional[str]:
    """'Rain likely 8 PM – midnight (70%)' when the next 12 hours have a stretch at 50% or more."""
    wet = [h for h in hourly[:12] if _pop(h) >= 50]
    if not wet:
        return None
    first = hourly.index(wet[0])
    run = [wet[0]]
    for h in hourly[first + 1:12]:
        if _pop(h) < 50:
            break
        run.append(h)
    end_h = (int(run[-1]["startTime"][11:13]) + 1) % 24
    word = "Storms" if any("thunder" in (h.get("shortForecast") or "").lower() for h in run) else \
        "Snow" if any(icon_for(h.get("shortForecast", "")) == "snow" for h in run) else "Rain"
    start = "now" if first == 0 else _hour_label(run[0]["startTime"])
    end = "midnight" if end_h == 0 else "noon" if end_h == 12 else f"{end_h % 12} {'AM' if end_h < 12 else 'PM'}"
    return f"{word} likely {start} – {end} ({max(_pop(h) for h in run)}%)"


def rain_phrase(pct: int) -> str:
    if pct < 15:
        return "Rain unlikely"
    if pct < 40:
        return f"{pct}% rain"
    return f"Rain likely ({pct}%)"
