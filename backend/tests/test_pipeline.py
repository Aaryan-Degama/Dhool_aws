"""The demo inverter cloud and the analysis step that turns readings into a verdict. No network."""
import json

import boto3
import pandas as pd
import pvlib
import pytest
from moto import mock_aws

from dhool import config, connectors
from dhool.analyse import analyse
from dhool.expected import expected_daily_kwh
from handlers import analysis, mock_inverter

META = {"kw": 3, "lat": config.SIM_LAT, "lon": config.SIM_LON, "tilt": 20, "azimuth": 180}


def mock(route, plant_id=None, query=None, key=None):
    event = {"routeKey": route, "pathParameters": {"plantId": plant_id}, "queryStringParameters": query,
             "headers": {"authorization": f"Bearer {key}"} if key else {}}
    response = mock_inverter.handler(event, None)
    return response["statusCode"], response["body"]


def test_inverter_api_shows_one_plant_per_key_and_never_leaks_what_was_planted():
    key = mock_inverter.api_key("home-00")
    assert mock("GET /mock/v1/plants")[0] == 401
    assert mock("GET /mock/v1/plants", key="inv_" + "0" * 24)[0] == 401
    status, body = mock("GET /mock/v1/plants", key=key)
    plants = json.loads(body)
    assert status == 200 and [p["id"] for p in plants] == ["home-00"]
    assert set(plants[0]) == {"id", "kw", "lat", "lon", "tilt", "azimuth"}
    status, body = mock("GET /mock/v1/plants/{plantId}/daily", "home-00", {"from": "2026-04-01", "to": "2026-04-03"}, key)
    daily = json.loads(body)
    assert [d["date"] for d in daily] == ["2026-04-01", "2026-04-02", "2026-04-03"] and set(daily[0]) == {"date", "kwh"}
    assert mock("GET /mock/v1/plants/{plantId}/daily", "home-05", key=key)[0] == 403  # someone else's plant
    fleet = json.loads(mock("GET /mock/fleet/daily")[1])
    assert len(fleet) == 33 and set(fleet["home-05"]) == {"kw", "readings"}
    page = mock("GET /mock/app", query={"plant": "home-05"})[1]
    assert mock_inverter.api_key("home-05") in page and "__DATA__" not in page
    assert not any(word in json.dumps(fleet) + body + page for word in ("fault", "soiling", "problem", "cause"))


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
    # "Should have made" and "possible" are this roof's own normal (93% of the physics here), not the physics:
    # a healthy day sits on the line, and the week ahead is likely 67% of possible, as the roof runs now.
    assert result["series"][0]["actual"] == pytest.approx(result["series"][0]["expected"], abs=0.02)
    assert all(d["likely_kwh"] == pytest.approx(d["possible_kwh"] * 0.67, abs=0.2) for d in week)
    assert week[0]["temp_max"] == 28 and week[0]["rain_mm"] == 0.0
    json.dumps(result)  # must be storable as JSON


def test_the_chart_reaches_back_to_a_fault_older_than_its_90_days():
    weather = clear_weather(157)  # 150 days of readings + a week of forecast
    expected = expected_daily_kwh(weather, META["lat"], META["lon"], META["kw"], META["tilt"], META["azimuth"])
    factor = pd.Series(0.93, index=expected.index[:150])
    factor.iloc[30:] *= 0.67  # a string dies 120 days before the last reading
    readings = {str(day.date()): round(kwh, 2) for day, kwh in (expected[:150] * factor).items()}

    result = analyse(META, readings, weather)
    dates = [d["date"] for d in result["series"]]
    assert result["cause"] == "fault" and dates[-1] == result["as_of"]
    assert dates.index(result["evidence"]["step_date"]) == 21  # three weeks of normal output, then the drop


def test_the_nightly_run_survives_a_house_linked_before_api_keys(monkeypatch):
    """A house with a plant but no key (linked the old way) is read from its own readings, not the inverter."""
    for name, value in {"AWS_DEFAULT_REGION": "ap-south-1", "AWS_ACCESS_KEY_ID": "t", "AWS_SECRET_ACCESS_KEY": "t",
                        "TABLE": "dhool-test"}.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(connectors, "inverter_readings", lambda *a: pytest.fail("there is no key to call the inverter with"))
    with mock_aws():
        table = boto3.resource("dynamodb").create_table(
            TableName="dhool-test", BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}, {"AttributeName": "sk", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}, {"AttributeName": "sk", "KeyType": "RANGE"}])
        table.put_item(Item={"pk": "HOUSES", "sk": "h1"})
        table.put_item(Item={"pk": "HOUSE#h1", "sk": "META", "plant_id": "home-04", "inverter_url": "https://api.invalid/mock",
                             "kw": 3, "lat": "28.59", "lon": "77.23", "tilt": 20, "azimuth": 180})
        monkeypatch.setattr(analysis, "_table", None)
        assert analysis.handler({}, None) == {"done": 1, "failed": 0}


def test_a_reported_wash_reaches_the_verdict_with_its_before_and_after():
    weather = clear_weather(67)
    expected = expected_daily_kwh(weather, META["lat"], META["lon"], META["kw"], META["tilt"], META["azimuth"])
    dirt = pd.Series([0.004 * (i if i < 50 else i - 50) for i in range(60)], index=expected.index[:60])  # washed on day 50
    readings = {str(day.date()): round(kwh, 2) for day, kwh in (expected[:60] * 0.93 * (1 - dirt)).items()}
    result = analyse(META, readings, weather, actions=[{"date": "2026-04-20", "type": "wash"}])
    check = result["check"]
    assert (check["status"], check["date"], result["verdict"]) == ("verified", "2026-04-20", "OK")
    assert check["predicted_pct"] == pytest.approx(check["observed_pct"], abs=4) and check["observed_pct"] > 15
    json.dumps(result)


def test_a_dust_storm_forecast_after_the_last_reading_reaches_the_wash_plan():
    weather = clear_weather(67)
    expected = expected_daily_kwh(weather, META["lat"], META["lon"], META["kw"], META["tilt"], META["azimuth"])
    dirt = pd.Series([0.004 * i for i in range(60)], index=expected.index[:60])
    readings = {str(day.date()): round(kwh, 2) for day, kwh in (expected[:60] * 0.93 * (1 - dirt)).items()}
    storms = pd.Series(False, index=expected.index[60:67])  # the forecast starts the day after the last reading
    storms.iloc[1] = True
    assert analyse(META, readings, weather)["verdict"] == "CLEAN"
    result = analyse(META, readings, weather, dust_storms=storms)
    assert (result["verdict"], result["evidence"]["wait_for"]) == ("WAIT", "dust_storm")
