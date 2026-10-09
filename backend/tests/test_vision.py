"""The screenshot reader: what it does with the model's answers, and what the Lambda writes back.
The model itself is not run here (it needs 1.5 GB of weights); scripts/eval-vision.py measures it on real images.
"""
import io
import json

import boto3
import pytest
from moto import mock_aws
from PIL import Image

import screenshot_reader
import vision_handler


@pytest.mark.parametrize("reply,expected", [
    ("2026-09-25,11.96\n2026-09-24,13.45", [("2026-09-25", 11.96), ("2026-09-24", 13.45)]),
    ("2026-09-25, 12.0 kWh", [("2026-09-25", 12.0)]),
    ("Here are the rows:\n2026-09-25,11.96\nTotal: 372.1 kWh", [("2026-09-25", 11.96)]),   # chatter and totals are ignored
    ("2026-09-25,11.96\n2026-09-25,99.9", [("2026-09-25", 11.96)]),                          # a date counts once
    ("NONE", []), ("", []), ("25 Sept, 12.0\n17 Sept, 12.0", []), ("2026-09-25,-3", []), ("2026-09-25,12.0.1", []),
    # what the model did on a chart screen: today's number pinned on every date under the chart
    ("2026-08-27,12.0\n2026-09-03,12.0\n2026-09-10,12.0\n2026-09-17,12.0\n2026-09-25,12.0", []),
    ("2026-09-25,12.0\n2026-09-24,12.0", [("2026-09-25", 12.0), ("2026-09-24", 12.0)]),      # two equal days can be real
    # what the model did on a real app's per-panel grid: every figure under one made-up date
    ("2023-04-05,508.25\n2023-04-05,511.5\n2023-04-05,498.25\n2023-04-05,513", []),
])
def test_only_well_formed_rows_become_readings(reply, expected):
    assert [(r["date"], r["kwh"]) for r in screenshot_reader.rows(reply)] == expected


def png(width, height, mode="RGB"):
    out = io.BytesIO()
    Image.new(mode, (width, height), "white").save(out, "PNG")
    return out.getvalue()


SCREEN = png(1080, 2400)  # a phone screenshot


def test_a_picture_is_shrunk_to_the_models_budget_in_whole_patches():
    small = Image.open(io.BytesIO(screenshot_reader.fit(SCREEN)))
    assert small.width % 32 == 0 and small.height % 32 == 0
    assert screenshot_reader.IMAGE_TOKENS - 30 <= (small.width // 32) * (small.height // 32) <= screenshot_reader.IMAGE_TOKENS
    assert abs(small.height / small.width - 2400 / 1080) < 0.15  # the shape is kept


def test_a_picture_too_large_for_a_screenshot_is_refused_before_it_is_unpacked():
    bomb = png(8_000, 5_000, mode="1")  # a few kilobytes on the wire, 120 MB once unpacked
    assert len(bomb) < 100_000
    with pytest.raises(ValueError, match="too large"):
        screenshot_reader.fit(bomb)


def answers(monkeypatch, replies):
    """Stand in for the model: answer each question from a table, and record what was asked."""
    asked = []
    monkeypatch.setattr(screenshot_reader, "start", lambda: None)
    monkeypatch.setattr(screenshot_reader, "ask", lambda picture, question, max_tokens: asked.append(question) or replies[question])
    return asked


def test_a_list_screen_is_copied_row_by_row(monkeypatch):
    asked = answers(monkeypatch, {screenshot_reader.ASK_KIND: "A", screenshot_reader.ASK_ROWS: "2026-09-25,11.96\n2026-09-24,13.45"})
    result = screenshot_reader.read(SCREEN)
    assert result["readings"] == [{"date": "2026-09-25", "kwh": 11.96}, {"date": "2026-09-24", "kwh": 13.45}]
    assert asked == [screenshot_reader.ASK_KIND, screenshot_reader.ASK_ROWS]


@pytest.mark.parametrize("today,check,date,expected", [
    ("12.0", "YES", "2026-09-25", [{"date": "2026-09-25", "kwh": 12.0}]),
    ("12.0 kWh", "Yes.", "NONE", [{"date": "TODAY", "kwh": 12.0}]),   # no date on the screen: the API uses the day of upload
    ("NONE", "YES", "2026-09-25", []),
    ("14.2", "NO", "2026-09-25", []),   # Dhool's own "Units possible 14.2": the label is not a reading
    ("9.8", "produced", "NONE", [{"date": "TODAY", "kwh": 9.8}]),   # a real app: the label's word instead of YES
])
def test_a_summary_screen_gives_one_reading_and_never_reads_the_chart(monkeypatch, today, check, date, expected):
    asked = answers(monkeypatch, {screenshot_reader.ASK_KIND: "B", screenshot_reader.ASK_TODAY: today,
                                  screenshot_reader.ASK_CHECK: check, screenshot_reader.ASK_DATE: date})
    assert screenshot_reader.read(SCREEN)["readings"] == expected
    assert screenshot_reader.ASK_ROWS not in asked


def test_any_other_picture_gives_nothing(monkeypatch):
    asked = answers(monkeypatch, {screenshot_reader.ASK_KIND: "C"})
    assert screenshot_reader.read(SCREEN)["readings"] == [] and len(asked) == 1


@pytest.fixture
def aws(monkeypatch):
    for name, value in {"AWS_DEFAULT_REGION": "ap-south-1", "AWS_ACCESS_KEY_ID": "t", "AWS_SECRET_ACCESS_KEY": "t",
                        "UPLOADS": "uploads-test", "TABLE": "dhool-test"}.items():
        monkeypatch.setenv(name, value)
    with mock_aws():
        boto3.client("s3").create_bucket(Bucket="uploads-test", CreateBucketConfiguration={"LocationConstraint": "ap-south-1"})
        boto3.client("s3").put_object(Bucket="uploads-test", Key="houses/h1/s1.jpg", Body=b"picture bytes")
        table = boto3.resource("dynamodb").create_table(
            TableName="dhool-test", BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}, {"AttributeName": "sk", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}, {"AttributeName": "sk", "KeyType": "RANGE"}])
        table.put_item(Item={"pk": "HOUSE#h1", "sk": "SHOT#s1", "status": "reading", "at": 1})
        yield table


EVENT = {"house_id": "h1", "shot_id": "s1", "key": "houses/h1/s1.jpg"}


def test_the_lambda_writes_what_the_model_read_onto_the_screenshot(aws, monkeypatch):
    seen = []
    found = {"reader": "test", "kind": "A", "readings": [{"date": "2026-09-25", "kwh": 11.96}], "replies": {}}
    monkeypatch.setattr(screenshot_reader, "read", lambda image: seen.append(image) or found)
    assert vision_handler.handler(EVENT, None)["status"] == "read"
    assert seen == [b"picture bytes"]
    item = aws.get_item(Key={"pk": "HOUSE#h1", "sk": "SHOT#s1"})["Item"]
    assert item["status"] == "read" and item["at"] == 1
    assert json.loads(item["result"])["readings"] == [{"date": "2026-09-25", "kwh": 11.96}]


def test_a_reader_that_breaks_still_reports_back(aws, monkeypatch):
    def broken(image):
        raise RuntimeError("the model server stopped with exit code 137")
    monkeypatch.setattr(screenshot_reader, "read", broken)
    assert vision_handler.handler(EVENT, None)["status"] == "failed"
    item = aws.get_item(Key={"pk": "HOUSE#h1", "sk": "SHOT#s1"})["Item"]
    assert item["status"] == "failed" and "exit code 137" in json.loads(item["result"])["error"]


def test_the_keep_warm_ping_only_loads_the_model(aws, monkeypatch):
    started = []
    monkeypatch.setattr(screenshot_reader, "prime", lambda: started.append(True))
    monkeypatch.setattr(screenshot_reader, "read", lambda *a: pytest.fail("a ping must not read anything"))
    assert vision_handler.handler({"warm": True}, None) == {"status": "warm"}
    assert started == [True]
    assert aws.get_item(Key={"pk": "HOUSE#h1", "sk": "SHOT#s1"})["Item"]["status"] == "reading"


def test_the_questions_rule_out_other_apps_and_estimates():
    assert "C: something else" in screenshot_reader.ASK_KIND and "forecast" in screenshot_reader.ASK_KIND
    assert "possible or expected value" in screenshot_reader.ASK_TODAY and "NONE" in screenshot_reader.ASK_TODAY
