"""Open-Meteo's answers, kept in the table: homes at the same spot and a run repeated within hours do not ask
again, and a run still has weather when Open-Meteo cannot be reached.

One item per address asked, WXCACHE#<sha256 of the whole URL>: the coordinates are part of the URL exactly as
sent, never rounded here. The low-level client, because a run fetches from three threads at once.
"""
import gzip
import hashlib
import json
import os
import time

from botocore.exceptions import ClientError

from dhool import keys
from handlers.common import client, log

FRESH_S = 3 * 3600     # an answer this young is used without asking again
STALE_S = 24 * 3600    # when Open-Meteo fails, one up to this old is used and the log says so; then DynamoDB drops it
MAX_BYTES = 380_000    # an item holds 400 KB; a longer answer (several years, zipped) is simply not kept


def cached(fetch):
    """fetch(url) -> the JSON it answers with. Returns the same, with the cache around it. The cache failing
    (a throttled table) never fails the fetch."""
    def get(url):
        key = {"pk": {"S": keys.wxcache_pk(hashlib.sha256(url.encode()).hexdigest())}, "sk": {"S": keys.META}}
        now, item = int(time.time()), None
        try:
            item = client("dynamodb").get_item(TableName=os.environ["TABLE"], Key=key).get("Item")
        except ClientError as e:
            log(weather="cache_unread", error=e.response["Error"]["Code"])
        kept = lambda: json.loads(gzip.decompress(item["body"]["B"]))
        if item and int(item["fresh_until"]["N"]) > now:
            return kept()
        try:
            answer = fetch(url)
        except Exception as e:
            if item and int(item["expiresAt"]["N"]) > now:  # checked here too: DynamoDB removes expired items late
                log(weather="stale", age_s=now - int(item["at"]["N"]), error=type(e).__name__)
                return kept()
            raise
        body = gzip.compress(json.dumps(answer).encode())
        if len(body) <= MAX_BYTES:
            try:
                client("dynamodb").put_item(TableName=os.environ["TABLE"], Item={
                    **key, "body": {"B": body}, "at": {"N": str(now)},
                    "fresh_until": {"N": str(now + FRESH_S)}, "expiresAt": {"N": str(now + STALE_S)}})
            except ClientError as e:
                log(weather="cache_unwritten", error=e.response["Error"]["Code"])
        return answer
    return get
