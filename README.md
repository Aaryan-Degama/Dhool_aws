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
   - **Call your vendor:** a sudden drop that stayed down and the neighbours did not share, or repeated one-day shutdowns. A WhatsApp message to the vendor is written with the figures.
   - **Wash the panels:** a slow slide since the last rain, and only when the wash pays: what the dust will cost before the next forecast rain or dust storm must be more than one wash costs that household. Both totals are shown.
   - **Wait:** rain is coming and will wash them for free; a dust storm is coming, so wash after it; the dust is not costing enough yet; or it is haze and washing will not help.
   - **Your solar is working.**
4. **Checks afterwards.** Tell Dhool you washed the panels or the vendor came, and it compares the week before with the clear days after: "needed +13%, came back +12%". A wash that changes nothing turns the advice into "call your vendor".
5. **Reads the vendor's reply.** Paste the WhatsApp reply (Hinglish, Hindi or English) and Dhool sorts it into coming, wants something first, refusing, or no clear answer, with the next step.
6. **One home, the whole family.** Each person has their own login; a six-letter code joins them to the home.

No model makes the verdict or produces a number. It is physics and plain rules, and every verdict carries its reason.

## Built on AWS

Everything is defined in one SAM template (`template.yaml`) and deployed with the **SAM CLI** to `ap-south-1`. It is serverless and scales to zero.

| Service | What it does here |
|---|---|
| **Lambda** (5 functions) | The API (zip); the analysis with pvlib (container image); the screenshot reader, Qwen3-VL-2B on CPU through llama.cpp (container image); the vendor-reply reader, Laya on ONNX Runtime (container image); the demo inverter cloud (zip). |
| **API Gateway** (HTTP API) | Every route, with a JWT authorizer. The caller's identity comes only from the token. |
| **Cognito** | Sign-up and sign-in by email. |
| **DynamoDB** | One on-demand table: houses, members, readings, daily verdicts, reported washes and visits, invite codes with a TTL. `Query` only, never `Scan`. |
| **S3** | Uploaded screenshots, reached only through signed URLs issued after an access check, deleted after 30 days. |
| **EventBridge** | The nightly analysis of every home, and a five-minute ping that keeps the two model containers loaded. |
| **ECR** | Holds the three container images. |
| **CloudWatch** | Logs: every access decision is one JSON line. |
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
EventBridge: nightly analysis of every home; keep-warm pings
```

## What is real and what is simulated

- **Real:** the weather (Open-Meteo, per home), the physics, the rules, the app, the accounts, the models.
- **Simulated:** the homes behind the demo inverter. There is no real inverter brand connected. Thirty-three homes in Delhi follow the real sun, cloud and rain of the past year; dust, washes, two dead strings, new shading and an inverter that trips are planted in code (`backend/dhool/sim.py`), never generated by a language model. Rain really cleans them, so whether a dusty home says "wash" today depends on the real weather.
- **The vendor replies used to train Laya** were written by an AI assistant, not collected from vendors.

## How well it works, as measured

| What | Result |
|---|---|
| Verdict rules, development neighbourhoods (3 seeds, Delhi) | 93–95% of checks correct (7 Oct; the year of weather it runs on moves with the date, it was 94–96% on 3 Oct) |
| Verdict rules, hidden test set (Jaipur, Lucknow, Ahmedabad; every simulator setting redrawn and wider; never tuned on) | **84%** over 3,870 checks |
| Real rooftops (nine NREL PVDAQ homes, about ten years each, no labels) | No accuracy figure. On a single real roof with no neighbours, "wash" and "unclear" are still raised too often. |
| Screenshot reader, demo inverter screens | 93 of 93 printed values, none invented (saved screens; a screenshot of the whole demo page is refused) |
| Screenshot reader, store screenshots of three real inverter apps | 6 of 11 values, 1 invented. The homeowner confirms or corrects every number before it is saved. |
| Vendor-reply reader (Laya v3.2) | 52 of 60 on the one test set written before training. No real vendor reply has been tried. |

The misses on the hidden set are mostly on the cautious side ("unclear, wait" for a dusty roof). `CONTEXT.md` has the full record, including what went wrong on the way.

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
| [Laya](https://huggingface.co/convaiinnovations/laya) (`convaiinnovations/laya`, fine-tuned by us) | Sorting vendor replies | Apache-2.0 |
| [ONNX Runtime](https://github.com/microsoft/onnxruntime), [PyTorch](https://pytorch.org/) | Running Laya | MIT, BSD-3-Clause |
| [NREL PVDAQ](https://data.openei.org/submissions/4568) | Real rooftop data for checking the rules | CC BY 4.0 |
| [pandas](https://pandas.pydata.org/), [NumPy](https://numpy.org/), [Pillow](https://python-pillow.github.io/) | Data handling, shrinking pictures | BSD-3-Clause, BSD-3-Clause, MIT-CMU |
| [React](https://react.dev/), [Vite](https://vite.dev/) | The web app | MIT |
| [Anek Devanagari](https://fonts.google.com/specimen/Anek+Devanagari) | The typeface, Hindi and English | SIL OFL 1.1 |
| [boto3](https://github.com/boto/boto3), [moto](https://github.com/getmoto/moto), [pytest](https://pytest.org/) | AWS calls and tests | Apache-2.0, Apache-2.0, MIT |

The app's design follows phone weather apps and a car-maker's app the team looked at for reference; no code or artwork was taken from them. The fine-tuned Laya weights are in this repo's `laya-models` release.

Built with Claude Code (Anthropic) as the AI coding tool throughout: code, tests, the Hindi text and these documents, directed by the team.
