"""One connector per data source. Each returns the same standard readings, {"YYYY-MM-DD": kwh},
so the analysis never knows where a reading came from. A new inverter brand is one more set of
functions here, pointed at that brand's API.

No heavy imports: the small API Lambda uses this too.
"""
import json
import re
import urllib.error
import urllib.request

API_KEY = re.compile(r"[A-Za-z0-9_-]{8,100}")


def _get(url, api_key=None):
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"} if api_key else {})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def inverter_plant(base_url, api_key):
    """The plant this key belongs to (id, kw, lat, lon, tilt, azimuth), or None if the key is not accepted."""
    if not isinstance(api_key, str) or not API_KEY.fullmatch(api_key):
        return None
    try:
        plants = _get(f"{base_url}/v1/plants", api_key)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            return None
        raise
    return plants[0] if plants else None


def inverter_readings(base_url, api_key, plant_id):
    return {r["date"]: r["kwh"] for r in _get(f"{base_url}/v1/plants/{plant_id}/daily", api_key)}


def inverter_fleet(base_url):
    """Nearby plants, {plant_id: {"kw": ..., "readings": {...}}}, for the neighbour comparison."""
    return _get(f"{base_url}/fleet/daily")
