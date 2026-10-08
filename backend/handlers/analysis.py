"""Analysis Lambda (container image, because pvlib is too big for a zip).

Invoked with {"house_id": ...} right after new data arrives, or with no house_id by the nightly
EventBridge schedule, which runs every house. Writes one VERDICT#<date> item per run.
"""
import datetime
import json
import os
import time

import boto3
from boto3.dynamodb.conditions import Key

from dhool import connectors
from dhool.analyse import analyse
from dhool.expected import fetch_pm25, fetch_weather_with_forecast

_table = None


def table():
    global _table
    if _table is None:
        _table = boto3.resource("dynamodb").Table(os.environ["TABLE"])
    return _table


def run_house(house_id):
    meta = table().get_item(Key={"pk": f"HOUSE#{house_id}", "sk": "META"})["Item"]
    fleet = None
    if meta.get("plant_id"):  # connected inverter: pull from the brand's cloud (here, the demo one)
        readings = connectors.inverter_readings(meta["inverter_url"], meta["inverter_key"], meta["plant_id"])
        fleet = connectors.inverter_fleet(meta["inverter_url"])
        fleet.pop(meta["plant_id"], None)
    else:  # screenshots and typed-in readings
        items = table().query(
            KeyConditionExpression=Key("pk").eq(f"HOUSE#{house_id}") & Key("sk").begins_with("READING#"))["Items"]
        readings = {i["sk"].split("#", 1)[1]: float(i["kwh"]) for i in items}
    if not readings:
        return None

    lat, lon = float(meta["lat"]), float(meta["lon"])
    first, last = min(readings), max(readings)
    weather = fetch_weather_with_forecast(lat, lon, datetime.date.fromisoformat(first))
    try:
        pm25 = fetch_pm25(lat, lon, first, last)
    except Exception as e:  # air quality only sharpens the haze call; the verdict works without it
        print(json.dumps({"analysis": "pm25_unavailable", "house": house_id, "error": str(e)}))
        pm25 = None

    result = analyse(meta, readings, weather, pm25, fleet)
    table().put_item(Item={"pk": f"HOUSE#{house_id}", "sk": f"VERDICT#{result['as_of']}",
                           "json": json.dumps(result), "at": int(time.time())})
    print(json.dumps({"analysis": "done", "house": house_id, "as_of": result["as_of"],
                      "verdict": result["verdict"], "cause": result["cause"], "confidence": result["confidence"]}))
    return result["verdict"]


def handler(event, context):
    if event.get("house_id"):
        return {"verdict": run_house(event["house_id"])}
    # Nightly: every house. ponytail: one after another in one invocation; fan out per house past ~50 homes.
    houses = table().query(KeyConditionExpression=Key("pk").eq("HOUSES"))["Items"]
    done = failed = 0
    for house in houses:
        try:
            run_house(house["sk"])
            done += 1
        except Exception as e:
            failed += 1
            print(json.dumps({"analysis": "failed", "house": house["sk"], "error": str(e)}))
    print(json.dumps({"analysis": "nightly", "done": done, "failed": failed}))
    return {"done": done, "failed": failed}
