"""Measure and fine-tune Laya (multilingual) on reading a vendor's reply to an inspection request.

    .venv-laya/bin/python scripts/laya-tune.py eval                 # the shipped checkpoint, untouched
    .venv-laya/bin/python scripts/laya-tune.py train                # writes messages/models/vendor-replies-v2
    .venv-laya/bin/python scripts/laya-tune.py eval messages/models/vendor-replies-v2

The training loop is adapted from Laya's own CPU script (notebooks/laya_finetune_typed_decisions_mps.py,
Apache-2.0, https://github.com/NandhaKishorM/laya); see CREDITS.md. Changes: our data, frozen token
embeddings, calibration through laya.calibrate.
"""
import argparse
import collections
import json
import random
from pathlib import Path

import numpy as np
import torch
from huggingface_hub import snapshot_download
from safetensors.torch import load_file, save_file

import laya
from laya.agent import _load_tokenizer
from laya.calibrate import fit_temperature_map, records_from_labeled
from laya.common import QTYPES, build_model, build_sequence, collate_items, ece_score, proper_reward

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "messages" / "vendor-replies.jsonl"
OUT = ROOT / "messages" / "models" / "vendor-replies-v2"  # one folder per version; see checkpoints.md
BASE = ("convaiinnovations/laya", "multilingual")
# Pinned: the checkpoint this was measured on.
BASE_REVISION = "55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851"

# The model is tuned on this exact wording and option order; it is saved next to the weights
# (questions.json) so whatever serves the model asks the same question.
# ponytail: fixed option order, so the model may lean on position. Shuffle options while training
# if the question ever has to change at request time.
QUESTIONS = {"reply": {
    "type": "choice",
    "instructions": "A homeowner asked their solar vendor to inspect a fault on the rooftop system. "
                    "What does the vendor's reply say?",
    "criteria": {
        "visit_scheduled": "the vendor will come or send someone",
        "asking_details": "the vendor wants something first: a photo, a model, an error code, "
                          "an address, a date, or agreement to a charge",
        "refused": "the vendor will not visit or help: not their job, out of warranty, no service, "
                   "or says nothing needs doing",
        "unclear": "an acknowledgement or a reply with no commitment, question or refusal",
    },
}}
LABELS = list(QUESTIONS["reply"]["criteria"])


def rows(split):
    lines = [l for l in DATA.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    return [r for r in map(json.loads, lines) if r["split"] == split]


def onehot(label):
    return [float(l == label) for l in LABELS]


def evaluate(agent, split="test"):
    hits, conf, wrong = collections.defaultdict(list), [], []
    for r in rows(split):
        a = agent.predict(r["text"], QUESTIONS)["answers"]["reply"]
        ok = a["choice"] == r["label"]
        for key in ("all", "lang:" + r["lang"], "label:" + r["label"]):
            hits[key].append(ok)
        conf.append(a["answer_confidence"])
        if not ok:
            wrong.append((r["label"], a["choice"], round(a["answer_confidence"], 2), r["text"]))
    for key in sorted(hits):
        print(f"  {key:24s} {sum(hits[key]):3d}/{len(hits[key]):3d} = {np.mean(hits[key]):.3f}")
    print(f"  calibration error (ECE)  {ece_score(np.array(conf), np.array(hits['all'], dtype=float)):.3f}"
          f"   mean confidence {np.mean(conf):.3f}")
    for w in wrong:
        print("  wrong: want %s, got %s (%.2f): %s" % w)
    return float(np.mean(hits["all"]))


def train(args):
    torch.manual_seed(0)
    base = Path(snapshot_download(BASE[0], revision=BASE_REVISION, allow_patterns=[BASE[1] + "/*"])) / BASE[1]
    cfg = json.loads((base / "rl_agent_config.json").read_text())
    tok = _load_tokenizer(str(base / "tokenizer"), cfg)
    model = build_model(cfg, encoder_dir=str(base / "encoder"))
    model.load_state_dict(load_file(str(base / "model.safetensors")), strict=True)
    model.float().train()
    # 197M of the 322M parameters are the token table. Frozen: training fits in a laptop's memory,
    # and words that never appear in 150 examples keep the meaning they were pretrained with.
    for name, p in model.named_parameters():
        if name.startswith("encoder.embeddings."):
            p.requires_grad = False

    q = QUESTIONS["reply"]
    internal = {"t": q["type"], "ins": q["instructions"], "crit": q["criteria"]}
    data = rows("train")
    calib, fit = data[::5], [r for i, r in enumerate(data) if i % 5]
    items = []
    for r in fit:
        ids, markers = build_sequence(tok, r["text"], internal, cfg["max_len"], cfg["head_max_len"])
        assert len(markers) == len(LABELS)
        items.append({"ids": ids, "markers": markers, "qtype": QTYPES["choice"], "target": onehot(r["label"])})

    encoder = [p for n, p in model.named_parameters() if n.startswith("encoder.") and p.requires_grad]
    head = [p for n, p in model.named_parameters() if not n.startswith("encoder.")]
    opt = torch.optim.AdamW([{"params": encoder, "lr": 2.5e-5}, {"params": head, "lr": 1e-4}], weight_decay=0.01)
    steps = args.epochs * -(-len(items) // args.batch)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=steps, eta_min=1e-6)
    print(f"training on {len(items)} replies, calibrating on {len(calib)}, {steps} updates")

    for epoch in range(args.epochs):
        random.Random(42 + epoch).shuffle(items)
        sigma = 0.4 + (0.1 - 0.4) * epoch / max(1, args.epochs - 1)
        total = 0.0
        for start in range(0, len(items), args.batch):
            b = collate_items([items[start:start + args.batch]], tok.pad_token_id)
            mask, target, qtype = b["marker_mask"], b["target"], b["qtype"]
            logits, act = model(b["input_ids"], b["attention_mask"], b["marker_pos"], mask, qtype)
            # Upstream's loss, unchanged: REINFORCE on a proper scoring rule, plus cross-entropy.
            k = mask.sum(-1, keepdim=True).float()
            eps = torch.randn((4,) + logits.shape) * sigma * mask
            eps = (eps - eps.sum(-1, keepdim=True) / k) * mask
            noisy = logits.detach().unsqueeze(0) + eps
            with torch.no_grad():
                reward = proper_reward(torch.softmax(noisy.masked_fill(~mask, -1e4), -1),
                                       target.unsqueeze(0), qtype, mask, w_sph=0.75, w_rps=1.0)
                adv = reward - reward.mean(0, keepdim=True)
                adv = adv / (adv.std() + 1e-6)
            logp = -(((noisy - logits.unsqueeze(0)) ** 2) * mask).sum(-1) / (2 * sigma ** 2)
            ce = -(target * torch.log_softmax(logits.masked_fill(~mask, -1e4), -1)).sum(-1).mean()
            loss = -(adv * logp).mean() + ce + 0.0 * act.sum()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()
            opt.zero_grad(set_to_none=True)
            total += ce.item() * len(mask)
        print(f"epoch {epoch + 1}/{args.epochs}  cross-entropy {total / len(items):.4f}", flush=True)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    save_file({n: v.detach().half().contiguous() for n, v in model.state_dict().items()},
              str(out / "model.safetensors"))
    model.encoder.config.save_pretrained(out / "encoder")
    tok.save_pretrained(out / "tokenizer")
    cfg.update({"fine_tuned": True, "model_name": "laya-dhool-vendor-replies", "temperature": [1.0, 1.0, 1.0]})
    cfg.pop("temperature_by_options", None)  # inherited buckets would mask the fit below
    (out / "rl_agent_config.json").write_text(json.dumps(cfg, indent=2))
    (out / "questions.json").write_text(json.dumps(QUESTIONS, indent=2, ensure_ascii=False))
    del model, opt

    # Temperature from replies the model was not trained on, measured on the weights as saved.
    agent = laya.load(str(out), device="cpu")
    records = records_from_labeled(agent, [(r["text"], QUESTIONS, {"reply": onehot(r["label"])}) for r in calib])
    cfg["temperature"] = fit_temperature_map(records)["temperature"]
    (out / "rl_agent_config.json").write_text(json.dumps(cfg, indent=2))
    print("temperature", cfg["temperature"], "-> saved", out)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=["eval", "train"])
    p.add_argument("model", nargs="?", help="eval: a fine-tuned folder; omit for the shipped checkpoint")
    p.add_argument("--out", default=str(OUT))
    p.add_argument("--epochs", type=int, default=6)
    p.add_argument("--batch", type=int, default=8)
    args = p.parse_args()
    if args.command == "train":
        train(args)
        args.model = args.out
    agent = (laya.load(args.model, device="cpu") if args.model
             else laya.load(BASE[0], subfolder=BASE[1], device="cpu", revision=BASE_REVISION))
    for split in ("test", "test2"):  # test2 was written after v1's mistakes on test were seen
        print(split, "replies,", args.model or "shipped multilingual checkpoint")
        evaluate(agent, split)
