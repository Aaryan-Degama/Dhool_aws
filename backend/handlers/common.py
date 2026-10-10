"""What the API and the analysis handlers share: the table, AWS clients kept for the life of the container,
one shape of log line, and reading a list to its end."""
import json
import os

import boto3
from botocore.config import Config

# A throttled call or a passing network fault is tried again up to three times, with backoff, before it fails.
RETRIES = Config(retries={"mode": "standard", "max_attempts": 3})

_made = {}         # clients and resources, made on first use and not again for every request
request_id = None  # this invocation's, set by the handler and put on every log line


def client(name, key=None, config=None, **kwargs):
    """A boto3 client, made once. `key` names a second client of the same service with other settings;
    `config` is laid over RETRIES."""
    key = key or name
    if key not in _made:
        _made[key] = boto3.client(name, config=RETRIES.merge(config) if config else RETRIES, **kwargs)
    return _made[key]


def bucket(name):
    if "s3 resource" not in _made:
        _made["s3 resource"] = boto3.resource("s3", config=RETRIES)
    return _made["s3 resource"].Bucket(name)


def table():
    if "table" not in _made:
        _made["table"] = boto3.resource("dynamodb").Table(os.environ["TABLE"])
    return _made["table"]


def log(**fields):
    print(json.dumps({**fields, "request_id": request_id}))


def query_all(table, **query):
    """Every item a query matches, page after page: one answer from DynamoDB stops at 1 MB (or at Limit)."""
    while True:
        page = table.query(**query)
        yield from page["Items"]
        if "LastEvaluatedKey" not in page:
            return
        query["ExclusiveStartKey"] = page["LastEvaluatedKey"]
