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

**On branch `hardening` (10 Oct 2026): not merged, not pushed, not deployed.** A hardening pass; the Log entry of 2026-10-10 in `CONTEXT.md` lists it. Until it is merged and deployed, what is live is the list below.

**Complete and live**
- Sign-in and family sharing: one house, several logins, joined by a 6-letter code.
- Verdicts (wash, call the vendor, wait, all good) with a reason, money lost, a chart and a 7-day forecast; re-run nightly (one run per home) and when data arrives. A sunny day at almost nothing is "call the vendor" at once (outage).
- Verdict rules, scored four ways on the hidden test set (never tune against it): with neighbours 84%, alone 83%, with 15% weather error 48%, alone with weather error 56% and almost no faults caught. Development seeds: 94–95% in the best case. Quote the hard case first.
- Alerts by Web Push from the nightly run (call the vendor, wash, readings stopped). Built and deployed; not yet seen arriving on a real phone, which needs the public URL.
- Per-home tariff and wash cost; delete a home, remove a member, leave, delete account; home picker; back button; offline shell; a card when readings are 3 or more days old.
- Operations: API throttling and a join lockout, a failure queue, alarms (no email subscribed yet), tracing, 30-day logs.
- Wash decision by cost: wash only when the saving beats the wash cost (settable per home), both totals in the reason.
- Wash and vendor-visit check, and a log of advice and actions. A wash or visit reported for today shows its card at once.
- Readings in three ways: inverter link by API key, screenshot upload, typed number.
- Demo inverter cloud: 33 simulated homes on real weather (faults `home-00` to `home-03`, healthy ones, dusty `home-30` to `home-32`).
- Screenshot reader: OCR first (Tesseract, about a second), Qwen3-VL-2B when OCR finds nothing (`vision/reader.py`). 93/93 on demo screens; 8 of 11 on real-app store screenshots, none invented, 1 wrong (each alone: model 6, OCR 5).
- Vendor-reply reader: Laya v3.2 (int8, ONNX Runtime) on Lambda, about 250 ms a reply. Every Laya version is in the GitHub release `laya-models`.
- The app: roof scene, weather skies, frosted cards, four tabs.
- English and Hindi across the whole app, the reasons included. Starts in the phone's language; changed in Setup.
- `README.md` and `WRITEUP.md` (the live URL and the video link are still blank in both).

**Pending, needs the owner**
1. Public URL: connect the repo to Amplify Hosting in Singapore (ap-southeast-1), monorepo root `web`. Dhool is not on Amplify; the only Amplify app on the account is Slate's (Mumbai). When the link exists: put it in `README.md` and `WRITEUP.md`, check it signed out with the showcase accounts, and tighten the two `AllowOrigins` in `template.yaml` to it.
2. Read the Hindi through once, on the review page (https://claude.ai/artifact/JByxFCkVnqs5HfEXQST4L1, private to the owner): it was written by Claude, checked twice by Claude, and no native speaker has read it. About 45 lines added on 7 Oct (alerts, family, deletion, tariff, outage) are in `hi.js`, `reasons.py` and `notify.py` and not on that page.
3. Real inverter screenshots (a today screen and a daily list) and 20 to 30 real vendor replies: none exist yet. Commands, below, say what to do when they arrive.
4. 
5. Merge and deploy branch `hardening`. (It carries the license, Apache-2.0.)
6. Whether the showcase logins are printed in the public README for judges or only given in the submission form.
7. An address for alarms: deploy once with `sam deploy --parameter-overrides AlarmEmail=<address> VapidSubject=mailto:<address>` and click the confirmation email.

**Pending, to build or check**
1. The 3-minute video.
2. Right before recording, and every two days through judging: refresh the demo data (Commands, below) and confirm the wash showcase account still says "wash". Rain of 5 mm turns the dusty homes back to "all good", and data 3 days old shows a "no new reading" card on every demo home.
3. With the public URL: switch alerts on from a real phone and see one push arrive.
4. Check live: whether a phone screenshot of the whole demo inverter *page* now reads (OCR read it in the trial; the model alone refused it).

**Checked on 7 Oct** (scripted Chrome at phone width against the live backend, English and Hindi; and the Android emulator): the three cases (fault, wash, all good), the vendor-reply box, wash and visit report with undo, the wash-cost field, the log, the language choice, screenshot upload in Hindi, and every form with the phone keyboard up (the field stays visible; the nav bar stays under the keyboard). No sideways scrolling or clipped text in either language. Not seen with the keyboard: the family-code box on "Add your home" (it is the same field component).

**Costs:** charges were effectively zero on 3 Oct. Two model Lambdas are pinged every 5 minutes to stay loaded, and about 14 GB of container images sit in ECR. The `Dhool-laya` worktree can be removed; its v1 and v2 model folders are also in the release.

## Project layout
_Code lives in the `Dhool_aws` repo._

```
template.yaml              SAM: user pool, HTTP API + JWT authorizer, table, bucket, functions, nightly schedule
backend/dhool/             pure logic, no AWS calls (sim, expected, verdict, reasons, analyse, notify, connectors, authz, config; evaluate and realcheck score the rules)
backend/handlers/          thin I/O wrappers: api, analysis (pvlib container, nightly), mock_inverter (demo inverter cloud)
vision/                    the screenshot reader: reader.py tries ocr_reader.py (Tesseract) and falls back to screenshot_reader.py (Qwen3-VL-2B on CPU through llama.cpp); a Lambda container (weights in vision/models/, not in git)
backend/tests/             pytest
messages/                  the vendor-reply reader: Laya fine-tuned on vendor-replies.jsonl, a Lambda container (weights in messages/models/, not in git)
web/                       React + Vite PWA, deployed by Amplify Hosting from `main` (App.jsx tabs and routes; account.jsx sign-in, add home, family, deletion; readings.jsx the three ways in; words.js headlines; check.jsx wash and visit check; plan.jsx costs and log; store.js what the phone keeps; public/sw.js offline shell and push; i18n.js and hi.js the Hindi)
.github/workflows/ci.yml   template lint, the analysis image build, pytest, and the web test, lint and build on every push
```

## Commands
_All confirmed unless a line says otherwise._

- Setup: `uv venv --python 3.12 .venv && uv pip install -p .venv -r backend/requirements-dev.txt`
- Test: `.venv/bin/pytest` (fails under 82% coverage; the number is in `pyproject.toml`: raise it as coverage rises, never lower it)
- Lint, format, types: `.venv/bin/ruff check .`, `.venv/bin/ruff format .`, `.venv/bin/mypy` (config in `pyproject.toml`; no blanket ignores: a `noqa` or `type: ignore` names its rule and gives its reason on the line). Hooks: `.venv/bin/pre-commit install` once.
- Browser test: `npm run e2e` in `web/` (Playwright, Chromium; `npx playwright install chromium-headless-shell` once). It runs `/#preview` on the dev server and the built app under the headers in `customHttp.yml`.
- Generate the simulated neighbourhood (real Open-Meteo weather, a year through yesterday): `cd backend && ../.venv/bin/python -m dhool.sim`, then deploy and run the analysis for every house (`aws lambda invoke --function-name <AnalysisFunction> --payload '{}' out.json`). Do it again right before recording a demo, or the demo inverter's last reading falls behind the live weather.
- Deploy backend (confirmed): `sam validate && ./scripts/build.sh && sam deploy` (the script is `sam build` plus proxy handling for the container build)
- Score the verdict rules against the simulator: `cd backend && ../.venv/bin/python -m dhool.evaluate <seed>` (seeds 0–2 are development data). It prints four cases: with neighbours, alone, with weather error, and both. The hidden test set is `... -m dhool.evaluate hidden`: never tune against it; after any rule change rerun it and report the number as it comes.
- Real-rooftop check (nine NREL PVDAQ homes, downloads to `~/.cache/dhool` on first run): `cd backend && ../.venv/bin/python -m dhool.realcheck`. Run it after any rule change: the simulator is far cleaner than real data.
- Deploy settings are in `samconfig.toml`: stack `dhool-aws`, region `ap-south-1` (a `staging` environment is defined and not deployed). Template parameters: `WebOrigin` (CORS, `*` until the Amplify URL exists), `AlarmEmail`, `VapidParam`, `VapidSubject`.
- After regenerating the demo data and deploying, the demo homes need no relinking; a home linked before 7 Oct keeps its old 4-decimal location until its owner links it again.
- Failed background runs: `aws sqs get-queue-attributes --queue-url <FailureQueueUrl output> --attribute-names ApproximateNumberOfMessages`. Logs are in `/dhool/dhool/{api,analysis,vision,messages,mock-inverter}`.
- Web Push key: the private half is the SSM SecureString `/dhool/vapid-private-key`, the public half is `VAPID_PUBLIC_KEY` in `web/src/config.js`. They are a pair: replacing one without the other breaks every phone's subscription.
- Live endpoints, pool IDs, the demo accounts and the three showcase accounts (`SHOWCASE_USERS`, one home each: wash on `home-30`, call the vendor on `home-01`, all good on `home-05`): `.env` (gitignored, never commit)
- Screenshot reader weights (1.5 GB, pinned and hash-checked): `./scripts/fetch-model.sh` (`./scripts/build.sh` runs it first). Keep the weights out of `backend/`: SAM would pack them into the zip Lambdas.
- Measure the reader (accuracy, time, memory) in its Lambda image, as the Lambda sees it: `docker run --rm --cpuset-cpus=0,1 --memory=3008m --memory-swap=3008m -v "$PWD/scripts:/scripts:ro" -v "$PWD/vision:/vision:ro" -v <image dir>:/imgs:ro -e MODEL_DIR=/opt/models -e LLAMA_SERVER=/opt/llama-server --entrypoint python3 visionfunction:latest /scripts/eval-vision.py --both /imgs/<image> ...` (`--both` is what is deployed; `--ocr` or no switch scores one reader alone). Demo screens carry their answer key; for a real screenshot write `<image>.json` beside it (see the script's header). Run sets one at a time: parallel runs slow each other.
- The vendor-reply reader's image needs `messages/models/vendor-replies-v3.2-int8/` (335 MB, from `scripts/laya-tune.py quantize` on v3 or a copy of the folder; checksum in `checkpoints.md`), readable by everyone: `chmod -R a+rX messages/models`. Lambda does not run as the file's owner, and a local `docker run` (root) will not show the problem.
- When real inverter screenshots arrive: keep them outside the repo (they show a real home), write `<image>.json` beside each with the numbers printed on it, and run the reader measurement above on them. Report the count as it comes; do not tune the questions on the same screenshots you then quote.
- When real vendor replies arrive: add each to `messages/vendor-replies.jsonl` with `"split": "real"` (names, phone numbers and addresses taken out), then `scripts/laya-tune.py eval messages/models/vendor-replies-v3`: the `real` rows are scored on their own and are never trained on.
- Laya (vendor-reply sorter; its own environment, never in `.venv` or CI): `uv venv --python 3.12 .venv-laya && uv pip install -p .venv-laya --index-url https://download.pytorch.org/whl/cpu torch && uv pip install -p .venv-laya "laya[onnx]"`. Score the shipped checkpoint: `.venv-laya/bin/python scripts/laya-tune.py eval`. Fine-tune and score (about 45 minutes on the laptop CPU for 1,000 replies, needs about 5 GB free): `.venv-laya/bin/python scripts/laya-tune.py train --out messages/models/vendor-replies-v<N>`. Data in `messages/vendor-replies.jsonl`, weights in `messages/models/` (not in git). Every fine-tuned model gets a new folder and a section in `checkpoints.md`; never overwrite an old one.
- `backend/requirements-analysis.txt` holds the heavy pvlib dependencies for the analysis container. Do not add a `backend/requirements.txt`: SAM would pack those into the small API Lambda zip.
- Run one function locally: `sam local invoke <FunctionName>`
- Frontend: `npm run dev` / `npm run build` in `web/`; `/#preview` shows every verdict state without signing in. Amplify Hosting builds `main` using `amplify.yml`.
- On the owner's phone over the Wi-Fi: `npm run build && npx vite preview --host 0.0.0.0 --port 4173` in `web/`, then open `http://<laptop Wi-Fi address>:4173` (the laptop's is in `ip -4 addr`, under its Wi-Fi interface). Serves the built files only, never the dev server. A rebuild is picked up without a restart.
- Web tests (the weather-to-sky rule; every line of the app has its Hindi; the stale-reading day count): `npm test` in `web/`; `npm run lint` for ESLint. Add `?sky=day|cloud|rain|storm|snow|sand|night` to the address to force a sky, `&dark=1` for its night version, and `?lang=hi|en` to force a language.
- Design decisions live in `DESIGN.md`; read it before changing the UI.
- Android emulator (AVD `dhool`, Android 15; it needs its window, `-no-window` crashes on this machine): `~/Android/Sdk/emulator/emulator -avd dhool -http-proxy "$HTTPS_PROXY"`, then `adb reverse tcp:5173 tcp:5173` and open `http://localhost:5173` in the emulator's Chrome while `npm run dev` runs. To script that Chrome: `adb forward tcp:9222 localabstract:chrome_devtools_remote`.

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
- **Keys and shared pieces.** Every table key comes from `backend/dhool/keys.py`; the table, the log line, metrics and AWS clients from `backend/handlers/common.py` (`client()` is made once per container, with retries). Do not write a key string or make a boto3 client in a handler.
- **Weather goes through `expected.get_json`.** The analysis Lambda puts its DynamoDB cache there (`handlers/weather_cache.py`: fresh 3 hours, used up to a day old when Open-Meteo is down). `backend/dhool` itself still makes no AWS call.
- **An alert is measured against `last_notified` on the house**, written only after a push went out and removed when the advice goes back to all good or wait.
- **A write that follows slow work checks the home still exists** (the verdict's transaction, the screenshot result's condition), or a deleted home gets a piece back.
- **A new API route goes in `ROUTES` and in `ApiFunction`'s Events**; a test fails if the two differ. A new DynamoDB operation goes in `TableSystemErrorsAlarm`; a test fails on that too.
- **The web app's headers are `customHttp.yml`.** A new host the page talks to goes in its `connect-src`, or the browser blocks it; `npm run e2e` runs the built app under those headers.
- **Identity is server-side.** The caller is the JWT `sub` from the authorizer. Never read a user, house, role or ownership from the request body or query string.
- **Every handler calls `authorize(sub, house_id, action)`** before touching house data, and logs the decision as one JSON line. (`get_house` reads the member list once and decides from it with `_decide`, which logs the same line.)
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
- **Two languages, fixed text.** Every line the app shows goes through `t("English")` (`web/src/i18n.js`) and has its Hindi in `web/src/hi.js`; `npm test` fails on a line without one. A verdict's reason is built on the server in both languages from one set of figures (`backend/dhool/reasons.py`, returned as `reason` and `reason_hi`): add the Hindi with the English, never a number in one and not the other. The Hindi is looked up by the English line itself, so each line has one spelling: `npm test` fails when two lines (in `t()` calls, `hi.js` or `ARRIVES`) differ only by capital letters or spacing. No model translates. "Dhool" stays in Latin letters in Hindi (धूल is also the word for dust).
- **Owner-only:** creating an invite, linking an inverter, removing a member, deleting the home. A member may leave. The path's `sub` in `DELETE .../members/{sub}` says who is removed; who is asking is still only the token.
- **Push endpoints are untrusted URLs.** The server posts to them, so `api.py` accepts only the known push hosts. Alert text is fixed, in both languages, in `backend/dhool/notify.py` (the one place outside `words.js` and `reasons.py` that words a verdict).
- **A roof's normal is learned from the roof, with no floor from its size.** Real healthy roofs run as low as 0.67 of the physics; a floor made them faults. Under 0.6 sets `low_normal`, a note and not a verdict.
- **A verdict never holds NaN.** Too few readings to learn a normal is WAIT (`sparse`), and the verdict's `json.dumps` calls pass `allow_nan=False`.
- **Scores are quoted hard case first** (alone, with weather error), and always as "in simulation".
- A wash or visit dated after the last reading (today, when readings end yesterday) still gets its check card (`waiting`) and, for a wash, the "just cleaned" OK: do not filter such reports out of `verdict()`.
- **Two sessions, one stack.** When another session is working in this checkout, work in your own `git worktree` on a branch, push the branch, and let the session that owns the checkout merge and deploy: a deploy from a second copy overwrites what the first has live.
