#!/usr/bin/env python3
"""Measure the screenshot reader against images saved from the demo inverter app.

Each saved image carries, as hidden text, the numbers printed on that screen (its answer key). The reader
is given the picture only; this script compares what it read with the key and reports the time it took.
Any other image (a screenshot of another app, of Dhool itself) has no key: the reader must find nothing in it.

    scripts/eval-vision.py image.png [image.png ...]

Needs the weights (scripts/fetch-model.sh) and a llama-server binary: set LLAMA_SERVER to its path.
Run under `taskset -c 0,1` to see the speed on two cores, which is what the Lambda has.
"""
import json
import os
import pathlib
import struct
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "vision"))
os.environ.setdefault("MODEL_DIR", str(ROOT / "vision" / "models"))
import screenshot_reader as reader  # noqa: E402  (needs MODEL_DIR set first)

if os.environ.get("IMAGE_TOKENS"):
    reader.IMAGE_TOKENS = int(os.environ["IMAGE_TOKENS"])


def answer_key(png):
    pos = 8
    while pos + 8 <= len(png):
        length, kind = struct.unpack(">I4s", png[pos:pos + 8])
        body = png[pos + 8:pos + 8 + length]
        if kind == b"tEXt" and body.startswith(b"dhool-demo\x00"):
            return json.loads(body[11:])
        pos += 12 + length
    return {"readings": []}  # not from the demo inverter app: nothing on it is a reading


started = time.time()
reader.start()
print(f"model ready in {time.time() - started:.0f}s on {len(os.sched_getaffinity(0))} cores, image tokens <= {reader.IMAGE_TOKENS}")
right = total = invented = 0
for path in sys.argv[1:]:
    image = pathlib.Path(path).read_bytes()
    truth = {r["date"]: r["kwh"] for r in answer_key(image)["readings"]}
    started = time.time()
    result = reader.read(image)
    seconds = time.time() - started
    got = {r["date"]: r["kwh"] for r in result["readings"]}
    ok = sum(1 for date, kwh in truth.items() if date in got and abs(got[date] - kwh) < 0.005)
    extra = sorted(set(got) - set(truth))
    wrong = {date: (got.get(date), kwh) for date, kwh in truth.items() if date not in got or abs(got[date] - kwh) >= 0.005}
    right, total, invented = right + ok, total + len(truth), invented + len(extra)
    print(f"{pathlib.Path(path).name}: {seconds:.0f}s, kind {result['kind'] or '?'}, {ok}/{len(truth)} right"
          + (f", NOT ON SCREEN: {extra}" if extra else "") + (f", wrong (read, true): {wrong}" if wrong else ""))
    if os.environ.get("SHOW"):
        print("   ", json.dumps(result["replies"])[:600])
print(f"overall: {right}/{total} printed values read exactly, {invented} values invented")
peak = next(line.split()[1] for line in open(f"/proc/{reader._server.pid}/status") if line.startswith("VmHWM"))
print(f"model server peak memory: {int(peak) // 1024} MB")
reader._server.terminate()
