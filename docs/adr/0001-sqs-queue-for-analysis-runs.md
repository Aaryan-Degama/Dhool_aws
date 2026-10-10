# ADR 0001: An SQS queue between "this house needs a run" and the run

Status: Proposed (not built)
Date: 2026-10-10

## Context

- Nightly, `handler` in `backend/handlers/analysis.py` walks the `HOUSES` partition and starts one background run of itself per house, sleeping `NIGHTLY_PACE_S` (1.5 s) between starts. Short of time, it hands the cursor to a fresh invocation.
- The sleep is there because the account runs 10 Lambdas at once and each run also calls the demo inverter twice (the comment on `NIGHTLY_PACE_S`). It is a guess at how long a run takes, not a cap. Concurrency during a nightly run: not measured.
- About 70 houses fit in one 120 s invocation (same comment). Each further house adds 1.5 s of a 1024 MB function asleep.
- On demand, `_start_analysis` in `backend/handlers/api.py` starts a run at once from `add_reading`, `record_action`, `connect_inverter` and `save_settings`. Three saves in a row are three runs.
- Two overlapping runs for one house can finish out of order: `run_house` puts `VERDICT#<date>` with no check on which run read newer data. Read from the code, not observed.

## Decision

- `AnalysisQueue` (standard SQS) in `template.yaml`, redriving to the existing `FailureQueue` after 3 receives. Visibility timeout: six times the function's 120 s (AWS's guidance for Lambda consumers; to confirm before building).
- An SQS event on `AnalysisFunction`: `BatchSize: 1`, `ScalingConfig: {MaximumConcurrency: 2}`. Lambda's documentation gives the range as 2 to 1,000, free, and independent of reserved concurrency.
- Nightly: the dispatcher sends `{"house_id", "nightly": true}` in batches of 10. `NIGHTLY_PACE_S` and the sleep go; the cursor hand-over stays. `run_house` is unchanged; `handler` gains a branch for `Records`.
- On demand: `_start_analysis` sets `run_queued_at` on the house's `META` item, on condition that it is absent or minutes old, and only then sends one message with `DelaySeconds`. A run removes the mark before it reads the house, so a later save queues again.
- The verdict put gains a condition: a run that read older data cannot overwrite a newer verdict.
- The API's role swaps its invoke permission on `AnalysisFunction` for `sqs:SendMessage`.

## Consequences

- Better: AWS holds the cap; a failing house is retried on its own; a burst of saves is one run.
- Worse: a typed reading's verdict arrives later, by the delay plus SQS's polling time (not measured), while the app waits on `POLL_MS` (`web/src/store.js`).
- Delivery is at least once. A repeated run is safe today: it rewrites the same item and `_notify` checks `last_notified`.
- New: an on-demand run waits behind the night's backlog. A second queue needs 2 more concurrent runs, which a limit of 10 cannot spare.
- New: `FailureQueue` receives two shapes (Lambda's failure record, a redriven message).
- `backend/tests/test_notify.py` asserts the `lambda.invoke` calls and must be rewritten.

## What would make us do it

- The house list passing about 70 (the first hand-over), a `Throttles` count on `ApiFunction` during the nightly run, or a stale verdict reported.
- If AWS raises the limit first, `NIGHTLY_PACE_S = 0` is the smaller step, as the comment says.
- Owner-only: the quota request for Lambda concurrent executions.

## Open questions

- The delay: long enough to join a burst, short enough for the "Working it out" wait. To be set by trying it.
- Whether messages throttled because other functions hold the 10 count toward the 3 receives (to confirm before building).
