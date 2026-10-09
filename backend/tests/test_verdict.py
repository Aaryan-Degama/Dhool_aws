"""Verdict rules on hand-built series: each case is one pattern the rules must name correctly."""
import numpy as np
import pandas as pd
import pytest

from dhool.verdict import verdict

DAYS = pd.date_range("2026-01-01", periods=120, freq="D", tz="Asia/Kolkata")
NO_RAIN = pd.Series(0.0, index=DAYS)
DRY_WEEK = [0.0] * 7


def home(factor, days=DAYS, seed=0):
    """A 3 kW roof expecting 14 kWh a day, running at 93% of the physics, times `factor`, with 1% noise."""
    noise = np.random.default_rng(seed).normal(1.0, 0.01, len(days))
    return pd.DataFrame({"expected": 14.0, "actual": 14.0 * 0.93 * np.asarray(factor) * noise}, index=days)


def healthy_neighbours(n=6):
    return pd.DataFrame({f"n{i}": home(np.ones(len(DAYS)), seed=10 + i).eval("actual / expected") for i in range(n)})


def dust(rate, reset_day):
    """Dust building at `rate` per day, washed off on `reset_day`."""
    days_dirty = np.where(np.arange(len(DAYS)) < reset_day, np.arange(len(DAYS)), np.arange(len(DAYS)) - reset_day)
    return 1 - rate * days_dirty


def rain_on(day):
    rain = NO_RAIN.copy()
    rain.iloc[day] = 20.0
    return rain


def test_healthy_roof_is_ok():
    v = verdict(home(np.ones(120)), NO_RAIN, DRY_WEEK)
    assert (v["verdict"], v["cause"]) == ("OK", "ok")
    assert v["loss_rs_per_week"] < 20


def test_sawtooth_with_no_rain_coming_is_clean():
    v = verdict(home(dust(0.004, reset_day=80)), rain_on(80), DRY_WEEK, neighbours=healthy_neighbours())
    assert (v["verdict"], v["cause"], v["confidence"]) == ("CLEAN", "dust", "high")
    assert v["evidence"]["rate_pct_per_day"] == pytest.approx(0.4, abs=0.1)
    assert abs(v["evidence"]["days_since_clean"] - 39) <= 1
    assert 12 < v["loss_pct"] < 18 and v["loss_kwh_per_day"] > 1.5 and v["loss_rs_per_week"] > 70


def test_dust_with_rain_coming_is_wait():
    v = verdict(home(dust(0.004, reset_day=80)), rain_on(80), [0.0, 12.0, 0.0])
    assert (v["verdict"], v["cause"]) == ("WAIT", "dust")


def test_rain_in_five_days_is_too_far_to_wait_for():
    v = verdict(home(dust(0.004, reset_day=80)), rain_on(80), [0.0, 0.0, 0.0, 0.0, 12.0])
    assert v["verdict"] == "CLEAN"


def test_step_drop_that_stays_is_inspect():
    factor = np.ones(120)
    factor[90:] = 0.67  # one of three strings dies on day 90
    v = verdict(home(factor), NO_RAIN, DRY_WEEK, neighbours=healthy_neighbours())
    assert (v["verdict"], v["cause"], v["confidence"]) == ("INSPECT", "fault", "high")
    assert abs((pd.Timestamp(v["evidence"]["step_date"], tz="Asia/Kolkata") - DAYS[90]).days) <= 1
    assert v["evidence"]["drop_pct"] == pytest.approx(33, abs=3)


def test_fault_is_still_inspect_after_rain():
    factor = np.ones(120)
    factor[60:] = 0.67
    v = verdict(home(factor * dust(0.003, reset_day=100)), rain_on(100), DRY_WEEK)
    assert v["verdict"] == "INSPECT"


def test_haze_with_neighbours_down_is_wait_not_inspect():
    haze = np.ones(120)
    haze[114:] = 0.82  # the whole area dims for the last six days
    neighbours = pd.DataFrame({f"n{i}": home(haze, seed=10 + i).eval("actual / expected") for i in range(6)})
    pm25 = pd.Series(80.0, index=DAYS)
    pm25.iloc[114:] = 330.0
    v = verdict(home(haze), NO_RAIN, DRY_WEEK, pm25=pm25, neighbours=neighbours)
    assert (v["verdict"], v["cause"]) == ("WAIT", "haze")
    assert v["evidence"]["pm25"] == 330


def test_same_drop_alone_with_clean_air_is_inspect():
    alone = np.ones(120)
    alone[110:] = 0.82
    v = verdict(home(alone), NO_RAIN, DRY_WEEK, pm25=pd.Series(80.0, index=DAYS), neighbours=healthy_neighbours())
    assert v["verdict"] == "INSPECT"


def test_repeated_one_day_dips_are_inspect():
    factor = np.ones(120)
    factor[[95, 103, 112]] = 0.5
    v = verdict(home(factor), NO_RAIN, DRY_WEEK, neighbours=healthy_neighbours())
    assert (v["verdict"], v["cause"]) == ("INSPECT", "trips")
    assert len(v["evidence"]["dip_days"]) == 3


def fault_from(day):
    factor = np.ones(120)
    factor[day:] = 0.67
    return factor


@pytest.mark.parametrize("factor", [np.ones(120), dust(0.004, reset_day=80), fault_from(90),
                                    fault_from(8)],  # nearly all the history is after the fault
                         ids=["ok", "dust", "fault", "early-fault"])
def test_the_figures_shown_together_add_up(factor):
    """Should have made, made, and the loss a day sit side by side on the Why tab: the subtraction must work,
    against this roof's own normal (not the physics, which no roof reaches), and match the percentage."""
    v = verdict(home(factor), NO_RAIN, DRY_WEEK)
    assert v["expected_kwh"] - v["actual_kwh"] == pytest.approx(v["loss_kwh_per_day"], abs=0.006)
    assert 12 < v["expected_kwh"] < 14  # 14 kWh of physics, at what this roof normally runs at (about 93%)
    assert v["actual_kwh"] / v["expected_kwh"] == pytest.approx(1 - v["loss_pct"] / 100, abs=0.02)
    assert v["loss_rs_per_week"] == round(v["loss_kwh_per_day"] * 7 * 7)


def test_too_little_data_is_wait():
    v = verdict(home(np.ones(5), days=DAYS[:5]), NO_RAIN[:5], DRY_WEEK)
    assert (v["verdict"], v["cause"], v["confidence"]) == ("WAIT", "no_data", "low")


def test_unclear_loss_defaults_to_wait():
    factor = np.ones(120)
    factor[40:] = 0.93  # a small lasting loss: too small to call a fault, no slope to call dust
    v = verdict(home(factor), NO_RAIN, DRY_WEEK)
    assert (v["verdict"], v["cause"], v["confidence"]) == ("WAIT", "unclear", "low")


def test_today_is_measured_along_the_trend_not_three_days_ago():
    """24 days of dust at 0.3% a day is 7.2% today, about 6.3% against a normal that itself carries a few
    days of dust. A week's median alone describes three days ago and would read 5.4%."""
    rains = [0, 32, 64, 95]
    since_rain = np.array([d - max(r for r in rains if r <= d) for d in range(120)])
    rain = NO_RAIN.copy()
    rain.iloc[rains] = 20.0
    v = verdict(home(1 - 0.003 * since_rain), rain, DRY_WEEK)
    assert (v["verdict"], v["cause"]) == ("CLEAN", "dust") and 5.8 <= v["loss_pct"] <= 7.5


def test_rain_yesterday_is_ok_until_clear_days_confirm_it():
    v = verdict(home(dust(0.003, reset_day=119)), rain_on(119), DRY_WEEK)  # 12% of dust until the last day's rain
    assert (v["verdict"], v["confidence"], v["evidence"]) == ("OK", "medium", {"cleaned_on": str(DAYS[119].date())})


def test_a_fault_is_found_even_when_rain_lifts_the_whole_area_that_week():
    lifted = dust(0.003, reset_day=90)  # everyone's dust is rinsed off on day 90...
    neighbours = pd.DataFrame({f"n{i}": home(lifted, seed=10 + i).eval("actual / expected") for i in range(6)})
    v = verdict(home(lifted * fault_from(90)), rain_on(90), DRY_WEEK, neighbours=neighbours)  # ...the day a string dies
    assert (v["verdict"], v["cause"]) == ("INSPECT", "fault")


def test_a_noisy_healthy_roof_alone_is_not_sent_to_the_vendor():
    """Real roofs scatter 3 to 8% a day around the physics, with whole weeks the weather data gets wrong."""
    rng = np.random.default_rng(3)
    factor = rng.normal(1.0, 0.05, 120) * np.repeat(rng.normal(1.0, 0.04, 18), 7)[:120]
    factor[[60, 75, 97, 110]] *= 0.6  # clouds the forecast missed, not inverter trips
    assert verdict(home(factor), NO_RAIN, DRY_WEEK)["verdict"] != "INSPECT"


WASH = [{"date": str(DAYS[100].date()), "type": "wash"}]


def test_a_wash_that_worked_is_verified():
    v = verdict(home(dust(0.004, reset_day=100)[:110], days=DAYS[:110]), NO_RAIN[:110], DRY_WEEK, actions=WASH)
    check = v["check"]
    assert (check["status"], check["type"], check["date"]) == ("verified", "wash", WASH[0]["date"])
    assert check["predicted_pct"] == pytest.approx(60, abs=6) and check["observed_pct"] == pytest.approx(58, abs=6)
    assert v["verdict"] == "OK"


def test_a_wash_is_waiting_until_three_clear_days_follow():
    v = verdict(home(dust(0.004, reset_day=100)[:102], days=DAYS[:102]), NO_RAIN[:102], DRY_WEEK, actions=WASH)
    assert (v["check"]["status"], v["check"]["observed_pct"], v["verdict"]) == ("waiting", None, "OK")


def test_a_wash_that_changed_nothing_means_it_was_not_dust():
    factor = np.linspace(1.0, 0.85, 120)  # a slow slide that washing does not touch
    v = verdict(home(factor), NO_RAIN, DRY_WEEK, actions=WASH)
    assert (v["verdict"], v["cause"], v["check"]["status"]) == ("INSPECT", "not_dust", "not_recovered")


def test_no_reported_action_means_no_check():
    assert verdict(home(np.ones(120)), NO_RAIN, DRY_WEEK)["check"] is None
