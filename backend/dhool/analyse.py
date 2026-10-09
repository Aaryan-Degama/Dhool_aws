"""Readings + weather -> verdict and the series behind the "Why?" chart. No AWS calls here."""
import pandas as pd

from . import config
from .expected import expected_daily_kwh
from .verdict import verdict

CHART_DAYS = 90
CHART_LEAD_DAYS = 21  # a fault older than the chart: start this long before it, so the drop is on the chart
FORECAST_DAYS = 7  # the weather frame ends with this many forecast days


def _days(readings):
    series = pd.Series(readings, dtype=float)
    series.index = pd.DatetimeIndex(series.index).tz_localize(config.TZ)
    return series.sort_index()


def analyse(meta, readings, weather, pm25=None, fleet=None, actions=(), dust_storms=None):
    """meta: the house (kw, lat, lon, tilt, azimuth). readings: {"YYYY-MM-DD": kwh}.
    weather: hourly frame covering the first reading through a week past the last (the forecast).
    fleet: other homes nearby, {id: {"kw": ..., "readings": {...}}}, for the neighbour comparison.
    dust_storms: daily True/False, a dust storm forecast that day (expected.fetch_dust_storms).
    actions: washes and vendor visits the homeowner reported, [{"date": "YYYY-MM-DD", "type": "wash" | "visit"}].
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
                     pm25[:last] if pm25 is not None else None, neighbours, actions,
                     list(dust_storms[dust_storms.index > last].iloc[:7]) if dust_storms is not None else (),
                     float(meta["wash_cost_rs"]) if meta.get("wash_cost_rs") is not None else None)
    result["as_of"] = str(last.date())
    start = last - pd.Timedelta(days=CHART_DAYS - 1)
    if "step_date" in result["evidence"]:
        start = min(start, pd.Timestamp(result["evidence"]["step_date"], tz=config.TZ) - pd.Timedelta(days=CHART_LEAD_DAYS))
    # "Should have made" and "possible" are what this roof makes when it is clean and healthy: the physics
    # at the roof's own normal share, the basis the verdict measures against. No roof reaches the physics.
    share = result["normal_share"]
    chart = daily.loc[start:]
    result["series"] = [
        {"date": str(day.date()), "expected": round(row.expected * share, 2),
         "actual": None if pd.isna(row.actual) else round(row.actual, 2),
         "rain_mm": round(float(rain.get(day, 0.0)), 1)}
        for day, row in chart.iterrows()
    ]
    # The coming week: what this roof makes clean and healthy in the forecast weather, and what it is likely
    # to make if nothing changes (the same physics, scaled by how it has run this past week).
    running_at = min((daily["actual"] / daily["expected"]).dropna().tail(7).median(), share)
    temp_max = weather["temp_air"].resample("D").max()
    result["forecast"] = [
        {"date": str(day.date()), "possible_kwh": round(float(kwh * share), 1),
         "likely_kwh": round(float(kwh * running_at), 1) if pd.notna(running_at) else None,
         "rain_mm": round(float(rain[day]), 1), "temp_max": round(float(temp_max[day]))}
        for day, kwh in expected.tail(FORECAST_DAYS).items()
    ]
    return result
