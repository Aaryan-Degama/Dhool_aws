"""Score the verdict rules against a simulated neighbourhood, where every day's true cause is known.

    python -m dhool.evaluate [seed]     the development neighbourhood (Delhi, the last 12 months)
    python -m dhool.evaluate hidden     the hidden test set

The hidden test set is three other cities' real weather for a fixed past year, with every simulator setting
drawn afresh and wider than the rules were built against, and readings missing (see sim.simulate, hidden=True).
The rules were frozen before it was first run, and it is not used to tune them. If the rules change, run it
again and report the new number as it comes; never pick the better of two runs.
"""
import datetime
import sys
from collections import Counter

import pandas as pd

from . import config
from .expected import fetch_pm25, fetch_weather
from .sim import simulate
from .verdict import RAIN_SOON_DAYS, _ratio, check_action, normal, verdict

CLASSES = ["CLEAN", "INSPECT", "WAIT", "OK"]
HIDDEN_SEED = 20261003
HIDDEN_YEAR = ("2024-10-01", "2025-09-30")
HIDDEN_CITIES = {"Jaipur": (26.91, 75.79), "Lucknow": (26.85, 80.95), "Ahmedabad": (23.02, 72.57)}


def truth(home, i, rain):
    """What a perfect detector would say for this home on day i."""
    daily, problem = home["daily"], home["meta"]["problem"]
    faulty = daily["cause"].iloc[:i + 1] == "fault"
    if problem in ("string_fault", "shading") and faulty.iloc[-1]:
        return "INSPECT"
    if problem == "inverter_trips" and faulty.tail(30).sum() >= 2:
        return "INSPECT"
    if (daily["cause"].iloc[i - 2:i + 1] == "haze").sum() >= 2:
        return "WAIT"
    if daily["soiling"].iloc[i] >= 0.05:
        rain_soon = (rain.iloc[i + 1:i + 1 + RAIN_SOON_DAYS] >= home["meta"].get("clean_mm", config.CLEAN_RAIN_MM)).any()
        return "WAIT" if rain_soon else "CLEAN"
    return "OK"


def evaluate(homes, rain, pm25, start=60, every=7):
    """Returns Counter of (truth, verdict) pairs over every home, checked every `every` days."""
    ratios = pd.DataFrame({hid: h["daily"]["actual"] / h["daily"]["expected"] for hid, h in homes.items()})
    confusion = Counter()
    for hid, home in homes.items():
        others = ratios.drop(columns=hid)
        for i in range(start, len(rain) - 7, every):
            got = verdict(home["daily"].iloc[:i + 1], rain.iloc[:i + 1], list(rain.iloc[i + 1:i + 8]),
                          pm25.iloc[:i + 1], others.iloc[:i + 1])
            confusion[truth(home, i, rain), got["verdict"]] += 1
    return confusion


def wash_checks(homes):
    """The "I washed them" check against washes the simulator planted, reported a week later.
    Real washes of a dusty roof should come out verified; a wash that never happened on a roof with a
    dead string (the homeowner washed, it was not dust) should come out not recovered."""
    outcome = Counter()
    for home in homes.values():
        daily, days = home["daily"], home["daily"].index
        washed = [i for i in range(14, len(days) - 8) if str(days[i].date()) in home["meta"]["wash_days"]
                  and daily["soiling"].iloc[i - 1] >= 0.05 and daily["cause"].iloc[i] != "fault"]
        faulty = (daily["cause"] == "fault").to_numpy()
        not_dust = [int(faulty.argmax()) + 15] if home["meta"]["problem"] == "string_fault" and faulty.sum() > 30 else []
        for i, kind in [(i, "real wash") for i in washed] + [(i, "wash of a faulty roof") for i in not_dust]:
            ratio = _ratio(daily.iloc[:i + 8])
            check = check_action(ratio, normal(ratio), {"date": str(days[i].date()), "type": "wash"})
            outcome[kind, check["status"] if check else "no data"] += 1
    return outcome


def report(confusion):
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
    return "\n".join(lines)


def run(name, lat, lon, start, end, seed, hidden):
    weather = fetch_weather(lat, lon, start, end)
    pm25 = fetch_pm25(lat, lon, start, end)
    rain = weather["rain"].resample("D").sum()
    homes = simulate(weather, pm25, seed=seed, hidden=hidden, lat=lat, lon=lon)
    confusion = evaluate(homes, rain, pm25.reindex(rain.index).fillna(0.0))
    print(f"\n{name}: {len(homes)} homes, {start} to {end}, seed {seed}")
    print(report(confusion))
    return confusion, wash_checks(homes)


def main(seed="0"):
    if seed == "hidden":
        total, washes = Counter(), Counter()
        for i, (city, (lat, lon)) in enumerate(HIDDEN_CITIES.items()):
            confusion, checks = run(city, lat, lon, *HIDDEN_YEAR, HIDDEN_SEED + i, hidden=True)
            total += confusion
            washes += checks
        print("\nHidden test set, all three cities")
        print(report(total))
    else:
        end = datetime.date.today() - datetime.timedelta(days=7)
        _, washes = run("Delhi", config.SIM_LAT, config.SIM_LON, str(end - datetime.timedelta(days=365)), str(end), int(seed), hidden=False)
    print("\nWash check:", ", ".join(f"{kind}: {status} {n}" for (kind, status), n in sorted(washes.items())))


if __name__ == "__main__":
    main(*sys.argv[1:2])
