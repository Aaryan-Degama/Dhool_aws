"""Dummy screenshot reader. It stands exactly where the vision model will: same request, same response.

It does NOT look at the picture. It reads the numbers that the demo inverter app embeds in the images it
saves (a PNG text chunk named "dhool-demo"). Any other image gets ok=False and the app asks the homeowner
to type the number in. To use a real model, replace this function; nothing else changes.

Request:  {"key": "<object key in the uploads bucket>"}
Response: {"ok": true, "reader": "dummy", "app": "...", "readings": [{"date": "YYYY-MM-DD", "kwh": 12.4}, ...]}
          {"ok": false, "reader": "dummy"}
"""
import json
import os
import struct

import boto3

MAX_BYTES = 5_000_000
PNG = b"\x89PNG\r\n\x1a\n"
TAG = b"dhool-demo\x00"


def embedded(image):
    """The JSON a demo image carries, or None for any other image."""
    if not image.startswith(PNG):
        return None
    pos = len(PNG)
    while pos + 8 <= len(image):
        length, kind = struct.unpack(">I4s", image[pos:pos + 8])
        body = image[pos + 8:pos + 8 + length]
        if kind == b"tEXt" and body.startswith(TAG):
            return json.loads(body[len(TAG):].decode("latin-1"))
        if kind == b"IEND":
            break
        pos += 12 + length
    return None


def handler(event, context):
    image = boto3.client("s3").get_object(Bucket=os.environ["UPLOADS"], Key=event["key"],
                                          Range=f"bytes=0-{MAX_BYTES}")["Body"].read()
    try:
        data = embedded(image)
    except ValueError:
        data = None
    if not isinstance(data, dict) or not isinstance(data.get("readings"), list):
        return {"ok": False, "reader": "dummy"}
    return {"ok": True, "reader": "dummy", "app": str(data.get("app", ""))[:60], "readings": data["readings"][:120]}
