# ADR 0007: arm64 one function at a time, and reserved concurrency once the limit allows

Status: Proposed (not built)
Date: 2026-10-10

## Context

- No function in `template.yaml` sets `Architectures`, so all five run on Lambda's default, x86_64.
- `vision/Dockerfile` builds llama.cpp with `-DGGML_AVX2=ON -DGGML_FMA=ON -DGGML_F16C=ON -DGGML_BMI2=ON`: x86 instructions. Every recorded speed, memory and accuracy figure for the two readers was taken on x86.
- The account runs 10 Lambdas at once (the comment on `NIGHTLY_PACE_S` in `backend/handlers/analysis.py`; CONTEXT.md, Log). No function reserves any, so the API, the nightly runs and two keep-warm pings draw on the same 10.
- Lambda's documentation: a function can reserve up to the unreserved value minus 100. Read against a limit of 10, nothing can be reserved (to confirm before building, by trying it).
- Charges are near zero (CLAUDE.md, Costs).

## Decision

Two separate changes.

Reserved concurrency, after the quota is raised:

- A reservation for `ApiFunction`, so background work cannot starve it.
- A cap on `VisionFunction`, `MessageFunction` and `MockInverterFunction`. `AnalysisFunction` is capped by the queue in ADR 0001.
- The numbers come from a week of each function's `ConcurrentExecutions` metric. Not measured.

arm64, in this order:

- `ApiFunction` and `MockInverterFunction`: zip, Python only, no compiled package (there is no `backend/requirements.txt`). One line each, `Architectures: [arm64]`.
- `AnalysisFunction`: rebuild the image. The pinned pvlib, pandas, numpy and pywebpush need arm64 wheels (to confirm before building).
- `VisionFunction` and `MessageFunction`: only after measuring in the Lambda image on arm64 with the commands in CLAUDE.md (`scripts/eval-vision.py --both` on the demo and real-app sets, `scripts/laya-tune.py eval`). Move one only if its counts are the same and it is no slower. llama.cpp needs an ARM build in place of the AVX2 flags. Whether the int8 ONNX weights answer the same on ARM: not measured.
- The laptop and CI's `ubuntu-latest` are x86, so arm64 images build under emulation or on an ARM runner. Build time: not measured.

## Consequences

- Better: a floor under the API; a lower price per GB-second on arm64 (how much: to confirm before building).
- Worse: reserved concurrency leaves the shared pool even when idle. Two architectures to build while the move is half done.
- New: a cap set too low throttles. A throttled reply reader is a 503 and the four buttons by hand (`read_vendor_reply`). A throttled screenshot read is retried by Lambda for up to 6 hours (its documented default), while the app gives up after `READING_TIMEOUT_S`.
- New: a reader that is slower, or reads differently, on ARM. Hence the measurement first.

## What would make us do it

- Reserved concurrency: the quota is raised, or `Throttles` appears on `ApiFunction`.
- arm64: a Lambda bill worth cutting. Today there is none.
- Owner-only: the quota request for concurrent executions in ap-south-1.

## Open questions

- Does llama.cpp on Graviton read a screenshot inside the 900 s timeout and 3008 MB? Not measured.
- Will AWS raise a limit of 10 on this account's plan? Not asked yet.
