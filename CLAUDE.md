# CLAUDE.md — Dhool

Hackathon project for Environmental Hacks (WeMakeDevs × AWS, Oct 8 – 11, 2026). **Read `CONTEXT.md` first** for the rules, judging criteria, the current plan and the log.

## Context files (read before planning or building)

| File | What it holds |
|---|---|
| `CONTEXT.md` | Hackathon rules, judging criteria, current decisions, open questions, dated log. Read first. |
| `DHOOL.md` | The full product design: problem, verdict logic, data strategy, architecture, demo storyboard, build plan, cut order. |
| `LESSON.md` | Lessons from Slate, our previous hackathon in this series (26/30). Repeat what scored; fix what held us back (no tests, single-format coupling, late UI and video). Its AWS specifics describe Slate, not Dhool. |
| `checkpoints.md` | Every fine-tuned model we keep: data, settings, scores, caveats, where the weights are. |
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
backend/handlers/          thin I/O wrappers: api, analysis (pvlib container, nightly), mock_inverter (demo inverter cloud)
vision/                    the screenshot reader: Qwen3-VL-2B on CPU through llama.cpp, a Lambda container (weights in vision/models/, not in git)
backend/tests/             pytest
messages/                  labelled vendor replies for Laya (weights in messages/models/, not in git)
web/                       React + Vite PWA, deployed by Amplify Hosting from `main`
.github/workflows/ci.yml   pytest + sam validate on every push
```

## Commands
_Deploy commands are planned; confirm each one when that code exists._

- Setup: `uv venv --python 3.12 .venv && uv pip install -p .venv -r backend/requirements-dev.txt`
- Test: `.venv/bin/pytest`
- Generate the simulated neighbourhood (real Open-Meteo weather, a year through yesterday): `cd backend && ../.venv/bin/python -m dhool.sim`, then deploy and run the analysis for every house (`aws lambda invoke --function-name <AnalysisFunction> --payload '{}' out.json`). Do it again right before recording a demo, or the demo inverter's last reading falls behind the live weather.
- Deploy backend (confirmed): `sam validate && ./scripts/build.sh && sam deploy` (the script is `sam build` plus proxy handling for the container build)
- Score the verdict rules against the simulator: `cd backend && ../.venv/bin/python -m dhool.evaluate <seed>` (seed 0 is the development data; use other seeds for an honest number)
- Deploy settings are in `samconfig.toml`: stack `dhool-aws`, region `ap-south-1`.
- Live endpoints, pool IDs and demo account password: `.env` (gitignored, never commit)
- Screenshot reader weights (1.5 GB, pinned and hash-checked): `./scripts/fetch-model.sh` (`./scripts/build.sh` runs it first). Keep the weights out of `backend/`: SAM would pack them into the zip Lambdas.
- Measure the reader against saved demo screens (each carries its answer key): `LLAMA_SERVER=<path to llama-server> taskset -c 0,1 .venv/bin/python scripts/eval-vision.py <images>`. `taskset -c 0,1` matches the Lambda's two cores.
- Laya (vendor-reply sorter; its own environment, never in `.venv` or CI): `uv venv --python 3.12 .venv-laya && uv pip install -p .venv-laya --index-url https://download.pytorch.org/whl/cpu torch && uv pip install -p .venv-laya laya`. Score the shipped checkpoint: `.venv-laya/bin/python scripts/laya-tune.py eval`. Fine-tune and score (about 11 minutes, needs about 5 GB free): `.venv-laya/bin/python scripts/laya-tune.py train --out messages/models/vendor-replies-v<N>`. Data in `messages/vendor-replies.jsonl`, weights in `messages/models/` (not in git). Every fine-tuned model gets a new folder and a section in `checkpoints.md`; never overwrite an old one.
- `backend/requirements-analysis.txt` holds the heavy pvlib dependencies for the analysis container. Do not add a `backend/requirements.txt`: SAM would pack those into the small API Lambda zip.
- Run one function locally: `sam local invoke <FunctionName>`
- Frontend: `npm run dev` / `npm run build` in `web/`; `/#preview` shows every verdict state without signing in. Amplify Hosting builds `main` using `amplify.yml`.
- On the owner's phone over the Wi-Fi: `npm run build && npx vite preview --host 0.0.0.0 --port 4173` in `web/`, then open `http://<laptop Wi-Fi address>:4173` (the laptop's is in `ip -4 addr show wlp1s0`). Serves the built files only, never the dev server. A rebuild is picked up without a restart.
- Web test (the weather-to-sky rule): `npm test` in `web/`. Add `?sky=day|cloud|rain|storm|snow|sand|night` to the address to force a sky, and `&dark=1` for its night version.
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
- A model may read (screenshots), never decide. Whatever it reads is untrusted: the API drops values that cannot be true for the roof, and the homeowner confirms or corrects every number before it is saved. Ask the reader narrow questions; a broad "list everything" made it invent rows.
- Deployment-specific values (tariff, thresholds, default tilt and azimuth, region) live in `config.py`.
- Serverless and scale-to-zero only.
