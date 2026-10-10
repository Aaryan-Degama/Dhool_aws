"""Reads the daily generation figures off a screenshot of an inverter app.

A small vision-language model does the reading: Qwen3-VL-2B-Instruct (Apache-2.0, 4-bit GGUF), served on
CPU by llama.cpp's own server (MIT), started once per container and reused while it stays warm. The model
is asked only for numbers printed on the screen: a list of days, or today's figure. Charts are not read.

What it returns is never trusted as fact: the API drops any value that cannot be true for the roof, and
the homeowner confirms or corrects the rest before anything is saved.
"""
import base64
import io
import json
import math
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from PIL import Image

MODEL_DIR = os.environ.get("MODEL_DIR", "/opt/models")
SERVER = os.environ.get("LLAMA_SERVER", "/opt/llama-server")
PORT = 8081
# How much of the model's attention one picture takes: each token covers PATCH x PATCH pixels. Fewer tokens
# read faster and need less memory. Measured with scripts/eval-vision.py in the Lambda image (two cores):
# at 400 instead of 640 a list reads in 47 s instead of 64 and a today screen in 33 s instead of 52, with
# every demo value still exact.
IMAGE_TOKENS = 400
PATCH = 32               # the model's 16-pixel patches, merged two by two
MAX_PIXELS = 30_000_000  # no phone screenshot is larger; a small file can unpack to far more than memory holds
MAX_REPLY_TOKENS = 420   # room for about thirty rows of a list
READER = "qwen3-vl-2b-instruct-q4"

# A small model answers narrow questions far more reliably than one broad one. Asked to "list every daily
# value", it invented rows from the dates under a chart. So it is asked what kind of screen this is first,
# and then only for what that kind of screen prints. The picture is the shared start of every question,
# so it is taken in once and the follow-up questions are quick. Screenshots of other apps (Dhool's own
# screens among them) must come back empty: "Units possible" is not a reading. A today figure is only kept
# if a last yes/no question confirms its label says it was generated today.
ASK_KIND = """This is a screenshot. Which one is it?
A: an inverter or solar app's list or table of days, one row per day, each row with a date and the energy generated \
that day
B: an inverter or solar app's screen showing the energy the system has generated so far today, as one large number
C: something else, such as a forecast, an estimate, a settings or sign-in screen, or another kind of app
Answer with the letter only."""
ASK_ROWS = (
    "Copy the rows of that list. Write one line per row: the date as YYYY-MM-DD, a comma, "
    "then the kWh number exactly as printed. Write nothing else."
)
ASK_TODAY = (
    "What is the energy the solar system has generated today, in kWh, exactly as printed? "
    "Only a measured figure counts: not the power right now (kW or W), not a forecast, not a possible or expected "
    "value, and not a total over several days. If there is none, answer NONE. Otherwise answer with the number only."
)
ASK_CHECK = (
    "Look at the label printed next to that figure. Is it a label for today's energy, such as energy today, "
    "production today, today's yield or generated today (and not power now, possible, expected, forecast, a month "
    "or a total)? Answer YES or NO."
)
ASK_DATE = """Which date is printed for today's figure? Answer as YYYY-MM-DD. If no date is printed, answer NONE."""

LINE = re.compile(r"^\s*(\d{4}-\d{2}-\d{2})\s*[,;:]\s*(\d{1,4}(?:\.\d+)?)\s*(?:kWh)?\s*$", re.IGNORECASE)
NUMBER = re.compile(r"\d{1,4}(?:\.\d+)?")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")

_server = None
_primed = False


def rows(reply):
    """The model's copy of a list -> [{"date", "kwh"}], one per date, in the order given."""
    seen, lines = {}, 0
    for line in reply.splitlines():
        match = LINE.match(line)
        if match:
            lines += 1
            seen.setdefault(match.group(1), float(match.group(2)))
    # A list of days has one row per date. Many rows under one date is a grid of something else (per-panel
    # figures, on a real app) with a date made up for it.
    if lines >= 3 and len(seen) * 2 < lines:
        return []
    # Several days with one identical value is the mark of a model filling in rows it did not read.
    if len(seen) >= 3 and len(set(seen.values())) == 1:
        return []
    return [{"date": date, "kwh": kwh} for date, kwh in seen.items()]


def fit(image):
    """The picture as the model takes it in: shrunk with a high-quality filter to at most IMAGE_TOKENS tokens,
    its sides in whole patches, as PNG. Shrinking here keeps thin digits sharp (the model server's own resize
    is rougher), keeps the server's decoding small, and refuses an oversized picture from its header alone."""
    picture = Image.open(io.BytesIO(image))
    if picture.width * picture.height > MAX_PIXELS:
        raise ValueError(f"the picture is {picture.width} x {picture.height} pixels, too large for a screenshot")
    scale = min(1.0, math.sqrt(IMAGE_TOKENS * PATCH * PATCH / (picture.width * picture.height)))
    size = (max(PATCH, int(picture.width * scale) // PATCH * PATCH), max(PATCH, int(picture.height * scale) // PATCH * PATCH))
    picture.draft("RGB", size)  # a JPEG decodes straight to near the size it is shrunk to
    out = io.BytesIO()
    picture.convert("RGB").resize(size, Image.LANCZOS, reducing_gap=3.0).save(out, "PNG")
    return out.getvalue()


def _call(path, body=None, timeout=5):
    request = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}",
                                     data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


PIECE = 32 << 20


def _read_piece(piece):
    path, offset = piece
    with open(path, "rb", buffering=0) as f:
        f.seek(offset)
        f.read(PIECE)


def fetch_weights():
    """Read the weights once, in large pieces, sixteen at a time. A fresh Lambda pulls its container image in
    lazily; left to the model server, the same 1.5 GB arrives as small scattered reads, which took about four
    minutes. The data is thrown away here: the point is that the kernel now holds it for the server to map."""
    paths = [f"{MODEL_DIR}/{name}" for name in ("Qwen3VL-2B-Instruct-Q4_K_M.gguf", "mmproj-Qwen3VL-2B-Instruct-Q8_0.gguf")]
    with ThreadPoolExecutor(16) as pool:
        list(pool.map(_read_piece, [(path, offset) for path in paths for offset in range(0, os.path.getsize(path), PIECE)]))


def start():
    """Start llama.cpp's server once; later calls return at once while it is still running."""
    global _server
    if _server is not None and _server.poll() is None:
        return
    fetch_weights()
    threads = str(len(os.sched_getaffinity(0)))  # the cores this process may actually use: two, in Lambda at 3 GB
    _server = subprocess.Popen(
        [SERVER, "-m", f"{MODEL_DIR}/Qwen3VL-2B-Instruct-Q4_K_M.gguf", "--mmproj", f"{MODEL_DIR}/mmproj-Qwen3VL-2B-Instruct-Q8_0.gguf",
         "--host", "127.0.0.1", "--port", str(PORT), "--threads", threads, "--threads-batch", threads,
         # Memory is the tight resource: this account's Lambda tops out at 3008 MB, and at that ceiling the
         # model's pages get pushed out and reading slows down. Measured in the Lambda image: llama.cpp's
         # repacked copy of the weights took 646 MB and bought no speed on two cores, so it is off and the
         # weights are read straight from the mapped file (which the kernel can drop and re-read, where an
         # out-of-memory kill is final). With that, 400 picture tokens and a context of a picture, a question
         # and thirty rows, the server's own memory peaks at about 940 MB instead of 1,711.
         # An 8-bit attention cache would save a little more, but with it the model read a "99%" off one of
         # Dhool's own screens as today's generation, so the cache stays at full precision.
         "--no-repack", "--ctx-size", str(math.ceil((IMAGE_TOKENS + 200 + MAX_REPLY_TOKENS) / 256) * 256),
         "--batch-size", "256", "--ubatch-size", "256", "--parallel", "1", "--image-max-tokens", str(IMAGE_TOKENS),
         "--cache-ram", "0",  # no saved prompts between screenshots: every one is new, and memory here is tight
         "--no-webui", "--no-slots"],
        env={**os.environ, "HOME": "/tmp"})
    for _ in range(600):  # the first load reads 1.5 GB of weights: allow up to five minutes
        if _server.poll() is not None:
            raise RuntimeError(f"the model server stopped with exit code {_server.returncode}")
        try:
            if _call("/health").get("status") == "ok":
                return
        except (urllib.error.URLError, ConnectionError, TimeoutError, ValueError):
            pass
        time.sleep(0.5)
    raise RuntimeError("the model server did not come up")


def prime():
    """Start the model and pull its weights into memory, so the next real screenshot does not wait for them.
    The server answers its health check before the weights are read; a one-word reply reads them all."""
    global _primed
    start()
    if not _primed:
        _call("/v1/chat/completions", timeout=600, body={"max_tokens": 1, "messages": [{"role": "user", "content": "Hello"}]})
        _primed = True


def ask(picture, question, max_tokens):
    """One question about the picture; the model's raw answer."""
    reply = _call("/v1/chat/completions", timeout=840, body={
        "temperature": 0, "max_tokens": max_tokens, "cache_prompt": True,
        "messages": [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": picture}},
                                                  {"type": "text", "text": question}]}],
    })
    return (reply["choices"][0]["message"]["content"] or "").strip()


def read(image):
    """PNG or JPEG bytes ->
    {"reader", "kind", "readings": [{"date": "YYYY-MM-DD" or "TODAY", "kwh": float}], "replies"}"""
    picture = f"data:image/png;base64,{base64.b64encode(fit(image)).decode()}"
    start()
    replies = {"kind": ask(picture, ASK_KIND, 4)}
    kind, readings = replies["kind"][:1].upper(), []
    if kind == "A":
        replies["rows"] = ask(picture, ASK_ROWS, MAX_REPLY_TOKENS)
        readings = rows(replies["rows"])
    elif kind == "B":
        replies["today"] = ask(picture, ASK_TODAY, 12)
        number = NUMBER.search(replies["today"])
        if number:  # a figure only counts if its own label says it was generated today
            replies["check"] = ask(picture, ASK_CHECK, 4)
            # Asked yes or no, the model sometimes answers with the label's own word ("produced").
            if re.match(r"\s*(yes|produc|generat|yield)", replies["check"], re.IGNORECASE):
                replies["date"] = ask(picture, ASK_DATE, 14)
                date = DATE.search(replies["date"])
                readings = [{"date": date.group(0) if date else "TODAY", "kwh": float(number.group(0))}]
    return {"reader": READER, "kind": kind, "readings": readings, "replies": {k: v[:1500] for k, v in replies.items()}}
