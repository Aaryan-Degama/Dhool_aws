"""HTTP API for houses, members and readings. One Lambda, routed by routeKey.

The caller is always the `sub` claim verified by the API Gateway JWT authorizer.
Nothing in the body or query string is trusted for identity or house membership.
"""
import base64
import datetime
import json
import os
import secrets
import time
import uuid
from decimal import Decimal
from zoneinfo import ZoneInfo

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from dhool import authz, config, connectors

INVITE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # no 0/O or 1/I/L
INVITE_TTL_S = 7 * 24 * 3600
MAX_KWH_PER_KW = 12  # no roof makes more than this per installed kW in a day

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


def add_reading(sub, event):
    house_id = event["pathParameters"]["houseId"]
    authorize(sub, house_id, "write")
    data = _body(event)
    try:
        date = datetime.date.fromisoformat(data.get("date", ""))
    except (TypeError, ValueError):
        raise HttpError(400, "date must be YYYY-MM-DD")
    if date > datetime.datetime.now(ZoneInfo(config.TZ)).date():
        raise HttpError(400, "date cannot be in the future")
    kwh = _number(data, "kwh", 0, _house_meta(house_id)["kw"] * MAX_KWH_PER_KW)
    table().put_item(Item={"pk": f"HOUSE#{house_id}", "sk": f"READING#{date}", "kwh": kwh,
                           "source": "manual", "by": sub, "at": int(time.time())})
    _start_analysis(house_id)
    return 201, {"date": str(date), "kwh": kwh}


def _start_analysis(house_id):
    """Ask the analysis Lambda for a fresh verdict. Returns at once; the app polls GET .../verdict."""
    boto3.client("lambda").invoke(FunctionName=os.environ["ANALYSIS_FUNCTION"], InvocationType="Event",
                                  Payload=json.dumps({"house_id": house_id}))


def connect_inverter(sub, event):
    house_id = event["pathParameters"]["houseId"]
    authorize(sub, house_id, "write")
    plant_id = _body(event).get("plant_id")
    # The mock inverter cloud lives on this same API. A real brand would have its own fixed URL here.
    inverter_url = f"https://{event['requestContext']['domainName']}/mock"
    plant = connectors.mock_plant(inverter_url, plant_id) if isinstance(plant_id, str) else None
    if plant is None:
        raise HttpError(404, "No such plant on the inverter account")
    # The inverter knows the system better than a typed form does, so its details replace the house's.
    table().update_item(
        Key={"pk": f"HOUSE#{house_id}", "sk": "META"},
        UpdateExpression="SET plant_id = :p, inverter_url = :url, kw = :kw, lat = :lat, lon = :lon, tilt = :tilt, azimuth = :az",
        ExpressionAttributeValues={":p": plant_id, ":url": inverter_url, ":kw": Decimal(str(plant["kw"])),
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
