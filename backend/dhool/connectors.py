"""One connector per data source. Each returns the same standard readings, {"YYYY-MM-DD": kwh},
so the analysis never knows where a reading came from. A new inverter brand is one more function here.

No heavy imports: the small API Lambda uses this too.
"""
import json
import urllib.request


def _get(url):
    with urllib.request.urlopen(url, timeout=20) as response:
        return json.load(response)


def mock_plant(base_url, plant_id):
    """The plant's details (kw, lat, lon, tilt, azimuth), or None if the inverter cloud has no such plant."""
    return next((p for p in _get(f"{base_url}/plants") if p["id"] == plant_id), None)


def mock_readings(base_url, plant_id):
    return {r["date"]: r["kwh"] for r in _get(f"{base_url}/plants/{plant_id}/daily")}


def mock_fleet(base_url):
    """Every plant on the account: {plant_id: {"kw": ..., "readings": {...}}}. Used for the neighbour comparison."""
    return _get(f"{base_url}/fleet/daily")
