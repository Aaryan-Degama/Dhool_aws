"""The screenshot reader as a Lambda (container image: the model and llama.cpp are too big for a zip).

The API starts it in the background for one uploaded screenshot and returns at once; reading takes
longer than an API call may. The result is written onto that screenshot's item, where the API finds it.

Event: {"house_id": ..., "shot_id": ..., "key": "<object key in the uploads bucket>"}
"""
import json
import os
import time

import boto3
from botocore.exceptions import ClientError

import reader


def handler(event, context):
    if event.get("warm"):  # the 5-minute ping: have the model loaded and its weights in memory, nothing else
        reader.prime()
        return {"status": "warm"}
    started = time.time()
    try:
        image = boto3.client("s3").get_object(Bucket=os.environ["UPLOADS"], Key=event["key"])["Body"].read()
        result = reader.read(image)
        status = "read"
    except Exception as e:  # whatever went wrong, the homeowner must not be left waiting on a spinner
        result, status = {"readings": [], "error": f"{type(e).__name__}: {e}"[:300]}, "failed"
    seconds = int(time.time() - started)
    try:
        # Only onto the screenshot's own item: if the home was deleted while this read, writing would bring
        # back a piece of it that nothing would ever remove.
        boto3.resource("dynamodb").Table(os.environ["TABLE"]).update_item(
            Key={"pk": f"HOUSE#{event['house_id']}", "sk": f"SHOT#{event['shot_id']}"},
            UpdateExpression="SET #status = :status, #result = :result, seconds = :seconds",
            ConditionExpression="attribute_exists(pk)",
            ExpressionAttributeNames={"#status": "status", "#result": "result"},
            ExpressionAttributeValues={":status": status, ":result": json.dumps(result), ":seconds": seconds})
    except ClientError as e:
        if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
            raise
        status = "gone"
    print(json.dumps({"vision": status, "house": event["house_id"], "shot": event["shot_id"], "seconds": seconds,
                      "reader": result.get("reader"), "readings": len(result["readings"]), "error": result.get("error")}))
    return {"status": status, "seconds": seconds}
