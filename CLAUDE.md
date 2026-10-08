# CLAUDE.md — Dhool

Hackathon project for Environmental Hacks (WeMakeDevs × AWS, Oct 8 – 11, 2026). **Read `CONTEXT.md` first** for the rules, judging criteria, the current plan and the log.

## Context files (read before planning or building)

| File | What it holds |
|---|---|
| `CONTEXT.md` | Hackathon rules, judging criteria, current decisions, open questions, dated log. Read first. |
| `DHOOL.md` | The full product design: problem, verdict logic, data strategy, architecture, demo storyboard, build plan, cut order. |
| `LESSON.md` | Lessons from Slate, our previous hackathon in this series (26/30). Repeat what scored; fix what held us back (no tests, single-format coupling, late UI and video). Its AWS specifics describe Slate, not Dhool. |
| `CLAUDE.md` | This file: how to work in this repo. |

## Standing instructions (every session, every message)

1. **Keep the docs current.** At the end of any turn that changed something, update the files before replying:
   - `CONTEXT.md`: decisions, stack, features done or in progress, blockers, open questions, plus a dated line at the top of **Log**.
   - `CLAUDE.md`: only when *how to work* changes (commands, conventions, structure, new standing rules).
   - Skip the update only if nothing changed (a pure Q&A turn, for example).
2. **Respect the hackathon rules** in `CONTEXT.md`. Work within the event schedule (Oct 8–11).
3. **Optimise for the judging criteria:** real impact, AWS clearly used, usable by non-team members, one feature that works end to end, and a 3-minute demo video.
4. **Ship the smallest thing that works.** Pick a working vertical slice over breadth.
5. Every piece of third-party code gets a credit and needs a compatible license.

## Project layout
_Code lives in the `Dhool_aws` repo._

```
template.yaml              SAM: user pool, HTTP API + JWT authorizer, table, bucket, functions, nightly schedule
backend/dhool/             pure logic, no AWS calls (sim, expected, verdict, connectors, authz, config)
backend/handlers/          thin I/O wrappers: api, mock_inverter, nightly, agent (Strands tools)
backend/tests/             pytest
web/                       React + Vite PWA, deployed by Amplify Hosting from `main`
.github/workflows/ci.yml   pytest + sam validate on every push
```

## Commands
_Deploy commands are planned; confirm each one when that code exists._

- Setup: `uv venv --python 3.12 .venv && uv pip install -p .venv -r backend/requirements-dev.txt`
- Test: `.venv/bin/pytest`
- Generate the simulated neighbourhood (real Open-Meteo weather): `cd backend && ../.venv/bin/python -m dhool.sim`
- Deploy backend (confirmed): `sam validate && ./scripts/build.sh && sam deploy` (the script is `sam build` plus proxy handling for the container build)
- Score the verdict rules against the simulator: `cd backend && ../.venv/bin/python -m dhool.evaluate <seed>` (seed 0 is the development data; use other seeds for an honest number)
- Deploy settings are in `samconfig.toml`: stack `dhool-aws`, region `ap-south-1`.
- Live endpoints, pool IDs and demo account password: `.env` (gitignored, never commit)
- `backend/requirements-analysis.txt` holds the heavy pvlib dependencies for the analysis container. Do not add a `backend/requirements.txt`: SAM would pack those into the small API Lambda zip.
- Run one function locally: `sam local invoke <FunctionName>`
- Frontend: `npm run dev` / `npm run build` in `web/`; `/#preview` shows every verdict state without signing in. Amplify Hosting builds `main` using `amplify.yml`.
- Design decisions live in `DESIGN.md`; read it before changing the UI.
- Android emulator (AVD `dhool`, Android 15): `~/Android/Sdk/emulator/emulator -avd dhool -http-proxy "$HTTPS_PROXY"`, then `adb reverse tcp:5173 tcp:5173` and open `http://localhost:5173` in the emulator's Chrome while `npm run dev` runs. To script that Chrome: `adb forward tcp:9222 localabstract:chrome_devtools_remote`.

## Conventions
- **Definition of done:** pure logic in `backend/dhool/` → tests pass → deployed → verified on the live URL → commit → push.
- **Identity is server-side.** The caller is the JWT `sub` from the authorizer. Never read a user, house, role or ownership from the request body or query string.
- **Every handler calls `authorize(sub, house_id, action)`** before touching house data, and logs the decision as one JSON line.
- Data belongs to a house, not a person. Screenshots are reached only through presigned URLs issued after `authorize()`.
- DynamoDB: `Query`, never `Scan`. Data with a natural lifetime gets a TTL attribute.
- Every input source goes through a connector that returns the standard reading; the analysis never knows the source.
- The verdict is never made by a language model. Never generate data with an LLM.
- Deployment-specific values (tariff, thresholds, default tilt and azimuth, region) live in `config.py`.
- Serverless and scale-to-zero only.
