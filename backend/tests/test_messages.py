"""The labelled vendor replies Laya is tuned on: every row usable, no reply in both splits."""
import json
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "messages" / "vendor-replies.jsonl"
LABELS = {"visit_scheduled", "asking_details", "refused", "unclear"}


def test_vendor_replies_are_labelled_and_splits_do_not_overlap():
    rows = [json.loads(l) for l in DATA.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    assert all(r["text"].strip() and r["label"] in LABELS and r["lang"] in {"en", "hi", "hing"}
               and r["split"] in {"train", "test", "test2"} for r in rows)
    texts = [r["text"].strip().lower() for r in rows]
    assert len(texts) == len(set(texts))
    assert {r["label"] for r in rows if r["split"] == "test"} == LABELS
