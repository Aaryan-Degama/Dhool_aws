# CONTEXT.md — Dhool

The project's current state. **Update this file whenever something changes** (a decision, the stack, a feature finished, a blocker). Newest log entry goes at the top.

## Hackathon

- **Event:** Environmental Hacks, event 02 of the Bharat Builds Tour (WeMakeDevs × AWS Builder Center)
- **Link:** https://www.wemakedevs.org/aws/env · Rules: https://www.wemakedevs.org/aws/rules
- **Dates:** Oct 8 – 11, 2026, online. Optional build day at DTU Delhi on Sat, Oct 10 (8 AM – 8 PM, sign up on https://luma.com/env)
- **Team:** 1 to 4 people. Open to university students in India, 18+, with verified student status on AWS Builder Center.
- **Goal:** Win. That means a track win (₹2,00,000 + $2,000 AWS credits), plus a top-10 fast-track Amazon interview for pre-final (2028) or final (2027) year students.

### Tracks (pick one)
1. **Air:** AQI, pollution exposure, stubble burning, indoor air, school safety on bad days
2. **Heat and Water:** heatwaves, floods, monsoon waterlogging, droughts, water tankers, leaks, groundwater
3. **Waste and Energy:** segregation, recycling, e-waste, informal recyclers, rooftop solar, EV nudges, public transport

### Hard rules (breaking these disqualifies you)
- **Written rule: no project work before Oct 8.** Learning, planning and practice are fine.
- Must use **at least one AWS open-source tool** (Strands Agents, PartyRock, Finch, SAM CLI, LocalStack, OpenSearch, Cedar, Firecracker, Corretto, EKS Distro/Anywhere) **or be deployed on AWS** (Lambda, API Gateway, S3, DynamoDB, Amplify, App Runner, EC2, SageMaker, Cognito, etc.). The demo video must show AWS in use.
- The event page's "Ship It" service list (SageMaker AI; EKS, ECS, Fargate; Lambda, API Gateway, Step Functions; EC2, Lightsail, App Runner, Amplify Hosting; S3, DynamoDB, RDS, Aurora; Cognito; CloudFront, Route 53, EventBridge, SQS, SNS, CloudWatch) is, in the page's words, "just a starting point … not a set of rules". Other AWS services are allowed. Bedrock and Textract are not on it; SageMaker AI is the only AI service listed. (Checked Oct 8.)
- Demo video must be on YouTube, public or unlisted, and open in a signed-out browser. AI coding tools must be listed in the write-up.
- Public repo. Credit any third-party code and make sure its license allows use. Libraries, public APIs and templates are allowed; only work done during the event is judged.

### Submission
- Public GitHub repo
- Demo video, **3 min max**, recorded (there is no live demo). Show what it does, who it's for, and where AWS fits.
- Short writeup: the problem, the build, where AWS fits
- Optional: a blog on AWS Builder Center linked in the submission. The top 5 blogs win AirPods.

### Judging criteria
1. **Idea and impact:** a real environmental problem, and what changes for the people living with it. A small problem solved well beats a big one solved vaguely.
2. **Built on AWS:** mandatory to win
3. **Design and usability:** someone outside the team knows how to use it
4. **Execution:** it works. One working feature beats five half-working ones.
5. **Demo video:** the only thing judges actually see

## Project: Dhool

- **Name:** Dhool (धूल, "dust"). Full design is in `DHOOL.md`.
- **Track:** Waste and Energy (rooftop solar).
- **Problem statement:** Rooftop-solar households see a daily kWh number and can't tell whether it is good, so losses from dust, faults or haze go unnoticed.
- **Target users:** PM Surya Ghar homeowners with small (1–3 kW) systems.
- **Core feature (the one that must work):** screenshot or inverter data in → expected output from pvlib + Open-Meteo weather → one verdict (CLEAN / INSPECT / WAIT) → verify recovery afterwards.
- **Stack:** pvlib physics baseline plus explainable rules (LightGBM and Laya optional), mock inverter API serving a simulated neighbourhood.
- **End product:** mobile-first React PWA on Amplify Hosting (the URL judges open), wrapped with Capacitor as an Android APK from the same code. The wrapper is the first thing to cut. The inverter API is called by the backend, so it does not affect the frontend choice.
- **AWS usage:** SAM CLI, Strands Agents SDK, Bedrock, Lambda, API Gateway (HTTP API), Cognito, S3, DynamoDB, EventBridge, Amplify Hosting, CloudWatch.
- **Backend:** AWS SAM, Python 3.12 Lambdas behind an HTTP API, one `template.yaml`. Analysis functions (pvlib) ship as a Lambda container image; plain API handlers stay zip. Region ap-south-1 if the Bedrock vision model is available there. Chosen because pvlib is Python and the same stack is what ships after the hackathon.
- **Auth and households:** Cognito user pool (email) with an HTTP API JWT authorizer. Data belongs to a **house**, not a person: every family member has their own login and sees the same screenshots, readings, inverter connection and verdicts. The first person creates the house (`owner`) and shares a 6-character invite code (DynamoDB TTL, 7 days); others join with it (`member`). Identity is the token `sub`; every handler calls one `authorize(sub, house_id, action)` and logs the decision as one JSON line. Owner-only: create invite, remove member, disconnect inverter. Judges get two pre-created demo accounts in one demo house.
- **DynamoDB (one table, on-demand, `Query` only):** `HOUSE#<id>` with `META`, `MEMBER#<sub>`, `READING#<date>`, `VERDICT#<date>`; `USER#<sub>` → `HOUSE#<id>` lookup; `INVITE#<code>` with `expiresAt` TTL. Screenshots in S3 under `houses/<id>/`, reached only through presigned URLs issued after `authorize()`.
- **Self-hosted models on CPU (replaces the Textract and templates-only plan, since Textract and Bedrock are both blocked on the Free plan):**
  - **Vision and text:** one small vision-language model does both jobs, reading the screenshot and writing explanations and vendor messages, so there is one deployment instead of two. First candidate: **Qwen3-VL-2B-Instruct** as GGUF through llama.cpp (official GGUF repo: Q4_K_M 1.11 GB, Q8_0 1.83 GB, plus an mmproj vision file). **Licence still to confirm** before use. Alternatives if it is too slow or inaccurate: InternVL3.5-2B, HunyuanOCR.
  - **Laya:** `convaiinnovations/laya` multilingual checkpoint (mmBERT, 322M, about 647 MB, Apache 2.0, `laya` Python SDK), on CPU, for sorting homeowner messages and reading vendor replies. Its own page reports 0.362 accuracy without fine-tuning on its benchmark, so measure it on our cases first and fine-tune only if needed.
  - **Hosting:** decided after a local CPU speed test. SageMaker Serverless Inference (on the event's list; CPU only, 6 GB memory, 60 s timeout, 4 MB payload, 10 GB image) if the model fits those limits, otherwise a Lambda container image called asynchronously (upload → job → result in DynamoDB → the app polls).
  - **Guardrails that stay:** the verdict and every number come from code, never from a model; the user confirms the kWh read from a screenshot; manual entry and fixed templates remain as fallbacks.
  - The Strands agent stays dropped (it needs a hosted model API). Say openly in the write-up that Bedrock and Textract were unavailable on the Free plan.
- **Dropped up front:** LightGBM, Step Functions, vendor view, neighbour map, Capacitor APK. Add back only if Day 3 ends early.
- **Day-by-day plan:** `DHOOL.md` 2.16, with these changes: Day 1 also stands up Cognito, the house and invite flow, CI and the Amplify-connected live URL; household sharing joins the never-cut list.

## Pre-event prep (allowed before Oct 8)
- Verify the Builder Center student profile; create the AWS account; request Bedrock model access in ap-south-1.
- Local machine (checked Oct 8): AWS CLI, Docker, Python 3.12, Node 22, git and gh are installed. SAM CLI 1.166.2 installed with pipx (`~/.local/bin/sam`). AWS credentials now work as IAM user `Dhool`. The CLI default region is `ap-south-1`. A throwaway practice stack (Lambda + HTTP API + Cognito user pool + DynamoDB table) deployed in ap-south-1 with `sam deploy`, answered HTTP 200, and was deleted, so the account restriction that blocks Bedrock does not affect these services. Not yet tested: Lambda container images (ECR), Textract, Amplify Hosting. SAM's managed deployment bucket (stack `aws-sam-cli-managed-default`) remains in ap-south-1 for reuse.
- Try the Textract console demo on two or three real inverter screenshots to confirm it reads the kWh value and that the account restriction does not cover Textract.
- Collect 10–15 real inverter screenshots; line up one before-and-after wash; ask the college for rooftop solar logs.
- Read one pvlib ModelChain example and the RdTools soiling docs.
- Find citable sources for the statistics in `DHOOL.md` 2.1.

## Done so far
- **Simulator and expected output:** `backend/dhool/expected.py` (Open-Meteo fetch + pvlib), `sim.py` (30 homes, planted dust, washes, 2 string faults, 1 shading onset, 1 home with inverter trips, shared haze, each day labelled with its true cause), `config.py`. 5 tests pass without network. A real-weather run (Delhi, 2025-09-25 to 2026-09-25) shows the fault home's ratio stepping from about 0.8–0.9 down to about 0.6 and staying there, and a dust-only home dipping to 0.85 in winter and returning to 0.94 in the monsoon. Not committed yet.

- **Sign-in and house API, deployed:** stack `dhool-aws` in ap-south-1 (`template.yaml`, `samconfig.toml`): Cognito user pool and client, HTTP API with a JWT authorizer, one DynamoDB table with TTL, one API Lambda (`backend/handlers/api.py`) with routes `GET /me`, `POST /houses`, `POST /join`, `GET /houses/{id}`, `POST /houses/{id}/invites`, `POST|GET /houses/{id}/readings`. `backend/dhool/authz.py` holds the role rules. 34 tests pass (authz matrix, family flow, stranger denied, identity in the body ignored, invite expiry, input validation). Verified live: father creates the house and a reading, mother joins by code and sees it, mother cannot invite, a stranger gets 403, no token gets 401, a 124 kWh typo on a 3 kW roof gets 400, and the deny lines appear in CloudWatch. API URL, pool IDs, demo house ID and the two demo accounts' password are in `.env` (gitignored). Not committed yet.
- **Model speed test (local, 2 CPU threads, Ollama `qwen3-vl:2b`):** it read a 1755×766 screenshot correctly into JSON, but took 114 s, 96 s of that encoding the image, with another install running at the same time. That is over SageMaker Serverless's 60 s limit, so plan on a Lambda container called asynchronously, and downscale images first. Text writing is **unverified**: Ollama's build spends its whole output on hidden reasoning and returns nothing, so test the official Instruct GGUF with llama.cpp. No real inverter screenshot has been tried.

- **Verdict rules, deployed:** `backend/dhool/verdict.py` returns CLEAN / INSPECT / WAIT / OK with a cause (fault, trips, haze, dust, unclear, no_data), confidence, a plain-language reason, loss in %, kWh/day and ₹/week, and the evidence (fault date, dust rate, days since cleaning, PM2.5). Order of rules: sudden drop that stays and the area did not share → INSPECT; repeated one-day dips → INSPECT; within 5% of the roof's own normal → OK; hazy air and the area fell together → WAIT; steady decline since last rain or wash → CLEAN, or WAIT if 5 mm of rain is forecast within 2 days; otherwise WAIT with low confidence. `evaluate.py` scores the rules against the simulator's known causes: **91% accuracy on seed 0 (the development data), 92% on seed 7 (never used for tuning)**, 1,290 checks each. INSPECT precision 1.00, recall 0.99–1.00. CLEAN precision 0.97–0.99, recall 0.76–0.80. Known weakness: WAIT precision about 0.5, because borderline dust cases fall back to WAIT or OK; the errors are on the cautious side.
- **Analysis pipeline and mock inverter API, deployed:** `AnalysisFunction` is a Lambda container image (pvlib) that runs when a reading is added or an inverter is connected, and nightly at 02:00 IST through an EventBridge schedule for every house (walks the `HOUSES` partition, no scan). It writes `VERDICT#<date>` items; `GET /houses/{id}/verdict` returns the latest with a 90-day chart series. `MockInverterFunction` serves the simulated neighbourhood at `/mock/plants`, `/mock/plants/{id}/daily` and `/mock/fleet/daily` (public, simulated data only, never exposes what was planted). `POST /houses/{id}/inverter` connects a house to a plant. `connectors.py` holds one function per source. 49 tests pass. Verified live: the demo house connected to `home-00` gets INSPECT, high confidence, "fell about 33% around 27 Mar", matching the planted fault (27 Mar, one of three strings); the other family member sees the same verdict; a manual nightly run reports `done: 1, failed: 0`. Analysis takes about 16 s cold.
- **Build behind the campus proxy:** use `./scripts/build.sh` instead of `sam build`; it passes the proxy to the container build without storing it in the image.

## Next
1. React PWA on Amplify Hosting: sign-in, create or join a house, add a reading, verdict card.
2. Model container: Qwen3-VL-2B Instruct through llama.cpp, then Laya.
3. CI (GitHub Actions) and the first commit and push.
4. Verification after a wash or vendor visit ("predicted +X%, observed +Y%"), and the hidden test set with varied simulator settings.

## Blockers
- **The AWS account is on the Free plan** (`accountPlanType: FREE`, $139.10 credits left, expires 2027-02-17; checked Oct 8). **Textract is blocked too:** `SubscriptionRequiredException` in ap-south-1 and us-east-1. Lambda, HTTP API, Cognito, DynamoDB work; SageMaker, ECR and Amplify answer API calls. Decided: stay on the Free plan and host our own models on CPU (see "Self-hosted models on CPU").
- **No real inverter screenshots yet.** The vision model cannot be judged for accuracy without them; needed before the model choice is final.
- **Bedrock inference is blocked on the AWS account** (found Oct 8). The playground in us-east-1 returns `ValidationException: Operation not allowed` for both Kimi K3 and Amazon Nova 2 Lite, as the IAM admin user and as root, so it is an account-level restriction and not IAM. Fix: AWS Support case (Account and billing) asking to enable Bedrock inference; also check the payment method and free-plan status in Billing. Decided Oct 8: not chasing this first; Bedrock work is Day 3, so nothing earlier depends on it. Bedrock has two jobs only: reading screenshots (vision) and writing explanations and vendor messages. Fallback if still blocked on Day 3: Amazon Textract plus a small parser for the kWh number (manual entry behind it), and fixed Hindi/English templates for the text. Laya cannot replace either job: it only picks a label from a fixed set.

## Open questions
- Team: assumed solo with Claude. If teammates join, one of them generates the hidden test set.
- Real data: screenshots, one before-and-after wash, campus solar logs
- Statistics in `DHOOL.md` 2.1 and prior art in 2.12 still need citable sources before the write-up

## Log
- **2026-10-08:** Backend stack deployed: Cognito, HTTP API, DynamoDB, shared houses with invite flow, simulated neighbourhood, pvlib analysis container, nightly EventBridge schedule, and verdict rules scoring 91–92%. 49 tests pass.
- **2026-10-08:** Initial setup: SAM project configured with Python 3.12 Lambdas and requirements.
