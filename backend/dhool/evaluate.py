"""Score the verdict rules against a simulated neighbourhood, where every day's true cause is known.

    python -m dhool.evaluate [seed]     the development neighbourhood (Delhi, the last 12 months)
    python -m dhool.evaluate hidden     the hidden test set

Each run prints four scores. The first is the best case: every home is compared with 29 neighbours, and the
weather data is exactly right about the sun over each roof. The other three take those away, one at a time
and then both: "alone" gives the rules no neighbours (what a home sending screenshots or typed numbers gets),
and "weather error" scales what each roof made by a random factor each day (see sim.simulate, weather_noise),
because gridded weather is never right about one roof. Quote the first number only with the others beside it.

The hidden test set is three other cities' real weather for a fixed past year, with every simulator setting
drawn afresh and wider than the rules were built against, and readings missing (see sim.simulate, hidden=True).
The rules were frozen before it was first run, and it is not used to tune them. If the rules change, run it
again and report the new number as it comes; never pick the better of two runs.

Under each score's accuracy line come more figures, all worked out from the same table of truth against
verdict:

Baseline: the accuracy of always giving the commonest true class in that table, whatever the readings say.
Most checks fall on a healthy roof, so accuracy is to be read against this. A tie goes to the class that
comes first in CLASSES.

F1, for each class: 2 x right / (2 x right + said wrongly + missed), which is the harmonic mean of its
precision and recall. A class that happened but was never said, or was said but never happened, has nothing
right and scores 0. A class that neither happened nor was said has no F1: it is printed as "none", never as
nan, and is left out of the mean below.

Macro-F1: the plain mean of the per-class F1s, each class counting the same however few its cases.

False alerts per roof per month. An alert is a check that said CLEAN or INSPECT, the two verdicts the app
sends to the phone. It is false when the truth was neither (OK or WAIT). Each roof is checked every 7 days,
so the figure is false alerts / all checks x (30.44 / 7). Every such check is counted. The app alerts only
when its advice changes, so a wrong verdict that stands for a month is one alert there and four here: for
wrong verdicts that last, this is an upper bound on what a household would get. It is not one for a wrong
verdict that comes and goes inside a week: the app looks every night and would alert each time it came
back. How often that happens is not measured here.

Wrong-action alerts: said CLEAN when the truth was INSPECT, or INSPECT when it was CLEAN. The roof did need
something, so these are not false alerts, but the advice was the wrong one. They are counted on their own
and are not among the false alerts.

The precision and recall lines print nan for a class that was never said (no precision) or never happened
(no recall). When one does, a line under the accuracy line says which is which.
"""

import datetime
import sys
from collections import Counter
from typing import Any

import pandas as pd

from . import config
from .expected import fetch_pm25, fetch_weather
from .sim import simulate
from .verdict import _ratio, check_action, normal, verdict, wash_plan

CLASSES = ["CLEAN", "INSPECT", "WAIT", "OK"]
HIDDEN_SEED = 20261003
HIDDEN_YEAR = ("2024-10-01", "2025-09-30")
HIDDEN_CITIES = {"Jaipur": (26.91, 75.79), "Lucknow": (26.85, 80.95), "Ahmedabad": (23.02, 72.57)}
WEATHER_NOISE = 0.15  # how far off the weather data is taken to be about one roof's sun, day to day
# The four scores of a run: title, weather error or not, alone or not. The first is the score as it always was.
VARIANTS = [
    ("with neighbours, no weather error", False, False),
    ("alone (no neighbours)", False, True),
    (f"with weather error (about {WEATHER_NOISE:.0%} a day)", True, False),
    ("alone, with weather error", True, True),
]
ALERTS = ("CLEAN", "INSPECT")  # the verdicts the app sends to the phone (notify.message)
CHECK_EVERY = 7  # days between two checks of a roof: evaluate()'s default, which every score here uses
DAYS_PER_MONTH = 30.44  # 365.25 / 12
Confusion = Counter[tuple[str, str]]  # (truth, verdict) -> how many checks; a name for the type, nothing more


def truth(home: dict[str, Any], i: int, rain: pd.Series) -> str:
    """What a perfect detector would say for this home on day i."""
    daily, problem = home["daily"], home["meta"]["problem"]
    faulty = daily["cause"].iloc[: i + 1] == "fault"
    if problem in ("string_fault", "shading") and faulty.iloc[-1]:
        return "INSPECT"
    if problem == "inverter_trips" and faulty.tail(30).sum() >= 2:
        return "INSPECT"
    if (daily["cause"].iloc[i - 2 : i + 1] == "haze").sum() >= 2:
        return "WAIT"
    if daily["soiling"].iloc[i] >= 0.05:
        # The same wash plan the rules use, but fed the truth: the real dust, the roof's real normal, and
        # how much rain it really takes to clean this roof. What is scored is the measuring, not the policy.
        meta = home["meta"]
        normal_kwh = meta["baseline"] * float(daily["expected"].iloc[i - 6 : i + 1].mean())
        plan = wash_plan(
            daily["soiling"].iloc[i],
            meta["soiling_rate"],
            normal_kwh,
            list(rain.iloc[i + 1 : i + 8]),
            clean_mm=meta.get("clean_mm", config.CLEAN_RAIN_MM),
        )
        return "CLEAN" if plan["wash"] else "WAIT"
    return "OK"


def evaluate(
    homes: dict[str, dict[str, Any]],
    rain: pd.Series,
    pm25: pd.Series,
    start: int = 60,
    every: int = 7,
    alone: bool = False,
) -> Confusion:
    """Returns Counter of (truth, verdict) pairs over every home, checked every `every` days.
    alone=True gives the rules no neighbours to compare with."""
    ratios = pd.DataFrame({hid: h["daily"]["actual"] / h["daily"]["expected"] for hid, h in homes.items()})
    confusion: Confusion = Counter()
    for hid, home in homes.items():
        others = None if alone else ratios.drop(columns=hid)
        for i in range(start, len(rain) - 7, every):
            got = verdict(
                home["daily"].iloc[: i + 1],
                rain.iloc[: i + 1],
                list(rain.iloc[i + 1 : i + 8]),
                pm25.iloc[: i + 1],
                # others is None only when alone, and then .iloc is not reached
                others if alone else others.iloc[: i + 1],  # type: ignore[union-attr]
            )
            confusion[truth(home, i, rain), got["verdict"]] += 1
    return confusion


def wash_checks(homes: dict[str, dict[str, Any]]) -> Counter[tuple[str, str]]:
    """The "I washed them" check against washes the simulator planted, reported a week later.
    Real washes of a dusty roof should come out verified; a wash that never happened on a roof with a
    dead string (the homeowner washed, it was not dust) should come out not recovered."""
    outcome: Counter[tuple[str, str]] = Counter()
    for home in homes.values():
        daily, days = home["daily"], home["daily"].index
        washed = [
            i
            for i in range(14, len(days) - 8)
            if str(days[i].date()) in home["meta"]["wash_days"]
            and daily["soiling"].iloc[i - 1] >= 0.05
            and daily["cause"].iloc[i] != "fault"
        ]
        faulty = (daily["cause"] == "fault").to_numpy()
        not_dust = (
            [int(faulty.argmax()) + 15] if home["meta"]["problem"] == "string_fault" and faulty.sum() > 30 else []
        )
        for i, kind in [(i, "real wash") for i in washed] + [(i, "wash of a faulty roof") for i in not_dust]:
            ratio = _ratio(daily.iloc[: i + 8])
            check = check_action(ratio, normal(ratio), {"date": str(days[i].date()), "type": "wash"})
            outcome[kind, check["status"] if check else "no data"] += 1
    return outcome


def report(confusion: Confusion) -> str:
    lines = ["truth \\ verdict  " + "".join(f"{c:>9}" for c in CLASSES)]
    for t in CLASSES:
        lines.append(f"{t:<16} " + "".join(f"{confusion[t, v]:>9}" for v in CLASSES))
    for c in CLASSES:
        said = sum(confusion[t, c] for t in CLASSES)
        actual = sum(confusion[c, v] for v in CLASSES)
        precision = confusion[c, c] / said if said else float("nan")
        recall = confusion[c, c] / actual if actual else float("nan")
        lines.append(f"{c:<8} precision {precision:.2f}  recall {recall:.2f}  (n={actual})")
    total = sum(confusion.values())
    lines.append(f"accuracy {sum(confusion[c, c] for c in CLASSES) / total:.2f} over {total} checks")
    # Everything above is printed as it always was, so old output can be laid beside new. New lines go below.
    return "\n".join(lines + beyond_accuracy(confusion))


def _said(confusion, c):
    return sum(confusion[t, c] for t in CLASSES)


def _actual(confusion, c):
    return sum(confusion[c, v] for v in CLASSES)


def baseline(confusion: Confusion) -> tuple[str, float]:
    """(class, accuracy) of always saying the commonest true class. A tie goes to the first in CLASSES."""
    commonest = max(CLASSES, key=lambda c: _actual(confusion, c))
    return commonest, _actual(confusion, commonest) / sum(confusion.values())


def f1(confusion: Confusion, c: str) -> float | None:
    """One class's F1: 2 x right / (2 x right + said wrongly + missed). None when the class neither happened
    nor was said: there is nothing to score, and a 0 would count against the rules for a class that was not there."""
    either = _said(confusion, c) + _actual(confusion, c)  # the right ones are in both, so this is that divisor
    return 2 * confusion[c, c] / either if either else None


def macro_f1(confusion: Confusion) -> float:
    """The plain mean of the per-class F1s, over the classes that have one."""
    scores = [score for score in (f1(confusion, c) for c in CLASSES) if score is not None]
    return sum(scores) / len(scores)


def alert_counts(confusion: Confusion) -> tuple[int, int]:
    """(false alerts, wrong-action alerts). False: said CLEAN or INSPECT when the truth was OK or WAIT.
    Wrong action: said one of the two when the truth was the other."""
    false = sum(confusion[t, v] for t in CLASSES if t not in ALERTS for v in ALERTS)
    wrong_action = sum(confusion[t, v] for t in ALERTS for v in ALERTS if t != v)
    return false, wrong_action


def per_roof_month(count: int, checks: int, every: float = CHECK_EVERY) -> float:
    """A count of checks as a rate per roof per month, each roof being checked every `every` days."""
    return count / checks * DAYS_PER_MONTH / every


def beyond_accuracy(confusion: Confusion) -> list[str]:
    """The lines report() adds under the accuracy line. The module docstring says what each one means."""
    total, lines = sum(confusion.values()), []
    if any(not _said(confusion, c) or not _actual(confusion, c) for c in CLASSES):
        lines.append("nan above: a class never said has no precision, a class that never happened has no recall")
    commonest, share = baseline(confusion)
    lines.append(
        f"baseline {share:.2f}: always saying {commonest}, the commonest truth "
        f"({_actual(confusion, commonest)} of {total} checks)"
    )
    scores = {c: f1(confusion, c) for c in CLASSES}
    for c, score in scores.items():
        lines.append(
            f"{c:<8} F1 "
            + ("none (never happened, never said: left out of macro-F1)" if score is None else f"{score:.2f}")
        )
    lines.append(
        f"macro-F1 {macro_f1(confusion):.2f}: the plain mean of the "
        f"{sum(s is not None for s in scores.values())} F1s above"
    )
    false, wrong_action = alert_counts(confusion)
    lines.append(
        f"false alerts {per_roof_month(false, total):.2f} per roof per month: {false} of {total} checks, "
        f"{CHECK_EVERY} days apart, said CLEAN or INSPECT when the truth was OK or WAIT"
    )
    lines.append(
        "  (the app alerts only when its advice changes, so a wrong verdict that lasts counts here every time "
        "and there once)"
    )
    lines.append(
        f"wrong-action alerts {wrong_action}: said CLEAN when the truth was INSPECT, or INSPECT when it was CLEAN"
    )
    return lines


def run(
    name: str, lat: float, lon: float, start: str, end: str, seed: int, hidden: bool
) -> tuple[list[Confusion], Counter[tuple[str, str]]]:
    """Prints the four scores for one neighbourhood. Returns their confusions, in VARIANTS order, and the
    wash checks (on the homes without weather error, as before)."""
    weather = fetch_weather(lat, lon, start, end)
    pm25 = fetch_pm25(lat, lon, start, end)
    rain = weather["rain"].resample("D").sum()
    # The same homes twice: the weather error has its own random draws, so nothing else about them differs.
    homes = {
        noisy: simulate(
            weather, pm25, seed=seed, hidden=hidden, lat=lat, lon=lon, weather_noise=WEATHER_NOISE if noisy else 0.0
        )
        for noisy in (False, True)
    }
    # The first block is headed as it always was, so old numbers can be laid beside new ones.
    print(f"\n{name}: {len(homes[False])} homes, {start} to {end}, seed {seed}")
    confusions: list[Confusion] = []
    for title, noisy, alone in VARIANTS:
        if confusions:
            print(f"\n{name}, {title}")
        confusions.append(evaluate(homes[noisy], rain, pm25.reindex(rain.index).fillna(0.0), alone=alone))
        print(report(confusions[-1]))
    return confusions, wash_checks(homes[False])


def main(seed: str = "0") -> None:
    totals: list[Confusion]
    washes: Counter[tuple[str, str]]
    if seed == "hidden":
        totals, washes = [Counter() for _ in VARIANTS], Counter()
        for i, (city, (lat, lon)) in enumerate(HIDDEN_CITIES.items()):
            confusions, checks = run(city, lat, lon, *HIDDEN_YEAR, HIDDEN_SEED + i, hidden=True)
            totals = [total + confusion for total, confusion in zip(totals, confusions, strict=True)]
            washes += checks
        for i, (total, (title, _, _)) in enumerate(zip(totals, VARIANTS, strict=True)):
            print("\nHidden test set, all three cities" + (f", {title}" if i else ""))
            print(report(total))
    else:
        end = datetime.date.today() - datetime.timedelta(days=7)
        _, washes = run(
            "Delhi",
            config.SIM_LAT,
            config.SIM_LON,
            str(end - datetime.timedelta(days=365)),
            str(end),
            int(seed),
            hidden=False,
        )
    print("\nWash check:", ", ".join(f"{kind}: {status} {n}" for (kind, status), n in sorted(washes.items())))


if __name__ == "__main__":
    main(*sys.argv[1:2])
