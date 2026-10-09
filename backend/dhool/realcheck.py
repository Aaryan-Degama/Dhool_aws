"""Run the method on real rooftops: nine homes in California and Arizona, about ten years of daily kWh each.

    python -m dhool.realcheck

Data: NREL PVDAQ public datasets (PVOutput.org residential systems), CC BY 4.0,
https://data.openei.org/submissions/4568, read from the open S3 bucket. Weather: Open-Meteo archive.
Nothing is labelled, so this cannot give an accuracy number. It answers three things the simulator cannot:

1. How closely does the physics track a real roof from day to day? (The simulator assumes 2% scatter.)
2. After a long dry spell, does the first real rain bring output back, by about what the loss predicted?
   Rain is a wash nobody had to report, so this tests the same check the "I washed them" button uses.
3. What do the rules say month by month on a real roof, with no neighbours and no air-quality data?

Downloads are cached in ~/.cache/dhool (about 1 MB of readings and ten years of weather per place).
"""
import io
import pathlib
import re
import time
import urllib.request
from collections import Counter

import numpy as np
import pandas as pd

from . import config
from .expected import expected_daily_kwh, fetch_weather
from .verdict import _ratio, check_action, normal, verdict

S3 = "https://oedi-data-lake.s3.amazonaws.com"
CACHE = pathlib.Path.home() / ".cache/dhool"
START, END = "2015-01-01", "2024-12-31"
DRY_DAYS = 60  # a dry spell this long before rain counts as a natural wash
# system id: place, lat, lon, kW, tilt, azimuth, fixed standard-time zone (from PVDAQ's systems list)
SYSTEMS = {
    10068: ("San Jose CA", 37.2964, -121.9179, 3.675, 16, 180, "Etc/GMT+8"),
    10079: ("Fresno CA", 36.8645, -119.6260, 6.0, 24, 180, "Etc/GMT+8"),
    10914: ("Fresno CA", 36.7369, -119.6640, 4.96, 22, 180, "Etc/GMT+8"),
    10589: ("Bakersfield CA", 35.2005, -119.1740, 6.16, 20, 180, "Etc/GMT+8"),
    10185: ("Thousand Oaks CA", 34.2088, -118.8735, 7.0, 15, 180, "Etc/GMT+8"),
    10920: ("Cathedral City CA", 33.8078, -116.4647, 6.7, 25, 180, "Etc/GMT+8"),
    10092: ("Tucson AZ", 32.2163, -110.8851, 4.725, 30, 180, "Etc/GMT+7"),
    10733: ("Phoenix AZ", 33.5428, -112.0845, 10.08, 18, 180, "Etc/GMT+7"),
    10149: ("Lake Havasu AZ", 34.4699, -114.2786, 7.2, 15, 180, "Etc/GMT+7"),
}


def _get(url):
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=120) as response:
                return response.read()
        except OSError:
            if attempt == 3:
                raise
            time.sleep(5 * (attempt + 1))


def _cached(name, make):
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / name
    if not path.exists():
        make().to_pickle(path)
    return pd.read_pickle(path)


def _readings(system_id):
    keys = re.findall(r"<Key>([^<]+\.csv)</Key>", _get(f"{S3}/?list-type=2&prefix=pvdaq/csv/pvdata/system_id={system_id}/").decode())
    frame = pd.concat(pd.read_csv(io.BytesIO(_get(f"{S3}/{key}")), index_col=0, parse_dates=True) for key in keys).sort_index()
    kwh = frame[[c for c in frame.columns if c.endswith("daily_sum")]].sum(axis=1, min_count=1)
    return kwh[~kwh.index.duplicated()]


def _weather(lat, lon):
    def fetch():  # a year per request keeps each response small
        years = range(int(START[:4]), int(END[:4]) + 1)
        return pd.concat(fetch_weather(round(lat, 2), round(lon, 2), f"{y}-01-01", f"{y}-12-31") for y in years)
    return fetch


def load(system_id):
    """Daily [expected, actual] and daily rain for one real system."""
    place, lat, lon, kw, tilt, azimuth, tz = SYSTEMS[system_id]
    config.TZ = tz  # a fixed-offset zone: no daylight-saving gaps, and solar days are the same
    weather = _cached(f"weather-{lat:.2f}-{lon:.2f}.pkl", _weather(lat, lon))
    actual = _cached(f"pvdaq-{system_id}.pkl", lambda: _readings(system_id))
    actual.index = pd.DatetimeIndex(actual.index).tz_localize(tz)
    daily = pd.DataFrame({"expected": expected_daily_kwh(weather, lat, lon, kw, tilt, azimuth), "actual": actual})[START:END]
    daily.loc[daily["actual"] <= 0, "actual"] = np.nan
    return daily, weather["rain"].resample("D").sum()[START:END]


def natural_washes(daily, rain):
    """For each first real rain after a long dry spell: what the loss predicted, and what came back."""
    ratio, events, last_wet = _ratio(daily), [], None
    for day in rain[rain >= config.CLEAN_RAIN_MM].index:
        if last_wet is not None and (day - last_wet).days >= DRY_DAYS:
            year = ratio[day - pd.Timedelta(days=365):day - pd.Timedelta(days=1)]
            if year.notna().sum() >= 120:
                check = check_action(ratio, normal(year), {"date": str(day.date()), "type": "wash"})
                if check and check["observed_pct"] is not None:
                    events.append(check)
        last_wet = day
    return events


def monthly_verdicts(daily, rain):
    """The verdict at each month end, from the year of readings before it: what a homeowner would have seen."""
    said = []
    for end in pd.date_range(daily.index[0] + pd.Timedelta(days=365), daily.index[-1] - pd.Timedelta(days=7), freq="ME"):
        window = daily[end - pd.Timedelta(days=364):end]
        if window["actual"].tail(30).notna().sum() < 10:
            continue  # the inverter was not reporting
        result = verdict(window, rain[window.index[0]:end], list(rain[end:].iloc[1:8]))
        said.append(f"{result['verdict']}:{result['cause']}")
    return said


def main():
    events, said = [], Counter()
    print(f"{'system':<26}{'days':>6}{'runs at':>9}{'scatter':>9}{'washes':>8}{'came back':>11}{'median gain':>13}")
    for system_id, (place, *_) in SYSTEMS.items():
        daily, rain = load(system_id)
        ratio = _ratio(daily).dropna()
        scatter = 1.4826 * (ratio / ratio.rolling(15, center=True, min_periods=5).median() - 1).abs().median()
        washes = natural_washes(daily, rain)
        gains = [w["observed_pct"] for w in washes]
        events += washes
        said.update(monthly_verdicts(daily, rain))
        print(f"{system_id} {place:<20}{len(ratio):>6}{ratio.median():>9.2f}{scatter:>9.1%}{len(washes):>8}"
              f"{np.mean([g > 0 for g in gains]):>11.0%}{np.median(gains):>12.1f}%")
    frame = pd.DataFrame(events)
    dusty = frame[frame["predicted_pct"] >= 5]
    print(f"\n{len(frame)} first rains after {DRY_DAYS}+ dry days: output rose after {np.mean(frame['observed_pct'] > 0):.0%} of them, "
          f"median {frame['observed_pct'].median():+.1f}%.")
    print(f"Where the roof was 5% or more below its normal before the rain ({len(dusty)} events): predicted "
          f"{dusty['predicted_pct'].median():+.1f}%, came back {dusty['observed_pct'].median():+.1f}% (medians); "
          f"check said {dict(Counter(dusty['status']))}; correlation {dusty['predicted_pct'].corr(dusty['observed_pct']):.2f}.")
    total = sum(said.values())
    print(f"\nMonth-end verdicts over {total} system-months, one roof at a time (no neighbours, no PM2.5):")
    for name, count in said.most_common():
        print(f"  {name:<16}{count:>5}  {count / total:.0%}")


if __name__ == "__main__":
    main()
