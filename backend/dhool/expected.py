"""What a roof should have produced: Open-Meteo weather in, pvlib physics, daily kWh out."""
import datetime
import json
import urllib.parse
import urllib.request

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


def _fetch_hourly(url, lat, lon, variables, **params):
    query = urllib.parse.urlencode({
        "latitude": lat, "longitude": lon, "hourly": ",".join(variables), "timezone": config.TZ, **params,
    })
    with urllib.request.urlopen(f"{url}?{query}", timeout=60) as response:
        hourly = json.load(response)["hourly"]
    index = pd.DatetimeIndex(hourly.pop("time")).tz_localize(config.TZ)
    return pd.DataFrame(hourly, index=index).astype(float)


def fetch_weather(lat, lon, start, end):
    """Hourly ghi, dni, dhi (W/m²), temp_air (°C), wind_speed (m/s), rain (mm). Dates are YYYY-MM-DD."""
    df = _fetch_hourly(ARCHIVE_URL, lat, lon, _COLUMNS, start_date=start, end_date=end, wind_speed_unit="ms")
    return df.rename(columns=_COLUMNS)


def fetch_weather_with_forecast(lat, lon, start):
    """Same columns, from `start` (a date) through the next 7 days of forecast."""
    recent = _fetch_hourly(FORECAST_URL, lat, lon, _COLUMNS, past_days=FORECAST_PAST_DAYS, forecast_days=7,
                           wind_speed_unit="ms").rename(columns=_COLUMNS)
    first_recent = recent.index[0].date()
    if start >= first_recent:
        return recent[recent.index.date >= start]
    older = fetch_weather(lat, lon, str(start), str(first_recent - datetime.timedelta(days=1)))
    return pd.concat([older, recent])


def fetch_pm25(lat, lon, start, end):
    """Daily mean PM2.5 in µg/m³."""
    df = _fetch_hourly(AIR_QUALITY_URL, lat, lon, ["pm2_5"], start_date=start, end_date=end)
    return df["pm2_5"].resample("D").mean()


def fetch_dust_storms(lat, lon):
    """For today and the next six days: True where a dust storm is forecast (see config.STORM_*)."""
    air = _fetch_hourly(AIR_QUALITY_URL, lat, lon, ["dust"], forecast_days=7)
    wind = _fetch_hourly(FORECAST_URL, lat, lon, ["wind_gusts_10m", "visibility"], forecast_days=7)
    hours = air.join(wind, how="inner")
    storm = ((hours["dust"] >= config.STORM_DUST) & (hours["wind_gusts_10m"] >= config.STORM_GUST_KMH)
             & (hours["visibility"] <= config.STORM_VISIBILITY_M))
    return storm.resample("D").max().astype(bool)


def expected_daily_kwh(weather, lat, lon, kw, tilt=config.DEFAULT_TILT, azimuth=config.DEFAULT_AZIMUTH):
    """Daily kWh a clean, healthy system of `kw` should produce in this weather."""
    # Open-Meteo radiation is the mean over the hour ending at the timestamp,
    # so the sun's position is taken at the middle of that hour.
    sun = pvlib.solarposition.get_solarposition(weather.index - pd.Timedelta(minutes=30), lat, lon)
    poa = pvlib.irradiance.get_total_irradiance(
        tilt, azimuth, sun["apparent_zenith"].to_numpy(), sun["azimuth"].to_numpy(),
        dni=weather["dni"].to_numpy(), ghi=weather["ghi"].to_numpy(), dhi=weather["dhi"].to_numpy(),
    )["poa_global"]
    poa = np.nan_to_num(poa)
    cell_temp = pvlib.temperature.faiman(poa, weather["temp_air"].to_numpy(), weather["wind_speed"].to_numpy())
    dc_kw = pvlib.pvsystem.pvwatts_dc(poa, cell_temp, kw, config.TEMP_COEFF)
    ac_kw = np.clip(dc_kw * config.INVERTER_EFFICIENCY, 0, kw)
    return pd.Series(ac_kw, index=weather.index).resample("D").sum()  # hourly kW summed = kWh
