# ADR 0006: The demo inverter cloud gets its own stack

Status: Proposed (not built)
Date: 2026-10-10

## Context

- `MockInverterFunction` sits in `template.yaml` beside the real backend. Its four routes (`/mock/app`, `/mock/v1/plants`, `/mock/v1/plants/{plantId}/daily`, `/mock/fleet/daily`) are on the same HTTP API with `Authorizer: NONE`. That is on purpose: a brand's service is outside our sign-in.
- What sharing the API costs:
  - `Api5xxAlarm` counts every route of `Api`. A demo failure raises the API's alarm, and demo traffic thins its percentage.
  - Two demo routes have their own throttle (burst 100, rate 50) inside the real API's `RouteSettings`.
  - `connect_inverter` (`backend/handlers/api.py`) builds the inverter's URL from the request's own host, and stores it on each linked house as `inverter_url`.
  - Taking the demo out means editing the stack that holds the retained user pool, table and bucket.
  - A public HTML page is served from the API's host.
- What it does not cost: the function has no policy on the table or the bucket.

## Decision

- A second template, `mock/template.yaml`: its own `AWS::Serverless::HttpApi`, `MockInverterFunction`, its log group and error alarm, and an output `MockUrl`. A `mock` environment in `samconfig.toml`, stack `dhool-mock`.
- The main stack takes a parameter `InverterUrl` and hands it to `ApiFunction` as an environment variable. `connect_inverter` uses it in place of `event['requestContext']['domainName']`.
- `web/src/readings.jsx` links to the demo app through a new `MOCK_URL` in `web/src/config.js`, not `${API_URL}/mock/app`. It is a link, not a fetch, so `customHttp.yml` should not need the new host (to confirm before building).
- Order: deploy the mock stack; deploy main with `InverterUrl` and the old routes still in place; link the showcase and demo homes again (each stores the old URL); then remove the old routes and their throttle lines.
- Unchanged: `backend/handlers/mock_inverter.py`, `backend/dhool/connectors.py`, the simulator.

## Consequences

- Better: the real API has no unauthenticated route. Its alarm and throttles describe only itself. The demo is deleted as one stack.
- Not better: Lambda concurrency. The limit of 10 belongs to the account and region, so a second stack in ap-south-1 shares it, and each run's two demo calls still count.
- Worse: two deploys to keep in step. Regenerating the demo data now deploys the mock stack. "The demo homes need no relinking" (CLAUDE.md, Commands) is untrue once.
- New: a wrong `InverterUrl`. Linking then answers 500, since `inverter_plant` passes on any error but 401 and 403, and linked homes' nightly runs fail into `FailureQueue`.

## What would make us do it

- Before the first real connector (ADR 0003), before WAF or per-person limits go on the real API, or before real homeowners are invited.
- Not during judging: the three showcase accounts depend on their links.
- Owner-only: nothing.

## Open questions

- Would another region give the demo its own concurrency (to confirm before building), and is that worth cross-region calls every night?
- Should a house store `inverter_brand` rather than a URL (ADR 0003)? Then a move like this one needs no relinking.
- Does `test_the_template_sends_the_api_function_exactly_the_routes_it_answers` need a twin for the mock template?
