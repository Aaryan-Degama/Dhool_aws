"""API handler against an in-memory DynamoDB, with events shaped like API Gateway's (HTTP API v2 + JWT authorizer)."""

import datetime
import json
import pathlib
import re
import time

import boto3
import pytest
from boto3.dynamodb.conditions import Key
from botocore.config import Config
from moto import mock_aws

from dhool import authz
from handlers import api, common

FATHER, MOTHER, STRANGER = "sub-father", "sub-mother", "sub-stranger"
HOUSE = {"name": "Sharma house", "kw": 3, "lat": 28.61, "lon": 77.21}
ANALYSED = []  # house ids the API asked the analysis Lambda to run


@pytest.fixture(autouse=True)
def table(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "ap-south-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("TABLE", "dhool-test")
    monkeypatch.setenv("UPLOADS", "dhool-uploads-test")
    with mock_aws():
        boto3.client("s3").create_bucket(
            Bucket="dhool-uploads-test", CreateBucketConfiguration={"LocationConstraint": "ap-south-1"}
        )
        boto3.resource("dynamodb").create_table(
            TableName="dhool-test",
            BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[
                {"AttributeName": "pk", "AttributeType": "S"},
                {"AttributeName": "sk", "AttributeType": "S"},
            ],
            KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}, {"AttributeName": "sk", "KeyType": "RANGE"}],
        )
        common._made.clear()
        ANALYSED.clear()
        monkeypatch.setattr(api, "_start_analysis", ANALYSED.append)
        yield api.table()


def call(sub, route, body=None, house_id=None, shot_id=None, member=None):
    event = {
        "routeKey": route,
        "requestContext": {
            "domainName": "api.invalid",
            "authorizer": {"jwt": {"claims": {"sub": sub, "token_use": "access"}}},
        },
        "pathParameters": {"houseId": house_id, "shotId": shot_id, "sub": member} if house_id else None,
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


@pytest.mark.parametrize(
    "role,action,allowed",
    [
        ("owner", "read", True),
        ("owner", "create_invite", True),
        ("member", "read", True),
        ("member", "write", True),
        ("member", "create_invite", False),
        ("member", "remove_member", False),
        ("member", "connect_inverter", False),
        ("member", "delete_house", False),
        ("member", "set_size", False),
        ("owner", "set_size", True),
        ("member", "leave", True),
        ("owner", "connect_inverter", True),
        ("owner", "delete_house", True),
        (None, "read", False),
        (None, "write", False),
        ("admin", "read", False),
    ],
)
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
    assert last == {
        "authz": "deny",
        "sub": STRANGER,
        "house": house,
        "action": "write",
        "role": None,
        "request_id": None,
    }


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


@pytest.mark.parametrize(
    "body",
    [
        {"date": "2026-09-30", "kwh": 124},  # typo: more than a 3 kW roof can make
        {"date": "2026-09-30", "kwh": -1},
        {"date": "2026-09-30", "kwh": "12.4"},
        {"date": "30/09/2026", "kwh": 12.4},
        {"date": "2999-01-01", "kwh": 12.4},
        {"kwh": 12.4},
    ],
)
def test_bad_readings_are_rejected(house, body):
    assert call(FATHER, "POST /houses/{houseId}/readings", body, house)[0] == 400


@pytest.mark.parametrize("patch", [{"kw": 0}, {"kw": True}, {"lat": 91}, {"name": ""}, {"name": 5}, {"tilt": 120}])
def test_bad_houses_are_rejected(patch):
    assert call(FATHER, "POST /houses", {**HOUSE, **patch})[0] == 400


def test_body_that_is_not_json_is_rejected():
    event = {
        "routeKey": "POST /houses",
        "body": "not json",
        "requestContext": {"authorizer": {"jwt": {"claims": {"sub": FATHER}}}},
    }
    assert api.handler(event, None)["statusCode"] == 400


def test_a_body_that_is_not_base64_when_it_says_so_is_rejected():
    event = {
        "routeKey": "POST /houses",
        "body": "not base64!",
        "isBase64Encoded": True,
        "requestContext": {"authorizer": {"jwt": {"claims": {"sub": FATHER}}}},
    }
    assert api.handler(event, None)["statusCode"] == 400


def test_the_template_sends_the_api_function_exactly_the_routes_it_answers():
    """A route in api.py and not in template.yaml is never reached; one in the template alone is a 404."""
    template = (pathlib.Path(__file__).parents[2] / "template.yaml").read_text()
    function = re.search(r"\n  ApiFunction:\n(.*?)\n  \S", template, re.S).group(1)
    found = re.findall(r"Method: (\w+), Path: (?:'([^']+)'|([^\s,}]+))", function)  # a path with {braces} is quoted
    events = [f"{method} {quoted or bare}" for method, quoted, bare in found]
    assert sorted(events) == sorted(api.ROUTES) and len(events) >= 20


def test_a_route_the_api_does_not_have_is_not_found():
    assert call(FATHER, "PATCH /houses") == (404, {"error": "No such route"})
    assert api.handler({}, None)["statusCode"] == 404


def test_an_error_nobody_foresaw_is_a_500_with_the_request_id_and_is_logged(monkeypatch, capsys):
    def broken(sub, event):
        raise RuntimeError("the table is on fire")

    monkeypatch.setitem(api.ROUTES, "GET /me", broken)
    event = {"routeKey": "GET /me", "requestContext": {"authorizer": {"jwt": {"claims": {"sub": FATHER}}}}}
    response = api.handler(event, type("Context", (), {"aws_request_id": "req-123"})())
    assert response["statusCode"] == 500
    assert json.loads(response["body"]) == {"error": "Something went wrong", "request_id": "req-123"}
    line = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert line["error"] == "unhandled" and line["exception"] == "RuntimeError" and line["request_id"] == "req-123"
    assert "the table is on fire" in line["detail"] and line["route"] == "GET /me"


def test_new_reading_starts_an_analysis_and_verdict_is_shared(house, table):
    assert call(FATHER, "GET /houses/{houseId}/verdict", house_id=house) == (200, {"verdict": None})
    call(FATHER, "POST /houses/{houseId}/readings", {"date": "2026-09-30", "kwh": 12.4}, house)
    assert ANALYSED == [house]
    table.put_item(Item={"pk": f"HOUSE#{house}", "sk": "VERDICT#2026-09-29", "json": '{"verdict": "OK"}', "at": 1})
    table.put_item(Item={"pk": f"HOUSE#{house}", "sk": "VERDICT#2026-09-30", "json": '{"verdict": "CLEAN"}', "at": 2})
    join(MOTHER, house)
    assert call(MOTHER, "GET /houses/{houseId}/verdict", house_id=house) == (
        200,
        {"verdict": "CLEAN", "computed_at": 2},
    )
    assert call(STRANGER, "GET /houses/{houseId}/verdict", house_id=house)[0] == 403


def test_connecting_an_inverter_needs_a_working_key_and_keeps_it_server_side(house, table, monkeypatch):
    plant = {"id": "home-00", "kw": 2.0, "lat": 28.6, "lon": 77.2, "tilt": 18.5, "azimuth": 171.0}
    monkeypatch.setattr(api.connectors, "_get", lambda url, key=None: [plant] if key == "inv_goodkey123" else [])
    assert call(STRANGER, "POST /houses/{houseId}/inverter", {"api_key": "inv_goodkey123"}, house)[0] == 403
    join(MOTHER, house)  # linking replaces the roof's details for everyone, so it is the owner's to do
    assert call(MOTHER, "POST /houses/{houseId}/inverter", {"api_key": "inv_goodkey123"}, house)[0] == 403
    assert call(FATHER, "POST /houses/{houseId}/inverter", {"api_key": "inv_wrongkey99"}, house)[0] == 404
    assert call(FATHER, "POST /houses/{houseId}/inverter", {"api_key": "bad key\r\nX-Evil: 1"}, house)[0] == 404
    assert call(FATHER, "POST /houses/{houseId}/inverter", {}, house)[0] == 404
    assert call(FATHER, "POST /houses/{houseId}/inverter", {"api_key": "inv_goodkey123"}, house) == (
        200,
        {"house_id": house, "plant_id": "home-00"},
    )
    body = call(FATHER, "GET /houses/{houseId}", house_id=house)[1]
    assert (body["kw"], body["tilt"], body["linked"]) == (2, 18.5, True)
    assert "inv_goodkey123" not in json.dumps(body)  # the key is never sent back to a browser
    assert table.get_item(Key={"pk": f"HOUSE#{house}", "sk": "META"})["Item"]["inverter_key"] == "inv_goodkey123"
    assert ANALYSED == [house]


def test_readings_confirmed_from_a_screenshot_are_saved_together(house):
    readings = [
        {"date": "2026-09-28", "kwh": 11.9},
        {"date": "2026-09-29", "kwh": 12.1},
        {"date": "2026-09-29", "kwh": 12.4},
    ]
    assert call(FATHER, "POST /houses/{houseId}/readings", {"readings": readings, "source": "screenshot"}, house) == (
        201,
        {"saved": 3},
    )
    saved = call(FATHER, "GET /houses/{houseId}/readings", house_id=house)[1]["readings"]
    assert [(r["date"], r["kwh"], r["source"]) for r in saved] == [
        ("2026-09-28", 11.9, "screenshot"),
        ("2026-09-29", 12.4, "screenshot"),
    ]
    assert ANALYSED == [house]
    for bad in (
        {"readings": []},
        {"readings": "x"},
        {"readings": [{"date": "2026-09-28", "kwh": 999}]},
        {"readings": readings, "source": "inverter"},
        {"readings": [{"date": "2026-09-28", "kwh": 1}] * 121},
    ):
        assert call(FATHER, "POST /houses/{houseId}/readings", bad, house)[0] == 400


def test_upload_slot_is_scoped_to_the_house_and_limited(house, monkeypatch):
    monkeypatch.setenv("AWS_REGION", "ap-south-1")
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
    for bad in (
        "houses/aaaaaaaaaaaa/" + "ab" * 16 + ".png",
        f"houses/{house}/../x.png",
        f"houses/{house}/short.png",
        7,
        None,
    ):
        assert call(FATHER, "POST /houses/{houseId}/screenshots/read", {"key": bad}, house)[0] == 400
    assert call(STRANGER, "POST /houses/{houseId}/screenshots/read", {"key": key}, house)[0] == 403
    assert started == []

    assert call(FATHER, "POST /houses/{houseId}/screenshots/read", {"key": key}, house) == (
        202,
        {"shot_id": shot, "status": "reading"},
    )
    assert started == [(house, shot, key)]

    def result(who=FATHER):
        return call(who, "GET /houses/{houseId}/screenshots/{shotId}", house_id=house, shot_id=shot)

    assert result() == (200, {"status": "reading"})
    assert result(STRANGER)[0] == 403
    assert call(FATHER, "GET /houses/{houseId}/screenshots/{shotId}", house_id=house, shot_id="cd" * 16)[0] == 404

    # the reader (a model) writes what it thinks it saw; the API keeps only what can be true for this 3 kW roof
    said = {
        "reader": "test",
        "readings": [
            {"date": "2026-09-29", "kwh": 12.4},
            {"date": "2026-09-28", "kwh": 11.9},
            {"date": "TODAY", "kwh": 9.5},
            {"date": "2026-09-27", "kwh": 372.1},
            {"date": "not a date", "kwh": 3},
            "junk",
            {"date": "2999-01-01", "kwh": 3},
        ],
    }
    uploaded = int(datetime.datetime(2026, 10, 1, 12, tzinfo=datetime.UTC).timestamp())
    table.update_item(
        Key={"pk": f"HOUSE#{house}", "sk": f"SHOT#{shot}"},
        UpdateExpression="SET #s = :s, #r = :r, seconds = :t, #a = :a",
        ExpressionAttributeNames={"#s": "status", "#r": "result", "#a": "at"},
        ExpressionAttributeValues={":s": "read", ":r": json.dumps(said), ":t": 48, ":a": uploaded},
    )
    join(MOTHER, house)
    assert result(MOTHER) == (
        200,
        {
            "status": "read",
            "seconds": 48,
            "readings": [
                {"date": "2026-09-28", "kwh": 11.9},
                {"date": "2026-09-29", "kwh": 12.4},
                {"date": "2026-10-01", "kwh": 9.5},
            ],
        },
    )
    assert call(FATHER, "GET /houses/{houseId}/readings", house_id=house)[1]["readings"] == []  # nothing saved yet


@pytest.mark.parametrize(
    "item",
    [
        {"status": "failed", "result": json.dumps({"readings": [], "error": "boom"})},
        {"status": "read", "result": json.dumps({"readings": []})},
        {"status": "read", "result": json.dumps({"readings": [{"date": "2026-09-27", "kwh": 372.1}]})},
        {"status": "reading", "at": 1},  # started long ago and never finished
    ],
)
def test_a_screenshot_that_could_not_be_read_says_so(house, table, item):
    table.put_item(Item={"pk": f"HOUSE#{house}", "sk": "SHOT#" + "ab" * 16, "at": int(time.time()), **item})
    assert call(FATHER, "GET /houses/{houseId}/screenshots/{shotId}", house_id=house, shot_id="ab" * 16) == (
        200,
        {"status": "unreadable"},
    )


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


def test_a_member_says_whether_a_days_advice_was_useful_and_it_is_kept_as_long_as_the_verdict(house, table):
    from handlers import analysis  # here, not at the top: only this test needs the pvlib container's handler

    route = "POST /houses/{houseId}/feedback"
    assert call(STRANGER, route, {"date": "2026-09-30", "helpful": True}, house)[0] == 403
    for bad in (
        {"helpful": True},
        {"date": "2999-01-01", "helpful": True},
        {"date": "30/09/2026", "helpful": True},
        {"date": "2026-09-30"},
        {"date": "2026-09-30", "helpful": "yes"},
        {"date": "2026-09-30", "helpful": 1},
        {"date": "2026-09-30", "helpful": None},
    ):
        assert call(FATHER, route, bad, house)[0] == 400
    assert not [i for i in everything_of(table, house) if i["sk"].startswith("FEEDBACK#")]  # nothing refused was kept
    join(MOTHER, house)
    # She says who she is and names another home in the body. Only the token's sub and the path count.
    said = {"date": "2026-09-30", "helpful": True, "by": FATHER, "sub": FATHER, "house_id": "aaaaaaaaaaaa"}
    assert call(MOTHER, route, said, house) == (201, {"date": "2026-09-30", "helpful": True})
    item = table.get_item(Key={"pk": f"HOUSE#{house}", "sk": "FEEDBACK#2026-09-30"})["Item"]
    assert (item["helpful"], item["by"]) == (True, MOTHER)
    assert abs(int(item["expiresAt"]) - (time.time() + 400 * 24 * 3600)) < 60
    assert api.FEEDBACK_TTL_S == analysis.VERDICT_TTL_S
    assert ANALYSED == []  # an opinion is not a reading: no new verdict is worked out


def test_a_second_answer_for_the_same_day_replaces_the_first(house, table):
    route = "POST /houses/{houseId}/feedback"
    join(MOTHER, house)
    assert call(MOTHER, route, {"date": "2026-09-30", "helpful": True}, house)[0] == 201
    assert call(FATHER, route, {"date": "2026-09-30", "helpful": False}, house) == (
        201,
        {"date": "2026-09-30", "helpful": False},
    )
    assert call(FATHER, route, {"date": "2026-09-29", "helpful": True}, house)[0] == 201  # another day is another item
    kept = [(i["sk"], i["helpful"], i["by"]) for i in everything_of(table, house) if i["sk"].startswith("FEEDBACK#")]
    assert kept == [("FEEDBACK#2026-09-29", True, FATHER), ("FEEDBACK#2026-09-30", False, FATHER)]


def test_a_vendor_reply_is_read_for_members_only_and_the_model_is_not_trusted(house, monkeypatch):
    asked = []
    monkeypatch.setattr(api, "_read_reply", lambda text: asked.append(text) or "visit_scheduled")
    route = "POST /houses/{houseId}/vendor-reply"
    assert call(FATHER, route, {"text": "  Sir kal 11 baje aata hu "}, house) == (200, {"label": "visit_scheduled"})
    assert asked == ["Sir kal 11 baje aata hu"]
    assert call(STRANGER, route, {"text": "ok"}, house)[0] == 403
    assert (
        call(FATHER, route, {"text": "   "}, house)[0] == 400
        and call(FATHER, route, {"text": "x" * 1001}, house)[0] == 400
    )
    monkeypatch.setattr(api, "_read_reply", lambda text: "wash_the_car")  # not one of the four labels
    assert call(FATHER, route, {"text": "ok"}, house)[0] == 503

    def down(text):
        raise TimeoutError("the reader is still starting")

    monkeypatch.setattr(api, "_read_reply", down)
    assert call(FATHER, route, {"text": "ok"}, house)[0] == 503 and len(asked) == 1


def test_the_cost_of_a_wash_is_a_setting_of_the_house(house):
    assert call(FATHER, "GET /houses/{houseId}", house_id=house)[1]["wash_cost_rs"] == 50
    assert call(STRANGER, "POST /houses/{houseId}/settings", {"wash_cost_rs": 350}, house)[0] == 403
    for bad in ({"wash_cost_rs": -1}, {"wash_cost_rs": "350"}, {"wash_cost_rs": 99999}, {}):
        assert call(FATHER, "POST /houses/{houseId}/settings", bad, house)[0] == 400
    assert call(FATHER, "POST /houses/{houseId}/settings", {"wash_cost_rs": 350}, house) == (200, {"wash_cost_rs": 350})
    assert call(FATHER, "GET /houses/{houseId}", house_id=house)[1]["wash_cost_rs"] == 350 and ANALYSED == [house]


def test_the_tariff_is_a_setting_too_and_either_figure_can_be_sent(house):
    route = "POST /houses/{houseId}/settings"
    assert call(FATHER, "GET /houses/{houseId}", house_id=house)[1]["tariff_rs"] == 7
    for bad in ({"tariff_rs": 0}, {"tariff_rs": 31}, {"tariff_rs": 8, "wash_cost_rs": -1}):
        assert call(FATHER, route, bad, house)[0] == 400
    assert call(FATHER, route, {"tariff_rs": 8.5}, house) == (200, {"tariff_rs": 8.5})
    assert call(FATHER, route, {"tariff_rs": 6, "wash_cost_rs": 200}, house) == (
        200,
        {"tariff_rs": 6, "wash_cost_rs": 200},
    )
    body = call(FATHER, "GET /houses/{houseId}", house_id=house)[1]
    assert (body["tariff_rs"], body["wash_cost_rs"]) == (6, 200) and ANALYSED == [house, house]


def test_the_sixth_wrong_code_locks_joining_for_an_hour(house, table):
    for _ in range(5):
        assert call(MOTHER, "POST /join", {"code": "NOSUCH"})[0] == 404
    assert call(MOTHER, "POST /join", {"code": "NOSUCH"}) == (
        429,
        {"error": "Too many wrong codes. Try again in an hour."},
    )
    assert join(MOTHER, house)[0] == 429  # a right code is refused too while locked
    assert join(STRANGER, house)[0] == 200  # the count is each person's own
    # an hour on, before DynamoDB has removed the count
    table.update_item(
        Key={"pk": f"JOINFAIL#{MOTHER}", "sk": "META"},
        UpdateExpression="SET expiresAt = :t",
        ExpressionAttributeValues={":t": int(time.time()) - 1},
    )
    assert join(MOTHER, house)[0] == 200


def test_a_person_can_be_in_five_homes_and_no_more(house):
    for n in range(api.MAX_HOUSES - 1):
        assert call(MOTHER, "POST /houses", {**HOUSE, "name": f"Home {n}"})[0] == 201
    assert join(MOTHER, house)[0] == 200  # the fifth, by a family code
    assert call(MOTHER, "POST /houses", HOUSE) == (409, {"error": api.TOO_MANY_HOUSES})
    other = call(STRANGER, "POST /houses", HOUSE)[1]["house_id"]
    code = call(STRANGER, "POST /houses/{houseId}/invites", house_id=other)[1]["code"]
    assert call(MOTHER, "POST /join", {"code": code}) == (409, {"error": api.TOO_MANY_HOUSES})
    assert len(call(MOTHER, "GET /me")[1]["houses"]) == api.MAX_HOUSES


def test_a_home_holds_ten_people_and_no_more(house):
    for n in range(api.MAX_MEMBERS - 1):
        assert join(f"sub-cousin-{n}", house)[0] == 200
    assert join(STRANGER, house) == (409, {"error": api.HOUSE_FULL})
    assert call(STRANGER, "GET /houses/{houseId}", house_id=house)[0] == 403
    assert join("sub-cousin-0", house)[0] == 200  # someone already in is not counted against it
    assert len(call(FATHER, "GET /houses/{houseId}", house_id=house)[1]["members"]) == api.MAX_MEMBERS


def test_the_quota_lines_have_their_hindi():
    hindi = (pathlib.Path(__file__).parents[2] / "web/src/hi.js").read_text()
    assert f'"{api.TOO_MANY_HOUSES}"' in hindi and f'"{api.HOUSE_FULL}"' in hindi
    assert hindi.count(f'"{api.SIZE_FROM_INVERTER}"') == 2  # its Hindi, and in the list of lines that arrive


def test_a_new_home_never_overwrites_one_whose_id_it_drew(house, table, monkeypatch):
    drawn = iter([house, "b" * 12])  # the first draw is the id of the home that is already there
    monkeypatch.setattr(api, "_new_house_id", lambda: next(drawn))
    assert call(MOTHER, "POST /houses", {**HOUSE, "name": "Verma house"}) == (201, {"house_id": "b" * 12})
    assert call(FATHER, "GET /houses/{houseId}", house_id=house)[1]["name"] == "Sharma house"
    assert call(MOTHER, "GET /houses/{houseId}", house_id=house)[0] == 403
    assert [h["name"] for h in call(MOTHER, "GET /me")[1]["houses"]] == ["Verma house"]


def test_aws_clients_are_made_once_and_try_again_with_backoff():
    first = common.client("lambda")
    assert common.client("lambda") is first and common.table() is common.table()
    assert first.meta.config.retries == {"mode": "standard", "total_max_attempts": 4}  # the call and three more tries
    # The reply reader's own: one try and a short wait, because the homeowner is watching.
    reply = common.client("lambda", key="reply reader", config=Config(read_timeout=20, retries={"max_attempts": 0}))
    assert reply is not first and reply.meta.config.retries["total_max_attempts"] == 1


def test_lists_longer_than_one_page_come_back_whole(house, table, monkeypatch):
    asked = []

    def two_at_a_time(table, **query):  # DynamoDB pages at 1 MB; a page of two shows the same seam
        asked.append(query)
        return common.query_all(table, Limit=2, **query)

    monkeypatch.setattr(api, "query_all", two_at_a_time)
    days = [f"2026-09-{d:02d}" for d in range(1, 8)]
    call(FATHER, "POST /houses/{houseId}/readings", {"readings": [{"date": d, "kwh": 9} for d in days]}, house)
    for n in range(4):
        join(f"sub-cousin-{n}", house)
    assert [r["date"] for r in call(FATHER, "GET /houses/{houseId}/readings", house_id=house)[1]["readings"]] == days
    assert len(call(FATHER, "GET /houses/{houseId}", house_id=house)[1]["members"]) == 5
    assert call(FATHER, "DELETE /houses/{houseId}", house_id=house)[0] == 200
    assert everything_of(table, house) == [] and len(asked) == 3


def test_the_location_is_kept_to_two_decimals(table, monkeypatch):
    _, body = call(FATHER, "POST /houses", {**HOUSE, "lat": 28.613939, "lon": 77.209021})
    home = call(FATHER, "GET /houses/{houseId}", house_id=body["house_id"])[1]
    assert (home["lat"], home["lon"], home["linked"]) == (28.61, 77.21, False)
    plant = {"id": "home-00", "kw": 2.0, "lat": 26.91243, "lon": 75.78727, "tilt": 18.5, "azimuth": 171.0}
    monkeypatch.setattr(api.connectors, "_get", lambda url, key=None: [plant])
    call(FATHER, "POST /houses/{houseId}/inverter", {"api_key": "inv_goodkey123"}, body["house_id"])
    home = call(FATHER, "GET /houses/{houseId}", house_id=body["house_id"])[1]
    assert (home["lat"], home["lon"]) == (26.91, 75.79)


def test_members_are_listed_with_when_they_joined_and_which_one_is_you(house, table):
    join(MOTHER, house)
    table.put_item(
        Item={"pk": f"HOUSE#{house}", "sk": "MEMBER#sub-old", "role": "member"}
    )  # joined before dates were kept
    members = {m["sub"]: m for m in call(MOTHER, "GET /houses/{houseId}", house_id=house)[1]["members"]}
    assert [members[s]["me"] for s in (FATHER, MOTHER, "sub-old")] == [False, True, False]
    assert members[MOTHER]["joined_at"] > 1_700_000_000 and members["sub-old"]["joined_at"] is None
    assert members[FATHER]["role"] == "owner"


def test_a_home_is_fetched_with_one_read_of_its_members_and_the_decision_is_still_logged(house, monkeypatch, capsys):
    join(MOTHER, house)
    monkeypatch.setattr(api, "authorize", lambda *a: pytest.fail("the member list already says who is asking"))
    assert call(MOTHER, "GET /houses/{houseId}", house_id=house)[0] == 200
    assert json.loads(capsys.readouterr().out.strip().splitlines()[-1]) == {
        "authz": "allow",
        "sub": MOTHER,
        "house": house,
        "action": "read",
        "role": "member",
        "request_id": None,
    }
    assert call(STRANGER, "GET /houses/{houseId}", house_id=house) == (403, {"error": "Not allowed"})
    assert call(STRANGER, "GET /houses/{houseId}", house_id="nosuchhouse0")[0] == 403
    assert json.loads(capsys.readouterr().out.strip().splitlines()[-1]) == {
        "authz": "deny",
        "sub": STRANGER,
        "house": "nosuchhouse0",
        "action": "read",
        "role": None,
        "request_id": None,
    }


SUBSCRIPTION = {
    "endpoint": "https://fcm.googleapis.com/fcm/send/abc:APA91b-x_y",
    "keys": {"p256dh": "BPA" + "x" * 84, "auth": "y" * 22},
}


def test_a_push_subscription_is_kept_only_for_a_real_push_service(house, table):
    route = "POST /houses/{houseId}/push"
    assert call(STRANGER, route, {"subscription": SUBSCRIPTION, "lang": "hi"}, house)[0] == 403
    for endpoint in (
        "https://evil.example/fcm/send/abc",
        "http://fcm.googleapis.com/fcm/send/abc",
        "https://fcm.googleapis.com@evil.example/x",
        "https://fcm.googleapis.com.evil.example/x",
        "https://169.254.169.254/latest/meta-data/",
        "https://fcm.googleapis.com",
        None,
        7,
        "https://fcm.googleapis.com/x\nhttps://evil.example/",
        "https://push.apple.com.evil.example/x",
    ):
        status, body = call(
            FATHER, route, {"subscription": {**SUBSCRIPTION, "endpoint": endpoint}, "lang": "en"}, house
        )
        assert (status, body) == (400, {"error": "This browser's notifications are not supported."}), endpoint
    for bad in (
        {"subscription": {**SUBSCRIPTION, "keys": {"p256dh": "x"}}},
        {"subscription": {**SUBSCRIPTION, "keys": {"p256dh": "x" * 500, "auth": "y"}}},
        {"subscription": SUBSCRIPTION, "lang": "fr"},
        {"subscription": "x"},
        {},
    ):
        assert call(FATHER, route, bad, house)[0] == 400
    for good in (
        "https://updates.push.services.mozilla.com/wpush/v2/gAAAA",
        "https://web.push.apple.com/QOx-1",
        "https://wns2-par02p.notify.windows.com/w/?token=BQYAAAD%2b",
    ):
        assert call(FATHER, route, {"subscription": {**SUBSCRIPTION, "endpoint": good}}, house)[0] == 201
    assert call(FATHER, route, {"subscription": SUBSCRIPTION, "lang": "hi"}, house) == (201, {"subscribed": True})
    assert (
        call(FATHER, route, {"subscription": SUBSCRIPTION, "lang": "hi"}, house)[0] == 201
    )  # the same phone again: one item
    kept = [
        i
        for i in table.query(KeyConditionExpression=Key("pk").eq(f"HOUSE#{house}") & Key("sk").begins_with("PUSH#"))[
            "Items"
        ]
        if i["endpoint"] == SUBSCRIPTION["endpoint"]
    ]
    assert len(kept) == 1 and (kept[0]["lang"], kept[0]["by"], kept[0]["auth"]) == ("hi", FATHER, "y" * 22)
    assert call(FATHER, "DELETE /houses/{houseId}/push", {"endpoint": SUBSCRIPTION["endpoint"]}, house) == (
        200,
        {"subscribed": False},
    )
    assert "Item" not in table.get_item(Key={"pk": kept[0]["pk"], "sk": kept[0]["sk"]})


def everything_of(table, house):
    return table.query(KeyConditionExpression=Key("pk").eq(f"HOUSE#{house}"))["Items"]


def test_only_the_owner_deletes_the_house_and_nothing_of_it_is_left(house, table):
    join(MOTHER, house)
    call(
        FATHER,
        "POST /houses/{houseId}/readings",
        {"readings": [{"date": f"2026-09-{d:02d}", "kwh": 10} for d in range(1, 31)], "source": "screenshot"},
        house,
    )
    call(MOTHER, "POST /houses/{houseId}/actions", {"type": "wash", "date": "2026-09-30"}, house)
    call(MOTHER, "POST /houses/{houseId}/feedback", {"date": "2026-09-30", "helpful": True}, house)
    call(MOTHER, "POST /houses/{houseId}/push", {"subscription": SUBSCRIPTION}, house)
    _, invite = call(FATHER, "POST /houses/{houseId}/invites", house_id=house)
    bucket = boto3.resource("s3").Bucket("dhool-uploads-test")
    bucket.put_object(Key=f"houses/{house}/{'ab' * 16}.png", Body=b"x")
    bucket.put_object(Key=f"houses/aaaaaaaaaaaa/{'ab' * 16}.png", Body=b"x")  # a neighbour's
    _, other = call(STRANGER, "POST /houses", HOUSE)

    assert call(MOTHER, "DELETE /houses/{houseId}", house_id=house)[0] == 403
    assert call(STRANGER, "DELETE /houses/{houseId}", house_id=house)[0] == 403
    assert len(everything_of(table, house)) == 38  # with the two family codes it gave out
    assert "FEEDBACK#2026-09-30" in [i["sk"] for i in everything_of(table, house)]
    assert call(FATHER, "DELETE /houses/{houseId}", house_id=house) == (200, {"deleted": house})

    assert everything_of(table, house) == []
    assert call(FATHER, "GET /me")[1]["houses"] == [] and call(MOTHER, "GET /me")[1]["houses"] == []
    assert [i["sk"] for i in table.query(KeyConditionExpression=Key("pk").eq("HOUSES"))["Items"]] == [other["house_id"]]
    assert [o.key for o in bucket.objects.all()] == [f"houses/aaaaaaaaaaaa/{'ab' * 16}.png"]
    assert call(FATHER, "GET /houses/{houseId}", house_id=house)[0] == 403
    assert call(STRANGER, "POST /join", {"code": invite["code"]})[0] == 404  # the code outlived the house
    assert everything_of(table, house) == []
    assert call(STRANGER, "GET /houses/{houseId}", house_id=other["house_id"])[0] == 200  # the neighbour is untouched


def test_the_owner_removes_a_member_who_then_has_no_access_or_alerts(house, table):
    route = "DELETE /houses/{houseId}/members/{sub}"
    join(MOTHER, house), join(STRANGER, house)
    call(MOTHER, "POST /houses/{houseId}/push", {"subscription": SUBSCRIPTION}, house)
    call(
        FATHER,
        "POST /houses/{houseId}/push",
        {"subscription": {**SUBSCRIPTION, "endpoint": "https://web.push.apple.com/father"}},
        house,
    )
    assert call(STRANGER, route, house_id=house, member=MOTHER)[0] == 403  # a member cannot remove someone else
    assert call(MOTHER, route, house_id=house, member=FATHER)[0] == 403
    assert call("sub-outsider", route, house_id=house, member="sub-outsider")[0] == 403
    code = call(FATHER, "POST /houses/{houseId}/invites", house_id=house)[1]["code"]  # one she may still hold
    assert call(FATHER, route, house_id=house, member=MOTHER) == (200, {"removed": MOTHER})
    assert call(MOTHER, "POST /join", {"code": code})[0] == 404  # the home's codes went with her
    assert call(MOTHER, "GET /houses/{houseId}", house_id=house)[0] == 403
    assert call(MOTHER, "GET /houses/{houseId}/verdict", house_id=house)[0] == 403
    assert call(MOTHER, "GET /me")[1]["houses"] == []
    pushes = [i for i in everything_of(table, house) if i["sk"].startswith("PUSH#")]
    assert [i["by"] for i in pushes] == [FATHER]
    assert {m["sub"] for m in call(FATHER, "GET /houses/{houseId}", house_id=house)[1]["members"]} == {FATHER, STRANGER}


def test_removing_someone_who_is_not_in_the_home_is_a_404_and_revokes_nothing(house, table):
    join(MOTHER, house)
    call(MOTHER, "POST /houses/{houseId}/push", {"subscription": SUBSCRIPTION}, house)
    code = call(FATHER, "POST /houses/{houseId}/invites", house_id=house)[1]["code"]
    before = sorted(i["sk"] for i in everything_of(table, house))
    assert call(FATHER, "DELETE /houses/{houseId}/members/{sub}", house_id=house, member="sub-nobody") == (
        404,
        {"error": "That person is not in this home"},
    )
    assert sorted(i["sk"] for i in everything_of(table, house)) == before  # her alerts and the code are still there
    assert call(STRANGER, "POST /join", {"code": code})[0] == 200


def test_a_member_can_leave_and_the_owner_cannot(house):
    route = "DELETE /houses/{houseId}/members/{sub}"
    join(MOTHER, house)
    assert call(FATHER, route, house_id=house, member=FATHER) == (
        400,
        {"error": "The owner cannot leave. Delete the home instead."},
    )
    assert call(FATHER, "GET /me")[1]["houses"][0]["role"] == "owner"
    assert call(MOTHER, route, house_id=house, member=MOTHER) == (200, {"removed": MOTHER})
    assert (
        call(MOTHER, "GET /houses/{houseId}", house_id=house)[0] == 403 and call(MOTHER, "GET /me")[1]["houses"] == []
    )


def test_the_log_lists_what_dhool_advised_and_what_the_household_did(house, table):
    def said(date, verdict, cause, **more):
        table.put_item(
            Item={
                "pk": f"HOUSE#{house}",
                "sk": f"VERDICT#{date}",
                "at": 1,
                "json": json.dumps({"verdict": verdict, "cause": cause, "loss_pct": 9.0, **more}),
            }
        )

    said("2026-09-26", "OK", "ok")
    said("2026-09-27", "WAIT", "dust", evidence={"wait_for": "rain"})
    said("2026-09-28", "CLEAN", "dust")
    said("2026-09-29", "CLEAN", "dust")  # the same advice again: not a new line
    call(FATHER, "POST /houses/{houseId}/actions", {"type": "wash", "date": "2026-09-29"}, house)
    said("2026-10-02", "OK", "ok", check={"type": "wash", "date": "2026-09-29", "status": "verified"})
    assert call(STRANGER, "GET /houses/{houseId}/history", house_id=house)[0] == 403
    log = call(FATHER, "GET /houses/{houseId}/history", house_id=house)[1]["log"]
    assert [(e["date"], e["kind"], e.get("verdict") or e["type"]) for e in log] == [
        ("2026-10-02", "said", "OK"),
        ("2026-09-29", "did", "wash"),
        ("2026-09-28", "said", "CLEAN"),
        ("2026-09-27", "said", "WAIT"),
        ("2026-09-26", "said", "OK"),
    ]
    assert log[1]["status"] == "verified" and log[3]["wait_for"] == "rain"


def test_the_last_twenty_washes_and_visits_come_newest_first_each_with_what_a_verdict_said_of_it(house, table):
    def said(date, check):
        item = {"pk": f"HOUSE#{house}", "sk": f"VERDICT#{date}", "at": 1}
        table.put_item(Item={**item, "json": json.dumps({"verdict": "OK", "cause": "ok", "check": check})})

    route = "POST /houses/{houseId}/actions"
    for day in range(1, 23):  # 22 reports: the two oldest fall off
        call(FATHER, route, {"type": "visit" if day == 20 else "wash", "date": f"2026-08-{day:02d}"}, house)
    said("2026-08-19", {"type": "wash", "date": "2026-08-19", "status": "not_recovered"})
    said("2026-08-20", {"type": "visit", "date": "2026-08-20", "status": "waiting"})  # the next wash came too soon
    said("2026-08-21", {"type": "visit", "date": "2026-08-21", "status": "verified"})  # a visit since taken back
    said("2026-08-22", {"type": "wash", "date": "2026-08-22", "status": "waiting"})
    body = call(FATHER, "GET /houses/{houseId}/history", house_id=house)[1]
    actions = body["actions"]
    assert [a["date"] for a in actions] == [f"2026-08-{day:02d}" for day in range(22, 2, -1)]
    assert [(a["type"], a["status"]) for a in actions[:5]] == [
        ("wash", "waiting"),  # the newest: Dhool is still measuring
        ("wash", None),  # the outcome on record was for a visit that day, not this wash
        ("visit", None),  # never measured: nothing is said, not "still measuring"
        ("wash", "not_recovered"),
        ("wash", None),
    ]
    assert [e for e in body["log"] if e["kind"] == "did"] == actions


def test_the_system_size_is_the_owners_to_change_until_an_inverter_gives_it(house, table):
    route = "POST /houses/{houseId}/settings"
    join(MOTHER, house)
    assert call(MOTHER, route, {"kw": 3.3}, house)[0] == 403
    assert call(MOTHER, route, {"wash_cost_rs": 80}, house)[0] == 200  # the other figures stay anyone's in the home
    for bad in ({"kw": 0}, {"kw": 101}, {"kw": "3.3"}, {"kw": True}):
        assert call(FATHER, route, bad, house)[0] == 400
    assert call(FATHER, route, {"kw": 3.3}, house) == (200, {"kw": 3.3})
    assert call(FATHER, "GET /houses/{houseId}", house_id=house)[1]["kw"] == 3.3 and ANALYSED == [house, house]
    # A 3.3 kW roof can make 39.6 units in a day; the 3 kW it was could not.
    assert call(FATHER, "POST /houses/{houseId}/readings", {"date": "2026-09-30", "kwh": 39}, house)[0] == 201
    table.update_item(
        Key={"pk": f"HOUSE#{house}", "sk": "META"},
        UpdateExpression="SET plant_id = :p, inverter_key = :k",
        ExpressionAttributeValues={":p": "home-00", ":k": "inv_x"},
    )
    assert call(FATHER, route, {"kw": 5}, house) == (409, {"error": api.SIZE_FROM_INVERTER})
    assert call(FATHER, "GET /houses/{houseId}", house_id=house)[1]["kw"] == 3.3
