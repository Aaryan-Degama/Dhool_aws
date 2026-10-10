"""Verdict rules on hand-built series: each case is one pattern the rules must name correctly."""
import json

import numpy as np
import pandas as pd
import pytest

from dhool.verdict import verdict, wash_plan

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


def test_rain_in_five_days_is_still_worth_waiting_for_on_a_small_loss():
    """8% of a 3 kW roof is about ₹7 a day: four days of that does not pay for a wash the rain will do free."""
    v = verdict(home(dust(0.002, reset_day=80)), rain_on(80), [0.0, 0.0, 0.0, 0.0, 12.0])
    assert (v["verdict"], v["cause"], v["evidence"]["wait_for"]) == ("WAIT", "dust", "rain")
    assert v["evidence"]["saving_rs"] < v["evidence"]["wash_cost_rs"] == 50


def test_a_heavy_loss_is_washed_even_with_rain_five_days_off():
    v = verdict(home(dust(0.006, reset_day=80)), rain_on(80), [0.0, 0.0, 0.0, 0.0, 12.0])  # 23% down, ₹20 a day
    assert v["verdict"] == "CLEAN" and "before the rain on" in v["reason"] and v["evidence"]["saving_rs"] >= 50


def test_a_dust_storm_coming_means_wash_after_it():
    v = verdict(home(dust(0.004, reset_day=80)), rain_on(80), DRY_WEEK, dust_storms=[False, True, False])
    assert (v["verdict"], v["evidence"]["wait_for"]) == ("WAIT", "dust_storm") and "Wait and wash once after it" in v["reason"]


@pytest.mark.parametrize("loss,kwh,rain,storms,wash,wait_for,in_days", [
    (0.10, 13.0, [0] * 7, [], True, None, None),                  # ₹9 a day for a dry month: wash
    (0.10, 13.0, [0, 9, 0], [], False, "rain", 2),                # rain the day after tomorrow: one day's saving
    (0.10, 13.0, [0, 0, 0, 0, 0, 0, 9], [], True, None, 7),       # rain a week off: six days at ₹9 pays
    (0.10, 13.0, [0] * 7, [False, False, True], False, "dust_storm", 3),
    (0.05, 4.3, [0] * 7, [], False, "not_worth_it", 3),           # a 1 kW roof: ₹1.50 a day, ₹45 over a dry month
    (0.25, 4.3, [0] * 7, [], True, None, None),                   # the same roof once it is really dirty
])
def test_wash_plan_weighs_saving_against_the_cost_of_a_wash(loss, kwh, rain, storms, wash, wait_for, in_days):
    plan = wash_plan(loss, 0.002, kwh, rain, storms)
    assert (plan["wash"], plan["wait_for"], plan["in_days"]) == (wash, wait_for, in_days)


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


def off_for(days):
    factor = np.ones(120)
    factor[120 - days:] = 0.0  # a healthy roof, then nothing at all in good sun
    return factor


@pytest.mark.parametrize("neighbours", [None, healthy_neighbours()], ids=["alone", "neighbours"])
def test_a_sunny_day_at_zero_is_an_outage_not_all_good(neighbours):
    v = verdict(home(off_for(1)), NO_RAIN, DRY_WEEK, neighbours=neighbours)
    assert (v["verdict"], v["cause"], v["confidence"]) == ("INSPECT", "outage", "high")
    assert v["evidence"] == {"outage_days": 1, "since": str(DAYS[-1].date())}
    assert v["actual_kwh"] == 0 and v["loss_kwh_per_day"] == v["expected_kwh"] > 0  # the units agree with the 100%
    assert v["loss_pct"] == 100 and v["loss_rs_per_week"] > 0
    assert "made almost nothing on 30 Apr" in v["reason"] and "30 अप्रैल को" in v["reason_hi"]


def test_three_days_off_are_counted_from_the_first():
    v = verdict(home(off_for(3)), NO_RAIN, DRY_WEEK)
    assert (v["cause"], v["evidence"]) == ("outage", {"outage_days": 3, "since": str(DAYS[-3].date())})
    assert "has made almost nothing since 28 Apr" in v["reason"]


def test_a_power_cut_that_takes_the_whole_area_down_is_not_this_roofs_outage():
    neighbours = pd.DataFrame({f"n{i}": home(off_for(1), seed=10 + i).eval("actual / expected") for i in range(6)})
    assert verdict(home(off_for(1)), NO_RAIN, DRY_WEEK, neighbours=neighbours)["cause"] != "outage"


def test_a_dark_last_day_at_zero_is_not_an_outage():
    series = home(off_for(1))
    series.loc[DAYS[-1], "expected"] = 3.0  # heavy cloud: too dark a day to judge anything by
    assert verdict(series, NO_RAIN, DRY_WEEK)["cause"] != "outage"


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


def test_a_wash_reported_today_after_the_last_reading_is_taken_in_and_awaited():
    """The app's date box starts at today and readings end yesterday: the report must not vanish."""
    today = [{"date": str((DAYS[109] + pd.Timedelta(days=1)).date()), "type": "wash"}]
    dusty = home((1 - 0.004 * np.arange(120))[:110], days=DAYS[:110])
    assert verdict(dusty, NO_RAIN[:110], DRY_WEEK)["verdict"] == "CLEAN"
    v = verdict(dusty, NO_RAIN[:110], DRY_WEEK, actions=today)
    assert (v["verdict"], v["check"]["status"], v["check"]["date"], v["check"]["days_after"]) == ("OK", "waiting", today[0]["date"], 0)
    assert "Your wash on" in v["reason"]


def test_a_vendor_visit_reported_today_keeps_the_fault_and_waits_for_proof():
    factor = np.ones(120)
    factor[60:] = 0.67
    today = [{"date": str((DAYS[-1] + pd.Timedelta(days=1)).date()), "type": "visit"}]
    v = verdict(home(factor), NO_RAIN, DRY_WEEK, actions=today)
    assert (v["verdict"], v["cause"], v["check"]["type"], v["check"]["status"]) == ("INSPECT", "fault", "visit", "waiting")


def test_no_reported_action_means_no_check():
    assert verdict(home(np.ones(120)), NO_RAIN, DRY_WEEK)["check"] is None


def test_heavy_dust_is_named_within_days_of_the_rain_that_cleaned_the_roof():
    """Beside a dust source a roof loses over 1% a day: ten days after rain it is 14% down and should be washed."""
    v = verdict(home(dust(0.014, reset_day=110) * np.where(np.arange(120) < 110, 0, 1) + np.where(np.arange(120) < 110, 1, 0)),
                rain_on(110), DRY_WEEK)
    assert (v["verdict"], v["cause"]) == ("CLEAN", "dust") and 10 <= v["loss_pct"] <= 16


def test_a_gentle_wobble_over_a_week_is_not_called_dust():
    factor = np.ones(120)
    factor[112:] = 1 - 0.003 * np.arange(8)  # 2% over the last week: a week is too short to trust that
    assert verdict(home(factor), rain_on(111), DRY_WEEK)["verdict"] == "OK"


def test_the_owners_two_cases_wash_before_a_storm_only_if_the_loss_beats_one_wash():
    """A storm in a week means washing again afterwards either way. Missing ₹200 against a ₹350 wash: wait
    (₹550 against ₹700). Missing ₹600: wash now (₹700 against ₹950)."""
    storm = [False] * 6 + [True]
    small = wash_plan(0.10, 0.002, 200 / 6 / 0.10 / 7, [0] * 7, storm, cost=350)   # ₹200 over the 6 days before it
    large = wash_plan(0.10, 0.002, 600 / 6 / 0.10 / 7, [0] * 7, storm, cost=350)   # ₹600
    assert (small["wash"], small["wait_for"], small["saving_rs"]) == (False, "dust_storm", 200)
    assert (large["wash"], large["saving_rs"]) == (True, 600)


def test_a_dearer_wash_turns_wash_now_into_not_worth_it_yet():
    series, rain = home(dust(0.004, reset_day=80)), rain_on(80)
    assert verdict(series, rain, DRY_WEEK)["verdict"] == "CLEAN"
    v = verdict(series, rain, DRY_WEEK, wash_cost=2000)
    assert (v["verdict"], v["evidence"]["wait_for"], v["evidence"]["wash_cost_rs"]) == ("WAIT", "not_worth_it", 2000)
    assert "₹2000" in v["reason"]


def test_a_higher_tariff_raises_what_the_dust_costs_not_what_a_wash_costs():
    series, rain = home(dust(0.004, reset_day=80)), rain_on(80)
    usual, dear = verdict(series, rain, DRY_WEEK), verdict(series, rain, DRY_WEEK, tariff=14)
    assert (usual["tariff_rs"], dear["tariff_rs"]) == (7.0, 14)
    assert dear["evidence"]["saving_rs"] == pytest.approx(2 * usual["evidence"]["saving_rs"], abs=1)
    assert dear["loss_rs_per_week"] == pytest.approx(2 * usual["loss_rs_per_week"], abs=1)
    assert f"₹{dear['evidence']['saving_rs']} " in dear["reason"] and "₹50" in dear["reason"]
    assert dear["evidence"]["wash_cost_rs"] == usual["evidence"]["wash_cost_rs"] == 50


def test_every_reason_reads_in_hindi_with_the_same_figures_as_the_english():
    import re
    import string
    from dhool.reasons import REASONS, say
    day = pd.Timestamp("2026-08-17")  # a Monday
    for key, text in REASONS.items():
        names = {name for _, name, _, _ in string.Formatter().parse(text["en"]) if name}
        assert names == {name for _, name, _, _ in string.Formatter().parse(text["hi"]) if name}, key
        figures = {name: day if name in ("day", "on") else say("by_rain") if name in ("by", "until", "storm", "later")
                   else 0.37 if name in ("drop", "loss", "rate", "fell") else 41 + i for i, name in enumerate(sorted(names))}
        said = say(key, **figures)
        number = r"₹?\d+(?:\.\d+)?%?"
        assert sorted(re.findall(number, said["en"])) == sorted(re.findall(number, said["hi"])), key
        assert re.search(r"[ऀ-ॿ]", said["hi"]) and not re.search(r"[ऀ-ॿ]", said["en"]), key
    assert say("until_rain", on=day) == {"en": "before the rain on Monday", "hi": "सोमवार की बारिश से पहले"}
    assert say("fault", drop=0.33, day=day, days=40)["hi"].startswith("17 अगस्त के आसपास")


def test_a_roof_that_has_only_ever_read_zero_is_an_outage_not_a_crash():
    v = verdict(home(pd.Series(0.0, index=DAYS)), NO_RAIN, DRY_WEEK)
    assert (v["verdict"], v["cause"], v["evidence"]["since"]) == ("INSPECT", "outage", str(DAYS[0].date()))
    json.dumps(v, allow_nan=False)


@pytest.mark.parametrize("every", [3, 4, 5])
def test_readings_days_apart_are_not_enough_and_never_a_nan(every):
    actual = pd.Series(np.nan, index=DAYS)
    actual.iloc[::every] = 0.9 * 12
    v = verdict(pd.DataFrame({"expected": 12.0, "actual": actual}, index=DAYS), NO_RAIN, DRY_WEEK)
    assert (v["verdict"], v["cause"]) == ("WAIT", "no_data")
    json.dumps(v, allow_nan=False)


def test_a_roof_far_under_its_size_from_the_first_day_is_flagged():
    assert verdict(home(pd.Series(0.5, index=DAYS)), NO_RAIN, DRY_WEEK)["low_normal"] is True
    assert verdict(home(pd.Series(0.9, index=DAYS)), NO_RAIN, DRY_WEEK)["low_normal"] is False
