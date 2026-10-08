"""A stand-in inverter brand cloud, "Inverter Cloud (demo)", shaped like a real one.

It has the three things a real brand has, all serving the simulated neighbourhood
(data/neighbourhood.json, written by `python -m dhool.sim`):

- an owner's app page   GET /mock/app                    today's units, a 30-day chart, the owner's API
                                                         key, and a button that saves the screen as an image
- a keyed API           GET /mock/v1/plants              one API key sees one plant
                        GET /mock/v1/plants/{id}/daily
- a fleet feed          GET /mock/fleet/daily            every plant, for the neighbour comparison

It never exposes what was planted in each home: only what a real inverter would report.
"""
import hashlib
import hmac
import json
import pathlib

HERE = pathlib.Path(__file__).parent
_homes = None


def homes():
    global _homes
    if _homes is None:
        _homes = json.loads((HERE.parent / "data" / "neighbourhood.json").read_text())
    return _homes


def api_key(plant_id):
    # ponytail: keys are derived, so there is nothing to store or revoke. Fine for simulated data;
    # a real brand issues and revokes keys.
    return "inv_" + hashlib.sha256(f"dhool-demo-inverter:{plant_id}".encode()).hexdigest()[:24]


def _plant(home):
    return {k: home["meta"][k] for k in ("id", "kw", "lat", "lon", "tilt", "azimuth")}


def _daily(home, start="", end="9999"):
    # Two decimals, as an inverter reports them.
    return [{"date": d["date"], "kwh": round(d["actual"], 2)} for d in home["daily"] if start <= d["date"] <= end]


def _owner(event):
    """The home whose API key came in the Authorization header, or None."""
    sent = (event.get("headers") or {}).get("authorization", "").removeprefix("Bearer ").strip()
    return next((h for pid, h in homes().items() if hmac.compare_digest(sent, api_key(pid))), None)


def _json(status, body):
    return {"statusCode": status, "headers": {"content-type": "application/json"}, "body": json.dumps(body)}


def _app_page(query):
    plant_id = query.get("plant") if query.get("plant") in homes() else next(iter(homes()))
    home = homes()[plant_id]
    data = {"app": "Inverter Cloud (demo)", "plant": plant_id, "kw": home["meta"]["kw"], "key": api_key(plant_id),
            "plants": list(homes()), "readings": _daily(home)[-30:]}
    page = (HERE / "mock_app.html").read_text().replace("__DATA__", json.dumps(data).replace("<", "\\u003c"))
    return {"statusCode": 200, "headers": {"content-type": "text/html; charset=utf-8"}, "body": page}


def handler(event, context):
    route, query = event["routeKey"], event.get("queryStringParameters") or {}
    if route == "GET /mock/app":
        return _app_page(query)
    if route == "GET /mock/fleet/daily":
        return _json(200, {pid: {"kw": h["meta"]["kw"], "readings": {r["date"]: r["kwh"] for r in _daily(h)}}
                           for pid, h in homes().items()})
    home = _owner(event)
    if home is None:
        return _json(401, {"error": "Missing or unknown API key"})
    if route == "GET /mock/v1/plants":
        return _json(200, [_plant(home)])
    # GET /mock/v1/plants/{plantId}/daily
    if event["pathParameters"]["plantId"] != home["meta"]["id"]:
        return _json(403, {"error": "This API key cannot see that plant"})
    return _json(200, _daily(home, query.get("from", ""), query.get("to", "9999")))
