"""The demo inverter cloud, the dummy screenshot reader, and the analysis step. No network."""
import json
import struct
import zlib

import boto3
import pandas as pd
import pvlib
from moto import mock_aws
import pytest

from dhool import config
from dhool.analyse import analyse
from dhool.expected import expected_daily_kwh
from handlers import mock_inverter, vision_dummy

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
    assert len(fleet) == 30 and set(fleet["home-05"]) == {"kw", "readings"}
    page = mock("GET /mock/app", query={"plant": "home-05"})[1]
    assert mock_inverter.api_key("home-05") in page and "__DATA__" not in page
    assert not any(word in json.dumps(fleet) + body + page for word in ("fault", "soiling", "problem", "cause"))


def png_with(text=None):
    """The smallest PNG (header chunk and end chunk), optionally carrying the demo app's text chunk."""
    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))
    header = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    extra = chunk(b"tEXt", b"dhool-demo\x00" + text.encode()) if text is not None else b""
    return b"\x89PNG\r\n\x1a\n" + header + extra + chunk(b"IEND", b"")


def test_dummy_reader_reads_demo_images_and_refuses_everything_else(monkeypatch):
    for name, value in {"AWS_DEFAULT_REGION": "ap-south-1", "AWS_ACCESS_KEY_ID": "t", "AWS_SECRET_ACCESS_KEY": "t", "UPLOADS": "uploads-test"}.items():
        monkeypatch.setenv(name, value)
    payload = {"app": "Inverter Cloud (demo)", "plant": "home-05", "readings": [{"date": "2026-09-25", "kwh": 12.4}]}
    with mock_aws():
        s3 = boto3.client("s3")
        s3.create_bucket(Bucket="uploads-test", CreateBucketConfiguration={"LocationConstraint": "ap-south-1"})
        for key, body in {"demo.png": png_with(json.dumps(payload)), "plain.png": png_with(), "photo.jpg": b"\xff\xd8\xff\xe0 not a png",
                          "broken.png": png_with("{not json")}.items():
            s3.put_object(Bucket="uploads-test", Key=key, Body=body)
        assert vision_dummy.handler({"key": "demo.png"}, None) == {
            "ok": True, "reader": "dummy", "app": "Inverter Cloud (demo)", "readings": payload["readings"]}
        for other in ("plain.png", "photo.jpg", "broken.png"):
            assert vision_dummy.handler({"key": other}, None) == {"ok": False, "reader": "dummy"}


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
