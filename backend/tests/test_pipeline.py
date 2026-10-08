"""The mock inverter API and the analysis step that turns readings into a verdict. No network."""
import json

import pandas as pd
import pvlib
import pytest

from dhool import config
from dhool.analyse import analyse
from dhool.expected import expected_daily_kwh
from handlers import mock_inverter

META = {"kw": 3, "lat": config.SIM_LAT, "lon": config.SIM_LON, "tilt": 20, "azimuth": 180}


def mock(route, plant_id=None, query=None):
    event = {"routeKey": route, "pathParameters": {"plantId": plant_id}, "queryStringParameters": query}
    response = mock_inverter.handler(event, None)
    return response["statusCode"], json.loads(response["body"])


def test_mock_api_reports_like_an_inverter_and_never_leaks_what_was_planted():
    status, plants = mock("GET /mock/plants")
    assert status == 200 and len(plants) == 30
    assert set(plants[0]) == {"id", "kw", "lat", "lon", "tilt", "azimuth"}
    status, daily = mock("GET /mock/plants/{plantId}/daily", "home-00", {"from": "2026-04-01", "to": "2026-04-03"})
    assert [d["date"] for d in daily] == ["2026-04-01", "2026-04-02", "2026-04-03"]
    assert set(daily[0]) == {"date", "kwh"}
    assert mock("GET /mock/plants/{plantId}/daily", "home-99")[0] == 404
    fleet = mock("GET /mock/fleet/daily")[1]
    assert set(fleet["home-05"]) == {"kw", "readings"}
    assert not any(word in json.dumps(fleet) + json.dumps(plants) for word in ("fault", "soiling", "problem", "cause"))


def clear_weather(days):
    times = pd.date_range("2026-03-01", periods=days * 24, freq="h", tz=config.TZ)
    sky = pvlib.location.Location(config.SIM_LAT, config.SIM_LON, config.TZ).get_clearsky(times, model="simplified_solis")
    sky["temp_air"], sky["wind_speed"], sky["rain"] = 28.0, 2.0, 0.0
    return sky


def test_analyse_turns_readings_into_a_verdict_and_a_chart():
    weather = clear_weather(67)  # 60 days of readings + a week of forecast
    expected = expected_daily_kwh(weather, META["lat"], META["lon"], META["kw"], META["tilt"], META["azimuth"])
    factor = pd.Series(0.93, index=expected.index[:60])
    factor.iloc[40:] *= 0.67  # a string dies on day 40
    readings = {str(day.date()): round(kwh, 2) for day, kwh in (expected[:60] * factor).items()}
    del readings["2026-03-10"]  # a day the homeowner never sent
    fleet = {f"n{i}": {"kw": 2.0, "readings": {str(d.date()): round(k * 0.9 * 2 / 3, 2) for d, k in expected[:60].items()}}
             for i in range(5)}

    result = analyse(META, readings, weather, fleet=fleet)
    assert (result["verdict"], result["cause"]) == ("INSPECT", "fault")
    assert result["as_of"] == "2026-04-29"
    assert len(result["series"]) == 60 and result["series"][-1]["date"] == "2026-04-29"
    assert result["series"][9] == {"date": "2026-03-10", "expected": result["series"][9]["expected"],
                                   "actual": None, "rain_mm": 0.0}
    week = result["forecast"]
    assert [d["date"] for d in week] == [f"2026-0{m}-{d:02d}" for m, d in [(4, 30)] + [(5, d) for d in range(1, 7)]]
    assert all(d["likely_kwh"] == pytest.approx(d["possible_kwh"] * 0.93 * 0.67, abs=0.2) for d in week)
    assert week[0]["temp_max"] == 28 and week[0]["rain_mm"] == 0.0
    json.dumps(result)  # must be storable as JSON
