# ADR 0004: Neighbours from nearby Dhool homes, with consent, found by a geohash key

Status: Proposed (not built)
Date: 2026-10-10

## Context

- Neighbours exist only for a home linked to the demo inverter: `run_house` (`backend/handlers/analysis.py`) calls `connectors.inverter_fleet`, the demo cloud's feed of every plant. A home on screenshots or typed numbers gets `fleet = None`.
- Without neighbours, `backend/dhool/verdict.py` skips the trips rule (`_trips`), cannot tell a grid cut from an outage (`_outage`), and never gives a fault high confidence (`_fault`).
- In simulation, hidden set (CLAUDE.md, Status; CONTEXT.md, Log), score and faults caught: with neighbours 84% and 86%; alone 83% and 66%. With 15% weather error: with neighbours 48% and 37%; alone 56% and 1% (6 of 433).
- So neighbours find faults. With weather error they also lower the overall score, because the trips rule fires on noise. That error is drawn separately per roof; real neighbours share weather. How much they share: not measured.
- Location is already stored to 2 decimals, about a kilometre (`create_house` in `backend/handlers/api.py`).

## Decision

- Consent: a switch per home, off by default, owner-only (a new action in `authz.OWNER_ONLY`), with fixed text in both languages.
- Shared: one number a day, made divided by expected for that roof. Not kWh, size, name, house id or coordinates.
- Index, in the same table: `pk = GEO#<5-character geohash of the rounded location>`, `sk = <random pool id kept on META>`, the daily ratios, and `expiresAt` so a silent home drops out. Written at the end of that home's own run.
- Read: nine `Query` calls, the home's cell and the eight around it. No `Scan`, no new index. A cell is roughly 5 km across (to confirm before building).
- `analyse()` accepts ready ratios; `verdict()` already takes a frame of them. Each home's ratio then comes from its own physics, which retires the `ponytail:` note in `analyse.py`.
- Fewer than `MIN_POOL` neighbours counts as alone: a median of one neighbour is that neighbour.
- Homes linked to the demo inverter never write to the pool. Its plants sit at real Delhi coordinates (`config.SIM_LAT`, `SIM_LON`).
- Switching off, or deleting the home, deletes its pool item.
- A rule change follows the routine in CLAUDE.md, the hidden set once.

## Consequences

- Better: real homes get the comparison that finds faults.
- Worse: a neighbour's wrong typed numbers enter the median. A busy cell is one large partition, held down with `Limit`.
- New: pooled ratios are up to a day old. `_haze` and `_outage` read the latest days and need checking against that.
- "What Dhool keeps about you" changes, in both languages.

## What would make us do it

- `MIN_POOL` consenting real homes inside one nine-cell block. Today there are none.
- First, cheaply: a "k neighbours" case in `dhool.evaluate` on seeds 0 to 2. It scores 29 neighbours or none; how many are enough is not measured.
- Owner-only: the consent wording, reading its Hindi, and whether India's data protection law asks for more (not checked).

## Open questions

- `MIN_POOL`. A judgement until the case above is run.
- Do real neighbours share enough weather error to help? Only real homes can say.
- How many days of ratios a neighbour must keep.
