"""Mock inverter cloud API, shaped like a real brand's: plants and their daily generation.

Serves the simulated neighbourhood (data/neighbourhood.json, written by `python -m dhool.sim`).
It never exposes what was planted in each home: only what a real inverter would report.
"""
import json
import pathlib

_homes = None


def homes():
    global _homes
    if _homes is None:
        _homes = json.loads((pathlib.Path(__file__).parent.parent / "data" / "neighbourhood.json").read_text())
    return _homes


def _plant(home):
    return {k: home["meta"][k] for k in ("id", "kw", "lat", "lon", "tilt", "azimuth")}


def _daily(home, start="", end="9999"):
    return [{"date": d["date"], "kwh": d["actual"]} for d in home["daily"] if start <= d["date"] <= end]


def handler(event, context):
    route, query = event["routeKey"], event.get("queryStringParameters") or {}
    if route == "GET /mock/plants":
        body = [_plant(h) for h in homes().values()]
    elif route == "GET /mock/fleet/daily":
        body = {pid: {"kw": h["meta"]["kw"], "readings": {r["date"]: r["kwh"] for r in _daily(h)}}
                for pid, h in homes().items()}
    else:  # GET /mock/plants/{plantId}/daily
        home = homes().get(event["pathParameters"]["plantId"])
        if home is None:
            return {"statusCode": 404, "body": json.dumps({"error": "No such plant"})}
        body = _daily(home, query.get("from", ""), query.get("to", "9999"))
    return {"statusCode": 200, "headers": {"content-type": "application/json"}, "body": json.dumps(body)}
