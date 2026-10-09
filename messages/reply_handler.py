"""The vendor-reply reader as a Lambda (container image: the model and PyTorch are too big for a zip).

Laya (Apache-2.0), fine-tuned by us on vendor replies (see checkpoints.md), sorts one WhatsApp reply from a
solar vendor into: visit_scheduled, asking_details, refused, unclear. It only reads; the homeowner sees the
label and can change it. Its confidence is not returned: wrong answers come at the same confidence as right ones.

Event: {"text": "<the vendor's reply>"}, or {"warm": true} from the five-minute ping.
"""
import json
import os
from concurrent.futures import ThreadPoolExecutor

MODEL = os.environ.get("MODEL_DIR", "/opt/model")
PIECE = 32 << 20
os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HOME="/tmp/hf")  # everything is in the image

_reader = None


def _read_piece(offset):
    with open(f"{MODEL}/model.safetensors", "rb", buffering=0) as f:
        f.seek(offset)
        f.read(PIECE)


def reader():
    """Load the model once per container. A fresh Lambda pulls its image in lazily, so the weights are read
    first in large pieces, many at a time (the same trick as the screenshot reader)."""
    global _reader
    if _reader is None:
        with ThreadPoolExecutor(16) as pool:
            list(pool.map(_read_piece, range(0, os.path.getsize(f"{MODEL}/model.safetensors"), PIECE)))
        import laya  # slow to import (PyTorch): only when a container starts
        with open(f"{MODEL}/questions.json", encoding="utf-8") as f:
            questions = json.load(f)  # the exact question the model was tuned on; ask no other
        _reader = (laya.load(MODEL, device="cpu"), questions)
    return _reader


def handler(event, context):
    agent, questions = reader()
    if event.get("warm"):
        return {"status": "warm"}
    label = agent.predict(event["text"], questions)["answers"]["reply"]["choice"]
    print(json.dumps({"messages": "read", "label": label, "chars": len(event["text"])}))  # never the text itself
    return {"label": label}
