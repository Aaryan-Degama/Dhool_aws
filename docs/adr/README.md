# Architecture decision records

Design notes for work that is not built. Each says what the code does today, what we would build, what it costs, and what would make us do it. None of them changes what is deployed.

Where a note says "not measured", nobody has measured it. Where it says "to confirm before building", it is an AWS or third-party fact we did not check against a running system.

| No. | Title | Status | Gist |
|---|---|---|---|
| [0001](0001-sqs-queue-for-analysis-runs.md) | An SQS queue between "this house needs a run" and the run | Proposed (not built) | A queue with `MaximumConcurrency` replaces the 1.5 s sleep between nightly runs; saves from the app queue one delayed run per house. |
| [0002](0002-kms-for-inverter-credentials.md) | Inverter credentials are encrypted with one KMS key, not kept in Secrets Manager | Proposed (not built) | One key at a flat price against a fee per home; the API may only encrypt, the analysis only decrypt. |
| [0003](0003-real-inverter-connector.md) | One real inverter connector (SolarMAN or ShineMonitor) | Proposed (not built) | Nine things to find out from the vendor first, then one connector behind the standard reading. |
| [0004](0004-neighbour-pooling-with-consent.md) | Neighbours from nearby Dhool homes, with consent, found by a geohash key | Proposed (not built) | Consenting homes share a daily ratio under a geohash key; nine `Query` calls find the neighbours. |
| [0005](0005-srp-sign-in-and-mfa.md) | SRP sign-in, and an optional second step for owners | Proposed (not built) | An optional authenticator-app step first, then SRP, then the password flow is switched off. |
| [0006](0006-mock-inverter-own-stack.md) | The demo inverter cloud gets its own stack | Proposed (not built) | The demo moves to its own stack and HTTP API; the real API keeps no unauthenticated route. |
| [0007](0007-arm64-and-reserved-concurrency.md) | arm64 one function at a time, and reserved concurrency once the limit allows | Proposed (not built) | Reserve for the API after the quota is raised; move the zip functions to arm64 first, the readers only after measuring. |
| [0008](0008-github-oidc-deploy-to-staging.md) | GitHub Actions deploys the staging stack through OIDC | Proposed (not built) | A narrow role trusted for `main` deploys staging on every merge; production stays by hand. |
