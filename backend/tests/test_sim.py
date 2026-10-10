"""Physics and simulator checks on synthetic clear-sky weather. No network."""
import numpy as np
import pandas as pd
import pvlib
import pytest

from dhool import config
from dhool.evaluate import CLASSES, evaluate
from dhool.expected import expected_daily_kwh
from dhool.sim import simulate

LAT, LON = config.SIM_LAT, config.SIM_LON
RAIN_DAY = 60


@pytest.fixture(scope="module")
def weather():
    times = pd.date_range("2026-01-01", periods=120 * 24, freq="h", tz=config.TZ)
    sky = pvlib.location.Location(LAT, LON, config.TZ).get_clearsky(times, model="simplified_solis")
    sky["temp_air"], sky["wind_speed"], sky["rain"] = 25.0, 2.0, 0.0
    sky.loc[sky.index.normalize() == times[0].normalize() + pd.Timedelta(days=RAIN_DAY), "rain"] = 1.0  # 24 mm that day
    return sky


@pytest.fixture(scope="module")
def pm25(weather):
    days = weather["rain"].resample("D").sum().index
    series = pd.Series(60.0, index=days)
    series.iloc[100:105] = 350.0  # five hazy days
    return series


@pytest.fixture(scope="module")
def homes(weather, pm25):
    return simulate(weather, pm25, n_homes=8, seed=1)


def ratio(home):
    return home["daily"]["actual"] / home["daily"]["expected"]


def test_expected_is_plausible_and_scales_with_size(weather):
    one = expected_daily_kwh(weather, LAT, LON, 1)
    three = expected_daily_kwh(weather, LAT, LON, 3)
    assert 3 < one.mean() < 7  # a clear winter-to-spring day in Delhi, per kW
    assert three.mean() == pytest.approx(3 * one.mean(), rel=0.01)


def test_dust_builds_then_rain_resets_it(homes):
    home = homes["home-05"]  # dust only
    soiling = home["daily"]["soiling"]
    assert soiling.iloc[RAIN_DAY - 1] > soiling.iloc[RAIN_DAY]  # reset on the rain day
    assert soiling.iloc[RAIN_DAY] == pytest.approx(home["meta"]["soiling_rate"], abs=1e-4)
    r = ratio(home)
    assert r.iloc[RAIN_DAY + 1:RAIN_DAY + 4].mean() > r.iloc[RAIN_DAY - 4:RAIN_DAY - 1].mean()


def test_string_fault_is_a_step_that_stays(homes):
    home = homes["home-00"]
    faulty = home["daily"]["cause"] == "fault"
    onset = faulty.to_numpy().argmax()
    assert faulty.iloc[onset:].all() and not faulty.iloc[:onset].any()
    r = ratio(home)
    assert r.iloc[onset:onset + 10].mean() < 0.8 * r.iloc[onset - 10:onset].mean()


def test_haze_drops_every_home_together(homes):
    for home in homes.values():
        r = ratio(home)
        assert r.iloc[100:105].mean() < 0.9 * r.iloc[94:99].mean()


def test_same_seed_same_neighbourhood(weather, pm25, homes):
    again = simulate(weather, pm25, n_homes=8, seed=1)
    assert again["home-03"]["daily"].equals(homes["home-03"]["daily"])


def test_homes_sit_where_the_api_would_store_them(homes):
    """The API keeps a location to 2 decimals; the demo data must be made from weather at that same spot."""
    assert all(h["meta"][k] == round(h["meta"][k], 2) for h in homes.values() for k in ("lat", "lon"))


def test_weather_error_changes_what_each_roof_made_and_nothing_else(weather, pm25, homes):
    same = simulate(weather, pm25, n_homes=8, seed=1, weather_noise=0.0)
    assert all(same[h]["daily"].equals(homes[h]["daily"]) and same[h]["meta"] == homes[h]["meta"] for h in homes)
    noisy = simulate(weather, pm25, n_homes=8, seed=1, weather_noise=0.15)
    for h, home in homes.items():
        assert noisy[h]["meta"] == home["meta"]  # the answer key is untouched
        assert noisy[h]["daily"].drop(columns="actual").equals(home["daily"].drop(columns="actual"))
        assert 0.1 < np.log(noisy[h]["daily"]["actual"] / home["daily"]["actual"]).std() < 0.2


def test_scoring_alone_checks_the_same_days_against_the_same_truth(weather, pm25, homes):
    rain = weather["rain"].resample("D").sum()
    both, alone = evaluate(homes, rain, pm25), evaluate(homes, rain, pm25, alone=True)
    for truth in CLASSES:
        assert sum(both[truth, v] for v in CLASSES) == sum(alone[truth, v] for v in CLASSES)
    assert sum(both.values()) == 8 * 8 and both != alone  # 8 homes, 8 weekly checks each


def test_dusty_homes_are_added_without_changing_the_others(weather, pm25, homes):
    more = simulate(weather, pm25, n_homes=8, seed=1, dusty=2)
    assert list(more)[:8] == list(homes) and len(more) == 10
    assert all(more[h]["daily"].equals(homes[h]["daily"]) for h in homes)
    dusty = more["home-09"]
    assert dusty["meta"]["problem"] == "dust_source" and dusty["daily"]["soiling"].iloc[RAIN_DAY - 1] > 0.2
    assert dusty["daily"]["soiling"].iloc[RAIN_DAY] < 0.02  # rain still washes it
