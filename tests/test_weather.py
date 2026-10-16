from datetime import datetime

from app.weather import icon_for, rain_phrase, summarize

NOW = datetime(2026, 10, 15, 16, 12)


def test_summarize_picks_high_low_and_rain():
    forecast = [
        {"startTime": "2026-10-15T06:00:00-04:00", "isDaytime": True, "temperature": 68, "shortForecast": "Partly Sunny"},
        {"startTime": "2026-10-15T18:00:00-04:00", "isDaytime": False, "temperature": 49, "shortForecast": "Mostly Clear"},
    ]
    hourly = [
        {"startTime": "2026-10-15T16:00:00-04:00", "temperature": 63, "isDaytime": True, "shortForecast": "Partly Sunny",
         "probabilityOfPrecipitation": {"value": 10}},
        {"startTime": "2026-10-15T19:00:00-04:00", "temperature": 58, "isDaytime": False, "shortForecast": "Chance Showers",
         "probabilityOfPrecipitation": {"value": 30}},
    ]
    obs = {"temperature": {"value": 16.7}, "textDescription": "Partly Cloudy"}
    w = summarize(forecast, hourly, obs, NOW)
    assert {k: w[k] for k in ("temp", "text", "high", "low", "rain", "icon", "phrase")} == {
        "temp": 62, "text": "Partly Cloudy", "high": 68, "low": 49, "rain": 30, "icon": "partly", "phrase": "30% rain"}
    assert [h["label"] for h in w["hours"]] == ["Now", "7 PM"]
    assert w["days"][0] == {"name": "Today", "date": "2026-10-15", "high": 68, "low": 49, "text": "Partly sunny",
                            "rain": 0, "icon": "partly"}
    assert w["note"] is None


def test_falls_back_to_hourly_without_observation():
    hourly = [{"startTime": "2026-10-15T16:00:00-04:00", "temperature": 63, "isDaytime": True,
               "shortForecast": "Rain", "probabilityOfPrecipitation": {"value": 80}}]
    w = summarize([], hourly, None, NOW)
    assert w["temp"] == 63 and w["icon"] == "rain" and w["phrase"] == "Rain likely (80%)"


def test_icons_and_phrases():
    assert icon_for("Thunderstorms") == "storm"
    assert icon_for("Light Snow") == "snow"
    assert icon_for("Clear", is_day=False) == "moon"
    assert rain_phrase(5) == "Rain unlikely"


def _hour(h, pop, text="Showers"):
    return {"startTime": f"2026-10-15T{h:02d}:00:00-04:00", "temperature": 55, "isDaytime": h < 19,
            "shortForecast": text, "probabilityOfPrecipitation": {"value": pop}}


def test_three_days_and_rain_note():
    forecast = [
        {"startTime": "2026-10-15T18:00:00-04:00", "isDaytime": False, "temperature": 49, "shortForecast": "Rain"},
        {"startTime": "2026-10-16T06:00:00-04:00", "isDaytime": True, "temperature": 71, "shortForecast": "Sunny",
         "probabilityOfPrecipitation": {"value": 5}},
        {"startTime": "2026-10-16T18:00:00-04:00", "isDaytime": False, "temperature": 52, "shortForecast": "Clear"},
        {"startTime": "2026-10-17T06:00:00-04:00", "isDaytime": True, "temperature": 66, "shortForecast": "Sunny"},
        {"startTime": "2026-10-17T18:00:00-04:00", "isDaytime": False, "temperature": 45, "shortForecast": "Clear"},
        {"startTime": "2026-10-18T06:00:00-04:00", "isDaytime": True, "temperature": 60, "shortForecast": "Cloudy"},
    ]
    hourly = [_hour(16, 10, "Cloudy"), _hour(17, 20), _hour(18, 30), _hour(19, 30), _hour(20, 70), _hour(21, 60), _hour(22, 50),
              _hour(23, 20)]
    w = summarize(forecast, hourly, None, NOW)
    assert [(d["name"], d["high"], d["low"]) for d in w["days"]] == [("Tonight", None, 49), ("Friday", 71, 52), ("Saturday", 66, 45)]
    assert w["note"] == "Rain likely 8 PM – 11 PM (70%)"
    assert len(w["hours"]) == 6 and w["hours"][4]["icon"] == "rain"
