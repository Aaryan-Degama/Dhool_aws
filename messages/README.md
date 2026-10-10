# Vendor replies

`vendor-replies.jsonl`: replies from a solar vendor to a homeowner's "please inspect my rooftop solar" WhatsApp message, one JSON object a line, labelled.

- **Written by Claude (an AI model), not collected from real vendors.** Good enough to teach the labels; any score on the `test` rows is a score on the same author's writing, not on real replies. Replace or extend with real replies before claiming anything about them.
- A real vendor's reply goes in as a row with `"split": "real"` (take out names, phone numbers and addresses first); `scripts/laya-tune.py eval <model>` then scores those rows on their own. Never give a real reply any other split.
- `label`: `visit_scheduled` | `asking_details` | `refused` | `unclear`.
- `lang`: `en` | `hi` (Devanagari) | `hing` (Hindi in Latin letters).
