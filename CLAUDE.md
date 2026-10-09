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

## Status (7 Oct 2026; keep this current, details and numbers are in `CONTEXT.md`)

All branches are merged into `main` and deployed (stack `dhool-aws`, ap-south-1).

**Complete and live**
- Sign-in and family sharing: one house, several logins, joined by a 6-letter code.
- Verdicts (wash, call the vendor, wait, all good) with a reason, money lost, a chart and a 7-day forecast; re-run nightly and when data arrives.
- Verdict rules reworked: 93–95% on development data (7 Oct; it runs on the last year of weather, so it moves with the date), 84% on the hidden test set (never tune against it).
- Wash decision by cost: wash only when the saving beats the wash cost (settable per home), both totals in the reason.
- Wash and vendor-visit check, and a log of advice and actions. A wash or visit reported for today shows its card at once.
- Readings in three ways: inverter link by API key, screenshot upload, typed number.
- Demo inverter cloud: 33 simulated homes on real weather (faults `home-00` to `home-03`, healthy ones, dusty `home-30` to `home-32`).
- Screenshot reader: Qwen3-VL-2B on Lambda. 93/93 on demo screens; only 6 of 11 on real-app store screenshots.
- Vendor-reply reader: Laya v3.2 (int8, ONNX Runtime) on Lambda, about 250 ms a reply. Every Laya version is in the GitHub release `laya-models`.
- The app: roof scene, weather skies, frosted cards, four tabs.
- English and Hindi across the whole app, the reasons included. Starts in the phone's language; changed in Setup.
- `README.md` and `WRITEUP.md` (the live URL and the video link are still blank in both).

**Pending, needs the owner**
1. Public URL: connect the repo to Amplify Hosting in a region other than Mumbai. Dhool is not on Amplify; the only Amplify app on the account is Slate's. Then put the URL in `README.md` and `WRITEUP.md`.
2. Read the Hindi through once (`web/src/hi.js`, `backend/dhool/reasons.py`): it was written by Claude and no native speaker has checked it.
3. Real inverter screenshots (a today screen and a daily list).
4. Emails for the showcase accounts, and which case each shows (wash, call the vendor, all good).
5. 
6. Twenty to thirty real vendor replies, to score Laya honestly.
7. A license for the repo (there is no `LICENSE` file).

**Pending, to build or check**
1. The 3-minute video.
2. Right before recording: refresh the demo data (Commands, below) and confirm a dusty home still says "wash". On 7 Oct all three did (`home-30` to `home-32`, 10 dry days since the last rain); rain of 5 mm would turn them back to "all good".
3. The phone keyboard over the forms: the emulator check on 7 Oct could not bring the keyboard up from a script, so this was not seen.
4. Screenshot upload against the live backend in Hindi (the flow itself was verified on 3 Oct, in English).

**Checked on 7 Oct** (scripted Chrome at phone width against the live backend, English and Hindi; and the Android emulator): the three cases (fault, wash, all good), the vendor-reply box, wash and visit report with undo, the wash-cost field, the log, the language choice. No sideways scrolling or clipped text in either language.

**Costs:** charges were effectively zero on 3 Oct. Two model Lambdas are pinged every 5 minutes to stay loaded, and about 14 GB of container images sit in ECR. The `Dhool-laya` worktree can be removed; its v1 and v2 model folders are also in the release.

## Project layout
_Code lives in the `Dhool_aws` repo._

```
template.yaml              SAM: user pool, HTTP API + JWT authorizer, table, bucket, functions, nightly schedule
backend/dhool/             pure logic, no AWS calls (sim, expected, verdict, reasons, analyse, connectors, authz, config; evaluate and realcheck score the rules)
backend/handlers/          thin I/O wrappers: api, analysis (pvlib container, nightly), mock_inverter (demo inverter cloud)
vision/                    the screenshot reader: Qwen3-VL-2B on CPU through llama.cpp, a Lambda container (weights in vision/models/, not in git)
backend/tests/             pytest
messages/                  the vendor-reply reader: Laya fine-tuned on vendor-replies.jsonl, a Lambda container (weights in messages/models/, not in git)
web/                       React + Vite PWA, deployed by Amplify Hosting from `main` (App.jsx; words.js headlines; check.jsx wash and visit check; plan.jsx wash cost and log; i18n.js and hi.js the Hindi)
.github/workflows/ci.yml   pytest, the web test and the web build on every push
```

## Commands
_All confirmed unless a line says otherwise._

- Setup: `uv venv --python 3.12 .venv && uv pip install -p .venv -r backend/requirements-dev.txt`
- Test: `.venv/bin/pytest`
- Generate the simulated neighbourhood (real Open-Meteo weather, a year through yesterday): `cd backend && ../.venv/bin/python -m dhool.sim`, then deploy and run the analysis for every house (`aws lambda invoke --function-name <AnalysisFunction> --payload '{}' out.json`). Do it again right before recording a demo, or the demo inverter's last reading falls behind the live weather.
- Deploy backend (confirmed): `sam validate && ./scripts/build.sh && sam deploy` (the script is `sam build` plus proxy handling for the container build)
- Score the verdict rules against the simulator: `cd backend && ../.venv/bin/python -m dhool.evaluate <seed>` (seeds 0–2 are development data). The hidden test set is `... -m dhool.evaluate hidden`: never tune against it; after any rule change rerun it and report the number as it comes.
- Real-rooftop check (nine NREL PVDAQ homes, downloads to `~/.cache/dhool` on first run): `cd backend && ../.venv/bin/python -m dhool.realcheck`. Run it after any rule change: the simulator is far cleaner than real data.
- Deploy settings are in `samconfig.toml`: stack `dhool-aws`, region `ap-south-1`.
- Live endpoints, pool IDs and demo account password: `.env` (gitignored, never commit)
- Screenshot reader weights (1.5 GB, pinned and hash-checked): `./scripts/fetch-model.sh` (`./scripts/build.sh` runs it first). Keep the weights out of `backend/`: SAM would pack them into the zip Lambdas.
- Measure the reader (accuracy, time, memory) in its Lambda image, as the Lambda sees it: `docker run --rm --cpuset-cpus=0,1 --memory=3008m --memory-swap=3008m -v "$PWD/scripts:/scripts:ro" -v "$PWD/vision:/vision:ro" -v <image dir>:/imgs:ro -e MODEL_DIR=/opt/models -e LLAMA_SERVER=/opt/llama-server --entrypoint python3 visionfunction:latest /scripts/eval-vision.py /imgs/<image> ...`. Demo screens carry their answer key; for a real screenshot write `<image>.json` beside it (see the script's header). Run sets one at a time: parallel runs slow each other.
- The vendor-reply reader's image needs `messages/models/vendor-replies-v3.2-int8/` (335 MB, from `scripts/laya-tune.py quantize` on v3 or a copy of the folder; checksum in `checkpoints.md`), readable by everyone: `chmod -R a+rX messages/models`. Lambda does not run as the file's owner, and a local `docker run` (root) will not show the problem.
- Laya (vendor-reply sorter; its own environment, never in `.venv` or CI): `uv venv --python 3.12 .venv-laya && uv pip install -p .venv-laya --index-url https://download.pytorch.org/whl/cpu torch && uv pip install -p .venv-laya "laya[onnx]"`. Score the shipped checkpoint: `.venv-laya/bin/python scripts/laya-tune.py eval`. Fine-tune and score (about 45 minutes on the laptop CPU for 1,000 replies, needs about 5 GB free): `.venv-laya/bin/python scripts/laya-tune.py train --out messages/models/vendor-replies-v<N>`. Data in `messages/vendor-replies.jsonl`, weights in `messages/models/` (not in git). Every fine-tuned model gets a new folder and a section in `checkpoints.md`; never overwrite an old one.
- `backend/requirements-analysis.txt` holds the heavy pvlib dependencies for the analysis container. Do not add a `backend/requirements.txt`: SAM would pack those into the small API Lambda zip.
- Run one function locally: `sam local invoke <FunctionName>`
- Frontend: `npm run dev` / `npm run build` in `web/`; `/#preview` shows every verdict state without signing in. Amplify Hosting builds `main` using `amplify.yml`.
- On the owner's phone over the Wi-Fi: `npm run build && npx vite preview --host 0.0.0.0 --port 4173` in `web/`, then open `http://<laptop Wi-Fi address>:4173` (the laptop's is in `ip -4 addr show wlp1s0`). Serves the built files only, never the dev server. A rebuild is picked up without a restart.
- Web tests (the weather-to-sky rule; every line of the app has its Hindi): `npm test` in `web/`. Add `?sky=day|cloud|rain|storm|snow|sand|night` to the address to force a sky, `&dark=1` for its night version, and `?lang=hi|en` to force a language.
- Design decisions live in `DESIGN.md`; read it before changing the UI.
- Android emulator (AVD `dhool`, Android 15): `~/Android/Sdk/emulator/emulator -avd dhool -http-proxy "$HTTPS_PROXY"`, then `adb reverse tcp:5173 tcp:5173` and open `http://localhost:5173` in the emulator's Chrome while `npm run dev` runs. To script that Chrome: `adb forward tcp:9222 localabstract:chrome_devtools_remote`.

## Bedrock is out (7 Oct 2026)
_AWS Support rejected the request to enable Bedrock inference on the owner's account. Do not plan or build anything on Bedrock._

What that settles:
1. **Screenshot reading** stays on the self-hosted Qwen3-VL-2B reader (6 of 11 on real-app screens). The safety net is the confirm-and-correct screen and typed entry, not a better model.
2. **Explanations and the vendor message** stay fixed templates (`verdict.py` reasons, `vendorMessage` in `App.jsx`). Hindi is hand-written strings.
3. **The Strands agent** (`DHOOL.md` 2.9) is dropped for good. SAM CLI is the AWS open-source tool the rules ask for.
4. **Vendor replies** are sorted by Laya, already live.

Say in the write-up that Bedrock and Textract were unavailable on this account and that the models are self-hosted on Lambda for that reason. `DHOOL.md` still describes the original Bedrock design; it is the plan as first written, not what is built.

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
- **Washing is a money decision, in one place.** `wash_plan()` in `verdict.py` says CLEAN only when what the dust costs before the next forecast rain or dust storm is more than one wash costs (the house's `wash_cost_rs`, ₹50 until the owner sets it). Do not add a second wash rule elsewhere; the reason text must show the rupees on both sides.
- **Changing a verdict rule:** find the mechanism first (which estimate is wrong and why), not a threshold that scores better. Then run, in order: the tests, `dhool.evaluate` on seeds 0–2, `dhool.realcheck`, and `dhool.evaluate hidden` once. Report the hidden number as it comes in `CONTEXT.md`; never tune against it or keep the better of two runs.
- **Thresholds that separate a fault from noise scale with the roof's own data** (how much its weekly level wanders). A fixed percentage tuned on the simulator raised INSPECT in 57% of months on real, healthy roofs.
- The answer key in `evaluate.py` applies the same wash plan to the true dust, so the score measures detection, not the policy.
- What the homeowner reports (a wash, a vendor visit) is an `ACTION#<date>` item, treated by the rules as a known cleaning or repair and checked before against after. The log (`GET /houses/{id}/history`) is built from the stored daily verdicts and these items; nothing else writes to it.
- Verdict headlines are in `web/src/words.js` only; the card and the log both read them from there.
- **Two languages, fixed text.** Every line the app shows goes through `t("English")` (`web/src/i18n.js`) and has its Hindi in `web/src/hi.js`; `npm test` fails on a line without one. A verdict's reason is built on the server in both languages from one set of figures (`backend/dhool/reasons.py`, returned as `reason` and `reason_hi`): add the Hindi with the English, never a number in one and not the other. No model translates. "Dhool" stays in Latin letters in Hindi (धूल is also the word for dust).
- A wash or visit dated after the last reading (today, when readings end yesterday) still gets its check card (`waiting`) and, for a wash, the "just cleaned" OK: do not filter such reports out of `verdict()`.
- **Two sessions, one stack.** When another session is working in this checkout, work in your own `git worktree` on a branch, push the branch, and let the session that owns the checkout merge and deploy: a deploy from a second copy overwrites what the first has live.
