# ADR 0003: One real inverter connector (SolarMAN or ShineMonitor)

Status: Proposed (not built)
Date: 2026-10-10

## Context

- The only inverter source is the demo inverter cloud. `backend/dhool/connectors.py` has `inverter_plant`, `inverter_readings` and `inverter_fleet`, all against one URL shape with a bearer key (`_get`).
- `connect_inverter` (`backend/handlers/api.py`) builds `inverter_url` from the request's own host plus `/mock` and stores it on the house. `run_house` (`backend/handlers/analysis.py`) reads through it.
- The rule (CLAUDE.md, Conventions): every source goes through a connector that returns the standard reading, `{"YYYY-MM-DD": kwh}`. The analysis never knows the source.
- `README.md` names SolarMAN or ShineMonitor as the next thing to build.
- We have not read either vendor's API documentation or terms. Nothing here describes their APIs.

## Decision

Find out first. Each of these is unknown:

1. Whether a third party may use an API at all: terms, cost, approval, waiting time.
2. How a homeowner grants access. If the only way is their app password, we do not build it.
3. Whether the credential is static or expires and refreshes (this decides ADR 0002).
4. Daily energy: offered or not, how far back, in which unit, and on whose clock a day ends (`config.TZ` is Asia/Kolkata).
5. Plant details: size, location, tilt, direction. The demo cloud returns all of them and `connect_inverter` overwrites the house's with them.
6. Rate limits, against one call per home per night plus on-demand runs.
7. Whether the terms allow storing readings, and sharing ratios between homes (ADR 0004).
8. Which of the two our users' inverters report to. Not surveyed.
9. A real account to test against. None exists.

Then build one, the vendor that answers 1 and 2 acceptably:

- `inverter_brand` on the house; a fixed table of brand to base URL in `backend/dhool/config.py`. The URL never comes from the client.
- Per-brand functions in `connectors.py` returning the plant and the standard reading. No fleet: `run_house` passes `fleet = None` and the home is judged alone.
- The brand's numbers are untrusted, like a screenshot's: drop days above `MAX_KWH_PER_KW` times the roof's kW. Today only typed and screenshot readings meet that check (`_reading` in `api.py`).
- Location rounded to 2 decimals, as now. A missing tilt or direction keeps `config.DEFAULT_TILT` and `DEFAULT_AZIMUTH`.
- A refused credential becomes "link again" in the app. Today `inverter_readings` raises on any HTTP error and the run fails.
- Tests run on saved responses with personal fields removed. The credential is stored as ADR 0002 says.
- Unchanged: `analyse`, `verdict`, and Setup apart from choosing the brand.

## Consequences

- Better: a real home sends readings every night with no screenshot.
- Worse: that home has no neighbours, so the "alone" scores in CLAUDE.md apply.
- New: the vendor changes or withdraws the API; a credential lapses and the home goes quiet; rate limits at night.
- Whether the vendor's daily figure matches what its app shows: not measured.

## What would make us do it

- Written API access, and one homeowner with such an inverter willing to test.
- Owner-only: applying to the vendor and accepting its terms.

## Open questions

The nine above. None can be answered from this repo.
