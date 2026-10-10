"""What the API and the analysis handlers share: the table, AWS clients kept for the life of the container,
one shape of log line, one of metric line, and reading a list to its end."""

import json
import os
import sys
import time
from collections.abc import Iterator
from typing import Any

import boto3
from botocore.config import Config

# A throttled call or a passing network fault is tried again up to three times, with backoff, before it fails.
RETRIES = Config(retries={"mode": "standard", "max_attempts": 3})

_made: dict[str, Any] = {}  # clients and resources, made on first use and not again for every request
request_id: str | None = None  # this invocation's, set by the handler and put on every log line


def client(name: str, key: str | None = None, config: Config | None = None, **kwargs: Any) -> Any:
    """A boto3 client, made once. `key` names a second client of the same service with other settings;
    `config` is laid over RETRIES."""
    key = key or name
    if key not in _made:
        _made[key] = boto3.client(name, config=RETRIES.merge(config) if config else RETRIES, **kwargs)
    return _made[key]


def bucket(name: str) -> Any:
    if "s3 resource" not in _made:
        _made["s3 resource"] = boto3.resource("s3", config=RETRIES)
    return _made["s3 resource"].Bucket(name)


def table() -> Any:
    if "table" not in _made:
        _made["table"] = boto3.resource("dynamodb").Table(os.environ["TABLE"])
    return _made["table"]


def _line(fields):
    """One JSON line in one write. print() writes the text and the line end separately, and a run fetches
    weather from three threads: two of them speaking at once landed on one line that nothing could parse."""
    sys.stdout.write(json.dumps(fields) + "\n")


def log(**fields: Any) -> None:
    _line({**fields, "request_id": request_id})


def metric(name: str, value: float, unit: str = "Count", **dimensions: str) -> None:
    """One number for CloudWatch, as a log line in its Embedded Metric Format: the log group turns the line
    into a metric in the Dhool namespace, with no PutMetricData call and no permission to grant.
    Every different set of dimension values is a metric of its own, and is billed as one: keep them few.
    ponytail: one namespace for every stack; add the stack as a dimension when staging is deployed."""
    _line(
        {
            "_aws": {
                "Timestamp": int(time.time() * 1000),
                "CloudWatchMetrics": [
                    {"Namespace": "Dhool", "Dimensions": [list(dimensions)], "Metrics": [{"Name": name, "Unit": unit}]}
                ],
            },
            **dimensions,
            name: value,
        }
    )


def query_all(table: Any, **query: Any) -> Iterator[dict[str, Any]]:
    """Every item a query matches, page after page: one answer from DynamoDB stops at 1 MB (or at Limit)."""
    while True:
        page = table.query(**query)
        yield from page["Items"]
        if "LastEvaluatedKey" not in page:
            return
        query["ExclusiveStartKey"] = page["LastEvaluatedKey"]
