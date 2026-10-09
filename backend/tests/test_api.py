"""API handler against an in-memory DynamoDB, with events shaped like API Gateway's (HTTP API v2 + JWT authorizer)."""
import datetime
import json
import time

import boto3
import pytest
from moto import mock_aws

from dhool import authz
from handlers import api

FATHER, MOTHER, STRANGER = "sub-father", "sub-mother", "sub-stranger"
HOUSE = {"name": "Sharma house", "kw": 3, "lat": 28.61, "lon": 77.21}
ANALYSED = []  # house ids the API asked the analysis Lambda to run


@pytest.fixture(autouse=True)
def table(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "ap-south-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("TABLE", "dhool-test")
    with mock_aws():
        boto3.resource("dynamodb").create_table(
            TableName="dhool-test", BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"},
                                  {"AttributeName": "sk", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}, {"AttributeName": "sk", "KeyType": "RANGE"}],
        )
        monkeypatch.setattr(api, "_table", None)
        ANALYSED.clear()
        monkeypatch.setattr(api, "_start_analysis", ANALYSED.append)
        yield api.table()


def call(sub, route, body=None, house_id=None, shot_id=None):
    event = {
        "routeKey": route,
        "requestContext": {"domainName": "api.invalid",
                           "authorizer": {"jwt": {"claims": {"sub": sub, "token_use": "access"}}}},
        "pathParameters": {"houseId": house_id, "shotId": shot_id} if house_id else None,
        "body": json.dumps(body) if body is not None else None,
    }
    response = api.handler(event, None)
    return response["statusCode"], json.loads(response["body"])


@pytest.fixture
def house():
    status, body = call(FATHER, "POST /houses", HOUSE)
    assert status == 201
    return body["house_id"]


def join(sub, house_id):
    _, invite = call(FATHER, "POST /houses/{houseId}/invites", house_id=house_id)
    return call(sub, "POST /join", {"code": invite["code"]})


@pytest.mark.parametrize("role,action,allowed", [
    ("owner", "read", True), ("owner", "create_invite", True),
    ("member", "read", True), ("member", "write", True),
    ("member", "create_invite", False), ("member", "remove_member", False),
    (None, "read", False), (None, "write", False), ("admin", "read", False),
])
def test_authz_matrix(role, action, allowed):
    assert authz.decide(role, action) is allowed


def test_creator_owns_the_house_with_default_roof(house):
    assert call(FATHER, "GET /me")[1]["houses"] == [{"house_id": house, "name": "Sharma house", "role": "owner"}]
    status, body = call(FATHER, "GET /houses/{houseId}", house_id=house)
    assert status == 200 and body["kw"] == 3 and body["tilt"] == 20 and body["azimuth"] == 180


def test_family_member_joins_and_sees_the_same_readings(house):
    assert join(MOTHER, house) == (200, {"house_id": house})
    assert call(FATHER, "POST /houses/{houseId}/readings", {"date": "2026-09-30", "kwh": 12.4}, house)[0] == 201
    status, body = call(MOTHER, "GET /houses/{houseId}/readings", house_id=house)
    assert status == 200
    assert body["readings"] == [{"date": "2026-09-30", "kwh": 12.4, "source": "manual", "by": FATHER}]
    assert call(MOTHER, "GET /me")[1]["houses"][0]["role"] == "member"


def test_stranger_is_denied_and_the_decision_is_logged(house, capsys):
    assert call(STRANGER, "GET /houses/{houseId}", house_id=house)[0] == 403
    assert call(STRANGER, "GET /houses/{houseId}/readings", house_id=house)[0] == 403
    assert call(STRANGER, "POST /houses/{houseId}/readings", {"date": "2026-09-30", "kwh": 1}, house)[0] == 403
    last = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert last == {"authz": "deny", "sub": STRANGER, "house": house, "action": "write", "role": None}


def test_identity_in_the_body_is_ignored(house):
    # A stranger claims to be the father and names the house in the body. Only the token's sub counts.
    body = {"date": "2026-09-30", "kwh": 1, "sub": FATHER, "by": FATHER, "house_id": house, "role": "owner"}
    assert call(STRANGER, "POST /houses/{houseId}/readings", body, house)[0] == 403
    assert call(STRANGER, "GET /me")[1]["houses"] == []


def test_only_the_owner_can_invite(house):
    join(MOTHER, house)
    assert call(MOTHER, "POST /houses/{houseId}/invites", house_id=house)[0] == 403


def test_owner_using_own_code_stays_owner(house):
    assert join(FATHER, house)[0] == 200
    assert call(FATHER, "GET /me")[1]["houses"][0]["role"] == "owner"
    assert call(FATHER, "POST /houses/{houseId}/invites", house_id=house)[0] == 201


def test_expired_or_unknown_invite_is_rejected(house, table):
    table.put_item(Item={"pk": "INVITE#OLDONE", "sk": "META", "house_id": house, "expiresAt": int(time.time()) - 1})
    assert call(MOTHER, "POST /join", {"code": "OLDONE"})[0] == 404
    assert call(MOTHER, "POST /join", {"code": "NOSUCH"})[0] == 404
    assert call(MOTHER, "GET /houses/{houseId}", house_id=house)[0] == 403


@pytest.mark.parametrize("body", [
    {"date": "2026-09-30", "kwh": 124},      # typo: more than a 3 kW roof can make
    {"date": "2026-09-30", "kwh": -1},
    {"date": "2026-09-30", "kwh": "12.4"},
    {"date": "30/09/2026", "kwh": 12.4},
    {"date": "2999-01-01", "kwh": 12.4},
    {"kwh": 12.4},
])
def test_bad_readings_are_rejected(house, body):
    assert call(FATHER, "POST /houses/{houseId}/readings", body, house)[0] == 400


@pytest.mark.parametrize("patch", [{"kw": 0}, {"kw": True}, {"lat": 91}, {"name": ""}, {"name": 5}, {"tilt": 120}])
def test_bad_houses_are_rejected(patch):
    assert call(FATHER, "POST /houses", {**HOUSE, **patch})[0] == 400


def test_body_that_is_not_json_is_rejected():
    event = {"routeKey": "POST /houses", "body": "not json",
             "requestContext": {"authorizer": {"jwt": {"claims": {"sub": FATHER}}}}}
    assert api.handler(event, None)["statusCode"] == 400


def test_new_reading_starts_an_analysis_and_verdict_is_shared(house, table):
    assert call(FATHER, "GET /houses/{houseId}/verdict", house_id=house) == (200, {"verdict": None})
    call(FATHER, "POST /houses/{houseId}/readings", {"date": "2026-09-30", "kwh": 12.4}, house)
    assert ANALYSED == [house]
    table.put_item(Item={"pk": f"HOUSE#{house}", "sk": "VERDICT#2026-09-29", "json": '{"verdict": "OK"}', "at": 1})
    table.put_item(Item={"pk": f"HOUSE#{house}", "sk": "VERDICT#2026-09-30", "json": '{"verdict": "CLEAN"}', "at": 2})
    join(MOTHER, house)
    assert call(MOTHER, "GET /houses/{houseId}/verdict", house_id=house) == (200, {"verdict": "CLEAN", "computed_at": 2})
    assert call(STRANGER, "GET /houses/{houseId}/verdict", house_id=house)[0] == 403


def test_connecting_an_inverter_needs_a_working_key_and_keeps_it_server_side(house, table, monkeypatch):
    plant = {"id": "home-00", "kw": 2.0, "lat": 28.6, "lon": 77.2, "tilt": 18.5, "azimuth": 171.0}
    monkeypatch.setattr(api.connectors, "_get", lambda url, key=None: [plant] if key == "inv_goodkey123" else [])
    assert call(STRANGER, "POST /houses/{houseId}/inverter", {"api_key": "inv_goodkey123"}, house)[0] == 403
    assert call(FATHER, "POST /houses/{houseId}/inverter", {"api_key": "inv_wrongkey99"}, house)[0] == 404
    assert call(FATHER, "POST /houses/{houseId}/inverter", {"api_key": "bad key\r\nX-Evil: 1"}, house)[0] == 404
    assert call(FATHER, "POST /houses/{houseId}/inverter", {}, house)[0] == 404
    assert call(FATHER, "POST /houses/{houseId}/inverter", {"api_key": "inv_goodkey123"}, house) == (
        200, {"house_id": house, "plant_id": "home-00"})
    body = call(FATHER, "GET /houses/{houseId}", house_id=house)[1]
    assert (body["kw"], body["tilt"]) == (2, 18.5)
    assert "inv_goodkey123" not in json.dumps(body)  # the key is never sent back to a browser
    assert table.get_item(Key={"pk": f"HOUSE#{house}", "sk": "META"})["Item"]["inverter_key"] == "inv_goodkey123"
    assert ANALYSED == [house]


def test_readings_confirmed_from_a_screenshot_are_saved_together(house):
    readings = [{"date": "2026-09-28", "kwh": 11.9}, {"date": "2026-09-29", "kwh": 12.1}, {"date": "2026-09-29", "kwh": 12.4}]
    assert call(FATHER, "POST /houses/{houseId}/readings", {"readings": readings, "source": "screenshot"}, house) == (201, {"saved": 3})
    saved = call(FATHER, "GET /houses/{houseId}/readings", house_id=house)[1]["readings"]
    assert [(r["date"], r["kwh"], r["source"]) for r in saved] == [("2026-09-28", 11.9, "screenshot"), ("2026-09-29", 12.4, "screenshot")]
    assert ANALYSED == [house]
    for bad in ({"readings": []}, {"readings": "x"}, {"readings": [{"date": "2026-09-28", "kwh": 999}]},
                {"readings": readings, "source": "inverter"}, {"readings": [{"date": "2026-09-28", "kwh": 1}] * 121}):
        assert call(FATHER, "POST /houses/{houseId}/readings", bad, house)[0] == 400


def test_upload_slot_is_scoped_to_the_house_and_limited(house, monkeypatch):
    monkeypatch.setenv("AWS_REGION", "ap-south-1")
    monkeypatch.setenv("UPLOADS", "dhool-uploads-test")
    assert call(STRANGER, "POST /houses/{houseId}/screenshots", {"content_type": "image/png"}, house)[0] == 403
    assert call(FATHER, "POST /houses/{houseId}/screenshots", {"content_type": "application/pdf"}, house)[0] == 400
    assert call(FATHER, "POST /houses/{houseId}/screenshots", {"content_type": "image/webp"}, house)[0] == 400
    status, slot = call(FATHER, "POST /houses/{houseId}/screenshots", {"content_type": "image/png"}, house)
    assert status == 201 and api.SHOT_KEY.fullmatch(slot["key"]).group(1) == house and slot["key"].endswith(".png")
    assert slot["url"] == "https://dhool-uploads-test.s3.ap-south-1.amazonaws.com/"
    assert slot["fields"]["key"] == slot["key"] and slot["fields"]["Content-Type"] == "image/png"


def test_reading_a_screenshot_runs_in_the_background_and_trusts_nothing(house, table, monkeypatch):
    started = []
    monkeypatch.setattr(api, "_start_reading", lambda *args: started.append(args))
    key = f"houses/{house}/{'ab' * 16}.png"
    shot = "ab" * 16
    # only this house's own uploads can be read, and only by its members
    for bad in ("houses/aaaaaaaaaaaa/" + "ab" * 16 + ".png", f"houses/{house}/../x.png", f"houses/{house}/short.png", 7, None):
        assert call(FATHER, "POST /houses/{houseId}/screenshots/read", {"key": bad}, house)[0] == 400
    assert call(STRANGER, "POST /houses/{houseId}/screenshots/read", {"key": key}, house)[0] == 403
    assert started == []

    assert call(FATHER, "POST /houses/{houseId}/screenshots/read", {"key": key}, house) == (202, {"shot_id": shot, "status": "reading"})
    assert started == [(house, shot, key)]
    result = lambda who=FATHER: call(who, "GET /houses/{houseId}/screenshots/{shotId}", house_id=house, shot_id=shot)
    assert result() == (200, {"status": "reading"})
    assert result(STRANGER)[0] == 403
    assert call(FATHER, "GET /houses/{houseId}/screenshots/{shotId}", house_id=house, shot_id="cd" * 16)[0] == 404

    # the reader (a model) writes what it thinks it saw; the API keeps only what can be true for this 3 kW roof
    said = {"reader": "test", "readings": [
        {"date": "2026-09-29", "kwh": 12.4}, {"date": "2026-09-28", "kwh": 11.9}, {"date": "TODAY", "kwh": 9.5},
        {"date": "2026-09-27", "kwh": 372.1}, {"date": "not a date", "kwh": 3}, "junk", {"date": "2999-01-01", "kwh": 3}]}
    uploaded = int(datetime.datetime(2026, 10, 1, 12, tzinfo=datetime.timezone.utc).timestamp())
    table.update_item(Key={"pk": f"HOUSE#{house}", "sk": f"SHOT#{shot}"},
                      UpdateExpression="SET #s = :s, #r = :r, seconds = :t, #a = :a",
                      ExpressionAttributeNames={"#s": "status", "#r": "result", "#a": "at"},
                      ExpressionAttributeValues={":s": "read", ":r": json.dumps(said), ":t": 48, ":a": uploaded})
    join(MOTHER, house)
    assert result(MOTHER) == (200, {"status": "read", "seconds": 48, "readings": [
        {"date": "2026-09-28", "kwh": 11.9}, {"date": "2026-09-29", "kwh": 12.4}, {"date": "2026-10-01", "kwh": 9.5}]})
    assert call(FATHER, "GET /houses/{houseId}/readings", house_id=house)[1]["readings"] == []  # nothing saved yet


@pytest.mark.parametrize("item", [
    {"status": "failed", "result": json.dumps({"readings": [], "error": "boom"})},
    {"status": "read", "result": json.dumps({"readings": []})},
    {"status": "read", "result": json.dumps({"readings": [{"date": "2026-09-27", "kwh": 372.1}]})},
    {"status": "reading", "at": 1},  # started long ago and never finished
])
def test_a_screenshot_that_could_not_be_read_says_so(house, table, item):
    table.put_item(Item={"pk": f"HOUSE#{house}", "sk": "SHOT#" + "ab" * 16, "at": int(time.time()), **item})
    assert call(FATHER, "GET /houses/{houseId}/screenshots/{shotId}", house_id=house, shot_id="ab" * 16) == (200, {"status": "unreadable"})


def test_a_wash_or_visit_is_recorded_for_the_house_and_can_be_taken_back(house, table):
    route = "POST /houses/{houseId}/actions"
    assert call(STRANGER, route, {"type": "wash", "date": "2026-09-30"}, house)[0] == 403
    for bad in ({"type": "paint", "date": "2026-09-30"}, {"type": "wash", "date": "2999-01-01"}, {"type": "wash"}):
        assert call(FATHER, route, bad, house)[0] == 400
    join(MOTHER, house)
    assert call(MOTHER, route, {"type": "wash", "date": "2026-09-30"}, house) == (201, {"date": "2026-09-30"})
    item = table.get_item(Key={"pk": f"HOUSE#{house}", "sk": "ACTION#2026-09-30"})["Item"]
    assert (item["type"], item["by"]) == ("wash", MOTHER) and ANALYSED == [house]
    assert call(FATHER, route, {"date": "2026-09-30", "remove": True}, house)[0] == 201
    assert "Item" not in table.get_item(Key={"pk": f"HOUSE#{house}", "sk": "ACTION#2026-09-30"})
