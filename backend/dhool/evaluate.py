"""Score the verdict rules against a simulated neighbourhood, where every day's true cause is known.

    python -m dhool.evaluate [seed]

Run it on a seed the rules were never tuned on to get an honest number.
"""
import datetime
import sys
from collections import Counter

import pandas as pd

from . import config
from .expected import fetch_pm25, fetch_weather
from .sim import simulate
from .verdict import RAIN_SOON_DAYS, verdict

CLASSES = ["CLEAN", "INSPECT", "WAIT", "OK"]


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
        rain_soon = (rain.iloc[i + 1:i + 1 + RAIN_SOON_DAYS] >= config.CLEAN_RAIN_MM).any()
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


def main(seed=0):
    end = datetime.date.today() - datetime.timedelta(days=7)
    start = end - datetime.timedelta(days=365)
    weather = fetch_weather(config.SIM_LAT, config.SIM_LON, str(start), str(end))
    pm25 = fetch_pm25(config.SIM_LAT, config.SIM_LON, str(start), str(end))
    rain = weather["rain"].resample("D").sum()
    homes = simulate(weather, pm25, seed=int(seed))
    print(f"seed {seed}, {len(homes)} homes, {start} to {end}")
    print(report(evaluate(homes, rain, pm25.reindex(rain.index).fillna(0.0))))


if __name__ == "__main__":
    main(*sys.argv[1:2])
