#!/usr/bin/env python3
"""Measure the screenshot reader: what it reads, how long it takes, and how much memory it needs.

Each image's answer key (the numbers printed on that screen) comes from, in order:
- the image itself: screens saved from the demo inverter app carry it as hidden text;
- a file beside it, `<image>.json`, as {"readings": [{"date": "YYYY-MM-DD", "kwh": 12.3}]}: write one by hand
  for a real inverter screenshot (use "TODAY" as the date when the screen prints none);
- otherwise nothing: the image is not an inverter screen, and the reader must find nothing in it.
The reader is given the picture only, and this script compares what it read with the key.

    scripts/eval-vision.py image.png [image.jpg ...]

Needs the weights (scripts/fetch-model.sh) and a llama-server binary: set LLAMA_SERVER to its path.
Run it under `taskset -c 0,1`, or better in the Lambda image with `docker run --cpus=2 --memory=3008m`,
to see what the Lambda sees. Memory: "working" is the model server's own memory (what an out-of-memory
kill counts); the weights are mapped from disk on top of it and can be dropped and read again.
"""
import json
import os
import pathlib
import struct
import sys
import threading
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "vision"))
os.environ.setdefault("MODEL_DIR", str(ROOT / "vision" / "models"))
import screenshot_reader as reader  # noqa: E402  (needs MODEL_DIR set first)

if os.environ.get("IMAGE_TOKENS"):
    reader.IMAGE_TOKENS = int(os.environ["IMAGE_TOKENS"])


def answer_key(path, image):
    if image.startswith(b"\x89PNG"):
        pos = 8
        while pos + 8 <= len(image):
            length, kind = struct.unpack(">I4s", image[pos:pos + 8])
            body = image[pos + 8:pos + 8 + length]
            if kind == b"tEXt" and body.startswith(b"dhool-demo\x00"):
                return json.loads(body[11:])["readings"]
            pos += 12 + length
    beside = path.with_name(path.name + ".json")
    return json.loads(beside.read_text())["readings"] if beside.exists() else []


peaks = {"working": 0, "total": 0}


def watch(pid):
    """Sample the model server's memory every 50 ms: the peaks are what matter, and they last moments."""
    while True:
        try:
            status = {line.split(":")[0]: int(line.split()[1]) // 1024 for line in open(f"/proc/{pid}/status")
                      if line.startswith(("RssAnon", "VmRSS"))}
        except (FileNotFoundError, ProcessLookupError):
            return
        peaks["working"] = max(peaks["working"], status["RssAnon"])
        peaks["total"] = max(peaks["total"], status["VmRSS"])
        time.sleep(0.05)


started = time.time()
reader.start()
threading.Thread(target=watch, args=(reader._server.pid,), daemon=True).start()
print(f"model ready in {time.time() - started:.0f}s on {len(os.sched_getaffinity(0))} cores, image tokens <= {reader.IMAGE_TOKENS}")
right = total = invented = 0
for name in sys.argv[1:]:
    path = pathlib.Path(name)
    image = path.read_bytes()
    truth = {r["date"]: r["kwh"] for r in answer_key(path, image)}
    started = time.time()
    result = reader.read(image)
    seconds = time.time() - started
    got = {r["date"]: r["kwh"] for r in result["readings"]}
    ok = sum(1 for date, kwh in truth.items() if date in got and abs(got[date] - kwh) < 0.005)
    extra = sorted(set(got) - set(truth))
    wrong = {date: (got.get(date), kwh) for date, kwh in truth.items() if date not in got or abs(got[date] - kwh) >= 0.005}
    right, total, invented = right + ok, total + len(truth), invented + len(extra)
    print(f"{path.name}: {seconds:.0f}s, kind {result['kind'] or '?'}, {ok}/{len(truth)} right"
          + (f", NOT ON SCREEN: {extra}" if extra else "") + (f", wrong (read, true): {wrong}" if wrong else ""))
    if os.environ.get("SHOW"):
        print("   ", json.dumps(result["replies"])[:600])
print(f"overall: {right}/{total} printed values read exactly, {invented} values invented")
print(f"model server peak memory: working {peaks['working']} MB, with the mapped weights {peaks['total']} MB")
try:  # the container's own peak, page cache included, when run in one (cgroup v2)
    print(f"container peak: {int(open('/sys/fs/cgroup/memory.peak').read()) // 2**20} MB")
except OSError:
    pass
reader._server.terminate()
