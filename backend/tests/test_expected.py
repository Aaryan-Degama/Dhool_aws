"""Fetching the weather: new tries when Open-Meteo is busy, and one forecast call where there were two.

fixtures/openmeteo_*.json are Open-Meteo's own answers for Delhi, recorded on 10 Oct 2026 within one minute:
the three calls the analysis made until then (weather, gusts and visibility, dust) and the one forecast call
that now replaces the first two. No network here.
"""

import io
import json
import pathlib
import urllib.error
import urllib.parse

import pandas as pd
import pytest

from dhool import config, expected

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
LAT, LON = 28.61, 77.21


def recorded(name):
    return json.loads((FIXTURES / f"openmeteo_{name}.json").read_text())


def frame(name):
    """An answer as the old code read it: one column per variable, hours in local time."""
    hourly = dict(recorded(name)["hourly"])
    return pd.DataFrame(hourly, index=pd.DatetimeIndex(hourly.pop("time")).tz_localize(config.TZ)).astype(float)


@pytest.fixture
def open_meteo(monkeypatch):
    """Answers each call from the recordings, and keeps the addresses asked for."""
    asked = []

    def answer(url):
        asked.append(url)
        query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        if url.startswith(expected.AIR_QUALITY_URL):
            return recorded("air_dust")
        assert url.startswith(expected.FORECAST_URL) and "wind_gusts_10m" in query["hourly"][0], url
        return recorded("forecast_combined")

    monkeypatch.setattr(expected, "get_json", answer)
    return asked


def storms_as_before():
    """The dust-storm rule on the two calls it used to make, gusts in km/h as Open-Meteo sent them."""
    hours = frame("air_dust").join(frame("forecast_gusts"), how="inner")
    storm = (
        (hours["dust"] >= config.STORM_DUST)
        & (hours["wind_gusts_10m"] >= config.STORM_GUST_KMH)
        & (hours["visibility"] <= config.STORM_VISIBILITY_M)
    )
    return storm.resample("D").max().astype(bool)


def test_the_one_forecast_call_gives_the_weather_the_separate_call_gave(open_meteo):
    before = frame("forecast_weather").rename(columns=expected._COLUMNS)
    after = expected.fetch_weather_with_forecast(LAT, LON, before.index[0].date())
    pd.testing.assert_frame_equal(after[list(expected._COLUMNS.values())], before, check_exact=True)
    assert len(open_meteo) == 1 and len(before) == 67 * 24


def test_gusts_and_visibility_from_that_call_are_the_figures_the_second_call_gave(open_meteo):
    before = frame("forecast_gusts")
    after = expected.fetch_weather_with_forecast(LAT, LON, before.index[0].date()).loc[before.index]
    assert after["gust_kmh"].tolist() == before["wind_gusts_10m"].tolist()  # m/s x 3.6 to one decimal, every hour
    pd.testing.assert_series_equal(after["visibility_m"], before["visibility"], check_names=False, check_exact=True)
    assert len(before) == 7 * 24 and before["wind_gusts_10m"].max() > 30


@pytest.mark.parametrize(
    "dust,gust,visibility,any_storm",
    [
        (
            config.STORM_DUST,
            config.STORM_GUST_KMH,
            config.STORM_VISIBILITY_M,
            False,
        ),  # the rule as it stands: a calm week
        # Looser, so that some days are storms and the comparison has something to get wrong. 31.7 is the week's
        # strongest gust and 25.2 a common one: the rule's >= is tried exactly on a recorded figure.
        (0.0, 20.0, 1e9, True),
        (0.0, 25.2, 1e9, True),
        (0.0, 31.7, 1e9, True),
        (10.0, 15.0, 30000.0, True),
    ],
)
def test_dust_storm_days_are_the_same_with_one_forecast_call_as_with_two(
    open_meteo, monkeypatch, dust, gust, visibility, any_storm
):
    monkeypatch.setattr(config, "STORM_DUST", dust)
    monkeypatch.setattr(config, "STORM_GUST_KMH", gust)
    monkeypatch.setattr(config, "STORM_VISIBILITY_M", visibility)
    weather = expected.fetch_weather_with_forecast(LAT, LON, frame("forecast_weather").index[0].date())
    after = expected.fetch_dust_storms(LAT, LON, weather)
    pd.testing.assert_series_equal(after, storms_as_before(), check_exact=True)
    assert len(after) == 7 and len(open_meteo) == 2  # one forecast call and the dust call: there were three
    assert bool(after.any()) is any_storm and not after.all()


class Answers:
    """urlopen that fails as told, then answers."""

    def __init__(self, *failures):
        self.failures, self.calls = list(failures), 0

    def __call__(self, url, timeout):
        self.calls += 1
        if self.failures:
            raise self.failures.pop(0)
        return io.BytesIO(b'{"hourly": {}}')


def http_error(code):
    return urllib.error.HTTPError("https://api.invalid", code, "no", {}, None)


@pytest.mark.parametrize(
    "failures",
    [
        [http_error(429)],
        [http_error(503), http_error(500)],
        [TimeoutError("read timed out")],
        [urllib.error.URLError("connection refused"), TimeoutError()],
    ],
)
def test_a_busy_failing_or_silent_open_meteo_is_asked_again(monkeypatch, failures):
    waits, answers = [], Answers(*failures)
    monkeypatch.setattr(expected.urllib.request, "urlopen", answers)
    monkeypatch.setattr(expected.time, "sleep", waits.append)
    assert expected.http_get("https://api.invalid") == {"hourly": {}}
    assert answers.calls == len(failures) + 1 and len(waits) == len(failures)
    assert all(
        0 <= wait <= expected.BACKOFF_S * 2**n for n, wait in enumerate(waits)
    )  # a random wait, longer each time


def test_the_third_failure_is_the_last_and_a_bad_request_is_not_asked_again(monkeypatch):
    monkeypatch.setattr(expected.time, "sleep", lambda s: None)
    answers = Answers(http_error(503), http_error(503), http_error(503), http_error(503))
    monkeypatch.setattr(expected.urllib.request, "urlopen", answers)
    with pytest.raises(urllib.error.HTTPError):
        expected.http_get("https://api.invalid")
    assert answers.calls == expected.TRIES == 3
    answers = Answers(http_error(400))
    monkeypatch.setattr(expected.urllib.request, "urlopen", answers)
    with pytest.raises(urllib.error.HTTPError):
        expected.http_get("https://api.invalid")
    assert answers.calls == 1
