"""What a roof should have produced: Open-Meteo weather in, pvlib physics, daily kWh out."""

import datetime
import json
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd
import pvlib

from . import config

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
FORECAST_PAST_DAYS = 60  # the forecast API also serves recent history, which the archive lags on
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

_COLUMNS = {
    "shortwave_radiation": "ghi",
    "direct_normal_irradiance": "dni",
    "diffuse_radiation": "dhi",
    "temperature_2m": "temp_air",
    "wind_speed_10m": "wind_speed",
    "precipitation": "rain",
}
# What a dust storm is judged on, asked for in the same forecast call as the weather.
_STORM_COLUMNS = {"wind_gusts_10m": "gust_kmh", "visibility": "visibility_m"}

TRIES = 3  # in all, when Open-Meteo is busy (429), failing (5xx) or silent
TIMEOUT_S = 25  # each try; three of them and the waits between fit inside one analysis run
BACKOFF_S = 1.0  # the wait before a new try is a random time up to this, then up to twice this


def http_get(url: str) -> Any:
    """One GET, JSON back."""
    for tries_left in reversed(range(TRIES)):
        try:
            with urllib.request.urlopen(url, timeout=TIMEOUT_S) as response:
                return json.load(response)
        except urllib.error.HTTPError as e:  # a bad request stays bad: only "busy" and "broken" are worth a new try
            if not tries_left or (e.code != 429 and e.code < 500):
                raise
        except (urllib.error.URLError, TimeoutError):  # no connection, or no answer in time
            if not tries_left:
                raise
        time.sleep(random.uniform(0, BACKOFF_S * 2 ** (TRIES - 1 - tries_left)))


# What every fetch below asks through. The analysis Lambda puts its cache here (handlers/weather_cache.py);
# this module itself makes no AWS call.
get_json: Callable[[str], Any] = http_get


def _fetch_hourly(url, lat, lon, variables, **params):
    query = urllib.parse.urlencode(
        {
            "latitude": lat,
            "longitude": lon,
            "hourly": ",".join(variables),
            "timezone": config.TZ,
            **params,
        }
    )
    hourly = get_json(f"{url}?{query}")["hourly"]
    index = pd.DatetimeIndex(hourly.pop("time")).tz_localize(config.TZ)
    return pd.DataFrame(hourly, index=index).astype(float)


def fetch_weather(lat: float, lon: float, start: str, end: str) -> pd.DataFrame:
    """Hourly ghi, dni, dhi (W/m²), temp_air (°C), wind_speed (m/s), rain (mm). Dates are YYYY-MM-DD."""
    df = _fetch_hourly(ARCHIVE_URL, lat, lon, _COLUMNS, start_date=start, end_date=end, wind_speed_unit="ms")
    return df.rename(columns=_COLUMNS)


def fetch_weather_with_forecast(lat: float, lon: float, start: datetime.date) -> pd.DataFrame:
    """Same columns, from `start` (a date) through the next 7 days of forecast. The days the forecast API
    serves also carry gust_kmh and visibility_m, which fetch_dust_storms reads: one call, not two."""
    names = {**_COLUMNS, **_STORM_COLUMNS}
    recent = _fetch_hourly(
        FORECAST_URL, lat, lon, names, past_days=FORECAST_PAST_DAYS, forecast_days=7, wind_speed_unit="ms"
    ).rename(columns=names)
    # The call asks for wind in m/s (the physics wants it), so gusts come in m/s too. Open-Meteo's km/h figure
    # is this one times 3.6 to one decimal: hour for hour the same on the recorded answers (test_expected.py).
    recent["gust_kmh"] = (recent["gust_kmh"] * 3.6).round(1)
    first_recent = recent.index[0].date()
    if start >= first_recent:
        return recent[recent.index.date >= start]
    older = fetch_weather(lat, lon, str(start), str(first_recent - datetime.timedelta(days=1)))
    return pd.concat([older, recent])


def fetch_pm25(lat: float, lon: float, start: str, end: str) -> pd.Series:
    """Daily mean PM2.5 in µg/m³."""
    df = _fetch_hourly(AIR_QUALITY_URL, lat, lon, ["pm2_5"], start_date=start, end_date=end)
    return df["pm2_5"].resample("D").mean()


def fetch_dust_storms(lat: float, lon: float, weather: pd.DataFrame) -> pd.Series:
    """For today and the next six days: True where a dust storm is forecast (see config.STORM_*).
    weather: what fetch_weather_with_forecast returned for the same place, for its gusts and visibility."""
    air = _fetch_hourly(AIR_QUALITY_URL, lat, lon, ["dust"], forecast_days=7)
    hours = air.join(weather[list(_STORM_COLUMNS.values())], how="inner")
    storm = (
        (hours["dust"] >= config.STORM_DUST)
        & (hours["gust_kmh"] >= config.STORM_GUST_KMH)
        & (hours["visibility_m"] <= config.STORM_VISIBILITY_M)
    )
    return storm.resample("D").max().astype(bool)


def expected_daily_kwh(
    weather: pd.DataFrame,
    lat: float,
    lon: float,
    kw: float,
    tilt: float = config.DEFAULT_TILT,
    azimuth: float = config.DEFAULT_AZIMUTH,
) -> pd.Series:
    """Daily kWh a clean, healthy system of `kw` should produce in this weather."""
    # Open-Meteo radiation is the mean over the hour ending at the timestamp,
    # so the sun's position is taken at the middle of that hour.
    sun = pvlib.solarposition.get_solarposition(weather.index - pd.Timedelta(minutes=30), lat, lon)
    poa = pvlib.irradiance.get_total_irradiance(
        tilt,
        azimuth,
        sun["apparent_zenith"].to_numpy(),
        sun["azimuth"].to_numpy(),
        dni=weather["dni"].to_numpy(),
        ghi=weather["ghi"].to_numpy(),
        dhi=weather["dhi"].to_numpy(),
    )["poa_global"]
    poa = np.nan_to_num(poa)
    cell_temp = pvlib.temperature.faiman(poa, weather["temp_air"].to_numpy(), weather["wind_speed"].to_numpy())
    dc_kw = pvlib.pvsystem.pvwatts_dc(poa, cell_temp, kw, config.TEMP_COEFF)
    ac_kw = np.clip(dc_kw * config.INVERTER_EFFICIENCY, 0, kw)
    return pd.Series(ac_kw, index=weather.index).resample("D").sum()  # hourly kW summed = kWh
