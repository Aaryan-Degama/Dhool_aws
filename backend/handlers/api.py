"""HTTP API for houses, members and readings. One Lambda, routed by routeKey.

The caller is always the `sub` claim verified by the API Gateway JWT authorizer.
Nothing in the body or query string is trusted for identity or house membership.
"""
import base64
import datetime
import json
import os
import re
import secrets
import time
import uuid
from decimal import Decimal
from zoneinfo import ZoneInfo

import boto3
from boto3.dynamodb.conditions import Key
from botocore.config import Config
from botocore.exceptions import ClientError

from dhool import authz, config, connectors

INVITE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # no 0/O or 1/I/L
INVITE_TTL_S = 7 * 24 * 3600
MAX_KWH_PER_KW = 12  # no roof makes more than this per installed kW in a day
MAX_READINGS = 120   # in one request: a screenshot's history chart, not a bulk import
MAX_UPLOAD_BYTES = 5_000_000
IMAGE_TYPES = {"image/png": "png", "image/jpeg": "jpg"}
SHOT_KEY = re.compile(r"houses/([0-9a-f]{12})/([0-9a-f]{32})\.(?:png|jpg)")
SHOT_TTL_S = 24 * 3600         # a screenshot's reading result is kept for a day
READING_TIMEOUT_S = 15 * 60    # after this long with no result, the reader is taken to have failed
REPLY_LABELS = ("visit_scheduled", "asking_details", "refused", "unclear")
MAX_REPLY_CHARS = 1000

_table = None


def table():
    global _table
    if _table is None:
        _table = boto3.resource("dynamodb").Table(os.environ["TABLE"])
    return _table


class HttpError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


def _body(event):
    raw = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(raw)
    try:
        data = json.loads(raw, parse_float=Decimal)
    except ValueError:
        raise HttpError(400, "Body must be JSON")
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


def authorize(sub, house_id, action):
    """Every access to house data goes through here. One JSON log line per decision."""
    item = table().get_item(Key={"pk": f"HOUSE#{house_id}", "sk": f"MEMBER#{sub}"}).get("Item")
    role = item["role"] if item else None
    allowed = authz.decide(role, action)
    print(json.dumps({"authz": "allow" if allowed else "deny", "sub": sub, "house": house_id,
                      "action": action, "role": role}))
    if not allowed:
        raise HttpError(403, "Not allowed")


def _house_meta(house_id):
    return table().get_item(Key={"pk": f"HOUSE#{house_id}", "sk": "META"})["Item"]


def me(sub, event):
    items = table().query(KeyConditionExpression=Key("pk").eq(f"USER#{sub}"))["Items"]
    return 200, {"houses": [{"house_id": i["sk"].split("#", 1)[1], "name": i["name"], "role": i["role"]}
                            for i in items]}


def create_house(sub, event):
    data = _body(event)
    name = data.get("name")
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 60:
        raise HttpError(400, "name must be 1 to 60 characters")
    name = name.strip()
    house_id = uuid.uuid4().hex[:12]
    with table().batch_writer() as batch:
        batch.put_item(Item={
            "pk": f"HOUSE#{house_id}", "sk": "META", "name": name,
            "kw": _number(data, "kw", Decimal("0.1"), 100),
            "lat": _number(data, "lat", -90, 90),
            "lon": _number(data, "lon", -180, 180),
            "tilt": _number(data, "tilt", 0, 90, config.DEFAULT_TILT),
            "azimuth": _number(data, "azimuth", 0, 360, config.DEFAULT_AZIMUTH),
        })
        batch.put_item(Item={"pk": f"HOUSE#{house_id}", "sk": f"MEMBER#{sub}", "role": "owner"})
        batch.put_item(Item={"pk": f"USER#{sub}", "sk": f"HOUSE#{house_id}", "role": "owner", "name": name})
        batch.put_item(Item={"pk": "HOUSES", "sk": house_id})  # the list the nightly run walks
    return 201, {"house_id": house_id}


def get_house(sub, event):
    house_id = event["pathParameters"]["houseId"]
    authorize(sub, house_id, "read")
    meta = _house_meta(house_id)
    members = table().query(
        KeyConditionExpression=Key("pk").eq(f"HOUSE#{house_id}") & Key("sk").begins_with("MEMBER#"))["Items"]
    return 200, {
        "house_id": house_id,
        **{k: meta[k] for k in ("name", "kw", "lat", "lon", "tilt", "azimuth")},
        "members": [{"sub": m["sk"].split("#", 1)[1], "role": m["role"]} for m in members],
    }


def create_invite(sub, event):
    house_id = event["pathParameters"]["houseId"]
    authorize(sub, house_id, "create_invite")
    # ponytail: no collision retry; 31^6 codes. Add a conditional put if houses reach the tens of thousands.
    code = "".join(secrets.choice(INVITE_ALPHABET) for _ in range(6))
    expires_at = int(time.time()) + INVITE_TTL_S
    table().put_item(Item={"pk": f"INVITE#{code}", "sk": "META", "house_id": house_id, "expiresAt": expires_at})
    return 201, {"code": code, "expires_at": expires_at}


def join(sub, event):
    code = _body(event).get("code")
    if not isinstance(code, str):
        raise HttpError(400, "code is required")
    invite = table().get_item(Key={"pk": f"INVITE#{code.strip().upper()}", "sk": "META"}).get("Item")
    # DynamoDB TTL deletes late, so the expiry is checked here too.
    if not invite or invite["expiresAt"] < time.time():
        raise HttpError(404, "Invite code not found or expired")
    house_id = invite["house_id"]
    try:
        # Never overwrite an existing membership: an owner using their own code stays owner.
        table().put_item(Item={"pk": f"HOUSE#{house_id}", "sk": f"MEMBER#{sub}", "role": "member"},
                         ConditionExpression="attribute_not_exists(pk)")
    except ClientError as e:
        if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
            raise
    else:
        table().put_item(Item={"pk": f"USER#{sub}", "sk": f"HOUSE#{house_id}", "role": "member",
                               "name": _house_meta(house_id)["name"]})
    print(json.dumps({"authz": "join", "sub": sub, "house": house_id}))
    return 200, {"house_id": house_id}


def _reading(item, limit):
    """One {"date", "kwh"} checked against the calendar and the size of the roof."""
    if not isinstance(item, dict):
        raise HttpError(400, "Each reading needs a date and kwh")
    try:
        date = datetime.date.fromisoformat(item.get("date", ""))
    except (TypeError, ValueError):
        raise HttpError(400, "date must be YYYY-MM-DD")
    if date > datetime.datetime.now(ZoneInfo(config.TZ)).date():
        raise HttpError(400, "date cannot be in the future")
    return date, _number(item, "kwh", 0, limit)


def add_reading(sub, event):
    """One typed reading {"date", "kwh"}, or several confirmed from a screenshot {"readings": [...], "source": "screenshot"}."""
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
            batch.put_item(Item={"pk": f"HOUSE#{house_id}", "sk": f"READING#{date}", "kwh": kwh,
                                 "source": source, "by": sub, "at": int(time.time())})
    _start_analysis(house_id)
    return 201, {"saved": len(rows)}


def record_action(sub, event):
    """The homeowner washed the panels or the vendor came: {"type": "wash" | "visit", "date"}. Dhool then checks
    whether output came back. {"date", "remove": true} takes back one recorded by mistake."""
    house_id = event["pathParameters"]["houseId"]
    authorize(sub, house_id, "write")
    data = _body(event)
    try:
        date = datetime.date.fromisoformat(data.get("date", ""))
    except (TypeError, ValueError):
        raise HttpError(400, "date must be YYYY-MM-DD")
    if date > datetime.datetime.now(ZoneInfo(config.TZ)).date():
        raise HttpError(400, "date cannot be in the future")
    key = {"pk": f"HOUSE#{house_id}", "sk": f"ACTION#{date}"}
    if data.get("remove") is True:
        table().delete_item(Key=key)
    elif data.get("type") in ("wash", "visit"):
        table().put_item(Item={**key, "type": data["type"], "by": sub, "at": int(time.time())})
    else:
        raise HttpError(400, "type must be wash or visit")
    _start_analysis(house_id)
    return 201, {"date": str(date)}


def _read_reply(text):
    """Ask the vendor-reply reader (Laya, in its own Lambda) which of the four kinds of reply this is."""
    client = boto3.client("lambda", config=Config(read_timeout=20, retries={"max_attempts": 0}))
    out = client.invoke(FunctionName=os.environ["MESSAGE_FUNCTION"], Payload=json.dumps({"text": text}))
    return json.loads(out["Payload"].read()).get("label")


def read_vendor_reply(sub, event):
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
        print(json.dumps({"reply_reader": "unavailable", "house": house_id, "error": type(e).__name__}))
        raise HttpError(503, "Dhool could not read the reply just now. Pick what it says below.")
    if label not in REPLY_LABELS:  # the model's output is not trusted to be one of ours
        raise HttpError(503, "Dhool could not read the reply just now. Pick what it says below.")
    return 200, {"label": label}


def start_upload(sub, event):
    """A short-lived, size-limited upload slot for one screenshot, inside this house's folder."""
    house_id = event["pathParameters"]["houseId"]
    authorize(sub, house_id, "write")
    content_type = _body(event).get("content_type")
    if content_type not in IMAGE_TYPES:
        raise HttpError(400, "The screenshot must be a PNG or JPEG image")
    key = f"houses/{house_id}/{uuid.uuid4().hex}.{IMAGE_TYPES[content_type]}"
    region = os.environ["AWS_REGION"]
    s3 = boto3.client("s3", region_name=region, endpoint_url=f"https://s3.{region}.amazonaws.com",
                      config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}))
    post = s3.generate_presigned_post(
        os.environ["UPLOADS"], key, Fields={"Content-Type": content_type},
        Conditions=[{"Content-Type": content_type}, ["content-length-range", 1, MAX_UPLOAD_BYTES]], ExpiresIn=300)
    return 201, {"key": key, "url": post["url"], "fields": post["fields"]}


def _start_reading(house_id, shot_id, key):
    """Hand the screenshot to the reader (the vision model, in its own Lambda). It works in the background."""
    boto3.client("lambda").invoke(FunctionName=os.environ["VISION_FUNCTION"], InvocationType="Event",
                                  Payload=json.dumps({"house_id": house_id, "shot_id": shot_id, "key": key}))


def read_screenshot(sub, event):
    """Start reading an uploaded screenshot. Reading takes about a minute, so the app asks for the result after."""
    house_id = event["pathParameters"]["houseId"]
    authorize(sub, house_id, "write")
    key = _body(event).get("key")
    match = SHOT_KEY.fullmatch(key) if isinstance(key, str) else None
    if not match or match.group(1) != house_id:
        raise HttpError(400, "Upload the screenshot first")
    shot_id, now = match.group(2), int(time.time())
    table().put_item(Item={"pk": f"HOUSE#{house_id}", "sk": f"SHOT#{shot_id}", "status": "reading", "key": key,
                           "by": sub, "at": now, "expiresAt": now + SHOT_TTL_S})
    _start_reading(house_id, shot_id, key)
    return 202, {"shot_id": shot_id, "status": "reading"}


def screenshot_result(sub, event):
    """What the reader found in a screenshot, for the homeowner to confirm or correct. Nothing is saved here."""
    house_id = event["pathParameters"]["houseId"]
    authorize(sub, house_id, "read")
    item = table().get_item(Key={"pk": f"HOUSE#{house_id}", "sk": f"SHOT#{event['pathParameters']['shotId']}"}).get("Item")
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
    boto3.client("lambda").invoke(FunctionName=os.environ["ANALYSIS_FUNCTION"], InvocationType="Event",
                                  Payload=json.dumps({"house_id": house_id}))


def connect_inverter(sub, event):
    house_id = event["pathParameters"]["houseId"]
    authorize(sub, house_id, "write")
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
        Key={"pk": f"HOUSE#{house_id}", "sk": "META"},
        UpdateExpression="SET plant_id = :p, inverter_url = :url, inverter_key = :key, kw = :kw, lat = :lat, lon = :lon, tilt = :tilt, azimuth = :az",
        ExpressionAttributeValues={":p": plant_id, ":url": inverter_url, ":key": api_key, ":kw": Decimal(str(plant["kw"])),
                                   ":lat": Decimal(str(plant["lat"])), ":lon": Decimal(str(plant["lon"])),
                                   ":tilt": Decimal(str(plant["tilt"])), ":az": Decimal(str(plant["azimuth"]))})
    _start_analysis(house_id)
    return 200, {"house_id": house_id, "plant_id": plant_id}


def get_verdict(sub, event):
    house_id = event["pathParameters"]["houseId"]
    authorize(sub, house_id, "read")
    items = table().query(
        KeyConditionExpression=Key("pk").eq(f"HOUSE#{house_id}") & Key("sk").begins_with("VERDICT#"),
        ScanIndexForward=False, Limit=1)["Items"]
    if not items:
        return 200, {"verdict": None}
    return 200, {**json.loads(items[0]["json"]), "computed_at": items[0]["at"]}


def list_readings(sub, event):
    house_id = event["pathParameters"]["houseId"]
    authorize(sub, house_id, "read")
    items = table().query(
        KeyConditionExpression=Key("pk").eq(f"HOUSE#{house_id}") & Key("sk").begins_with("READING#"))["Items"]
    return 200, {"readings": [{"date": i["sk"].split("#", 1)[1], "kwh": i["kwh"], "source": i["source"],
                               "by": i["by"]} for i in items]}


ROUTES = {
    "GET /me": me,
    "POST /houses": create_house,
    "POST /join": join,
    "GET /houses/{houseId}": get_house,
    "POST /houses/{houseId}/invites": create_invite,
    "POST /houses/{houseId}/readings": add_reading,
    "GET /houses/{houseId}/readings": list_readings,
    "POST /houses/{houseId}/inverter": connect_inverter,
    "POST /houses/{houseId}/actions": record_action,
    "POST /houses/{houseId}/vendor-reply": read_vendor_reply,
    "POST /houses/{houseId}/screenshots": start_upload,
    "POST /houses/{houseId}/screenshots/read": read_screenshot,
    "GET /houses/{houseId}/screenshots/{shotId}": screenshot_result,
    "GET /houses/{houseId}/verdict": get_verdict,
}


def handler(event, context):
    try:
        sub = event["requestContext"]["authorizer"]["jwt"]["claims"]["sub"]
        status, payload = ROUTES[event["routeKey"]](sub, event)
    except HttpError as e:
        status, payload = e.status, {"error": e.message}
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(payload, default=lambda d: float(d) if d % 1 else int(d)),
    }
