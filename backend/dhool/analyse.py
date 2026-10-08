"""Readings + weather -> verdict and the series behind the "Why?" chart. No AWS calls here."""
import pandas as pd

from . import config
from .expected import expected_daily_kwh
from .verdict import verdict

CHART_DAYS = 90
FORECAST_DAYS = 7  # the weather frame ends with this many forecast days


def _days(readings):
    series = pd.Series(readings, dtype=float)
    series.index = pd.DatetimeIndex(series.index).tz_localize(config.TZ)
    return series.sort_index()


def analyse(meta, readings, weather, pm25=None, fleet=None):
    """meta: the house (kw, lat, lon, tilt, azimuth). readings: {"YYYY-MM-DD": kwh}.
    weather: hourly frame covering the first reading through a week past the last (the forecast).
    fleet: other homes nearby, {id: {"kw": ..., "readings": {...}}}, for the neighbour comparison.
    """
    actual = _days(readings)
    expected = expected_daily_kwh(weather, float(meta["lat"]), float(meta["lon"]), float(meta["kw"]),
                                  float(meta["tilt"]), float(meta["azimuth"]))
    rain = weather["rain"].resample("D").sum()
    last = actual.index[-1]
    daily = pd.DataFrame({"expected": expected, "actual": actual})[actual.index[0]:last]

    neighbours = None
    if fleet:
        # ponytail: neighbours are compared against this roof's expected output scaled by size, not their
        # own physics. Fine for the week-on-week steps the rules look at; run pvlib per neighbour if
        # homes ever differ much in tilt or direction.
        neighbours = pd.DataFrame({
            pid: _days(home["readings"]) / (daily["expected"] * home["kw"] / float(meta["kw"]))
            for pid, home in fleet.items()
        }).reindex(daily.index)

    result = verdict(daily, rain[:last], list(rain[last:].iloc[1:8]),
                     pm25[:last] if pm25 is not None else None, neighbours)
    result["as_of"] = str(last.date())
    chart = daily.tail(CHART_DAYS)
    result["series"] = [
        {"date": str(day.date()), "expected": round(row.expected, 2),
         "actual": None if pd.isna(row.actual) else round(row.actual, 2),
         "rain_mm": round(float(rain.get(day, 0.0)), 1)}
        for day, row in chart.iterrows()
    ]
    # The coming week: what a clean, healthy roof could make in the forecast weather, and what this roof
    # is likely to make if nothing changes (the same physics, scaled by how it has run this past week).
    running_at = (daily["actual"] / daily["expected"]).dropna().tail(7).median()
    temp_max = weather["temp_air"].resample("D").max()
    result["forecast"] = [
        {"date": str(day.date()), "possible_kwh": round(float(kwh), 1),
         "likely_kwh": round(float(kwh * running_at), 1) if pd.notna(running_at) else None,
         "rain_mm": round(float(rain[day]), 1), "temp_max": round(float(temp_max[day]))}
        for day, kwh in expected.tail(FORECAST_DAYS).items()
    ]
    return result
