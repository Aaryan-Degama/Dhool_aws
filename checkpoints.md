# checkpoints.md — fine-tuned models we are keeping

Every model we fine-tune gets a row here: what it does, what it was trained on, how well it scored and
where the weights are. Add a new version as a new section; never overwrite an old folder.

## Laya, vendor-reply sorter

**Job:** read a solar vendor's WhatsApp reply to the homeowner's "please inspect my system" message and
pick one label: `visit_scheduled`, `asking_details`, `refused`, `unclear`.

**Base model:** [`convaiinnovations/laya`](https://huggingface.co/convaiinnovations/laya), `multilingual`
subfolder (mmBERT-base, 322M parameters, Apache-2.0), revision `55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851`.

**Status:** local only. Not deployed, not used by the app, not uploaded anywhere.

### Scores

Correct answers out of each test set. No test reply was ever trained on.

- `test` (56): the original set.
- `test2` (40): written after v1's mistakes on `test` had been seen.
- `test3` (60): written before v3 was trained, heavy on edge cases (visits with a charge or a reschedule,
  questions that sound like visits, polite refusals, wrong numbers, auto-replies, emoji and one-word replies).

| Model | Trained on | `test` (56) | `test2` (40) | `test3` (60) | All three (156) |
|---|---|---|---|---|---|
| Shipped checkpoint, no tuning | nothing of ours | 20 (36%) | not run | not run | |
| v1 | 116 replies | 49 (87.5%) | 32 (80.0%) | 47 (78.3%) | 128 (82.1%) |
| v2 | 243 replies | 50 (89.3%) | 37 (92.5%) | 51 (85.0%) | 138 (88.5%) |
| **v3 (use this one)** | 999 replies | 54 (96.4%) | 39 (97.5%) | 54 (90.0%) | 147 (94.2%) |

Chance is 25%.

**Which number to quote for v3: 90%, from `test3`.** v3's training replies were written after the
mistakes of v1 and v2 on `test` and `test2` were known, so its 96.4% and 97.5% there are flattered.
`test3` is the only set written without knowing how any model would do on it.

| v3, by slice | `test` | `test2` | `test3` |
|---|---|---|---|
| English | 12/12 | 8/8 | 8/8 |
| Hindi (Devanagari) | 16/16 | 8/8 | 10/12 |
| Hinglish (Hindi in Latin letters) | 26/28 | 23/24 | 36/40 |
| `visit_scheduled` | 14/14 | 10/10 | 14/15 |
| `asking_details` | 14/14 | 9/10 | 13/15 |
| `refused` | 14/14 | 10/10 | 14/15 |
| `unclear` | 12/14 | 10/10 | 13/15 |
| Calibration error (ECE) | 0.005 | 0.023 | 0.096 |

| `test3`, by slice | v1 | v2 | v3 |
|---|---|---|---|
| English | 8/8 | 8/8 | 8/8 |
| Hindi | 8/12 | 10/12 | 10/12 |
| Hinglish | 31/40 | 33/40 | 36/40 |
| `visit_scheduled` | 14/15 | 13/15 | 14/15 |
| `asking_details` | 13/15 | 11/15 | 13/15 |
| `refused` | 13/15 | 14/15 | 14/15 |
| `unclear` | 7/15 | 13/15 | 13/15 |
| Calibration error (ECE) | 0.180 | 0.103 | 0.096 |

Slices for v1 and v2 on `test` and `test2`:

| | v1 `test` | v1 `test2` | v2 `test` | v2 `test2` |
|---|---|---|---|---|
| English | 12/12 | 6/8 | 11/12 | 8/8 |
| Hindi | 15/16 | 7/8 | 16/16 | 8/8 |
| Hinglish | 22/28 | 19/24 | 23/28 | 21/24 |
| `visit_scheduled` | 13/14 | 9/10 | 12/14 | 9/10 |
| `asking_details` | 14/14 | 8/10 | 13/14 | 8/10 |
| `refused` | 12/14 | 9/10 | 13/14 | 10/10 |
| `unclear` | 10/14 | 6/10 | 12/14 | 10/10 |
| Calibration error (ECE) | 0.098 | 0.154 | 0.056 | 0.056 |

### What these numbers do not show

- **Every reply, train and test, was written by Claude (an AI model), not collected from vendors.** The
  scores are an upper bound. No version has been tried on a single real vendor reply; expect lower.
- **The test sets are small.** One reply is 1.7 to 2.5 points. v3's lead over v2 (147 against 138 of 156)
  is real but the exact percentages are not precise.
- **Confidence is still not trustworthy.** v3's nine wrong answers all came at 0.90 to 0.96 confidence,
  the same as its right ones. Do not accept or reject an answer on its confidence; have the homeowner
  confirm the label.
- **Known weak spots (v3):**
  - A charge with a condition ("450 lagega aane ka, aap haan bolo tabhi nikalunga") is still read as a
    visit, in Hinglish and Hindi, although the training data has such examples. All three versions fail this.
  - A refusal phrased as a condition ("Pichla payment do pehle, uske bina koi nahi aayega") is read as a visit.
  - Greetings and confusion that end in a question mark ("Kya hua?? samjha nahi", "राम राम जी, कैसे हैं?")
    are read as asking for details.
  - Heavy texting shorthand ("haan aa rhe h sir 1 ghnte me") can be missed.

### Labelling rules used in the data

- A visit plus a courtesy check ("kal aata hu, ghar pe koi rahega na?") is `visit_scheduled`.
- An offer to come that waits on the homeowner ("kal aa jau kya?", "500 lagega, bolo to aata hu"), or a
  visit that needs something first ("bhej dunga, pehle address do"), is `asking_details`.
- "It is normal, nothing needs doing", a wrong number, and "pay the old bill first" are `refused`.
- "Will call", "will check", "it will be done" with no visit, auto-replies and greetings are `unclear`.

### v3 at other precisions (v3.1, v3.2)

Same trained weights as v3, stored and run differently. Measured 3 Oct 2026 on two cores
(`taskset -c 0,1`, to match a Lambda), one reply at a time.

| Model | Weights | Size on disk | `test` (56) | `test2` (40) | `test3` (60) | All (156) | Per reply | Peak memory |
|---|---|---|---|---|---|---|---|---|
| v3 / **v3.1** | float16, PyTorch | 647 MB | 54 (96.4%) | 39 (97.5%) | 54 (90.0%) | 147 (94.2%) | 396 ms | 2.3 GB |
| v3 ONNX | float32, ONNX Runtime | 1.3 GB | 54 (96.4%) | 39 (97.5%) | 54 (90.0%) | 147 (94.2%) | 130 ms | 1.1 GB |
| **v3.2** | int8, ONNX Runtime | 335 MB | 54 (96.4%) | 38 (95.0%) | 52 (86.7%) | 144 (92.3%) | 71 ms | 1.1 GB |
| int8, layers only (not kept) | int8 layers, float32 token table | 925 MB | 53 (94.6%) | 38 (95.0%) | 54 (90.0%) | 145 (92.9%) | 70 ms | 2.2 GB |

- **v3.1 is v3.** The training script has always saved weights in float16 (322M parameters at 2 bytes),
  so the 647 MB file was float16 from the start and v3's scores were measured on it. A float32 file would
  be 1.29 GB. `vendor-replies-v3.1-f16` is a link to the `vendor-replies-v3` folder, not a second copy.
  PyTorch widens the weights to float32 in memory, which is why it uses 2.3 GB.
- **v3 ONNX** gives exactly v3's answers (147 of 156, same mistakes) three times faster and in half the
  memory. It is the one to deploy if accuracy matters most.
- **v3.2 (int8)** is half the size of float16 and 5.6 times faster than PyTorch, for three more mistakes
  (144 against 147), two of them on the edge-case set. There is no 8-bit float; int8 is the 8-bit option.
  Made with ONNX Runtime's dynamic quantization of the layer weights and the token table, one scale per
  tensor. Its extra `test3` mistakes are refusals ("Maine ye dhandha band kar diya 2 saal pehle",
  "हमने यह नहीं लगाया था, जिसने लगाया उसे कहिए") and "Kal 10 baje 👍".
- **int8 on the layers only** is Laya's own recipe. It leaves the token table (60% of the model) in
  float32, so it is larger than float16; not kept. `scripts/laya-tune.py quantize` rebuilds it.
- A float16 ONNX graph was not made: ONNX Runtime on a CPU has no fast float16 kernels.
- Calibration error (`test` / `test2` / `test3`): v3 0.005 / 0.023 / 0.096; v3.2 0.065 / 0.007 / 0.079.
  Confidence is no more trustworthy after quantization than before.

| | v3 ONNX | v3.2 |
|---|---|---|
| Folder | `messages/models/vendor-replies-v3-onnx/` (`model.onnx` + `model.onnx.data`; uses v3's tokenizer and config) | `messages/models/vendor-replies-v3.2-int8/` (self-contained) |
| SHA-256 | `model.onnx.data`: `d2ae1dfa9a095c60c3fe745556c5f9901731bc1b8c59c7ce31c177a661b9d63c` | `model.onnx`: `d57a203eb94b57981519a1015e248f0a40370ad301c1a254c87f720ce7e52a60` |
| Made with | Laya's `scripts/export_onnx.py` (commit `c829d5a`) on the v3 folder | `scripts/laya-tune.py quantize messages/models/vendor-replies-v3` (writes `model-int8-all.onnx`) |

```python
import json
from laya.onnx_agent import ONNXAgent
folder = "messages/models/vendor-replies-v3.2-int8"
agent = ONNXAgent(folder, onnx_path=folder + "/model.onnx")
agent.predict("Sir kal 11 baje aata hu", json.load(open(folder + "/questions.json")))["answers"]["reply"]["choice"]
```

Score one: `taskset -c 0,1 .venv-laya/bin/python scripts/laya-tune.py eval <folder> --onnx <folder>/model.onnx`

### v3

| | |
|---|---|
| Folder | `messages/models/vendor-replies-v3/` (647 MB, not in git) |
| `model.safetensors` SHA-256 | `96430f98e0a14f5151ec239786dc5fa3a8117bda8fc5c106d9f3a0fbbba9ccb0` |
| Made | 3 Oct 2026, `scripts/laya-tune.py train` |
| Data | `messages/vendor-replies.jsonl`, 1,111 rows with `split: train`: 999 trained on, 112 (every tenth) held back to fit the temperature |
| Training rows by label | `visit_scheduled` 274, `asking_details` 275, `refused` 275, `unclear` 287 |
| Training rows by language | Hinglish 614, English 250, Hindi 247 |
| Settings | 6 epochs, batch 8, 750 updates; AdamW, 2.5e-5 on the encoder and 1e-4 on the decision head, cosine decay; token table frozen; seed 0 |
| Cost | 45 min on the laptop CPU, peak 5.2 GB |
| Temperature | 4.49 |

### v2

| | |
|---|---|
| Folder | `messages/models/vendor-replies-v2/` (647 MB, not in git) |
| `model.safetensors` SHA-256 | `6077bd2627ec29cb3722ff65ad8595605981d13ea0fb3e3c7833252839ae539d` |
| Made | 3 Oct 2026, commit `55c7d5a` |
| Data | the first 304 `train` rows of `messages/vendor-replies.jsonl` (everything above the first `test2` row): 243 trained on, 61 (every fifth) held back to fit the temperature |
| Training rows by label | `visit_scheduled` 74, `asking_details` 74, `refused` 74, `unclear` 82 |
| Settings | 6 epochs, batch 8, 186 updates; AdamW, 2.5e-5 on the encoder and 1e-4 on the decision head, cosine decay; token table frozen; seed 0 |
| Cost | 10 min 34 s on the laptop CPU, peak 5.2 GB |
| Temperature | 5.0 (the library's ceiling) |

### v1

| | |
|---|---|
| Folder | `messages/models/vendor-replies-v1/` (647 MB, not in git) |
| `model.safetensors` SHA-256 | `96b7d43022e39be2787bf57caa96af83173ecd53322786aff8d59acf21c9ea25` |
| Made | 3 Oct 2026, commit `7a2d517` |
| Data | the first 145 `train` rows of the same file (everything above the first `test` row): 116 trained on, 29 held back for the temperature |
| Settings | as v2, 90 updates |
| Cost | 8 min 33 s on the laptop CPU, peak 5.2 GB |
| Temperature | 5.0 (the library's ceiling) |

v1 and v2 cannot be rebuilt by rerunning the script on today's data file; each folder is the only copy.

### Using a saved model

Each folder holds the weights, tokenizer, config and `questions.json`, the exact question the model was
tuned on. Ask that question and no other.

```python
import json, laya
folder = "messages/models/vendor-replies-v3"
agent = laya.load(folder, device="cpu")
questions = json.load(open(folder + "/questions.json"))
agent.predict("Sir kal 11 baje aata hu", questions)["answers"]["reply"]["choice"]   # visit_scheduled
```

Score one again: `.venv-laya/bin/python scripts/laya-tune.py eval messages/models/vendor-replies-v3`

### Where the weights are, and the risk

All of these folders (3.5 GB together) live only on the owner's laptop, in the `Dhool-laya` worktree, and are ignored by git.
If they are deleted, v3 can be retrained in about 45 minutes; v1 and v2 cannot. Copy `messages/models/`
somewhere else (an S3 bucket, a drive) if any must survive the laptop.
