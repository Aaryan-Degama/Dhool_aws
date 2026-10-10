# Dhool (धूल)

**Is your rooftop solar actually working?** Your inverter app shows a number. Dhool tells you what your roof should have made in that weather, and what to do when it falls short: wash the panels, call the vendor, wait, or nothing at all.

Built for [Environmental Hacks](https://www.wemakedevs.org/aws/env) (WeMakeDevs × AWS, Oct 2026), Waste and Energy track. The short submission text is in [`WRITEUP.md`](WRITEUP.md).

## Try it

- **Live app:** _to be added: the web app is not on a public address yet (Amplify Hosting is the last step)._
- **Until then:** `cd web && npm install && npm run dev`, then open `http://localhost:5173`. It talks to the deployed backend. Create an account, add a home, and in **Setup** connect the demo inverter: open the "demo inverter app" link, pick a home, and copy its API key.
- **Homes worth picking in the demo inverter:** `home-00` (a dead string: "Call your vendor"), `home-05` (healthy: "Your solar is working"), `home-30` (beside a dust source: "Wash the panels", when it has not rained lately).
- **Every screen without signing in:** `http://localhost:5173/#preview` (add `?lang=hi` for Hindi).
- **Trying the screenshot upload:** in the demo inverter app press "Save this screen as an image" and upload that file. A plain screenshot of the whole demo page, with its demo banner on top, is refused by the reader.
- **Language:** English and Hindi. The app starts in the phone's language; change it in Setup.

## The problem

- Over 50 lakh households now have rooftop solar under PM Surya Ghar, against 7.94 lakh installations in the ten years before it ([PIB, 4 Aug 2026](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2294208)). Most are small systems owned by families with no technical background.
- An inverter app shows the units made today. It does not show the units that roof *should* have made in today's weather, so a cloudy day, a dusty panel and a dead string all look the same: a low number.
- Dust is a real loss in North India. A Delhi field study found weekly cleaning gave 7.6% more energy than leaving it to the rain ([Sādhanā, Indian Academy of Sciences](https://www.ias.ac.in/article/fulltext/sadh/051/0032)); a rooftop study in India's composite climate measured 0.24% a day in the monsoon to 0.39% a day in spring ([Solar Energy, 2022](https://www.sciencedirect.com/science/article/abs/pii/S0038092X2200500X)).
- But not every drop is dust. In smog season less sunlight reaches every roof and washing does nothing; a failed string needs an electrician, not a bucket.
- The vendor owes five years of comprehensive maintenance under the scheme's own agreement ([MNRE guidelines, clause 12](https://cdnbbsr.s3waas.gov.in/s3716e1b8c6cd17b771da77391355749f3/uploads/2024/07/202407021768035484.pdf)). A household cannot claim what it cannot measure.

## What Dhool does

1. **Takes the readings three ways:** a link to the inverter's cloud by API key, a screenshot of the inverter app, or a typed number.
2. **Works out what the roof should have made** each day from its size, tilt and direction and that day's real weather (pvlib physics on Open-Meteo data), then learns that roof's own normal.
3. **Gives one verdict with the reason and the money:**
   - **Call your vendor:** a sunny day on which the roof made almost nothing, a sudden drop that stayed down and the neighbours did not share, or repeated one-day shutdowns. A WhatsApp message to the vendor is written with the figures.
   - **Wash the panels:** a slow slide since the last rain, and only when the wash pays: what the dust will cost before the next forecast rain or dust storm must be more than one wash costs that household. Both totals are shown.
   - **Wait:** rain is coming and will wash them for free; a dust storm is coming, so wash after it; the dust is not costing enough yet; or it is haze and washing will not help.
   - **Your solar is working.**
4. **Checks afterwards.** Tell Dhool you washed the panels or the vendor came, and it compares the week before with the clear days after: "needed +13%, came back +12%". A wash that changes nothing turns the advice into "call your vendor".
5. **Reads the vendor's reply.** Paste the WhatsApp reply (Hinglish, Hindi or English) and Dhool sorts it into coming, wants something first, refusing, or no clear answer, with the next step.
6. **One home, the whole family.** Each person has their own login; a six-letter code joins them to the home. The owner can remove a member or delete the home with all its data; anyone can leave, or delete their account.
7. **Tells you, without being opened.** With alerts switched on, the phone gets a notification when the nightly check turns to "call your vendor" or "wash", or when readings have stopped for three days. In the app, a card says so whenever the last reading is three or more days old.
8. **Your own rates.** What a wash costs you and what a unit of electricity is worth to you are both settable per home; every rupee figure uses them.

No model makes the verdict or produces a number. It is physics and plain rules, and every verdict carries its reason.

## Built on AWS

Everything is defined in one SAM template (`template.yaml`) and deployed with the **SAM CLI** to `ap-south-1`. It is all serverless. It is not all scale-to-zero: the two model functions are pinged every five minutes to stay loaded, because a fresh container takes two to five minutes to load its model. Everything else costs nothing when idle.

| Service | What it does here |
|---|---|
| **Lambda** (5 functions) | The API (zip); the analysis with pvlib (container image); the screenshot reader, Tesseract OCR first and Qwen3-VL-2B on CPU through llama.cpp when OCR finds nothing (container image); the vendor-reply reader, Laya on ONNX Runtime (container image); the demo inverter cloud (zip). |
| **API Gateway** (HTTP API) | Every route, with a JWT authorizer and request throttling. The caller's identity comes only from the token. |
| **Cognito** | Sign-up and sign-in by email. |
| **DynamoDB** | One on-demand table: houses, members, readings, daily verdicts, reported washes and visits, invite codes with a TTL. `Query` only, never `Scan`. |
| **S3** | Uploaded screenshots, reached only through signed URLs issued after an access check, deleted after 30 days. |
| **EventBridge** | The nightly analysis (it hands each home to its own run), and a five-minute ping that keeps the two model containers loaded. |
| **SQS, SNS** | A queue that catches any background analysis or screenshot run that failed, and a topic the alarms report to. |
| **ECR** | Holds the three container images. |
| **CloudWatch, X-Ray** | Logs kept 30 days, every access decision one JSON line with its request ID; alarms on function errors and on the failure queue; tracing. |
| **Systems Manager** (Parameter Store) | Holds the private key that signs phone notifications (Web Push). |
| **Amplify Hosting** | Builds and serves the web app from `main` (`amplify.yml`). _Not connected yet._ |

**Bedrock and Textract are not used.** Both were unavailable on this AWS account (Textract is blocked on the free plan; AWS Support declined the Bedrock request). That is why the two models are small open ones that we host ourselves on Lambda, and why explanations are fixed text in two languages instead of generated.

```
phone (React PWA)
   │  sign in ──────────────► Cognito
   │  every call (JWT) ─────► API Gateway ──► API Lambda ──► DynamoDB
   │                                             │  ├─► S3 (screenshots, signed URLs)
   │                                             │  ├─► screenshot reader Lambda (Qwen3-VL-2B)
   │                                             │  ├─► vendor-reply reader Lambda (Laya)
   │                                             │  └─► analysis Lambda (pvlib + rules) ──► Open-Meteo weather
   └─ demo inverter app ────► demo inverter Lambda (33 simulated homes)
EventBridge: nightly analysis, one run per home, then Web Push to the family's phones; keep-warm pings
```

## What is real and what is simulated

- **Real:** the weather (Open-Meteo, per home), the physics, the rules, the app, the accounts, the models.
- **Simulated:** the homes behind the demo inverter. There is no real inverter brand connected. Thirty-three homes in Delhi follow the real sun, cloud and rain of the past year; dust, washes, two dead strings, new shading and an inverter that trips are planted in code (`backend/dhool/sim.py`), never generated by a language model. Rain really cleans them, so whether a dusty home says "wash" today depends on the real weather.
- **The vendor replies used to train Laya** were written by an AI assistant, not collected from vendors.

## How well it works, as measured

| What | Result |
|---|---|
| Verdict rules, hidden test set, **alone and with weather error**: no neighbours to compare with, and the weather data wrong about each roof's sun by about 15% a day | **56%** of 3,870 checks. Faults caught: 6 of 433. This is the hardest case and the closest to a household typing its own numbers. |
| The same, with weather error and 29 neighbours | 48%. The "repeated shutdowns" rule mistakes the noise for trips. The simulated error is drawn separately for every roof, which is harsher than real weather, where neighbours share most of it. |
| The same, alone, no weather error | 83%. Faults caught: 66%. |
| The same, best case: 29 neighbours and weather data that matches the simulator's exactly | **84%**. Faults caught: 86%. |
| Development neighbourhoods (3 seeds, Delhi), same four cases | 56–57%, 45–49%, 87–89%, 94–95% (7 Oct; the year of weather they run on moves with the date) |
| Real rooftops (nine NREL PVDAQ homes, about ten years each, no labels) | No accuracy figure. On a single real roof with no neighbours, "wash" and "unclear" are still raised too often. |
| Screenshot reader, demo inverter screens | 93 of 93 printed values, none invented |
| Screenshot reader, store screenshots of three real inverter apps | **8 of 11 values, none invented, 1 read wrong** (OCR first, the vision model when OCR finds nothing). OCR answers in a second or two; a screen that falls to the model takes about 35 s. The homeowner confirms or corrects every number before it is saved. |
| Each reader on its own, same screenshots | Model alone: 6 of 11, 1 invented. OCR alone: 5 of 11, none invented. We chose to combine them after seeing these, so 8 of 11 is not a first-look number. |
| Vendor-reply reader (Laya v3.2) | 52 of 60 on the one test set written before training. No real vendor reply has been tried. |

The hidden test set is three other cities with every simulator setting redrawn and wider; the rules were never tuned on it. All of these are scores **in simulation**, where the homes' output is built from the same physics the rules use; the weather-error cases are our attempt to take that advantage away. The misses in the best case are mostly on the cautious side ("unclear, wait" for a dusty roof). `CONTEXT.md` has the full record, including what went wrong on the way.

## Known limits and what is next

- **Alone and with imperfect weather, the rules rarely catch a fault** (the first row above). Pooling readings from nearby Dhool homes, with consent, would give every household the neighbour comparison.
- **No real inverter brand is connected.** One real connector (SolarMAN or ShineMonitor, which most Indian home inverters report to) is the next thing to build.
- **The screenshot reader has only seen store screenshots of real apps**, never a homeowner's own, and a screen OCR cannot read still takes about 35 s.
- **Readings must be regular.** With fewer than four readings in any week Dhool says so and gives no verdict. A roof whose best weeks are far below its size is flagged, not judged: Dhool cannot tell a roof that was faulty from the start from a wrong size on the form.
- **Sign-up emails use Cognito's built-in sender**, limited to about 50 a day; a launch needs SES.
- **Sign-in sends the password over TLS** (not SRP), there is no two-step sign-in, and the demo inverter's key sits on the house record; a real brand's key belongs in Secrets Manager.
- **Weather comes from Open-Meteo's free service**, which is for non-commercial use and limited to 10,000 calls a day. A launch needs their paid plan or a weather cache.
- **One stack, deployed from a laptop.** A staging environment is configured (`sam deploy --config-env staging`) but not deployed, and CI validates and builds without deploying.
- Also to come: Gujarati and Marathi, a loss report the family can send the vendor, a weekly summary, alerts by WhatsApp or SMS.

## Run it

```bash
# backend tests
uv venv --python 3.12 .venv && uv pip install -p .venv -r backend/requirements-dev.txt
.venv/bin/pytest

# web app
cd web && npm install && npm test && npm run dev

# score the rules against the simulator (seeds 0-2 are development data)
cd backend && ../.venv/bin/python -m dhool.evaluate 0

# deploy the backend (needs Docker, the SAM CLI and AWS credentials)
sam validate && ./scripts/build.sh && sam deploy
```

`CLAUDE.md` lists every command, including regenerating the demo data and measuring the screenshot reader.

## Layout

```
template.yaml        the whole backend, for the SAM CLI
backend/dhool/       the logic, with no AWS calls: simulator, physics, verdict rules, reasons in two languages
backend/handlers/    thin Lambda handlers: api, analysis, demo inverter
vision/              the screenshot reader (Lambda container)
messages/            the vendor-reply reader (Lambda container) and its training data
web/                 the app: React and Vite, no UI library; hi.js holds the Hindi
```

## Credits and licenses

| Used | For | License |
|---|---|---|
| [pvlib](https://github.com/pvlib/pvlib-python) | Solar physics: expected output | BSD-3-Clause |
| [Open-Meteo](https://open-meteo.com/) | Weather, forecast and air quality | Data CC BY 4.0 |
| [Qwen3-VL-2B-Instruct](https://huggingface.co/Qwen) (GGUF) | Reading screenshots | Apache-2.0 |
| [llama.cpp](https://github.com/ggml-org/llama.cpp) | Running the screenshot reader on CPU | MIT |
| [Tesseract](https://github.com/tesseract-ocr/tesseract) 5.5.1 with the English `tessdata_fast` model, [Leptonica](https://github.com/DanBloomberg/leptonica) 1.85.0 | Reading screenshots: OCR, tried first | Apache-2.0, BSD-2-Clause |
| [Laya](https://huggingface.co/convaiinnovations/laya) (`convaiinnovations/laya`, fine-tuned by us) | Sorting vendor replies | Apache-2.0 |
| [ONNX Runtime](https://github.com/microsoft/onnxruntime), [PyTorch](https://pytorch.org/) | Running Laya | MIT, BSD-3-Clause |
| [NREL PVDAQ](https://data.openei.org/submissions/4568) | Real rooftop data for checking the rules | CC BY 4.0 |
| [pandas](https://pandas.pydata.org/), [NumPy](https://numpy.org/), [Pillow](https://python-pillow.github.io/) | Data handling, shrinking pictures | BSD-3-Clause, BSD-3-Clause, MIT-CMU |
| [React](https://react.dev/), [Vite](https://vite.dev/) | The web app | MIT |
| [Anek Devanagari](https://fonts.google.com/specimen/Anek+Devanagari) | The typeface, Hindi and English | SIL OFL 1.1 |
| [boto3](https://github.com/boto/boto3), [moto](https://github.com/getmoto/moto), [pytest](https://pytest.org/) | AWS calls and tests | Apache-2.0, Apache-2.0, MIT |
| [pywebpush](https://github.com/web-push-libs/pywebpush) | Sending alerts by Web Push | MPL-2.0 |
| [ESLint](https://eslint.org/), [eslint-plugin-react-hooks](https://react.dev/) | Linting the web app | MIT |

The app's design follows phone weather apps and a car-maker's app the team looked at for reference; no code or artwork was taken from them. The fine-tuned Laya weights are in this repo's `laya-models` release.

Built with Claude Code (Anthropic) as the AI coding tool throughout: code, tests, the Hindi text and these documents, directed by the team.

## License

Dhool's own code, documents and the vendor-reply examples in this repository are under the [Apache License 2.0](LICENSE). Everything listed above keeps its own license; the full list with versions is in [`CREDITS.md`](CREDITS.md).
