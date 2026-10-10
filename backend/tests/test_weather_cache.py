"""The weather cache around Open-Meteo, against an in-memory DynamoDB. No network."""

import json

import boto3
import pytest
from moto import mock_aws

from dhool import expected
from handlers import analysis, common, weather_cache

URL = "https://api.open-meteo.com/v1/forecast?latitude=28.61&longitude=77.21&hourly=dust"
ANSWER = {"hourly": {"time": ["2026-10-10T00:00"], "dust": [0.1, 302.0, None]}}


@pytest.fixture
def cache(monkeypatch):
    """(get, asked, clock): the cached fetch, the addresses that reached Open-Meteo, and a clock to move."""
    for name, value in {
        "AWS_DEFAULT_REGION": "ap-south-1",
        "AWS_ACCESS_KEY_ID": "t",
        "AWS_SECRET_ACCESS_KEY": "t",
        "TABLE": "dhool-test",
    }.items():
        monkeypatch.setenv(name, value)
    asked, clock = [], [1_800_000_000]

    def open_meteo(url):
        asked.append(url)
        if asked.count("down"):
            raise TimeoutError("no answer")
        return ANSWER

    monkeypatch.setattr(weather_cache.time, "time", lambda: clock[0])
    with mock_aws():
        common._made.clear()
        boto3.resource("dynamodb").create_table(
            TableName="dhool-test",
            BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[
                {"AttributeName": "pk", "AttributeType": "S"},
                {"AttributeName": "sk", "AttributeType": "S"},
            ],
            KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}, {"AttributeName": "sk", "KeyType": "RANGE"}],
        )
        yield weather_cache.cached(open_meteo), asked, clock


def test_an_answer_is_asked_for_once_and_then_served_from_the_table_for_three_hours(cache):
    get, asked, clock = cache
    assert get(URL) == ANSWER and get(URL) == ANSWER  # the same numbers, to the last digit, from the table
    clock[0] += weather_cache.FRESH_S - 1
    assert get(URL) == ANSWER and asked == [URL]
    clock[0] += 2  # three hours old: asked again
    assert get(URL) == ANSWER and asked == [URL, URL]
    item = common.table().scan()["Items"][0]
    assert item["pk"].startswith("WXCACHE#") and len(item["pk"]) == 8 + 64
    assert (
        item["expiresAt"] == clock[0] + weather_cache.STALE_S
    )  # DynamoDB's TTL removes it a day after the last answer


def test_places_are_kept_apart_to_the_last_digit_sent(cache):
    get, asked, _ = cache
    nearby = URL.replace("28.61", "28.610001")
    get(URL), get(nearby), get(URL), get(nearby)
    assert asked == [URL, nearby]


def test_when_open_meteo_is_down_yesterdays_answer_is_used_and_the_log_says_so(cache, capsys):
    get, asked, clock = cache
    get(URL)
    asked.append("down")
    clock[0] += 20 * 3600
    assert get(URL) == ANSWER
    said = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert said["weather"] == "stale" and said["age_s"] == 20 * 3600 and said["error"] == "TimeoutError"
    clock[0] += 4 * 3600 + 1  # a day old and more: no weather is better than weather that old
    with pytest.raises(TimeoutError):
        get(URL)


def test_with_nothing_kept_a_failure_is_the_failure(cache):
    get, asked, _ = cache
    asked.append("down")
    with pytest.raises(TimeoutError):
        get(URL)
    assert common.table().scan()["Items"] == []


def test_an_answer_too_long_for_one_item_is_used_and_not_kept(cache, monkeypatch):
    get, asked, _ = cache
    monkeypatch.setattr(weather_cache, "MAX_BYTES", 10)
    assert get(URL) == ANSWER and get(URL) == ANSWER
    assert asked == [URL, URL] and common.table().scan()["Items"] == []


def test_a_table_that_cannot_be_read_or_written_never_fails_the_fetch(cache, monkeypatch, capsys):
    get, asked, _ = cache
    monkeypatch.setenv("TABLE", "no-such-table")
    assert get(URL) == ANSWER and asked == [URL]
    assert capsys.readouterr().out.count("ResourceNotFoundException") == 2  # the read and the write, each said once


def test_once_the_analysis_handler_is_loaded_every_weather_fetch_goes_through_the_cache():
    assert analysis.expected is expected and expected.get_json is not expected.http_get
    assert expected.get_json.__qualname__.startswith("cached")
