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

Correct answers out of each test set. `test` is the original 56 replies; `test2` is 40 replies written
after v1's mistakes on `test` had been seen, so it is the fairer comparison between versions.

| Model | Trained on | `test` (56) | `test2` (40) | Calibration error, `test` / `test2` |
|---|---|---|---|---|
| Shipped checkpoint, no tuning | nothing of ours | 20 (36%) | not run | 0.477 / not run |
| v1 | 116 replies | 49 (87.5%) | 32 (80.0%) | 0.098 / 0.154 |
| **v2 (use this one)** | 243 replies | 50 (89.3%) | 37 (92.5%) | 0.056 / 0.056 |

Chance is 25%.

| v2, by slice | `test` | `test2` |
|---|---|---|
| English | 11/12 | 8/8 |
| Hindi (Devanagari) | 16/16 | 8/8 |
| Hinglish (Hindi in Latin letters) | 23/28 | 21/24 |
| `visit_scheduled` | 12/14 | 9/10 |
| `asking_details` | 13/14 | 8/10 |
| `refused` | 13/14 | 10/10 |
| `unclear` | 12/14 | 10/10 |

| v1, by slice | `test` | `test2` |
|---|---|---|
| English | 12/12 | 6/8 |
| Hindi (Devanagari) | 15/16 | 7/8 |
| Hinglish | 22/28 | 19/24 |
| `visit_scheduled` | 13/14 | 9/10 |
| `asking_details` | 14/14 | 8/10 |
| `refused` | 12/14 | 9/10 |
| `unclear` | 10/14 | 6/10 |

### What these numbers do not show

- **Every reply, train and test, was written by Claude (an AI model), not collected from vendors.** The
  scores are an upper bound. Neither version has been tried on a single real vendor reply; expect lower.
- **The test sets are small.** One reply is 1.8 points on `test` and 2.5 on `test2`, so v1 and v2 are not
  separable on `test` (49 against 50); the gap on `test2` (32 against 37) is the evidence that v2 is better.
- **Confidence is not trustworthy in either version.** v2's nine wrong answers came at 0.47 to 0.95
  confidence, seven of them at 0.87 or above. The fitted temperature hit the library's ceiling (5.0) both
  times. Do not accept or reject an answer on its confidence; have the homeowner confirm the label.
- **Known weak spot (v2):** a charge with a condition ("Aane ka 400 lagega, manzoor hai to bolo") is read
  as a visit instead of a question, on both test sets. Hinglish is still the weakest language.

### v2

| | |
|---|---|
| Folder | `messages/models/vendor-replies-v2/` (647 MB, not in git) |
| `model.safetensors` SHA-256 | `6077bd2627ec29cb3722ff65ad8595605981d13ea0fb3e3c7833252839ae539d` |
| Made | 3 Oct 2026, `scripts/laya-tune.py train` |
| Data | `messages/vendor-replies.jsonl`, 304 rows with `split: train`: 243 trained on, 61 (every fifth) held back to fit the temperature |
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

v1 cannot be rebuilt by rerunning the script on today's data file; the folder is the only copy.

### Using a saved model

Each folder holds the weights, tokenizer, config and `questions.json`, the exact question the model was
tuned on. Ask that question and no other.

```python
import json, laya
folder = "messages/models/vendor-replies-v2"
agent = laya.load(folder, device="cpu")
questions = json.load(open(folder + "/questions.json"))
agent.predict("Sir kal 11 baje aata hu", questions)["answers"]["reply"]["choice"]   # visit_scheduled
```

Score one again: `.venv-laya/bin/python scripts/laya-tune.py eval messages/models/vendor-replies-v2`

### Where the weights are, and the risk

Both folders live only on the owner's laptop, in the `Dhool-laya` worktree, and are ignored by git. If
that folder is deleted, v2 can be retrained in about ten minutes; v1 cannot. Copy `messages/models/`
somewhere else (an S3 bucket, a drive) if either must survive the laptop.
