"""Analysis Lambda (container image, because pvlib is too big for a zip).

Invoked with {"house_id": ...} right after new data arrives, or with no house_id by the nightly
EventBridge schedule, which starts one run of this same function per house ({"house_id", "nightly": true}).
Writes one VERDICT#<date> item per run. A nightly run also tells the family's phones when the advice changed.
"""
import datetime
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from zoneinfo import ZoneInfo

import boto3
from boto3.dynamodb.conditions import Key

from dhool import config, connectors, notify
from dhool.analyse import analyse
from dhool.expected import fetch_dust_storms, fetch_pm25, fetch_weather_with_forecast

# ponytail: this account may run 10 Lambdas at once, and each run also calls the demo inverter (two more).
# Starting a house every 1.5 s keeps the night under that, and fits about 70 houses in the 120 s timeout.
# Once AWS raises the limit set this to 0; past a few hundred houses put an SQS queue in between.
NIGHTLY_PACE_S = 1.5
PUSH_TTL_S = 24 * 3600  # a phone that is off gets the alert within a day or not at all

_table = None
_request_id = None  # this invocation's, put on every log line
_vapid = False      # the key that signs notifications: False until looked up, None when there is none


def table():
    global _table
    if _table is None:
        _table = boto3.resource("dynamodb").Table(os.environ["TABLE"])
    return _table


def _log(**fields):
    print(json.dumps({**fields, "request_id": _request_id}))


def _vapid_key():
    global _vapid
    if _vapid is False:
        try:
            _vapid = boto3.client("ssm").get_parameter(
                Name=os.environ.get("VAPID_PARAM", "/dhool/vapid-private-key"), WithDecryption=True)["Parameter"]["Value"]
        except Exception as e:  # no key stored: verdicts go on, notifications are off until it is
            _vapid = None
            _log(analysis="push_off", error=type(e).__name__)
    return _vapid


def _webpush(item, message, key):
    from pywebpush import webpush  # here, not at the top: only a nightly run with something to say needs it
    webpush({"endpoint": item["endpoint"], "keys": {"p256dh": item["p256dh"], "auth": item["auth"]}},
            json.dumps(message, ensure_ascii=False), vapid_private_key=key,
            vapid_claims={"sub": os.environ["VAPID_SUBJECT"]}, ttl=PUSH_TTL_S, timeout=10)


def _notify(house_id, previous, result):
    """Tell every subscribed phone of the house, each in its own language, if this run has news."""
    days = (datetime.datetime.now(ZoneInfo(config.TZ)).date() - datetime.date.fromisoformat(result["as_of"])).days
    if not notify.message(previous, result, days, "en") or not _vapid_key():
        return
    sent = 0
    for item in table().query(
            KeyConditionExpression=Key("pk").eq(f"HOUSE#{house_id}") & Key("sk").begins_with("PUSH#"))["Items"]:
        try:
            _webpush(item, notify.message(previous, result, days, item.get("lang")), _vapid_key())
            sent += 1
        except Exception as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            if status in (404, 410):  # the browser dropped this subscription
                table().delete_item(Key={"pk": item["pk"], "sk": item["sk"]})
            _log(analysis="push_failed", house=house_id, status=status, error=type(e).__name__)
    _log(analysis="pushed", house=house_id, sent=sent)


def run_house(house_id, nightly=False):
    meta = table().get_item(Key={"pk": f"HOUSE#{house_id}", "sk": "META"}).get("Item")
    if not meta:  # deleted between being asked for and running
        return None
    fleet = None
    with ThreadPoolExecutor(max_workers=3) as pool:
        # Connected inverter: pull from the brand's cloud (here, the demo one). Houses linked before API keys
        # existed have a plant but no key; they count as not linked until the owner connects again in Setup.
        if meta.get("plant_id") and meta.get("inverter_key"):
            readings = pool.submit(connectors.inverter_readings, meta["inverter_url"], meta["inverter_key"], meta["plant_id"])
            fleet = pool.submit(connectors.inverter_fleet, meta["inverter_url"])
            readings, fleet = readings.result(), fleet.result()
            fleet.pop(meta["plant_id"], None)
        else:  # screenshots and typed-in readings
            items = table().query(
                KeyConditionExpression=Key("pk").eq(f"HOUSE#{house_id}") & Key("sk").begins_with("READING#"))["Items"]
            readings = {i["sk"].split("#", 1)[1]: float(i["kwh"]) for i in items}
        if not readings:
            return None

        lat, lon = float(meta["lat"]), float(meta["lon"])
        first, last = min(readings), max(readings)
        weather = pool.submit(fetch_weather_with_forecast, lat, lon, datetime.date.fromisoformat(first))
        pm25 = pool.submit(fetch_pm25, lat, lon, first, last)
        storms = pool.submit(fetch_dust_storms, lat, lon)
        weather = weather.result()
        try:
            pm25 = pm25.result()
        except Exception as e:  # air quality only sharpens the haze call; the verdict works without it
            _log(analysis="pm25_unavailable", house=house_id, error=str(e))
            pm25 = None

        try:  # a dust storm on the way means "wash after it"; without the forecast the wash plan uses rain alone
            storms = storms.result()
        except Exception as e:
            _log(analysis="dust_forecast_unavailable", house=house_id, error=str(e))
            storms = None

    def items(prefix, **more):
        return table().query(
            KeyConditionExpression=Key("pk").eq(f"HOUSE#{house_id}") & Key("sk").begins_with(prefix), **more)["Items"]
    # What the homeowner told Dhool they did (washed the panels, had the vendor in), for the before-and-after check.
    actions = [{"date": i["sk"].split("#", 1)[1], "type": i["type"]} for i in items("ACTION#")]
    result = analyse(meta, readings, weather, pm25, fleet, actions, storms)
    previous = items("VERDICT#", ScanIndexForward=False, Limit=1) if nightly else []
    table().put_item(Item={"pk": f"HOUSE#{house_id}", "sk": f"VERDICT#{result['as_of']}",
                           "json": json.dumps(result), "at": int(time.time())})
    _log(analysis="done", house=house_id, as_of=result["as_of"],
         verdict=result["verdict"], cause=result["cause"], confidence=result["confidence"])
    if nightly:
        try:
            _notify(house_id, json.loads(previous[0]["json"]) if previous else None, result)
        except Exception as e:  # the verdict is saved; a notification that could not go out never fails the run
            _log(analysis="push_failed", house=house_id, error=type(e).__name__)
    return result["verdict"]


def handler(event, context):
    global _request_id
    _request_id = getattr(context, "aws_request_id", None)
    if event.get("house_id"):
        return {"verdict": run_house(event["house_id"], nightly=event.get("nightly") is True)}
    # Nightly: one run of this same function per house, in the background, so a slow or broken house holds up
    # nobody and its failure lands in the failure queue.
    client, started, more = boto3.client("lambda"), 0, {}
    while True:
        page = table().query(KeyConditionExpression=Key("pk").eq("HOUSES"), **more)
        for house in page["Items"]:
            client.invoke(FunctionName=os.environ["AWS_LAMBDA_FUNCTION_NAME"], InvocationType="Event",
                          Payload=json.dumps({"house_id": house["sk"], "nightly": True}))
            started += 1
            time.sleep(NIGHTLY_PACE_S)
        if "LastEvaluatedKey" not in page:
            break
        more = {"ExclusiveStartKey": page["LastEvaluatedKey"]}
    _log(analysis="nightly", houses=started)
    return {"houses": started}
