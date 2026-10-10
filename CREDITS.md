# CREDITS.md — what Dhool is built on

Everything here is used under its own licence. Versions are the ones pinned or installed when this was
written (3 Oct 2026); the pywebpush, safetensors and ESLint lines were added on 10 Oct 2026, after a check
against the requirements files, the Dockerfiles and `web/package.json`. Dhool's own code is under
Apache-2.0 (`LICENSE`).

## Models and data

| What | Used for | Licence |
|---|---|---|
| [Qwen3-VL-2B-Instruct](https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct), GGUF build by the Qwen team ([Qwen/Qwen3-VL-2B-Instruct-GGUF](https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct-GGUF), 4-bit `Q4_K_M` and `mmproj-Q8_0`, revision `52d6c8f`) | Reading the numbers off inverter-app screenshots | Apache-2.0 |
| [Laya](https://huggingface.co/convaiinnovations/laya), multilingual checkpoint (Convai Innovations; mmBERT-base encoder, revision `55cf4c4`), fine-tuned by us on `messages/vendor-replies.jsonl` | Sorting a vendor's reply to an inspection request into four labels in its own Lambda, when the homeowner pastes the reply | Apache-2.0 |
| [Open-Meteo](https://open-meteo.com) weather, forecast and air-quality APIs | Sunlight, temperature, wind and rain for the physics; rain forecast; dust and PM2.5; the weather behind the app | Data under CC BY 4.0; free API for non-commercial use |
| [NREL PVDAQ public datasets](https://data.openei.org/submissions/4568): PVOutput.org residential systems, daily energy | Checking the method on nine real rooftops (`backend/dhool/realcheck.py`). Read at run time, not redistributed here | CC BY 4.0 |

## Code

| What | Used for | Licence |
|---|---|---|
| [llama.cpp](https://github.com/ggml-org/llama.cpp) (`llama-server`, release `b11351`, built from source) | Running the vision model on CPU inside Lambda | MIT |
| [Tesseract](https://github.com/tesseract-ocr/tesseract) 5.5.1, with the English model from [tessdata_fast](https://github.com/tesseract-ocr/tessdata_fast) 4.1.0, and [Leptonica](https://github.com/DanBloomberg/leptonica) 1.85.0, built from source in the reader's image | Reading the printed figures off a screenshot, tried before the vision model | Apache-2.0 (Tesseract and its model), BSD-2-Clause (Leptonica) |
| [Pillow](https://python-pillow.github.io) 12.3.0 | Shrinking screenshots for the vision model, and refusing oversized ones | MIT-CMU |
| [laya](https://github.com/NandhaKishorM/laya) 0.3.24 Python package, and its CPU fine-tuning script `notebooks/laya_finetune_typed_decisions_mps.py`, which `scripts/laya-tune.py` is adapted from | Running, fine-tuning and calibrating Laya | Apache-2.0 |
| Laya's `scripts/export_onnx.py` (commit `c829d5a`), whose int8 step `scripts/laya-tune.py` adapts; [ONNX](https://github.com/onnx/onnx) 1.23 and [ONNX Runtime](https://github.com/microsoft/onnxruntime) 1.30 | Exporting the fine-tuned Laya to ONNX, shrinking it to int8 and running it | Apache-2.0, Apache-2.0, MIT |
| PyTorch 2.14 (CPU), Transformers 5.18, safetensors 0.8 | Fine-tuning Laya on a laptop; imported by the `laya` package in the reply reader's image | BSD-3-Clause, Apache-2.0, Apache-2.0 |
| [pvlib](https://github.com/pvlib/pvlib-python) 0.16.1 | Solar position, sunlight on the panel, cell temperature, expected output | BSD-3-Clause |
| pandas 3.0.6, NumPy 2.5.3 (with SciPy and h5py pulled in by pvlib) | Time series for the physics and the verdict rules | BSD-3-Clause |
| boto3 | AWS calls from the Lambdas | Apache-2.0 |
| [pywebpush](https://github.com/web-push-libs/pywebpush) 2.5.0 (with py-vapid, http-ece and cryptography, which it pulls in) | Signing and sending alerts by Web Push from the nightly run. Used as installed, not modified | MPL-2.0 (pywebpush, py-vapid), MIT (http-ece), Apache-2.0 or BSD-3-Clause (cryptography) |
| React 19.3, React DOM 19.3 | The web app | MIT |
| Vite 8.3, @vitejs/plugin-react 6.1 | Building the web app | MIT |
| ESLint 10.12, @eslint/js 10.0, eslint-plugin-react-hooks 7.1 | Linting the web app | MIT |
| pytest 9.1, moto 5.2 | Tests (moto fakes DynamoDB and S3) | MIT, Apache-2.0 |
| AWS SAM CLI | Building and deploying the backend | Apache-2.0 |

## Fonts

| What | Licence |
|---|---|
| [Anek Devanagari](https://fonts.google.com/specimen/Anek+Devanagari) (Ek Type; copyright 2021 The Anek Project Authors). The Devanagari and Latin subsets as Google Fonts serves them (v17), unchanged, kept in `web/public/fonts/` with the licence text beside them (`OFL.txt`) and served by the app itself | SIL Open Font License 1.1 |

## AI tools

The hackathon rules ask for every AI coding tool to be listed.

| Tool | What it did |
|---|---|
| Claude Code (Anthropic), with Claude Opus models | Wrote most of the code, tests and documentation under the team's direction; ran the deploys and the checks in a browser and the Android emulator |
| Claude Code design skills (`frontend-design`, `ui-ux-pro-max`) | Design guidance for the web app's look |

Local checks also used Playwright (Apache-2.0) to drive Chrome; it is not part of the repository.
