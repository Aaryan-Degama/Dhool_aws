# ADR 0002: Inverter credentials are encrypted with one KMS key, not kept in Secrets Manager

Status: Proposed (not built)
Date: 2026-10-10

## Context

- `connect_inverter` in `backend/handlers/api.py` writes the brand's API key in the clear, as `inverter_key` on the house's `META` item. Its `ponytail:` comment says to move it before a real brand is connected.
- That comment says only the API's role reads it. `template.yaml` also gives `AnalysisFunction` `DynamoDBCrudPolicy` on the table, and `run_house` reads `meta["inverter_key"]` every night. Anyone who can read the table in the console, or restore it (point-in-time recovery is on), reads the key too.
- `get_house` returns only `linked`, never the key.
- Today the only key is the demo inverter's: derived from the plant id and printed on the public `/mock/app` page (`api_key` in `backend/handlers/mock_inverter.py`). Nothing real is at risk until ADR 0003.

## Decision

KMS.

- One customer managed key in `template.yaml`, `DeletionPolicy: Retain` like the table.
- `connect_inverter` calls `kms:Encrypt` with encryption context `{"house": house_id}` and stores the ciphertext as `inverter_key_enc`. `run_house` calls `kms:Decrypt` with the same context, so a ciphertext copied onto another house does not open.
- `ApiFunction` may only encrypt; `AnalysisFunction` may only decrypt.
- Houses linked today count as not linked until the owner links again (the path `run_house` already has for a plant with no key), or are re-encrypted once.

The comparison, in USD a month, one read per home per night (on-demand runs add more). Prices are from AWS's pricing pages as read today; ap-south-1 was not checked (to confirm before building).

| Linked homes | Secrets Manager, one secret per home | KMS, one key |
|---|---|---|
| 100 | 40 | 1 |
| 1,000 | 400 | about 1.03 |
| 10,000 | 4,000 | about 1.84 |

- Secrets Manager: $0.40 a secret, $0.05 per 10,000 calls. KMS: $1 a key, 20,000 requests free, then $0.03 per 10,000.
- What Secrets Manager adds for the money: scheduled rotation, a policy and versions per secret. A key the homeowner pastes has nothing to rotate.
- A deleted secret waits in a recovery window unless force-deleted (to confirm before building); "delete this home" would have to force it.
- Not chosen: one secret holding every key (each run would read them all); an SSM SecureString per home, as the push key is kept (no fee per standard parameter, but a cap per account and region: both to confirm before building).

## Consequences

- Better: a table read, export or restore yields ciphertext. Each role holds one half.
- Worse: a linked home's nightly run fails when KMS is throttled or down, and lands in `FailureQueue`.
- New: delete the KMS key and every stored credential is gone; every owner links again.
- No rotation and no per-home policy.

## What would make us do it

- The first real brand credential (ADR 0003). Before that there is nothing to protect.
- Owner-only: nothing.

## Open questions

- Is the real brand's credential static, or a token that expires and refreshes? Unknown (ADR 0003). If it refreshes, the analysis role must encrypt too, and Secrets Manager's rotation is worth a second look.
- Encrypt the demo keys as well (one code path), or leave them (they are public)?
