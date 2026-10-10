"""HTTP API for houses, members and readings. One Lambda, routed by routeKey.

The caller is always the `sub` claim verified by the API Gateway JWT authorizer.
Nothing in the body or query string is trusted for identity or house membership.
"""
import base64
import datetime
import hashlib
import json
import os
import re
import secrets
import time
import traceback
import uuid
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from boto3.dynamodb.conditions import Key
from botocore.config import Config
from botocore.exceptions import ClientError

from dhool import authz, config, connectors, keys
from handlers import common
from handlers.common import bucket, client, log, query_all, table

INVITE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # no 0/O or 1/I/L
INVITE_TTL_S = 7 * 24 * 3600
MAX_KWH_PER_KW = 12  # no roof makes more than this per installed kW in a day
MAX_READINGS = 120   # in one request: a screenshot's history chart, not a bulk import
HISTORY_DAYS = 45    # how far back the log of advice looks
MAX_UPLOAD_BYTES = 5_000_000
IMAGE_TYPES = {"image/png": "png", "image/jpeg": "jpg"}
SHOT_KEY = re.compile(r"houses/([0-9a-f]{12})/([0-9a-f]{32})\.(?:png|jpg)")
SHOT_TTL_S = 24 * 3600         # a screenshot's reading result is kept for a day
# An answer is kept as long as the verdict it is about: VERDICT_TTL_S in analysis.py, which this Lambda cannot
# import (it pulls in pvlib). test_api.py fails if the two drift apart.
FEEDBACK_TTL_S = 400 * 24 * 3600
READING_TIMEOUT_S = 15 * 60    # after this long with no result, the reader is taken to have failed
REPLY_LABELS = ("visit_scheduled", "asking_details", "refused", "unclear")
MAX_REPLY_CHARS = 1000

JOIN_TRIES, JOIN_LOCK_S = 5, 3600  # wrong invite codes one person may try, and how long the count is kept
MAX_HOUSES, MAX_MEMBERS = 5, 10    # homes one person may be in, and people in one home
TOO_MANY_HOUSES = f"You can be in up to {MAX_HOUSES} homes. Leave or delete one first."
HOUSE_FULL = f"This home already has {MAX_MEMBERS} people. Ask its owner to remove someone first."
SETTINGS = {"wash_cost_rs": (0, 5000), "tariff_rs": (1, 30)}
# The server posts to a subscription's endpoint, so it must be a browser push service and nothing else.
PUSH_ENDPOINT = re.compile(r"https://(?:fcm\.googleapis\.com|(?:[a-z0-9-]+\.)+(?:push\.services\.mozilla\.com"
                           r"|notify\.windows\.com|push\.apple\.com))/[A-Za-z0-9._~%:/?=&+-]*")
MAX_ENDPOINT_CHARS, MAX_PUSH_KEY_CHARS = 2000, 200

class HttpError(Exception):
    def __init__(self, status: int, message: str) -> None:
        self.status, self.message = status, message


def _body(event):
    raw = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        try:
            raw = base64.b64decode(raw, validate=True)
        except ValueError:
            raise HttpError(400, "Body is not valid base64") from None
    try:
        data = json.loads(raw, parse_float=Decimal)
    except ValueError:
        raise HttpError(400, "Body must be JSON") from None
    if not isinstance(data, dict):
        raise HttpError(400, "Body must be a JSON object")
    return data


def _number(data, key, low, high, default=None):
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise HttpError(400, f"{key} must be a number")
    value = Decimal(str(value))
    if not value.is_finite() or not low <= value <= high:
        raise HttpError(400, f"{key} must be between {low} and {high}")
    return value


def _decide(sub, house_id, action, role):
    """Allow or refuse what someone with this role asks, and say which in one JSON log line."""
    allowed = authz.decide(role, action)
    log(authz="allow" if allowed else "deny", sub=sub, house=house_id, action=action, role=role)
    if not allowed:
        raise HttpError(403, "Not allowed")
    return role


def authorize(sub: str, house_id: str, action: str) -> str:
    """Every access to house data goes through here. One JSON log line per decision."""
    item = table().get_item(Key={"pk": keys.house_pk(house_id), "sk": keys.member_sk(sub)}).get("Item")
    return _decide(sub, house_id, action, item["role"] if item else None)


def _house_meta(house_id):
    return table().get_item(Key={"pk": keys.house_pk(house_id), "sk": keys.META})["Item"]


def _house_keys(house_id, prefix=None):
    """The sort key (and who wrote it) of every item of a house, or of those starting with prefix, page by page."""
    condition = Key("pk").eq(keys.house_pk(house_id))
    if prefix:
        condition &= Key("sk").begins_with(prefix)
    return query_all(table(), KeyConditionExpression=condition,
                     ProjectionExpression="sk, #by", ExpressionAttributeNames={"#by": "by"})


def _count(pk, prefix):
    """How many items pk has under prefix.
    ponytail: counted, then written, so two requests at the same instant can end one over a quota. Keep a
    counter on the item and add to it in the same transaction if the limits ever have to be exact."""
    return table().query(KeyConditionExpression=Key("pk").eq(pk) & Key("sk").begins_with(prefix), Select="COUNT")["Count"]


def me(sub: str, event: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    items = table().query(KeyConditionExpression=Key("pk").eq(keys.user_pk(sub)))["Items"]
    return 200, {"houses": [{"house_id": keys.tail(i["sk"]), "name": i["name"], "role": i["role"]}
                            for i in items]}


def _new_house_id():
    return uuid.uuid4().hex[:12]


def create_house(sub: str, event: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    data = _body(event)
    name = data.get("name")
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 60:
        raise HttpError(400, "name must be 1 to 60 characters")
    name = name.strip()
    meta = {
        "sk": keys.META, "name": name,
        "kw": _number(data, "kw", Decimal("0.1"), 100),
        "lat": round(_number(data, "lat", -90, 90), 2),  # about a kilometre: enough for weather, not an address
        "lon": round(_number(data, "lon", -180, 180), 2),
        "tilt": _number(data, "tilt", 0, 90, config.DEFAULT_TILT),
        "azimuth": _number(data, "azimuth", 0, 360, config.DEFAULT_AZIMUTH),
    }
    if _count(keys.user_pk(sub), keys.HOUSE) >= MAX_HOUSES:
        raise HttpError(409, TOO_MANY_HOUSES)
    for last_try in (False, False, True):  # a fresh id if this one is taken
        house_id = _new_house_id()
        items = [
            {"pk": keys.house_pk(house_id), **meta},
            {"pk": keys.house_pk(house_id), "sk": keys.member_sk(sub), "role": "owner", "joined_at": int(time.time())},
            {"pk": keys.user_pk(sub), "sk": keys.house_pk(house_id), "role": "owner", "name": name},
            {"pk": keys.HOUSES, "sk": house_id},  # the list the nightly run walks
        ]
        try:  # all four or none, and never over a home that is already there
            table().meta.client.transact_write_items(TransactItems=[
                {"Put": {"TableName": table().name, "Item": item, "ConditionExpression": "attribute_not_exists(pk)"}}
                for item in items])
            break
        except ClientError as e:
            if e.response["Error"]["Code"] != "TransactionCanceledException" or last_try:
                raise
    return 201, {"house_id": house_id}


def get_house(sub: str, event: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    house_id = event["pathParameters"]["houseId"]
    # The member list is wanted anyway and holds the caller's own role: one read answers both. Nothing of
    # it leaves this function unless the decision below allows.
    members = list(query_all(
        table(), KeyConditionExpression=Key("pk").eq(keys.house_pk(house_id)) & Key("sk").begins_with(keys.MEMBER)))
    _decide(sub, house_id, "read", next((m["role"] for m in members if m["sk"] == keys.member_sk(sub)), None))
    meta = _house_meta(house_id)
    return 200, {
        "house_id": house_id,
        **{k: meta[k] for k in ("name", "kw", "lat", "lon", "tilt", "azimuth")},
        "wash_cost_rs": meta.get("wash_cost_rs", config.WASH_COST_RS),
        "tariff_rs": meta.get("tariff_rs", config.TARIFF_RS),
        "linked": bool(meta.get("plant_id") and meta.get("inverter_key")),
        "members": [{"sub": keys.tail(m["sk"]), "role": m["role"], "joined_at": m.get("joined_at"),
                     "me": m["sk"] == keys.member_sk(sub)} for m in members],
    }


def create_invite(sub: str, event: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    house_id = event["pathParameters"]["houseId"]
    authorize(sub, house_id, "create_invite")
    # ponytail: no collision retry; 31^6 codes. Add a conditional put if houses reach the tens of thousands.
    code = "".join(secrets.choice(INVITE_ALPHABET) for _ in range(6))
    expires_at = int(time.time()) + INVITE_TTL_S
    table().put_item(Item={"pk": keys.invite_pk(code), "sk": keys.META, "house_id": house_id, "expiresAt": expires_at})
    # The house keeps a note of its codes, so they can be cancelled when someone is removed.
    table().put_item(Item={"pk": keys.house_pk(house_id), "sk": keys.invite_pk(code), "expiresAt": expires_at})
    return 201, {"code": code, "expires_at": expires_at}


def join(sub: str, event: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    code = _body(event).get("code")
    if not isinstance(code, str):
        raise HttpError(400, "code is required")
    # Six letters can be guessed, so each person gets a few wrong tries an hour. DynamoDB TTL deletes late,
    # so both expiries are checked here too.
    now = int(time.time())
    fail_key = {"pk": keys.joinfail_pk(sub), "sk": keys.META}
    fails = table().get_item(Key=fail_key).get("Item")
    if fails and fails["expiresAt"] <= now:  # last hour's count, not yet removed
        table().delete_item(Key=fail_key)
    elif fails and fails["n"] >= JOIN_TRIES:
        log(authz="join_locked", sub=sub)
        raise HttpError(429, "Too many wrong codes. Try again in an hour.")
    invite = table().get_item(Key={"pk": keys.invite_pk(code.strip().upper()), "sk": keys.META}).get("Item")
    house = None
    if invite and invite["expiresAt"] >= now:  # the house may have been deleted since the code was made
        house = table().get_item(Key={"pk": keys.house_pk(invite['house_id']), "sk": keys.META}).get("Item")
    if not house:
        table().update_item(Key=fail_key, UpdateExpression="ADD n :one SET expiresAt = if_not_exists(expiresAt, :exp)",
                            ExpressionAttributeValues={":one": 1, ":exp": now + JOIN_LOCK_S})
        raise HttpError(404, "Invite code not found or expired")
    house_id = invite["house_id"]
    if "Item" not in table().get_item(Key={"pk": keys.house_pk(house_id), "sk": keys.member_sk(sub)}):  # someone new
        if _count(keys.user_pk(sub), keys.HOUSE) >= MAX_HOUSES:
            raise HttpError(409, TOO_MANY_HOUSES)
        if _count(keys.house_pk(house_id), keys.MEMBER) >= MAX_MEMBERS:
            raise HttpError(409, HOUSE_FULL)
    try:
        # Never overwrite an existing membership: an owner using their own code stays owner.
        table().put_item(Item={"pk": keys.house_pk(house_id), "sk": keys.member_sk(sub), "role": "member", "joined_at": now},
                         ConditionExpression="attribute_not_exists(pk)")
    except ClientError as e:
        if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
            raise
    else:
        table().put_item(Item={"pk": keys.user_pk(sub), "sk": keys.house_pk(house_id), "role": "member", "name": house["name"]})
    log(authz="join", sub=sub, house=house_id)
    return 200, {"house_id": house_id}


def delete_house(sub: str, event: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """The owner deletes the home: its readings, verdicts, screenshots, members and their alerts, for everyone."""
    house_id = event["pathParameters"]["houseId"]
    authorize(sub, house_id, "delete_house")
    bucket(os.environ["UPLOADS"]).objects.filter(Prefix=f"houses/{house_id}/").delete()
    # Members go last: if this stops half-way the owner is still the owner and can press delete again.
    theirs = sorted((i["sk"] for i in _house_keys(house_id)), key=lambda sk: sk.startswith(keys.MEMBER))
    with table().batch_writer() as batch:
        for sk in theirs:
            if sk.startswith(keys.MEMBER):
                batch.delete_item(Key={"pk": keys.user_pk(keys.tail(sk)), "sk": keys.house_pk(house_id)})
            if sk.startswith(keys.INVITE):
                batch.delete_item(Key={"pk": sk, "sk": keys.META})
            batch.delete_item(Key={"pk": keys.house_pk(house_id), "sk": sk})
        batch.delete_item(Key={"pk": keys.HOUSES, "sk": house_id})
    log(deleted="house", house=house_id, items=len(theirs))
    return 200, {"deleted": house_id}


def remove_member(sub: str, event: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """The owner removes someone, or a member leaves. Who is asking is the token's sub; the path names who goes."""
    house_id, member = event["pathParameters"]["houseId"], event["pathParameters"]["sub"]
    role = authorize(sub, house_id, "leave" if member == sub else "remove_member")
    if member == sub and role == "owner":
        raise HttpError(400, "The owner cannot leave. Delete the home instead.")
    # Nobody to remove: say so, and leave the home's codes and alerts as they are.
    if "Item" not in table().get_item(Key={"pk": keys.house_pk(house_id), "sk": keys.member_sk(member)}):
        raise HttpError(404, "That person is not in this home")
    with table().batch_writer() as batch:
        batch.delete_item(Key={"pk": keys.house_pk(house_id), "sk": keys.member_sk(member)})
        batch.delete_item(Key={"pk": keys.user_pk(member), "sk": keys.house_pk(house_id)})
        for item in _house_keys(house_id, keys.PUSH):  # their phones stop getting this home's alerts
            if item.get("by") == member:
                batch.delete_item(Key={"pk": keys.house_pk(house_id), "sk": item["sk"]})
        for item in _house_keys(house_id, keys.INVITE):  # or they could walk back in with a code they still hold
            batch.delete_item(Key={"pk": keys.house_pk(house_id), "sk": item["sk"]})
            batch.delete_item(Key={"pk": item["sk"], "sk": keys.META})
    log(removed="member", house=house_id, member=member)
    return 200, {"removed": member}


def _push_key(house_id, endpoint):
    if not isinstance(endpoint, str) or len(endpoint) > MAX_ENDPOINT_CHARS or not PUSH_ENDPOINT.fullmatch(endpoint):
        raise HttpError(400, "This browser's notifications are not supported.")
    return {"pk": keys.house_pk(house_id), "sk": keys.push_sk(hashlib.sha256(endpoint.encode()).hexdigest())}


def subscribe_push(sub: str, event: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """This phone wants the home's alerts: {"subscription": the browser's PushSubscription.toJSON(), "lang"}."""
    house_id = event["pathParameters"]["houseId"]
    authorize(sub, house_id, "write")
    data = _body(event)
    subscription: Any = data.get("subscription") if isinstance(data.get("subscription"), dict) else {}
    key = _push_key(house_id, subscription.get("endpoint"))
    push_keys = subscription.get("keys") if isinstance(subscription.get("keys"), dict) else {}
    lang = data.get("lang", "en")
    if lang not in ("en", "hi") or not all(
            isinstance(push_keys.get(k), str) and 1 <= len(push_keys[k]) <= MAX_PUSH_KEY_CHARS for k in ("p256dh", "auth")):
        raise HttpError(400, "This browser's notifications are not supported.")
    table().put_item(Item={**key, "endpoint": subscription["endpoint"], "p256dh": push_keys["p256dh"], "auth": push_keys["auth"],
                           "lang": lang, "by": sub, "at": int(time.time())})
    return 201, {"subscribed": True}


def unsubscribe_push(sub: str, event: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    house_id = event["pathParameters"]["houseId"]
    authorize(sub, house_id, "write")
    table().delete_item(Key=_push_key(house_id, _body(event).get("endpoint")))
    return 200, {"subscribed": False}


def _date(data):
    """The "date" of a request, a day that has already come where the homes are."""
    try:
        date = datetime.date.fromisoformat(data.get("date", ""))
    except (TypeError, ValueError):
        raise HttpError(400, "date must be YYYY-MM-DD") from None
    if date > datetime.datetime.now(ZoneInfo(config.TZ)).date():
        raise HttpError(400, "date cannot be in the future")
    return date


def _reading(item, limit):
    """One {"date", "kwh"} checked against the calendar and the size of the roof."""
    if not isinstance(item, dict):
        raise HttpError(400, "Each reading needs a date and kwh")
    return _date(item), _number(item, "kwh", 0, limit)


def add_reading(sub: str, event: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """One typed reading {"date", "kwh"}, or several confirmed from a screenshot
    {"readings": [...], "source": "screenshot"}."""
    house_id = event["pathParameters"]["houseId"]
    authorize(sub, house_id, "write")
    data = _body(event)
    items = data["readings"] if "readings" in data else [data]
    source = data.get("source", "manual")
    if not isinstance(items, list) or not 1 <= len(items) <= MAX_READINGS:
        raise HttpError(400, f"Send between 1 and {MAX_READINGS} readings")
    if source not in ("manual", "screenshot"):
        raise HttpError(400, "source must be manual or screenshot")
    limit = _house_meta(house_id)["kw"] * MAX_KWH_PER_KW
    rows = [_reading(item, limit) for item in items]
    with table().batch_writer(overwrite_by_pkeys=["pk", "sk"]) as batch:
        for date, kwh in rows:
            batch.put_item(Item={"pk": keys.house_pk(house_id), "sk": keys.reading_sk(date), "kwh": kwh,
                                 "source": source, "by": sub, "at": int(time.time())})
    _start_analysis(house_id)
    return 201, {"saved": len(rows)}


def record_action(sub: str, event: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """The homeowner washed the panels or the vendor came: {"type": "wash" | "visit", "date"}. Dhool then checks
    whether output came back. {"date", "remove": true} takes back one recorded by mistake."""
    house_id = event["pathParameters"]["houseId"]
    authorize(sub, house_id, "write")
    data = _body(event)
    date = _date(data)
    key = {"pk": keys.house_pk(house_id), "sk": keys.action_sk(date)}
    if data.get("remove") is True:
        table().delete_item(Key=key)
    elif data.get("type") in ("wash", "visit"):
        table().put_item(Item={**key, "type": data["type"], "by": sub, "at": int(time.time())})
    else:
        raise HttpError(400, "type must be wash or visit")
    _start_analysis(house_id)
    return 201, {"date": str(date)}


def record_feedback(sub: str, event: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """Whether the advice of one day was any use to the household: {"date", "helpful": true | false}. One answer
    for a home and a day, so a second one replaces the first. It is kept for people to read against the verdicts;
    no rule reads it, and no new verdict follows from it."""
    house_id = event["pathParameters"]["houseId"]
    authorize(sub, house_id, "write")
    data = _body(event)
    date, helpful = _date(data), data.get("helpful")
    if not isinstance(helpful, bool):
        raise HttpError(400, "helpful must be true or false")
    now = int(time.time())
    table().put_item(Item={"pk": keys.house_pk(house_id), "sk": keys.feedback_sk(date), "helpful": helpful,
                           "by": sub, "at": now, "expiresAt": now + FEEDBACK_TTL_S})
    return 201, {"date": str(date), "helpful": helpful}


def _read_reply(text):
    """Ask the vendor-reply reader (Laya, in its own Lambda) which of the four kinds of reply this is."""
    # Its own client: one try and a short wait. The homeowner is watching, and has the four buttons anyway.
    reader = client("lambda", key="reply reader", config=Config(read_timeout=20, retries={"max_attempts": 0}))
    out = reader.invoke(FunctionName=os.environ["MESSAGE_FUNCTION"], Payload=json.dumps({"text": text}))
    return json.loads(out["Payload"].read()).get("label")


def read_vendor_reply(sub: str, event: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """What a vendor's pasted reply says: {"text"} -> {"label"}. A model reads it, so the homeowner sees the
    label and can change it; nothing is saved here and the text is not kept."""
    house_id = event["pathParameters"]["houseId"]
    authorize(sub, house_id, "write")
    text = _body(event).get("text")
    if not isinstance(text, str) or not 1 <= len(text.strip()) <= MAX_REPLY_CHARS:
        raise HttpError(400, f"Paste the vendor's reply, up to {MAX_REPLY_CHARS} characters")
    try:
        label = _read_reply(text.strip())
    except Exception as e:  # a reader that is still starting up, or broken: the homeowner picks the label by hand
        log(reply_reader="unavailable", house=house_id, error=type(e).__name__)
        raise HttpError(503, "Dhool could not read the reply just now. Pick what it says below.") from e
    if label not in REPLY_LABELS:  # the model's output is not trusted to be one of ours
        log(reply_reader="bad_label", house=house_id)
        raise HttpError(503, "Dhool could not read the reply just now. Pick what it says below.")
    return 200, {"label": label}


def start_upload(sub: str, event: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """A short-lived, size-limited upload slot for one screenshot, inside this house's folder."""
    house_id = event["pathParameters"]["houseId"]
    authorize(sub, house_id, "write")
    content_type = _body(event).get("content_type")
    if content_type not in IMAGE_TYPES:
        raise HttpError(400, "The screenshot must be a PNG or JPEG image")
    key = f"houses/{house_id}/{uuid.uuid4().hex}.{IMAGE_TYPES[content_type]}"
    region = os.environ["AWS_REGION"]
    s3 = client("s3", region_name=region, endpoint_url=f"https://s3.{region}.amazonaws.com",
                config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}))
    post = s3.generate_presigned_post(
        os.environ["UPLOADS"], key, Fields={"Content-Type": content_type},
        Conditions=[{"Content-Type": content_type}, ["content-length-range", 1, MAX_UPLOAD_BYTES]], ExpiresIn=300)
    return 201, {"key": key, "url": post["url"], "fields": post["fields"]}


def _start_reading(house_id, shot_id, key):
    """Hand the screenshot to the reader (the vision model, in its own Lambda). It works in the background."""
    client("lambda").invoke(FunctionName=os.environ["VISION_FUNCTION"], InvocationType="Event",
                            Payload=json.dumps({"house_id": house_id, "shot_id": shot_id, "key": key}))


def read_screenshot(sub: str, event: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """Start reading an uploaded screenshot. Reading takes about a minute, so the app asks for the result after."""
    house_id = event["pathParameters"]["houseId"]
    authorize(sub, house_id, "write")
    key = _body(event).get("key")
    match = SHOT_KEY.fullmatch(key) if isinstance(key, str) else None
    if not match or match.group(1) != house_id:
        raise HttpError(400, "Upload the screenshot first")
    shot_id, now = match.group(2), int(time.time())
    table().put_item(Item={"pk": keys.house_pk(house_id), "sk": keys.shot_sk(shot_id), "status": "reading", "key": key,
                           "by": sub, "at": now, "expiresAt": now + SHOT_TTL_S})
    _start_reading(house_id, shot_id, key)
    return 202, {"shot_id": shot_id, "status": "reading"}


def screenshot_result(sub: str, event: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """What the reader found in a screenshot, for the homeowner to confirm or correct. Nothing is saved here."""
    house_id = event["pathParameters"]["houseId"]
    authorize(sub, house_id, "read")
    item = table().get_item(Key={"pk": keys.house_pk(house_id), "sk": keys.shot_sk(event['pathParameters']['shotId'])}).get("Item")
    if not item:
        raise HttpError(404, "No such screenshot")
    if item["status"] == "reading":  # still working, unless it has been far too long
        return 200, {"status": "reading" if time.time() - int(item["at"]) < READING_TIMEOUT_S else "unreadable"}
    limit = _house_meta(house_id)["kw"] * MAX_KWH_PER_KW
    uploaded = datetime.datetime.fromtimestamp(int(item["at"]), ZoneInfo(config.TZ)).date()
    readings = {}
    for entry in (json.loads(item.get("result") or "{}").get("readings") or [])[:MAX_READINGS]:
        if isinstance(entry, dict) and entry.get("date") == "TODAY":  # a screen with no date on it
            entry = {**entry, "date": str(uploaded)}
        try:  # a model read the picture and it is not trusted: drop anything that cannot be true for this roof
            date, kwh = _reading(entry, limit)
        except HttpError:
            continue
        readings[str(date)] = kwh
    if not readings:
        return 200, {"status": "unreadable"}
    return 200, {"status": "read", "seconds": item.get("seconds"),
                 "readings": [{"date": d, "kwh": readings[d]} for d in sorted(readings)]}


def _start_analysis(house_id):
    """Ask the analysis Lambda for a fresh verdict. Returns at once; the app polls GET .../verdict."""
    client("lambda").invoke(FunctionName=os.environ["ANALYSIS_FUNCTION"], InvocationType="Event",
                            Payload=json.dumps({"house_id": house_id}))


def connect_inverter(sub: str, event: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    house_id = event["pathParameters"]["houseId"]
    authorize(sub, house_id, "connect_inverter")
    api_key = _body(event).get("api_key")
    # The demo inverter cloud lives on this same API. A real brand would have its own fixed URL here.
    inverter_url = f"https://{event['requestContext']['domainName']}/mock"
    plant = connectors.inverter_plant(inverter_url, api_key)
    if plant is None:
        raise HttpError(404, "That API key did not work. Copy it again from your inverter app.")
    plant_id = plant["id"]
    # The inverter knows the system better than a typed form does, so its details replace the house's.
    # ponytail: the brand's key sits in the house item, readable only by this API's role and never sent to
    # clients. Move it to Secrets Manager before connecting a real brand.
    table().update_item(
        Key={"pk": keys.house_pk(house_id), "sk": keys.META},
        UpdateExpression="SET plant_id = :p, inverter_url = :url, inverter_key = :key, kw = :kw, lat = :lat, "
                         "lon = :lon, tilt = :tilt, azimuth = :az",
        ExpressionAttributeValues={":p": plant_id, ":url": inverter_url, ":key": api_key, ":kw": Decimal(str(plant["kw"])),
                                   ":lat": round(Decimal(str(plant["lat"])), 2), ":lon": round(Decimal(str(plant["lon"])), 2),
                                   ":tilt": Decimal(str(plant["tilt"])), ":az": Decimal(str(plant["azimuth"]))})
    _start_analysis(house_id)
    return 200, {"house_id": house_id, "plant_id": plant_id}


def save_settings(sub: str, event: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """What one wash costs this household and what it pays per unit, in ₹: the figures the wash-or-wait sums are
    done against. Either or both."""
    house_id = event["pathParameters"]["houseId"]
    authorize(sub, house_id, "write")
    data = _body(event)
    saved = {key: _number(data, key, low, high) for key, (low, high) in SETTINGS.items() if key in data}
    if not saved:
        raise HttpError(400, "Send wash_cost_rs or tariff_rs")
    table().update_item(Key={"pk": keys.house_pk(house_id), "sk": keys.META},
                        UpdateExpression="SET " + ", ".join(f"{key} = :{key}" for key in saved),
                        ExpressionAttributeValues={f":{key}": value for key, value in saved.items()})
    _start_analysis(house_id)
    return 200, saved


def history(sub: str, event: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """What Dhool advised and what the household did, newest first. A piece of advice is listed on the day it
    first appeared, not on every day it was repeated."""
    house_id = event["pathParameters"]["houseId"]
    authorize(sub, house_id, "read")
    def items(prefix, **more):
        return table().query(KeyConditionExpression=Key("pk").eq(keys.house_pk(house_id)) & Key("sk").begins_with(prefix), **more)["Items"]
    log: list[dict[str, Any]]
    last: tuple[str, str, str | None] | None
    log, last = [], None
    for item in reversed(items(keys.VERDICT, ScanIndexForward=False, Limit=HISTORY_DAYS)):  # oldest of them first
        v = json.loads(item["json"])
        said = (v["verdict"], v["cause"], (v.get("evidence") or {}).get("wait_for"))
        if said != last:
            log.append({"date": keys.tail(item["sk"]), "kind": "said", "verdict": said[0], "cause": said[1],
                        "wait_for": said[2], "loss_pct": v.get("loss_pct")})
        last = said
        check = v.get("check")
    latest = check if log else None  # the newest verdict carries the outcome of the newest wash or visit
    for item in items(keys.ACTION):
        date = keys.tail(item["sk"])
        log.append({"date": date, "kind": "did", "type": item["type"],
                    "status": latest["status"] if latest and latest["date"] == date else None})
    return 200, {"log": sorted(log, key=lambda e: (e["date"], e["kind"] == "did"), reverse=True)}


def get_verdict(sub: str, event: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    house_id = event["pathParameters"]["houseId"]
    authorize(sub, house_id, "read")
    items = table().query(
        KeyConditionExpression=Key("pk").eq(keys.house_pk(house_id)) & Key("sk").begins_with(keys.VERDICT),
        ScanIndexForward=False, Limit=1)["Items"]
    if not items:
        return 200, {"verdict": None}
    return 200, {**json.loads(items[0]["json"]), "computed_at": items[0]["at"]}


def list_readings(sub: str, event: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    house_id = event["pathParameters"]["houseId"]
    authorize(sub, house_id, "read")
    items = query_all(
        table(), KeyConditionExpression=Key("pk").eq(keys.house_pk(house_id)) & Key("sk").begins_with(keys.READING))
    return 200, {"readings": [{"date": keys.tail(i["sk"]), "kwh": i["kwh"], "source": i["source"],
                               "by": i["by"]} for i in items]}


ROUTES = {
    "GET /me": me,
    "POST /houses": create_house,
    "POST /join": join,
    "GET /houses/{houseId}": get_house,
    "DELETE /houses/{houseId}": delete_house,
    "DELETE /houses/{houseId}/members/{sub}": remove_member,
    "POST /houses/{houseId}/push": subscribe_push,
    "DELETE /houses/{houseId}/push": unsubscribe_push,
    "POST /houses/{houseId}/invites": create_invite,
    "POST /houses/{houseId}/readings": add_reading,
    "GET /houses/{houseId}/readings": list_readings,
    "POST /houses/{houseId}/inverter": connect_inverter,
    "POST /houses/{houseId}/actions": record_action,
    "POST /houses/{houseId}/feedback": record_feedback,
    "POST /houses/{houseId}/vendor-reply": read_vendor_reply,
    "POST /houses/{houseId}/screenshots": start_upload,
    "POST /houses/{houseId}/screenshots/read": read_screenshot,
    "GET /houses/{houseId}/screenshots/{shotId}": screenshot_result,
    "GET /houses/{houseId}/verdict": get_verdict,
    "POST /houses/{houseId}/settings": save_settings,
    "GET /houses/{houseId}/history": history,
}


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    common.request_id = getattr(context, "aws_request_id", None)
    try:
        route = ROUTES.get(event.get("routeKey"))  # type: ignore[arg-type]  # no routeKey looks up None: the 404 below
        if route is None:
            raise HttpError(404, "No such route")
        sub = event["requestContext"]["authorizer"]["jwt"]["claims"]["sub"]
        status, payload = route(sub, event)
    except HttpError as e:
        status, payload = e.status, {"error": e.message}
    except Exception as e:  # nothing foreseen: the caller gets a number to quote, the log gets the rest
        log(error="unhandled", route=event.get("routeKey"), exception=type(e).__name__, detail=str(e)[:500],
             trace=traceback.format_exc()[-2000:])
        status, payload = 500, {"error": "Something went wrong", "request_id": common.request_id}
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(payload, allow_nan=False, default=lambda d: float(d) if d % 1 else int(d)),
    }
