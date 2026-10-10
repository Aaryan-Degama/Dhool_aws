"""When a nightly run notifies the family's phones, and the nightly run itself: one background run per house."""
import datetime
import json

import boto3
import pytest
from moto import mock_aws

from dhool import notify
from handlers import analysis

FAULT = {"verdict": "INSPECT", "cause": "fault", "reason": "Output fell by a third on 8 Oct.", "reason_hi": "8 अक्टूबर को बिजली एक तिहाई गिर गई।"}
OUTAGE = {**FAULT, "cause": "outage"}
DUSTY = {"verdict": "CLEAN", "cause": "dust", "reason": "Dust is costing ₹90; a wash costs ₹50.", "reason_hi": "धूल से ₹90 का नुकसान; धुलाई ₹50 की।"}
FINE = {"verdict": "OK", "cause": "ok", "reason": "All good."}
WAIT = {"verdict": "WAIT", "cause": "dust", "reason": "Rain is coming."}


@pytest.mark.parametrize("previous,new,sent", [
    (FINE, FAULT, True), (None, FAULT, True), (FAULT, OUTAGE, True), (DUSTY, FAULT, True),
    (FINE, DUSTY, True), (WAIT, DUSTY, True),
    (FAULT, FAULT, False), (DUSTY, DUSTY, False),      # the same advice again
    (FAULT, FINE, False), (DUSTY, WAIT, False), (None, FINE, False),  # good news and "wait" do not ring the phone
])
def test_a_change_to_call_the_vendor_or_wash_is_sent_once(previous, new, sent):
    assert (notify.message(previous, new, 1, "en") is not None) is sent


def test_the_message_is_the_verdicts_own_reason_in_the_phones_language():
    assert notify.message(FINE, FAULT, 1, "en") == {
        "title": "Dhool: call your vendor", "body": "Output fell by a third on 8 Oct.", "url": "/#/roof"}
    hindi = notify.message(FINE, DUSTY, 1, "hi")
    assert hindi == {"title": "Dhool: पैनल धो दीजिए", "body": "धूल से ₹90 का नुकसान; धुलाई ₹50 की।", "url": "/#/roof"}
    assert notify.message(None, {"verdict": "CLEAN", "cause": "dust"}, 1, "hi")["body"].startswith("धूल")  # no reason stored
    assert notify.message(FINE, FAULT, 1, "fr")["title"] == "Dhool: call your vendor"  # an unknown language reads English


def test_readings_stopped_is_said_on_the_third_day_only():
    for days, sent in [(0, False), (1, False), (2, False), (3, True), (4, False), (30, False)]:
        assert (notify.message(FINE, FINE, days, "en") is not None) is sent, days
    assert notify.message(FAULT, FAULT, 3, "en")["title"] == "Dhool: no readings for 3 days"
    assert notify.message(FINE, FINE, 3, "hi")["title"] == "Dhool: 3 दिन से कोई रीडिंग नहीं"


def test_the_nightly_run_starts_one_background_run_per_house_across_pages(monkeypatch):
    pages = [{"Items": [{"sk": "h1"}, {"sk": "h2"}], "LastEvaluatedKey": {"pk": "HOUSES", "sk": "h2"}},
             {"Items": [{"sk": "h3"}]}]
    asked, started = [], []

    class Table:
        def query(self, **kwargs):
            asked.append(kwargs.get("ExclusiveStartKey"))
            return pages[len(asked) - 1]

    class Lambda:
        def invoke(self, **kwargs):
            started.append((kwargs["FunctionName"], kwargs["InvocationType"], json.loads(kwargs["Payload"])))

    monkeypatch.setenv("AWS_LAMBDA_FUNCTION_NAME", "dhool-AnalysisFunction-abc")
    monkeypatch.setattr(analysis, "table", Table)
    monkeypatch.setattr(analysis.boto3, "client", lambda name: Lambda())
    monkeypatch.setattr(analysis, "NIGHTLY_PACE_S", 0)
    clock = type("Context", (), {"aws_request_id": "r", "get_remaining_time_in_millis": lambda self: 100_000})()
    assert analysis.handler({}, clock) == {"houses": 3}
    assert asked == [None, {"pk": "HOUSES", "sk": "h2"}]
    assert started == [("dhool-AnalysisFunction-abc", "Event", {"house_id": h, "nightly": True}) for h in ("h1", "h2", "h3")]
    # Short of time before the second page: the rest is handed to a fresh run, which starts from that page.
    asked.clear(), started.clear()
    clock = type("Context", (), {"aws_request_id": "r", "get_remaining_time_in_millis": lambda self: 5_000})()
    assert analysis.handler({}, clock) == {"houses": 2, "continues": True}
    assert started[-1] == ("dhool-AnalysisFunction-abc", "Event", {"cursor": {"pk": "HOUSES", "sk": "h2"}})
    pages.pop(0), asked.clear(), started.clear()
    assert analysis.handler({"cursor": {"pk": "HOUSES", "sk": "h2"}}, clock) == {"houses": 1}
    assert asked == [{"pk": "HOUSES", "sk": "h2"}]


@pytest.fixture
def home(monkeypatch):
    """A house with typed readings, a stored "all good" and two subscribed phones; the run's inputs are stubbed."""
    for name, value in {"AWS_DEFAULT_REGION": "ap-south-1", "AWS_ACCESS_KEY_ID": "t", "AWS_SECRET_ACCESS_KEY": "t",
                        "TABLE": "dhool-test", "VAPID_SUBJECT": "https://dhool.invalid"}.items():
        monkeypatch.setenv(name, value)
    as_of = str(datetime.datetime.now(analysis.ZoneInfo(analysis.config.TZ)).date() - datetime.timedelta(days=1))
    for fetch in ("fetch_weather_with_forecast", "fetch_pm25", "fetch_dust_storms"):
        monkeypatch.setattr(analysis, fetch, lambda *a: None)
    monkeypatch.setattr(analysis, "analyse", lambda *a: {**FAULT, "as_of": as_of, "confidence": "high"})
    monkeypatch.setattr(analysis, "_vapid", "the-key")
    with mock_aws():
        table = boto3.resource("dynamodb").create_table(
            TableName="dhool-test", BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}, {"AttributeName": "sk", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}, {"AttributeName": "sk", "KeyType": "RANGE"}])
        table.put_item(Item={"pk": "HOUSE#h1", "sk": "META", "kw": 3, "lat": "28.61", "lon": "77.21"})
        table.put_item(Item={"pk": "HOUSE#h1", "sk": f"READING#{as_of}", "kwh": 9})
        table.put_item(Item={"pk": "HOUSE#h1", "sk": "VERDICT#2026-01-01", "json": json.dumps(FINE), "at": 1})
        for name, lang in (("a", "en"), ("b", "hi")):
            table.put_item(Item={"pk": "HOUSE#h1", "sk": f"PUSH#{name}", "endpoint": f"https://web.push.apple.com/{name}",
                                 "p256dh": "p", "auth": "a", "lang": lang, "by": "sub-father"})
        monkeypatch.setattr(analysis, "_table", None)
        yield table


def test_a_nightly_run_tells_each_phone_in_its_language_and_only_when_the_advice_changed(home, monkeypatch):
    sent = []
    monkeypatch.setattr(analysis, "_webpush", lambda item, message, key: sent.append((item["sk"], message["title"], key)))
    assert analysis.handler({"house_id": "h1"}, None) == {"verdict": "INSPECT"}
    assert sent == []  # a run that follows a tap in the app: the person is looking at the verdict already
    home.delete_item(Key={"pk": "HOUSE#h1", "sk": max(i["sk"] for i in home.scan()["Items"] if i["sk"].startswith("VERDICT#"))})
    assert analysis.handler({"house_id": "h1", "nightly": True}, None) == {"verdict": "INSPECT"}
    assert sent == [("PUSH#a", "Dhool: call your vendor", "the-key"), ("PUSH#b", "Dhool: वेंडर को बुलाइए", "the-key")]
    analysis.handler({"house_id": "h1", "nightly": True}, None)  # the next night, the same advice
    assert len(sent) == 2


def test_a_dead_subscription_is_dropped_and_a_failed_send_never_fails_the_run(home, monkeypatch, capsys):
    class Gone(Exception):
        response = type("Response", (), {"status_code": 410})

    def push(item, message, key):
        raise Gone() if item["sk"] == "PUSH#a" else TimeoutError("the push service did not answer")
    monkeypatch.setattr(analysis, "_webpush", push)
    assert analysis.handler({"house_id": "h1", "nightly": True}, None) == {"verdict": "INSPECT"}
    assert "Item" not in home.get_item(Key={"pk": "HOUSE#h1", "sk": "PUSH#a"})
    assert "Item" in home.get_item(Key={"pk": "HOUSE#h1", "sk": "PUSH#b"})
    assert '"status": 410' in capsys.readouterr().out


def test_without_a_key_nothing_is_sent_and_the_verdict_is_still_saved(home, monkeypatch, capsys):
    monkeypatch.setattr(analysis, "_vapid", False)
    monkeypatch.setattr(analysis, "_webpush", lambda *a: pytest.fail("there is no key to sign with"))
    assert analysis.handler({"house_id": "h1", "nightly": True}, None) == {"verdict": "INSPECT"}  # moto has no such parameter
    analysis.handler({"house_id": "h1", "nightly": True}, None)
    assert capsys.readouterr().out.count('"push_off"') == 1  # looked up once per container, said once


def test_a_house_deleted_before_its_run_is_skipped(home):
    assert analysis.handler({"house_id": "gone", "nightly": True}, None) == {"verdict": None}
