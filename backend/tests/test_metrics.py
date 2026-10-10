"""The numbers the analysis writes for CloudWatch (Embedded Metric Format lines on stdout), and the two
things in template.yaml that only a deploy would otherwise find wrong. No network."""

import json
import pathlib
import re
import time

import pytest

import test_notify
import test_weather_cache
from handlers import analysis, common

home, cache = test_notify.home, test_weather_cache.cache  # the fixtures those tests already use
ROOT = pathlib.Path(__file__).parents[2]


def emf(out):
    """Every metric line in what was printed, as (name, value, unit, dimensions), each checked against the
    format's rules: what the line declares exists at its top level, with the right types."""
    found = []
    for line in out.splitlines():
        said = json.loads(line)  # every line the handlers print is one JSON object
        if "_aws" not in said:
            continue
        stamp, (directive,) = said["_aws"]["Timestamp"], said["_aws"]["CloudWatchMetrics"]
        assert isinstance(stamp, int) and abs(stamp / 1000 - time.time()) < 60  # milliseconds, and now
        assert directive["Namespace"] == "Dhool"
        (names,), (declared,) = directive["Dimensions"], directive["Metrics"]
        assert all(isinstance(said[name], str) and said[name] for name in names)
        assert type(said[declared["Name"]]) in (int, float) and declared["Unit"] in ("Count", "Milliseconds")
        found.append((declared["Name"], said[declared["Name"]], declared["Unit"], {name: said[name] for name in names}))
    return found


def test_a_metric_is_one_line_of_valid_embedded_metric_format(capsys):
    common.metric("HouseRunDuration", 1234, "Milliseconds")
    common.metric("Verdicts", 1, verdict="CLEAN")
    out = capsys.readouterr().out
    assert out.count("\n") == 2 and out.endswith("\n")
    assert emf(out) == [("HouseRunDuration", 1234, "Milliseconds", {}), ("Verdicts", 1, "Count", {"verdict": "CLEAN"})]
    plain = json.loads(out.splitlines()[0])["_aws"]["CloudWatchMetrics"][0]
    assert plain["Dimensions"] == [[]]  # one empty set: a metric with no dimension, which the format allows


def test_a_log_line_is_as_it_was(capsys, monkeypatch):
    monkeypatch.setattr(common, "request_id", "r-1")
    common.log(analysis="done", house="h1")
    assert capsys.readouterr().out == '{"analysis": "done", "house": "h1", "request_id": "r-1"}\n'


@pytest.mark.usefixtures("home")
def test_a_run_says_how_long_it_took_and_which_verdict_it_gave(capsys):
    assert analysis.handler({"house_id": "h1"}, None) == {"verdict": "INSPECT"}
    out = capsys.readouterr().out
    (duration, ms, unit, no_dimensions), verdicts = emf(out)
    assert (duration, unit, no_dimensions) == ("HouseRunDuration", "Milliseconds", {}) and 0 <= ms < 60_000
    assert verdicts == ("Verdicts", 1, "Count", {"verdict": "INSPECT"})
    assert json.loads(out.splitlines()[-1])["analysis"] == "done"  # the log line is still the run's last


@pytest.mark.usefixtures("home")
def test_a_run_that_stores_no_verdict_counts_none(capsys):
    assert analysis.handler({"house_id": "gone"}, None) == {"verdict": None}
    assert emf(capsys.readouterr().out) == []


def test_a_weather_call_that_failed_is_counted_when_an_old_answer_stands_in(cache, capsys):
    get, asked, clock = cache
    get(URL := test_weather_cache.URL)
    assert emf(capsys.readouterr().out) == []  # an answered call counts nothing
    asked.append("down")
    clock[0] += 20 * 3600
    assert get(URL) == test_weather_cache.ANSWER
    out = capsys.readouterr().out
    assert emf(out) == [("WeatherFailures", 1, "Count", {})]
    assert json.loads(out.splitlines()[-1])["weather"] == "stale"


def test_a_weather_call_that_failed_is_counted_when_the_failure_is_raised(cache, capsys):
    get, asked, _ = cache
    asked.append("down")
    with pytest.raises(TimeoutError):
        get(test_weather_cache.URL)
    assert emf(capsys.readouterr().out) == [("WeatherFailures", 1, "Count", {})]


def resource(name):
    return re.search(rf"\n  {name}:\n(.*?)\n\n", (ROOT / "template.yaml").read_text(), re.DOTALL).group(1)


def test_the_system_errors_alarm_watches_every_dynamodb_operation_the_code_calls():
    """DynamoDB publishes SystemErrors per operation only: one the code calls and the alarm does not list
    would fail unseen."""
    watched = set(re.findall(r"Name: Operation, Value: (\w+)", resource("TableSystemErrorsAlarm")))
    calls = set()
    for source in [*(ROOT / "backend/handlers").glob("*.py"), ROOT / "vision/vision_handler.py"]:
        calls |= set(
            re.findall(
                r"\.(get_item|put_item|update_item|delete_item|query|scan|batch_writer|batch_get_item|"
                r"batch_write_item|transact_write_items|transact_get_items)\(",
                source.read_text(),
            )
        )
    assert watched == {"BatchWriteItem" if call == "batch_writer" else call.title().replace("_", "") for call in calls}


def test_the_dashboard_is_json_once_its_names_are_filled_in_and_draws_the_metrics_the_code_writes():
    body = resource("Dashboard").split("DashboardBody: !Sub |\n")[1]
    widgets = json.loads(re.sub(r"\$\{[\w:.]+\}", "x", body))["widgets"]
    assert all(w["type"] == "metric" and w["properties"]["region"] and w["properties"]["metrics"] for w in widgets)
    drawn = {(m[1], *m[2:-1]) for w in widgets for m in w["properties"]["metrics"] if m[0] == "Dhool"}
    assert drawn == {
        ("HouseRunDuration",),
        ("WeatherFailures",),
        *(("Verdicts", "verdict", v) for v in ("OK", "WAIT", "CLEAN", "INSPECT")),
    }
