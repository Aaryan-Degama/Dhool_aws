# ADR 0008: GitHub Actions deploys the staging stack through OIDC

Status: Proposed (not built)
Date: 2026-10-10

## Context

- Deploys are by hand from a laptop: `sam validate && ./scripts/build.sh && sam deploy` (CLAUDE.md, Commands). `.github/workflows/ci.yml` lints, tests and builds; its only permission is `contents: read`.
- `samconfig.toml` defines a `staging` environment (stack `dhool-staging`, ap-south-1). Nothing is deployed to it.
- CONTEXT.md, Blockers: a GitHub-to-AWS deploy role with admin rights was blocked by the session's permission policy.
- Two sessions deploying one stack overwrite each other (CLAUDE.md, "Two sessions, one stack").
- A CI build lacks the weights. `vision/models/` comes from `scripts/fetch-model.sh` (1.5 GB). `messages/models/vendor-replies-v3.2-int8/` (335 MB) comes from the `laya-models` release, then `chmod -R a+rX messages/models`.

## Decision

- IAM, made once by the owner: GitHub's OIDC provider (`token.actions.githubusercontent.com`, audience `sts.amazonaws.com`) and a deploy role trusted only for `repo:Aaryan-Degama/Dhool_aws:ref:refs/heads/main`.
- The role is not admin. It may act on the `dhool-staging` stack, SAM's artifact bucket and image repositories, and pass a CloudFormation execution role held inside a permissions boundary. `sam pipeline bootstrap` is meant to create this set (to confirm before building).
- A `deploy-staging` job in `ci.yml`, on a push to `main`, after `template` and `test`: `permissions: id-token: write`, `aws-actions/configure-aws-credentials`, fetch both sets of weights, `./scripts/build.sh`, `sam deploy --config-env staging`, then one call without a token that must answer 401.
- `samconfig.toml`, staging: `VapidParam=/dhool-aws-staging/vapid-private-key`. Without it staging's analysis role is granted, and reads, production's push key: `VapidParam` defaults to `/dhool/vapid-private-key` in `template.yaml`.
- A template parameter switches the two `KeepWarm` schedules and `Nightly` off in staging.
- Production stays a hand deploy.

## Consequences

- Better: every merge is tried on AWS before anyone deploys by hand. No long-lived AWS key sits in GitHub.
- Worse: a second copy of everything. Its user pool, table and bucket are `Retain` with deletion protection, so deleting the stack leaves them standing. Its three images sit in ECR beside production's (about 14 GB there now, CLAUDE.md).
- Worse: staging's functions share the account's 10 concurrent Lambdas with production.
- New: the role is a way into the account from GitHub, and a workflow change on `main` can use it.
- New: a deploy fails when Hugging Face or the GitHub release cannot be reached.
- CI time and runner disk for three images with their weights: not measured.

## What would make us do it

- A second person deploying, or a hand deploy that breaks production. Not before judging ends.
- Owner-only: creating the provider and the roles (the session may not), and a staging push key if staging should send alerts.

## Open questions

- Can a role this narrow still create the functions' own roles (`CAPABILITY_IAM`)?
- Keep staging standing, or create and delete it per run? The retained resources make deletion untidy.
- Does a SAM schedule's `Enabled` take a parameter (to confirm before building)?
