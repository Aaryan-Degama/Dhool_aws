# Dhool — Is Your Solar Actually Working?

**Track:** Waste & Energy (rooftop solar)
**Event:** WeMakeDevs × AWS Environmental Hacks, Oct 8–11, 2026

> **This is the design as first written, kept for the record. It is not what was built.** Bedrock and Textract turned out to be unavailable on the account (AWS Support declined the Bedrock request on 10 Oct 2026), so there is no Strands agent and no Bedrock: screenshots are read by a self-hosted Qwen3-VL-2B and vendor replies by a fine-tuned Laya, both on Lambda, and every explanation is fixed text in English and Hindi. `README.md` describes the product as built; `CONTEXT.md` has the decisions and the log.

---

## Section 1 — Brief Description

India has put rooftop solar on more than 50 lakh households under PM Surya Ghar in about two years. Every one of those households sees a number in an inverter app every day ("12.4 kWh today") and has no idea whether that number is good.

Nobody tells them what their roof *should* have produced. So they can't tell when output is being lost to dust, to a hardware fault, or simply to a hazy week that no amount of cleaning can fix. Many also don't know that their vendor is contractually obligated to maintain the system free for five years.

**Dhool** closes that gap. A homeowner either uploads a screenshot of their inverter app or connects their inverter account. Dhool compares the day's generation against a physics-based expectation for that exact roof and that day's weather, and against similar rooftops nearby. It then returns one clear verdict:

- **CLEAN** — gradual dust buildup, no rain coming soon, worth washing now.
- **INSPECT** — the pattern looks like a fault (a sudden drop that doesn't recover), not dust. Call the vendor, with a drafted request citing the maintenance contract.
- **WAIT** — the whole area dropped together (haze), or rain is expected that will clean the panels for free. Don't waste water.

After cleaning, the homeowner sends new data and Dhool checks whether output recovered as expected. That gives them proof that the cleaning (or the vendor's visit) actually worked.

**The idea in one line:** *Don't climb onto the roof, and don't waste water, unless the data says it will pay off.*

**Built on AWS:** Strands Agents SDK, Lambda, API Gateway, S3, DynamoDB, EventBridge, Step Functions (optional), Amplify Hosting, CloudWatch, and Bedrock for screenshot reading and explanations.

---

## Section 2 — Detailed Design

### 2.1 The problem

**Scale.** MNRE reported in August 2026 that PM Surya Ghar had crossed 50.06 lakh beneficiary households, after the entire decade before the scheme produced 7.94 lakh rooftop installations. Most of these systems are small (1–3 kW) and owned by families with no technical background. (Use the wording "households", not "installations", since that is how the government reports it.)

**A number without a reference.** Inverter apps show daily kWh. They don't show *expected* kWh for that roof on that day's weather. A homeowner cannot tell a normal cloudy day from a 10% loss caused by dust or a dead string.

**Dust is a real, seasonal loss in North India.**
- A 300-day Delhi field study (from November 2022) found weekly cleaning produced 7.6% more energy than relying on natural cleaning by rain. Soiling was worst in winter and lowest in the monsoon.
- A separate study of North Indian rooftops measured soiling losses of about 0.24–0.39% per day depending on season.
- October, when this hackathon runs, is when the rain stops and dust and smog deposition start climbing.

*Sources, confirmed 8 Oct 2026: the household figures are from the PIB release of 4 Aug 2026 (PRID 2294208); the 7.6% figure is from "Determination of soiling loss in Delhi through experimental analysis" (Sādhanā, Indian Academy of Sciences); 0.24–0.39% a day is from "Assessment of soiling impacts and cleaning frequencies of a rooftop BAPV system in composite climates of India" (Solar Energy, 2022); five years of maintenance is clause 12 of the vendor agreement in the MNRE guidelines. The "300 days from November 2022" detail of the Delhi study was not confirmed and is not used in the README or write-up. Links are in `README.md`.*

**But not every drop is dust.** In smog season, output falls everywhere because less sunlight reaches the roof. Washing panels does nothing for that. Faults such as a failed string also look like "low generation" but need an electrician, not a bucket.

**An unused entitlement.** PM Surya Ghar vendors must provide five years of comprehensive maintenance. Households can't enforce what they can't measure.

### 2.2 The overlooked insight

The homeowner's real question isn't "are my panels dusty?" It is:

> "Is my system producing what it should — and if not, what should I do about it?"

Nobody asks this, because nobody knows the question has an answer. Once someone sees "your roof should have made 14.6 kWh today, you made 12.4," the need becomes obvious. This is a latent need: invisible before the product exists, obvious afterwards.

### 2.3 Target users

- **Primary:** a PM Surya Ghar household with a 1–5 kW system and an inverter app.
- **Secondary (optional):** the installer or vendor, who can see verified issues across their customers. Cut this if time is short.

### 2.4 No hardware needed

Dhool does not need solar panels, an inverter or sensors of its own. The homeowner already owns the hardware, and their inverter app already logs every day's output. Dhool only reads that data and adds free weather data.

The inverter app is the brand's phone app (SolarMan, Growatt ShinePhone, iSolarCloud, SolisCloud and others), usually set up by the installer on installation day. It shows today's generation and a bar chart of past days and months.

### 2.5 Two ways to get the data in

The user picks one of two options on the first screen:

1. **Upload screenshot.** The homeowner takes a phone screenshot of their inverter app. Bedrock vision extracts today's kWh and, if visible, the daily bar chart history, which gives weeks of data from the first upload. The user confirms the numbers. A manual "type your kWh" box is the fallback when reading fails.
   - Works with every brand from day one, needs no passwords, and needs no API approval.
2. **Connect inverter.** Dhool pulls readings directly from the inverter brand's cloud API, several times a day. Readings during the day (not just a daily total) let Dhool catch midday shutdowns and new shading.
   - **In the hackathon** this connects to Dhool's own **mock inverter API** (see 2.10), which serves the simulated neighbourhood. This is stated openly in the demo.
   - **Real integrations** need each brand's approval. For example, SolarMan's OpenAPI requires a support ticket explaining who you are and why, plus email agreement to its developer terms; it is free only for small personal use, and replies can take weeks. Never ask users for their app password, and don't use unofficial scraping tools.

**Source-agnostic design.** Every input source has its own small connector that converts its data into the same reading format. The analysis never cares where a reading came from:

```
screenshot upload  → Bedrock vision   ┐
mock inverter API  → mock connector   ├─→ standard readings → analysis
real brand API     → brand connector  ┘   (later: one new connector per brand)
```

### 2.6 How Dhool decides

**Step 1 — Expected output (physics, pvlib).**
pvlib calculates what this roof should have produced today. It is a physics calculation, not a trained model.

Inputs from the homeowner:
- location (map pin), system size in kW
- direction (azimuth) and tilt (optional, with sensible defaults)

Inputs from Open-Meteo (free, no API key), for that location and day:
- **sunlight reaching the ground** (irradiance), which already reflects clouds and rain, and partly haze and dust storms because they block sunlight
- **temperature**, because hot panels produce less
- **wind**, which cools the panels

Output: **expected kWh** for that day.

**What the physics cannot see:** dust sitting on the panels, a broken string, new shading. These are exactly what Dhool detects, because they show up as the gap between actual and expected output.

**How weather events fit in:**

| Event | What happens | Dhool's reading |
|---|---|---|
| Cloudy or rainy day | Lower sunlight, already in the expected value | Not flagged |
| Dust storm | Lowers sunlight during the storm (expected), then leaves dust on panels (not expected) | Lasting gap afterwards → likely CLEAN |
| Rain | Washes the panels; the physics ignores this | Rain in the forecast → WAIT, nature may clean for free |
| Smog or haze | Weather data may not capture it fully | Confirmed by PM2.5 data and neighbours → WAIT |

**Step 2 — Performance ratio.** Actual ÷ expected, every day. Example: 12.4 ÷ 14.6 = 0.85.

**Step 3 — The home's own normal.** No system ever hits exactly 100% of the pvlib number (wiring losses, panel quality and so on). Use the home's best recent days, usually just after rain or a wash, as its baseline (for example 0.95). Measure drops against that baseline, not against 1.0.

**Step 4 — Pattern over recent days (rules).**
- Slow, steady decline that resets after rain or washing ("sawtooth") → **dust**
- Sudden one-day drop that stays down → **fault**
- Neighbours dropped too, or PM2.5 is high → **haze**
- Back near the baseline → **all fine**
- *Only with intraday data (Connect inverter):* midday zero output → **inverter trip**; a dip at the same hour every day → **shading**

The dust rate is estimated with the approach of NREL's open-source RdTools stochastic rate-and-recovery method, with a simple piecewise-linear fit between cleaning events as the fallback.

**Step 5 — Decision, using the rain forecast.**
- Dust, no rain coming → **CLEAN**
- Dust, rain within a day or two → **WAIT** (rain will wash it)
- Haze → **WAIT** (washing won't help)
- Fault → **INSPECT**

The decision weighs the kWh recoverable before the next likely rain against the effort and water cost of washing. Every verdict shows a confidence level; when unsure, Dhool says so and defaults to WAIT.

**Step 6 — Show and act.** Verdict card with loss in kWh and ₹, confidence, and a "Why?" chart of actual against expected over time. Then a wash reminder, a drafted vendor message, or "check again on Tuesday."

**Step 7 — Verify.** After a wash or vendor visit, the ratio should return to the baseline: "Predicted +6.8%, observed +6.4%, cleaning verified." If it doesn't recover, the cause is probably not dust, which leads to INSPECT. Each verified clean also becomes labelled real-world data.

**Example message to the user:**

> "Your roof should have made 14.6 kWh today. It made 12.4, which is 15% less. This has been building for 18 days, and no rain is expected this week. **Verdict: CLEAN.** You're losing about ₹90 a week."

### 2.7 Rules first, ML optional

The core verdict runs on physics plus clear, explainable rules. This is a deliberate choice:
- Rules are fast to build and easy to debug in four days.
- Each rule can be explained in the video and shown on the "Why?" screen.
- The judging rewards "one feature that runs" over complexity.

**Optional (Day 2, only if rules already work):** a gradient-boosted classifier (LightGBM) on engineered features such as recent slope of the ratio, largest single-day drop, days since last rain, and share of neighbours that also dropped. Gradient boosting is the standard tool for numeric data like this, trains in seconds, and its feature importances can feed the "Why?" screen.

### 2.8 Where language models fit (and where they don't)

The numeric verdict is **never** made by a language model. Language models are weak at arithmetic over numeric series and cannot explain a physical cause. They are used only where language is genuinely the job:

**Strands agent on Bedrock** — tools: `read_screenshot`, `get_verdict`, `explain_evidence`, `draft_vendor_request`, `verify_recovery`. Writes explanations and vendor messages in Hindi and English.

**Laya (optional add-on, Day 3–4 only).** Laya is an open-weight (Apache 2.0) decision model from Convai Innovations. It does not generate text; it picks from a fixed set of labelled options and returns calibrated probabilities. The English checkpoint is ModernBERT-based (~421M parameters, 512 tokens); the multilingual checkpoint is mmBERT-based (~322M parameters, 1,024 tokens) and handles Hindi.

Where Laya fits:
1. **Sorting homeowner messages** into intents, such as *wash question*, *error code*, *billing*, *vendor complaint*, *general*, so Dhool routes each to the right tool and only calls the larger Bedrock model when a written answer is needed.
2. **Reading vendor replies** to INSPECT requests: *visit scheduled*, *asking for details*, *refused*, *no clear answer*. Dhool then sets a verify-after-visit reminder or helps the homeowner follow up.

Where Laya does **not** fit — the CLEAN / INSPECT / WAIT verdict:
- It is a text model; the verdict depends on numeric time series.
- The base model scores poorly out of the box and needs fine-tuning, and our only labelled data is our own simulation, so it would just learn the simulator.
- It returns a label and probability but no physical reason, while the "Why?" screen needs one.
- It is very new, and a 421M model in Lambda means a heavy container and slow cold starts.

**Jev** (TypeSafe AI) is the closed, hosted equivalent. If a decision model is used at all, prefer Laya: it is open, free and can run locally. Don't use both.

**If a judge asks "why Laya and not Bedrock?"** The honest answer: speed, low cost and probabilities we can set thresholds on. It is an optimisation, not a necessity. **It is the first thing to cut** if time is short.

### 2.9 Why AI is necessary

The core task is separating confounded causes from a noisy signal: weather, haze, dust, faults and shading all push the same number down. Doing this well needs:

- a physics baseline per roof, driven by real weather
- time-series pattern detection and anomaly classification
- spatial comparison across neighbours
- uncertainty estimates, so low-confidence verdicts are shown as such
- decision-making under uncertain rain forecasts
- vision, to turn screenshots from many different apps into clean data

A chatbot alone could not do any of this.

### 2.10 Data strategy

**Rule: never generate data with an LLM.** An LLM can write plausible numbers but cannot produce output that follows the real sun angle and actual cloud cover on those days. Judges who check will find the numbers don't match the weather.

| Data | Source | Purpose |
|---|---|---|
| Irradiance, temperature, wind, rain (history + forecast) | Open-Meteo | Expected output and the rain decision. Free, no API key. |
| PM2.5, PM10, dust, aerosol | Open-Meteo Air Quality API | Supports haze → WAIT |
| Simulated neighbourhood, ~30 homes, 12 months | pvlib + real Open-Meteo weather, with problems planted in code: dust at set rates, rain cleanings, 2 string faults, 1 shading onset, 1 home with inverter trips | Development, the mock inverter API, and measuring accuracy |
| **Hidden test set** | A second set of simulated homes with random problem dates, rates and sizes, generated by a teammate the detector builder never sees until the end | Honest precision and recall per verdict class |
| Real PV data | NREL PVDAQ; Kaggle "Solar Power Generation Data" (two Indian plants, 15-minute resolution) | Shows the method behaves sensibly on real, messy data |
| Real screenshots | Friends and relatives with rooftop solar; demo or visitor modes of inverter apps; layouts seen in installer/review videos (for format only) | Testing the screenshot reader on 10–15 app layouts |
| Real household proof (strongly recommended) | A friend's before-and-after wash (screenshots for a few days, wash, a few more); campus rooftop solar logs from the college facilities office, ideally with cleaning dates; a local installer's anonymised data | Biggest credibility boost |

Do not use screenshots people posted publicly without asking them first.

**Mock inverter API.** A small Lambda behind API Gateway that mimics the shape of a real inverter cloud API and serves the simulated neighbourhood:
- `GET /plants` — list homes
- `GET /plants/{id}/daily?from=...&to=...` — daily kWh
- `GET /plants/{id}/realtime` — current reading (enables intraday detection)

### 2.11 Environmental impact

- **Faults fixed sooner.** A dead string silently loses far more than dust, often a third or more of output, for months. Catching it within days is usually the biggest single gain. Lead the impact story with this.
- **Recovered clean energy.** An illustrative example: a 3 kW system producing about 12 kWh/day that recovers a 5% average soiling loss gains roughly 0.6 kWh/day, or about 220 kWh/year (about ₹1,300–1,750/year at ₹6–8/unit). This displaces grid electricity that is still largely coal-based.
- **Less wasted water.** Rooftop washing uses roughly 2 L per m² of panel. Skipping washes that wouldn't help (haze, rain coming) saves water directly. Modest per home; don't overclaim.
- **Scale.** The same logic applies across 50+ lakh households, and the neighbour comparison gets more accurate as more households join.

All figures should be clearly labelled as illustrative estimates in the demo.

### 2.12 Differentiation and honest prior art

Related work exists and should be acknowledged in the write-up:

- **SOLVIA (2026)** — a research system validated on a Delhi rooftop that predicts dust losses and recommends cleaning.
- **NuraVolt, Fracsun** — commercial soiling and O&M platforms for operators.
- **SIH 2026** — included a solar asset-performance problem statement.
- **PVOutput.org** — lets hobbyists compare their generation with nearby systems.

*Verify each of these before citing.*

**What's different about Dhool:**
- It is homeowner-first, not operator-first.
- It needs zero integration (screenshot input), with direct connection as an option.
- It gives action-oriented verdicts (CLEAN / INSPECT / WAIT) rather than dashboards.
- It knows when *not* to act: it is rain-aware and haze-aware, which saves water as well as time.
- It verifies after the fact.
- It is tied to the PM Surya Ghar maintenance entitlement.

Other teams in this track will likely build panel-photo dust detectors, savings calculators or generic solar chatbots. The WAIT verdict is the strongest point of difference; protect it.

**Pitch it as:** "the first time an Indian solar household can tell whether its system is working." Do not pitch it as "nobody has built this."

### 2.13 Architecture

```
Homeowner (React PWA)
   ├─ Upload screenshot ──► API Gateway ──► Lambda: ingest ──► Bedrock vision ─┐
   └─ Connect inverter ───► API Gateway ──► Lambda: connector ◄── Mock inverter API (Lambda)
                                                                              │
                                              standard readings ──► S3 (raw) + DynamoDB
        │
        ▼
EventBridge (nightly) ──► analysis pipeline (single Lambda; Step Functions if time allows)
   1. Fetch weather / irradiance / PM / rain forecast (Open-Meteo)
   2. Expected kWh per home (pvlib)                         → Lambda container image
   3. Ratio, baseline, neighbour comparison, dust rate      → Lambda container image
   4. Pattern rules (+ optional LightGBM)
   5. CLEAN / INSPECT / WAIT + confidence
   6. Write verdicts                                        → DynamoDB
        │
        ▼
Strands agent (Bedrock) — tools:
   read_screenshot · get_verdict · explain_evidence · draft_vendor_request · verify_recovery
   [optional] Laya: message intent + vendor-reply classification
        │
        ▼
React PWA on Amplify Hosting (input choice, verdict card, "Why?" chart, verification)
CloudWatch — pipeline metrics and logs
```

**Why each AWS piece is there:**
- **Strands Agents SDK:** an AWS open-source tool, which satisfies the eligibility rule even if deployment struggles. Used with typed tools, not free chat.
- **Lambda + API Gateway:** ingestion, the mock inverter API and the connectors.
- **EventBridge:** the nightly run. **Step Functions** is optional: its execution graph looks good in the video, but a single Lambda is enough.
- **Lambda container images:** pvlib, RdTools and LightGBM exceed zip size limits.
- **S3 + DynamoDB:** cheap storage for time series, plus fast per-home state.
- **Amplify Hosting:** a public URL for judges.
- **Avoid SNS SMS:** Indian SMS requires DLT registration. Use in-app notifications or WhatsApp deep links (wa.me) instead.

### 2.14 User flow

1. The homeowner opens Dhool and enters system size and location (direction and tilt optional, with defaults).
2. They choose **Upload screenshot** or **Connect inverter**. For a screenshot, Dhool reads it and the user confirms the extracted numbers.
3. A verdict card appears: **CLEAN / INSPECT / WAIT**, with estimated loss in kWh and ₹, a confidence level, and a one-line reason.
4. They tap "Why?" to see the evidence: actual vs expected over time, neighbours' performance, and the rain forecast.
5. They act: wash it themselves, send the drafted vendor request, or wait.
6. After acting, they send new data and Dhool verifies the recovery.
7. A monthly card summarises energy recovered, washes skipped, water saved and CO₂ avoided.

### 2.15 Three-minute demo storyboard

| Time | On screen | What the judge learns |
|---|---|---|
| 0:00–0:12 | Inverter app screenshot: "12.4 kWh today." Voice: "50 lakh Indian households went solar. Every one of them sees a number like this, and nobody knows if it's good." | Problem, user and gap in 12 seconds |
| 0:12–0:30 | Both input options shown. Upload a **real** screenshot; Dhool reads it. Card: "Expected 14.6 kWh. You made 12.4. You're losing about ₹90/week." | The "oh" moment, on real data |
| 0:30–0:55 | **INSPECT**: a home with a sudden step drop, flat since. "Likely a failed string. Your vendor maintains this free until 2029." Drafted Hindi/English request with evidence. | Biggest impact first: fault detection plus the entitlement |
| 0:55–1:20 | **WAIT**: output low, but all neighbours dropped together, PM high. "Haze, not dust. Washing won't help. Save the water." | It knows when *not* to act |
| 1:20–1:45 | **CLEAN**: sawtooth chart, 0.4%/day buildup, no rain for 8 days. | Real inference, not a guess |
| 1:45–2:10 | Verification: after a real before-and-after wash, "Predicted +6.8%, observed +6.4%. Cleaning verified." | Closed loop and accountability |
| 2:10–2:35 | Rigor: results on the hidden test set, method on real PVDAQ data, the mock inverter API and connector design, Lambda and DynamoDB in the console. Voice states the neighbourhood is simulated. | Execution, honesty and AWS proof |
| 2:35–3:00 | Impact card for the simulated neighbourhood: faults caught, kWh recovered, washes skipped, water saved. Closing: "Dhool tells every solar home whether it's working, and when a bucket won't help." | What changed, why it's different, where AWS fits |

**Suggested voice line for the data:** "The neighbourhood comes from a mock inverter API serving simulated homes with known problems, so we can measure accuracy. Real homeowners connect through a screenshot today, and through official inverter APIs as we get access."

### 2.16 Build plan (Oct 8–11)

** Oct 8 (learning and setup only, no project code):**
- Read the RdTools soiling docs and a pvlib ModelChain example.
- Set up the AWS account and verify the Builder Center student profile.
- Collect real screenshots from friends and relatives; line up one before-and-after wash.
- Ask the college facilities office for campus rooftop solar logs and cleaning dates.
- If someone you know has a SolarMan inverter, apply for a free OpenAPI key (applying is not project code).
- Sketch the verdict card.

**Day 1 (Thu):** Neighbourhood simulator (pvlib + real weather) with planted problems; the hidden test set generated separately by a teammate; expected-output and ratio calculation; mock inverter API. *Exit criterion:* one home clearly shows a sawtooth against its expected output and neighbours.

**Day 2 (Fri):** Baseline, pattern rules, dust-rate estimate, the CLEAN / INSPECT / WAIT decision with confidence. Package as Lambda container images; nightly EventBridge run writing to DynamoDB. Optional LightGBM. *Exit criterion:* the nightly run writes correct verdicts end to end on AWS.

**Day 3 (Sat):** Screenshot reading via Bedrock vision, the connector for the mock API, the Strands agent with its tools, the React PWA (input choice, verdict card, "Why?" chart, verification), deployment on Amplify. Optional: Laya message sorting.

**Day 4 (Sun):** Hidden-test-set evaluation, real-data check on PVDAQ/Kaggle, real screenshots and the before-and-after wash, polish. Record the video by midday, re-record once, write the README and write-up (listing AI coding tools used, as the rules require). Optional: Builder Center blog post. Confirm the submission deadline on the schedule page.

**Cut order if behind:** Capacitor APK → Laya → LightGBM → Step Functions → vendor view → neighbour map → intraday classes (inverter trip, shading).
**Never cut:** the verdict card, the WAIT case, verification, and the real-screenshot moment.

### 2.17 Risks and fallbacks

| Risk | Fallback |
|---|---|
| Soiling method unstable on short histories | Simulate 12 months. Fall back to piecewise-linear fits between detected cleaning steps. Read the app's bar-chart history to backfill real users. |
| Heavy Python dependencies break Lambda | Container images. Worst case, one small Fargate/EC2 task triggered by EventBridge. |
| Screenshot reading fails on some apps | Manual kWh entry. Show 2–3 app layouts working in the demo. |
| Daily totals can't show midday trips or shading | Detect those only with intraday data (Connect inverter); otherwise INSPECT covers sudden drops only. |
| No real neighbours at launch | Physics baseline carries the verdict; neighbours presented as improving with scale. Show confidence honestly and use WAIT when unsure. |
| "Your data is simulated" | Hidden test set, real PVDAQ/Kaggle validation, real screenshots and one real wash. Say it openly. |
| Detector tuned to our own simulated data | Hidden test set built by a different teammate with random parameters. |
| Real inverter API approval doesn't arrive | Mock API for the demo; real API shown only if the key arrives. |
| Laya integration or hosting problems | Cut it; Bedrock handles message sorting. |
| Haze vs dust separation challenged | Present it as an explanation under WAIT, not the headline claim. |
| Vendor-request wording seen as legal advice | Frame it as a polite request citing the contract, not a legal claim. |
| Bedrock access or quota issues | The verdict pipeline doesn't depend on the agent. Strands supports other model providers. |

### 2.18 Thirty-second pitch

"India just put solar on 50 lakh households. Every one of them sees a daily number in an app, and nobody knows whether it's good. Dhool reads that screenshot or connects to the inverter, works out from physics and real weather what the roof should have produced, and gives one verdict. INSPECT, because this looks like a fault your vendor must fix free. CLEAN, because dust is costing you money and no rain is coming. Or WAIT, because the whole area is hazy and washing won't help. Then it verifies the fix actually worked. It runs on Lambda, EventBridge and a Strands agent on AWS."

### 2.19 What to build first

The **neighbourhood simulator with planted problems**, built with pvlib and real weather. Every other component, the mock inverter API, the evaluation and the demo depend on it.

---

## Section 3 — After the Hackathon: Shipping for Real

Not needed for the submission, but worth a short paragraph in the write-up to show the path forward.

- **Pilot first (weeks 1–6).** 20–50 real homes through one installer or the college network. Tune thresholds on real data, especially how often INSPECT fires wrongly, since false alarms make vendors ignore Dhool.
- **Channel.** Most households live on WhatsApp, not PWAs. A WhatsApp bot on Meta's WhatsApp Business Platform needs business verification, approved message templates and per-conversation fees. Use WhatsApp or email for login, since SMS OTP needs DLT registration.
- **Less effort for users.** Weekly screenshots that read the history chart, then official API connections for common brands, ideally through installers' business accounts (one partnership, many homes).
- **Legal and privacy.** Location, photos and energy data are personal data under India's DPDP Act: clear consent, a privacy policy, data deletion, and disclaimers that verdicts are estimates and vendor messages aren't legal advice. Register an entity before taking payments. Get a lawyer's review before launch.
- **Production infrastructure.** Proper authentication, upload limits, AWS Budgets alerts (Bedrock is the main per-user cost), DynamoDB backups, error monitoring, hosting in the Mumbai region.
- **Business model.** Free and independent for homeowners. Installers are the likely payers: a dashboard of which homes actually need a visit cuts their five-year maintenance costs. Sell vendors only aggregated, opt-in data so homeowners keep trusting Dhool.
- **Distribution.** Installers at handover, resident welfare associations, existing solar-owner groups. Launch one city at a time so the neighbour comparison is useful early.
