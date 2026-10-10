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

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from dhool import config, connectors, expected, keys, notify
from dhool.analyse import analyse
from dhool.expected import fetch_dust_storms, fetch_pm25, fetch_weather_with_forecast
from handlers import common, weather_cache
from handlers.common import client, log, metric, query_all, table

# ponytail: this account may run 10 Lambdas at once, and each run also calls the demo inverter (two more).
# Starting a house every 1.5 s keeps the night under that, and fits about 70 houses in the 120 s timeout.
# Once AWS raises the limit set this to 0; past a few hundred houses put an SQS queue in between.
NIGHTLY_PACE_S = 1.5
NIGHTLY_PAGE = 25       # houses started between looks at the clock
VERDICT_TTL_S = 400 * 24 * 3600  # a day's verdict is kept a little over a year; the readings behind it are kept
PUSH_TTL_S = 24 * 3600  # a phone that is off gets the alert within a day or not at all

expected.get_json = weather_cache.cached(expected.http_get)  # Open-Meteo's answers, kept for three hours

_vapid = False  # the key that signs notifications: False until looked up, None when there is none


def _vapid_key():
    global _vapid
    if _vapid is False:
        try:
            _vapid = client("ssm").get_parameter(
                Name=os.environ.get("VAPID_PARAM", "/dhool/vapid-private-key"), WithDecryption=True)["Parameter"]["Value"]
        except Exception as e:  # no key stored: verdicts go on, notifications are off until it is
            _vapid = None
            log(analysis="push_off", error=type(e).__name__)
    return _vapid


def _webpush(item, message, key):
    from pywebpush import webpush  # here, not at the top: only a nightly run with something to say needs it
    webpush({"endpoint": item["endpoint"], "keys": {"p256dh": item["p256dh"], "auth": item["auth"]}},
            json.dumps(message, ensure_ascii=False), vapid_private_key=key,
            vapid_claims={"sub": os.environ["VAPID_SUBJECT"]}, ttl=PUSH_TTL_S, timeout=10)


def _notify(house_id, told, result):
    """Tell every subscribed phone of the house, each in its own language, if this run has news.

    News is measured against what the phones were last told (told, the house's last_notified), not against
    the verdict stored before: a verdict that first appeared in a run started from the app (a typed reading)
    has been stored and never sent. last_notified is written only once a phone has been reached, so a night
    when every send fails is tried again the next; and it is removed when the advice goes back to "all good"
    or "wait", so the same trouble coming back months later is news again."""
    days = (datetime.datetime.now(ZoneInfo(config.TZ)).date() - datetime.date.fromisoformat(result["as_of"])).days
    advice = {"verdict": result["verdict"], "cause": result.get("cause")}
    alerting, meta = advice["verdict"] in ("INSPECT", "CLEAN"), {"pk": keys.house_pk(house_id), "sk": keys.META}
    if told and not alerting:
        table().update_item(Key=meta, UpdateExpression="REMOVE last_notified", ConditionExpression="attribute_exists(pk)")
    if not notify.message(told, result, days, "en") or not _vapid_key():
        return
    sent = 0
    for item in table().query(
            KeyConditionExpression=Key("pk").eq(keys.house_pk(house_id)) & Key("sk").begins_with(keys.PUSH))["Items"]:
        try:
            _webpush(item, notify.message(told, result, days, item.get("lang")), _vapid_key())
            sent += 1
        except Exception as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            if status in (404, 410):  # the browser dropped this subscription
                table().delete_item(Key={"pk": item["pk"], "sk": item["sk"]})
            log(analysis="push_failed", house=house_id, status=status, error=type(e).__name__)
    if sent and alerting and days != notify.STOPPED_AFTER_DAYS:  # "readings stopped" went out, not the advice
        table().update_item(Key=meta, UpdateExpression="SET last_notified = :told", ExpressionAttributeValues={":told": advice},
                            ConditionExpression="attribute_exists(pk)")
    log(analysis="pushed", house=house_id, sent=sent)


def run_house(house_id, nightly=False):
    began = time.monotonic()
    meta = table().get_item(Key={"pk": keys.house_pk(house_id), "sk": keys.META}).get("Item")
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
            items = query_all(
                table(), KeyConditionExpression=Key("pk").eq(keys.house_pk(house_id)) & Key("sk").begins_with(keys.READING))
            readings = {keys.tail(i["sk"]): float(i["kwh"]) for i in items}
        if not readings:
            return None

        lat, lon = float(meta["lat"]), float(meta["lon"])
        first, last = min(readings), max(readings)
        weather = pool.submit(fetch_weather_with_forecast, lat, lon, datetime.date.fromisoformat(first))
        pm25 = pool.submit(fetch_pm25, lat, lon, first, last)
        weather = weather.result()
        storms = pool.submit(fetch_dust_storms, lat, lon, weather)  # the gusts and visibility came with the weather
        try:
            pm25 = pm25.result()
        except Exception as e:  # air quality only sharpens the haze call; the verdict works without it
            log(analysis="pm25_unavailable", house=house_id, error=str(e))
            pm25 = None

        try:  # a dust storm on the way means "wash after it"; without the forecast the wash plan uses rain alone
            storms = storms.result()
        except Exception as e:
            log(analysis="dust_forecast_unavailable", house=house_id, error=str(e))
            storms = None

    def items(prefix, **more):
        return table().query(
            KeyConditionExpression=Key("pk").eq(keys.house_pk(house_id)) & Key("sk").begins_with(prefix), **more)["Items"]
    # What the homeowner told Dhool they did (washed the panels, had the vendor in), for the before-and-after check.
    actions = [{"date": keys.tail(i["sk"]), "type": i["type"]} for i in items(keys.ACTION)]
    result = analyse(meta, readings, weather, pm25, fleet, actions, storms)
    try:
        # Only while the home still stands: a run takes many seconds, and a verdict written after its owner
        # deleted the home would be a piece of it left behind for 400 days.
        table().meta.client.transact_write_items(TransactItems=[
            {"ConditionCheck": {"TableName": table().name, "Key": {"pk": keys.house_pk(house_id), "sk": keys.META},
                                "ConditionExpression": "attribute_exists(pk)"}},
            {"Put": {"TableName": table().name, "Item": {
                "pk": keys.house_pk(house_id), "sk": keys.verdict_sk(result['as_of']),
                "json": json.dumps(result, allow_nan=False), "at": int(time.time()),
                "expiresAt": int(time.time()) + VERDICT_TTL_S}}}])
    except ClientError as e:
        reasons = [r.get("Code") for r in e.response.get("CancellationReasons", [])]
        if e.response["Error"]["Code"] != "TransactionCanceledException" or reasons[:1] != ["ConditionalCheckFailed"]:
            raise
        log(analysis="house_gone", house=house_id)
        return None
    # For the dashboard: how long a run that reached a verdict took, up to storing it, and which verdict.
    metric("HouseRunDuration", round((time.monotonic() - began) * 1000), "Milliseconds")
    metric("Verdicts", 1, verdict=result["verdict"])
    log(analysis="done", house=house_id, as_of=result["as_of"],
         verdict=result["verdict"], cause=result["cause"], confidence=result["confidence"])
    if nightly:
        try:
            _notify(house_id, meta.get("last_notified"), result)
        except Exception as e:  # the verdict is saved; a notification that could not go out never fails the run
            log(analysis="push_failed", house=house_id, error=type(e).__name__)
    return result["verdict"]


def handler(event, context):
    common.request_id = getattr(context, "aws_request_id", None)
    if event.get("house_id"):
        return {"verdict": run_house(event["house_id"], nightly=event.get("nightly") is True)}
    # Nightly: one run of this same function per house, in the background, so a slow or broken house holds up
    # nobody and its failure lands in the failure queue.
    # Pacing makes a long list outlast one invocation: when time runs short, the rest is handed to a fresh one.
    runs, started = client("lambda"), 0
    more = {"ExclusiveStartKey": event["cursor"]} if event.get("cursor") else {}
    while True:
        if started and more and context.get_remaining_time_in_millis() < NIGHTLY_PAGE * NIGHTLY_PACE_S * 1000 + 15_000:
            runs.invoke(FunctionName=os.environ["AWS_LAMBDA_FUNCTION_NAME"], InvocationType="Event",
                        Payload=json.dumps({"cursor": more["ExclusiveStartKey"]}))
            log(analysis="nightly_continues", houses=started)
            return {"houses": started, "continues": True}
        page = table().query(KeyConditionExpression=Key("pk").eq(keys.HOUSES), Limit=NIGHTLY_PAGE, **more)
        for house in page["Items"]:
            runs.invoke(FunctionName=os.environ["AWS_LAMBDA_FUNCTION_NAME"], InvocationType="Event",
                        Payload=json.dumps({"house_id": house["sk"], "nightly": True}))
            started += 1
            time.sleep(NIGHTLY_PACE_S)
        if "LastEvaluatedKey" not in page:
            break
        more = {"ExclusiveStartKey": page["LastEvaluatedKey"]}
    log(analysis="nightly", houses=started)
    return {"houses": started}
