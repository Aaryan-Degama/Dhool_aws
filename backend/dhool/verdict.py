"""CLEAN / INSPECT / WAIT / OK from daily actual against expected output.

Physics and plain rules only: no model makes this decision, and every verdict carries the reason
and the numbers behind it. The rules, in order:

1. Sudden drop that never recovers, and the area did not drop with it  -> fault  -> INSPECT
2. Sharp one-day dips that come back, several in a month               -> trips  -> INSPECT
3. Within a few percent of this roof's own normal                      -> OK
4. Air is hazy and the area dropped together                           -> haze   -> WAIT
5. Slow steady decline since the last rain or wash                     -> dust   -> CLEAN,
   or WAIT if rain is about to wash the panels for free
6. Anything else                                                       -> WAIT, low confidence
"""
import numpy as np

from . import config

MIN_DAYS = 14          # days of data needed to learn a roof's normal
STEP_DROP = 0.90       # a week's median this far below the week before is a sudden drop
STAYS_DOWN = 0.92      # ...and it is a fault if output never climbs back above this share of before
AREA_DROP = 0.95       # neighbours' median falling this far means the whole area dropped
WASH_JUMP = 1.05       # a week's median this far above the week before means the panels got cleaned
DIP = 0.75             # one day this far below the days around it is a sharp dip
OK_LOSS = 0.05         # losses under this are not worth acting on
MIN_DUST_RATE = 0.001  # share of output lost per day before a decline counts as dust
RAIN_SOON_DAYS = 2


def _ratio(daily):
    ratio = daily["actual"] / daily["expected"]
    return ratio.where(daily["expected"] >= 0.3 * daily["expected"].median())  # very dark days are too noisy


def _steps(ratio, how="median"):
    """Per day: the median (or mean) of that day and the 6 after, over that of the 7 days before."""
    before = getattr(ratio.rolling(7, min_periods=4), how)().shift(1)
    after = getattr(ratio[::-1].rolling(7, min_periods=4), how)()[::-1]
    return after / before


def verdict(daily, rain, rain_forecast, pm25=None, neighbours=None):
    """daily: DataFrame[expected, actual] indexed by day, oldest first.
    rain: daily mm, same index. rain_forecast: mm for the coming days, tomorrow first.
    pm25: daily mean µg/m³ (optional). neighbours: DataFrame of actual/expected ratios, one column per
    nearby home (optional).
    """
    ratio = _ratio(daily)
    valid = ratio.dropna()

    def result(verdict, cause, confidence, reason, loss=0.0, level=None, **evidence):
        # The figures the homeowner sees, a day on average over the last 7 days with a reading: what this
        # roof normally makes in that weather (its own normal, `level` times the physics, not the physics
        # alone), what it made, and the difference. The three are shown together, so they must add up.
        week = daily.tail(7).dropna()
        share = level or baseline
        normal = round(share * float(week["expected"].mean()), 2)
        made = round(float(week["actual"].mean()), 2)
        lost = 0.0 if cause == "no_data" else round(max(0.0, normal - made), 2)  # no normal known yet
        return {
            "verdict": verdict, "cause": cause, "confidence": confidence, "reason": reason,
            "normal_share": round(share, 3),  # this roof's normal as a share of the physics, for the chart and forecast
            "expected_kwh": normal,
            "actual_kwh": made,
            "loss_pct": round(100 * loss, 1),
            "loss_kwh_per_day": lost,
            "loss_rs_per_week": round(lost * 7 * config.TARIFF_RS),
            "evidence": evidence,
        }

    if len(valid) < MIN_DAYS:
        baseline = 1.0
        return result("WAIT", "no_data", "low",
                      f"Only {len(valid)} days of data so far. Dhool needs about two weeks to learn this roof's normal.")

    baseline = float(valid.quantile(0.9))  # this roof's own normal: its best recent days
    recent = float(valid.tail(7).median())
    loss = max(0.0, 1 - recent / baseline)
    step = _steps(ratio)  # medians: robust for deciding whether a change happened
    sharp = _steps(ratio, "mean")  # means peak exactly on the day of the change: used to date it
    area_step = _steps(neighbours).median(axis=1).reindex(ratio.index) if neighbours is not None else None

    # 1. Fault: a sudden drop that the area did not share and that never recovered.
    sudden = (step <= STEP_DROP) & (sharp == sharp.rolling(15, center=True, min_periods=1).min())
    if area_step is not None:
        sudden &= ~(area_step <= AREA_DROP)
    elif pm25 is not None:
        hazy_week = pm25.reindex(ratio.index)[::-1].rolling(7, min_periods=1).mean()[::-1] >= config.HAZE_PM25
        sudden &= ~hazy_week
    for day in step[sudden].index:
        pre, post = ratio[:day].iloc[:-1].dropna(), ratio[day:].dropna()
        if len(pre) < 7 or len(post) < 4:
            continue
        level_before = float(pre.quantile(0.9))
        if post.rolling(7, min_periods=4).median().max() / level_before > STAYS_DOWN:
            continue  # it came back, so not a lasting fault
        drop = 1 - float(post.tail(7).median()) / level_before
        confidence = "high" if len(post) >= 14 and neighbours is not None else "medium" if len(post) >= 7 else "low"
        return result(
            "INSPECT", "fault", confidence,
            f"Output fell about {drop:.0%} around {day:%-d %b} and has stayed down for {len(post)} days. "
            "Dust builds slowly and haze lifts, so this looks like a hardware fault, such as a failed "
            "string or new shading.",
            loss=max(loss, drop), level=max(baseline, level_before),  # the bigger loss is against the higher level
            step_date=str(day.date()), drop_pct=round(100 * drop, 1), days_down=len(post))

    # 2. Trips: sharp one-day dips that recover, which the area did not share.
    dips = (ratio / ratio.rolling(7, center=True, min_periods=4).median() <= DIP).tail(30)
    if neighbours is not None:
        area_dip = (neighbours / neighbours.rolling(7, center=True, min_periods=4).median()).median(axis=1) <= 0.9
        dips &= ~area_dip.reindex(dips.index, fill_value=False)
    if dips.sum() >= 2:
        return result(
            "INSPECT", "trips", "medium" if neighbours is not None else "low",
            f"Output dropped sharply on {int(dips.sum())} separate days in the last 30 and came back each time. "
            "This can be the inverter shutting down for part of the day.",
            loss=loss, dip_days=[str(d.date()) for d in dips[dips].index])

    # 3. Near this roof's normal.
    if loss < OK_LOSS:
        return result("OK", "ok", "high",
                      f"Your roof is producing what it should: within {max(loss, 0.01):.0%} of its normal.", loss=loss)

    # 4. Haze: bad air, and the area fell together in the last few days.
    if pm25 is not None and len(valid) >= 10:
        pm_now = float(pm25.tail(3).mean())
        if pm_now >= config.HAZE_PM25:
            if neighbours is not None:
                fell = float((neighbours.tail(3).median() / neighbours.iloc[-10:-3].median()).median())
            else:
                fell = float(valid.tail(3).median() / valid.iloc[-10:-3].median())
            if fell <= (0.96 if neighbours is not None else AREA_DROP):
                return result(
                    "WAIT", "haze", "medium" if neighbours is not None else "low",
                    f"The air is hazy (PM2.5 around {pm_now:.0f}) and output across the area fell about "
                    f"{1 - fell:.0%} in the last few days. Less sunlight is reaching the panels. "
                    "Washing won't help, so save the water.",
                    loss=loss, pm25=round(pm_now), area_drop_pct=round(100 * (1 - fell), 1))

    # 5. Dust: a steady decline since the panels were last cleaned by rain or by hand.
    rained = rain.reindex(ratio.index).fillna(0) >= config.CLEAN_RAIN_MM
    washed = (step >= WASH_JUMP) & (sharp == sharp.rolling(15, center=True, min_periods=1).max())
    if area_step is not None:
        washed &= ~(area_step >= WASH_JUMP)  # the whole area jumping up is haze lifting, not a wash
    cleaned = rained | washed
    since = (ratio[cleaned[cleaned].index[-1]:] if cleaned.any() else ratio).dropna()
    if len(since) >= 5:
        days = int((since.index[-1] - since.index[0]).days)
        rate = -float(np.polyfit((since.index - since.index[0]).days, since.to_numpy(), 1)[0]) / baseline
        if rate >= MIN_DUST_RATE:
            evidence = {"rate_pct_per_day": round(100 * rate, 2), "days_since_clean": days}
            if any(mm >= config.CLEAN_RAIN_MM for mm in rain_forecast[:RAIN_SOON_DAYS]):
                return result(
                    "WAIT", "dust", "medium",
                    f"Dust has cut output by about {loss:.0%} over {days} days, but rain is forecast within "
                    f"{RAIN_SOON_DAYS} days and will wash the panels for free.",
                    loss=loss, **evidence)
            return result(
                "CLEAN", "dust", "high" if days >= 14 and loss >= 0.08 else "medium",
                f"Output has slipped about {rate:.1%} a day for {days} days since the panels were last cleaned, "
                f"and is now {loss:.0%} below this roof's normal. No rain is forecast in the next "
                f"{len(rain_forecast)} days, so washing will pay off.",
                loss=loss, **evidence)

    # 6. Something is off but the pattern is not clear. Say so, and don't send anyone up to the roof.
    return result("WAIT", "unclear", "low",
                  f"Output is about {loss:.0%} below this roof's normal, but the pattern is not clear yet. "
                  "Dhool will check again as more days come in.", loss=loss)
