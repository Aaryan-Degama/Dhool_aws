"""CLEAN / INSPECT / WAIT / OK from daily actual against expected output.

Physics and plain rules only: no model makes this decision, and every verdict carries the reason
and the numbers behind it. The rules, in order:

1. Sudden drop that never recovers, and the area did not drop with it  -> fault  -> INSPECT
2. Sharp one-day dips that come back, several in a month               -> trips  -> INSPECT
3. Rain or a reported wash in the last day or two, too soon to measure  -> OK
4. Within a few percent of this roof's own normal                      -> OK
5. Air is hazy and the area dropped together                           -> haze   -> WAIT
6. The homeowner washed the panels and output did not come back        -> not dust -> INSPECT
7. Slow steady decline since the last rain or wash                     -> dust   -> CLEAN if a wash
   pays for itself before rain or a dust storm undoes it (see wash_plan), otherwise WAIT
8. Anything else                                                       -> WAIT, low confidence

"Now" is measured since the panels were last cleaned (rain, a wash the homeowner reported, or a jump
in the data), and moved forward along the recent trend: a week's median describes the roof about
three days ago, which hides the newest dust and, right after rain, still shows the old dirt.
"""
import numpy as np
import pandas as pd

from . import config

MIN_DAYS = 14          # days of data needed to learn a roof's normal
STEP_DROP = 0.90       # a week's median this far below the week before is a sudden drop
STAYS_DOWN = 0.92      # ...and it is a fault if output never climbs back above this share of before
AREA_DROP = 0.95       # neighbours' median falling this far means the whole area dropped
WASH_JUMP = 1.05       # a week's median this far above the week before means the panels got cleaned
DIP = 0.75             # one day this far below the days around it is a sharp dip
OK_LOSS = 0.05         # losses under this are not worth acting on
MIN_DUST_RATE = 0.001  # share of output lost per day before a decline counts as dust
TREND_DAYS = 30        # the dust rate is also read off just these recent days, so one missed wash cannot hide it
LONG_TREND_DAYS = 120  # ...and off the whole spell since cleaning, so a hazy fortnight cannot hide it either
MIN_TREND_DAYS = 14    # days for a rate to be trusted on its own
SHORT_TREND_DAYS = 7   # fewer than MIN_TREND_DAYS still count when the slide is steep: see _trend
MIN_AFTER = 3          # clear days needed after a wash, visit or rain before its effect can be measured
MIN_RECOVERY = 0.02    # a wash or repair that brought back less than this did nothing measurable


def _ratio(daily):
    ratio = daily["actual"] / daily["expected"]
    return ratio.where(daily["expected"] >= 0.3 * daily["expected"].median())  # very dark days are too noisy


def _steps(ratio, how="median"):
    """Per day: the median (or mean) of that day and the 6 after, over that of the 7 days before."""
    before = getattr(ratio.rolling(7, min_periods=4), how)().shift(1)
    after = getattr(ratio[::-1].rolling(7, min_periods=4), how)()[::-1]
    return after / before


def normal(ratio):
    """A roof's own normal: its best weeks. Weekly medians, not single days, so a noisy roof's lucky days
    do not set a normal it can never reach."""
    return float(ratio.rolling(7, min_periods=4).median().quantile(0.9))


def wash_plan(loss, rate, normal_kwh, rain_forecast, dust_storms=(), clean_mm=config.CLEAN_RAIN_MM):
    """Is washing worth it today? A wash wins back today's dust loss every day until something undoes it:
    rain (which would have cleaned the panels for free) or a dust storm (which dirties them again).

    loss: share of normal output lost to dust now. rate: share lost per extra day. normal_kwh: what the roof
    makes in a day when clean. rain_forecast: mm for the coming days, tomorrow first. dust_storms: True for
    each coming day with a dust storm forecast. Returns {"wash", "saving_rs", "wait_for", "in_days"}.
    """
    per_day = loss * normal_kwh * config.TARIFF_RS
    rain = next((i + 1 for i, mm in enumerate(rain_forecast) if mm >= clean_mm), None)
    storm = next((i + 1 for i, hit in enumerate(dust_storms) if hit), None)
    end = min((d for d in (rain, storm) if d), default=None)
    # Dust builds at the same rate washed or not, so the gap a wash opens stays what it removed today.
    saving = per_day * ((end - 1) if end else config.DRY_SPELL_DAYS)
    plan = {"wash": bool(saving >= config.WASH_COST_RS), "saving_rs": round(saving), "wait_for": None, "in_days": end}
    if not plan["wash"]:
        plan["wait_for"] = "rain" if end and end == rain else "dust_storm" if end else "not_worth_it"
        if not end and rate > 0:  # how long until the dust is costing enough to repay a wash
            worth = config.WASH_COST_RS / (normal_kwh * config.TARIFF_RS * config.DRY_SPELL_DAYS)
            plan["in_days"] = max(1, int(np.ceil((worth - loss) / rate)))
    elif end:
        plan["wait_for"] = None
        plan["before"] = "rain" if end == rain else "dust_storm"
    return plan


def _trend(window, baseline):
    """Share of normal output lost per day over these days (positive = declining). Robust to odd days:
    the median slope over every pair of days (Theil-Sen), not a least-squares line."""
    if len(window) < SHORT_TREND_DAYS:
        return 0.0
    x, y = (window.index - window.index[0]).days.to_numpy(), window.to_numpy()
    i, j = np.triu_indices(len(x), 1)
    rate = -float(np.median((y[j] - y[i]) / (x[j] - x[i]))) / baseline
    # A week or two of days gives a shaky rate: a gentle one could be noise. A slide that has by itself
    # taken off an actionable share of output in that time (heavy dust, days after rain) is not.
    if len(window) < MIN_TREND_DAYS and rate * x[-1] < OK_LOSS:
        return 0.0
    return rate


def check_action(ratio, baseline, action):
    """Did a wash or a vendor visit work? Compares the week before it with the clear days after it.
    predicted: what a full return to this roof's normal would add. observed: what came back."""
    day = pd.Timestamp(action["date"], tz=ratio.index.tz)
    before = ratio[:day - pd.Timedelta(days=1)].dropna().tail(7)
    after = ratio[day + pd.Timedelta(days=1):].dropna().head(7)
    if len(before) < MIN_AFTER:
        return None  # nothing to compare with
    level = float(before.median())
    predicted = baseline / level - 1
    out = {"type": action["type"], "date": action["date"], "status": "waiting",
           "predicted_pct": round(100 * predicted, 1), "observed_pct": None, "days_after": len(after)}
    if len(after) >= MIN_AFTER:
        observed = float(after.median()) / level - 1
        out["observed_pct"] = round(100 * observed, 1)
        out["status"] = ("was_fine" if predicted < MIN_RECOVERY
                         else "verified" if observed >= max(MIN_RECOVERY, predicted / 2) else "not_recovered")
    return out


def verdict(daily, rain, rain_forecast, pm25=None, neighbours=None, actions=(), dust_storms=()):
    """daily: DataFrame[expected, actual] indexed by day, oldest first.
    rain: daily mm, same index. rain_forecast: mm for the coming days, tomorrow first.
    pm25: daily mean µg/m³ (optional). neighbours: DataFrame of actual/expected ratios, one column per
    nearby home (optional). actions: what the homeowner reported, [{"date": "YYYY-MM-DD", "type": "wash" | "visit"}].
    dust_storms: True for each coming day with a dust storm forecast, tomorrow first (optional).
    """
    ratio = _ratio(daily)
    valid = ratio.dropna()
    check = None

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
            "check": check,  # the latest wash or visit the homeowner reported, and whether it worked
        }

    if len(valid) < MIN_DAYS:
        baseline = 1.0
        return result("WAIT", "no_data", "low",
                      f"Only {len(valid)} days of data so far. Dhool needs about two weeks to learn this roof's normal.")

    baseline = normal(ratio)
    step = _steps(ratio)  # medians: robust for deciding whether a change happened
    sharp = _steps(ratio, "mean")  # means peak exactly on the day of the change: used to date it
    area_step = _steps(neighbours).median(axis=1).reindex(ratio.index) if neighbours is not None else None

    # When were the panels last cleaned, or the system last worked on? Rain is known from the weather, a
    # wash or visit from the homeowner, and an unreported wash shows as a jump in the data a few days later.
    rained = rain.reindex(ratio.index).fillna(0) >= config.CLEAN_RAIN_MM
    washed = (step >= WASH_JUMP) & (sharp == sharp.rolling(15, center=True, min_periods=1).max())
    if area_step is not None:
        washed &= ~(area_step >= WASH_JUMP)  # the whole area jumping up is haze lifting, not a wash
    told = pd.Series(False, index=ratio.index)
    actions = sorted((a for a in actions if pd.Timestamp(a["date"], tz=ratio.index.tz) in told.index), key=lambda a: a["date"])
    for action in actions:
        told[pd.Timestamp(action["date"], tz=ratio.index.tz)] = True
    cleaned = rained | washed | told
    last_clean = cleaned[cleaned].index[-1] if cleaned.any() else None
    since = (ratio[last_clean:] if last_clean is not None else ratio).dropna()
    measured = since if len(since) >= MIN_AFTER else valid  # too soon after a cleaning: fall back to the week
    week = measured.tail(7)
    rate = max(_trend(since.tail(TREND_DAYS), baseline), _trend(since.tail(LONG_TREND_DAYS), baseline))
    lag = (week.index[-1] - week.index[len(week) // 2]).days  # how old the week's median is
    recent = float(week.median()) - max(0.0, rate) * baseline * lag
    loss = max(0.0, 1 - recent / baseline)
    if actions:
        check = check_action(ratio, baseline, actions[-1])

    # 1. Fault: a sudden drop that the area did not share and that never recovered.
    # With neighbours, a roof's change is judged against theirs: a drop the whole area shares cancels out,
    # and a drop hidden by the area rising (rain rinsing everyone else's dust) still shows.
    if area_step is not None:
        own = step / area_step
        own_sharp = sharp / _steps(neighbours, "mean").median(axis=1).reindex(ratio.index)
    else:
        own, own_sharp = step, sharp
    # How much this roof's week-on-week level wanders when nothing is wrong (weather the forecast missed,
    # mostly). A drop has to stand well clear of that: on a steady roof 10% is enough, on a noisy one it is not.
    wander = float(1.4826 * (np.log(own.dropna()) - np.log(own.dropna()).median()).abs().median()) if own.notna().sum() >= 14 else 0.0
    step_drop = min(STEP_DROP, 1 - 4 * wander)
    stays_down = min(STAYS_DOWN, 1 - 3 * wander)
    sudden = (own <= step_drop) & (own_sharp == own_sharp.rolling(15, center=True, min_periods=1).min())
    if area_step is None and pm25 is not None:
        hazy_week = pm25.reindex(ratio.index)[::-1].rolling(7, min_periods=1).mean()[::-1] >= config.HAZE_PM25
        sudden &= ~hazy_week
    for day in step[sudden].index:
        pre, post = ratio[:day].iloc[:-1].dropna(), ratio[day:].dropna()
        if len(pre) < 7 or len(post) < 4:
            continue
        level_before = normal(pre)
        if post.rolling(7, min_periods=4).median().max() / level_before > stays_down:
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

    # 2. Trips: sharp one-day dips that recover, which the area did not share. Only with neighbours: on its
    # own, a roof's one-day dip is usually a cloud the weather data missed, and daily totals cannot tell.
    dips = (ratio / ratio.rolling(7, center=True, min_periods=4).median() <= DIP).tail(30)
    if neighbours is not None:
        area_dip = (neighbours / neighbours.rolling(7, center=True, min_periods=4).median()).median(axis=1) <= 0.9
        dips &= ~area_dip.reindex(dips.index, fill_value=False)
    if neighbours is not None and dips.sum() >= 2:
        return result(
            "INSPECT", "trips", "medium",
            f"Output dropped sharply on {int(dips.sum())} separate days in the last 30 and came back each time. "
            "This can be the inverter shutting down for part of the day.",
            loss=loss, dip_days=[str(d.date()) for d in dips[dips].index])

    # 3. Just cleaned: rain or a reported wash in the last day or two. The week's median still shows the dirt
    # from before, so say what is known and measure again once clear days come in.
    if last_clean is not None and len(since) < MIN_AFTER and (rained | told)[last_clean]:
        loss = 0.0
        by = "Rain" if rained[last_clean] else "Your wash" if actions[-1]["type"] == "wash" else "The vendor's visit"
        return result("OK", "ok", "medium",
                      f"{by} on {last_clean:%-d %b} should have brought the panels back. Dhool will confirm it "
                      "over the next few clear days.", cleaned_on=str(last_clean.date()))

    # 4. Near this roof's normal.
    if loss < OK_LOSS:
        return result("OK", "ok", "high",
                      f"Your roof is producing what it should: within {max(loss, 0.01):.0%} of its normal.", loss=loss)

    # 5. Haze: bad air, and the area fell together in the last few days.
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

    # 6. The homeowner washed the panels and output stayed down: whatever this is, it is not dust.
    if check and check["type"] == "wash" and check["status"] == "not_recovered":
        return result(
            "INSPECT", "not_dust", "medium",
            f"You washed the panels on {pd.Timestamp(check['date']):%-d %b}, but output is still about {loss:.0%} below "
            "this roof's normal. Dust was not the cause, so have the system inspected.", loss=loss)

    # 7. Dust: a steady decline since the panels were last cleaned by rain or by hand.
    if len(since) >= SHORT_TREND_DAYS:
        days = int((since.index[-1] - since.index[0]).days)
        if rate >= MIN_DUST_RATE:
            normal_kwh = baseline * float(daily["expected"].tail(7).mean())
            plan = wash_plan(loss, rate, normal_kwh, rain_forecast, dust_storms)
            per_day = round(loss * normal_kwh * config.TARIFF_RS)
            cost = round(config.WASH_COST_RS)
            on = (ratio.index[-1] + pd.Timedelta(days=plan["in_days"] or 0)).strftime("%A")
            evidence = {"rate_pct_per_day": round(100 * rate, 2), "days_since_clean": days,
                        "saving_rs": plan["saving_rs"], "wash_cost_rs": cost}
            if plan["wash"]:
                until = (f"before the {'rain' if plan['before'] == 'rain' else 'dust storm'} on {on}" if plan["in_days"]
                         else f"over the next {config.DRY_SPELL_DAYS} days if it stays dry")
                return result(
                    "CLEAN", "dust", "high" if days >= 14 and loss >= 0.08 else "medium",
                    f"Output has slipped about {rate:.1%} a day for {days} days since the panels were last cleaned, "
                    f"and is now {loss:.0%} below this roof's normal. Washing now saves about ₹{plan['saving_rs']} "
                    f"{until}, more than the ₹{cost} or so a wash costs in water and effort.",
                    loss=loss, **evidence)
            evidence["wait_for"] = plan["wait_for"]
            if plan["wait_for"] == "rain":
                reason = (f"Dust has cut output by about {loss:.0%} over {days} days, but rain is forecast on {on} and will "
                          f"wash the panels for free. Washing today would save only about ₹{plan['saving_rs']} before then.")
            elif plan["wait_for"] == "dust_storm":
                reason = (f"Dust has cut output by about {loss:.0%} over {days} days, but a dust storm is forecast on {on} "
                          "and would dirty the panels again. Wash after it, not before: washing today would save only "
                          f"about ₹{plan['saving_rs']}.")
            else:
                later = f" At this rate it will be in about {plan['in_days']} days." if plan["in_days"] else ""
                reason = (f"Dust is costing about ₹{per_day} a day, {loss:.0%} of this roof's output. A wash costs about "
                          f"₹{cost} in water and effort, so it is not worth it yet.{later}")
                evidence["worth_it_in_days"] = plan["in_days"]
            return result("WAIT", "dust", "medium", reason, loss=loss, **evidence)

    # 8. Something is off but the pattern is not clear. Say so, and don't send anyone up to the roof.
    return result("WAIT", "unclear", "low",
                  f"Output is about {loss:.0%} below this roof's normal, but the pattern is not clear yet. "
                  "Dhool will check again as more days come in.", loss=loss,
                  rate_pct_per_day=round(100 * rate, 2), days_measured=len(since))
