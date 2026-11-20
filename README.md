# CAPTCHA Solving & Verification Tool

Candidate assessment project for the Technology Brainz AI Automation / Full-Stack Developer role. It combines OCR for **locally generated synthetic text CAPTCHAs** with server-side verification of tokens from official provider test widgets.

**Scope:** This project does not browse or automate the 200 listed company websites, submit contact forms, or collect tokens from third-party sites. The supplied CSV is used for metadata recognition/summary only.

## Features

- Generate 50 synthetic five-character CAPTCHA images and ground-truth labels.
- Preprocess PNG/JPEG images with OpenCV and recognize text with Tesseract 5.4.0.
- Recognize provider markers in user-supplied static HTML.
- Acquire test tokens from Google reCAPTCHA v2, hCaptcha, or Cloudflare Turnstile widgets and validate them server-side.
- Return structured results for valid, invalid, missing, expired/reused, timeout, and unsupported cases.
- Run exact-match batch evaluation and write `data/results.csv`.
- Review session attempt and processing-time summaries in the UI.
- Summarize the supplied 200-row CSV without contacting listed websites.

## Measured results

Results below are from the current local dataset/run; the generator creates random challenges, so accuracy may differ after regeneration.

| Workflow | Observed result |
|---|---|
| Synthetic OCR, original PSM 8 baseline | 30/50 exact matches (60%) |
| Synthetic OCR, current PSM 7 solver | 40/50 exact matches (80%) |
| Current 50-image OCR batch duration | Approximately 141 seconds on the development machine |
| Provider detection examples | 7/7 expected marker/unsupported examples, per local assessment notes |
| Turnstile public test flow | Success; test hostname `example.com` |
| hCaptcha invalid-token flow | Structured `invalid_token` response |
| Google reCAPTCHA connectivity failure | `verification_unavailable` on a `ConnectTimeout`; this is a network failure, not a provider rejection |
| Missing token / unsupported provider | `missing_token` / `unsupported_provider` |
| Supplied CSV | 200 rows; reCAPTCHA 103, none 46, invisible reCAPTCHA 30, Turnstile 15, hCaptcha 6 |

The single-image solver's `success` means it returned a five-character candidate. It does **not** prove correctness. Only batch evaluation can calculate correctness against ground truth. Current confidence scores can be zero, so do not present confidence as calibrated probability.

## Requirements

- Windows or Linux/macOS
- Python 3.11
- Tesseract OCR 5.4.0 installed separately from Python packages
- Browser internet access for loading the official provider test widgets and reaching provider verification endpoints

On Windows, the solver checks `C:\Program Files\Tesseract-OCR\tesseract.exe` and sets pytesseract to that path when present. If Tesseract is installed elsewhere, update `TESSERACT_EXE` in `solver.py` or add the installation directory to `PATH`.

## Setup and run (Windows PowerShell)

From the project directory:

```powershell
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

If `data/synthetic/` is empty or absent, generate the local data once:

```powershell
python captcha_generator.py
```

Start the local server. Port 8001 avoids common Windows permission conflicts on port 8000:

```powershell
uvicorn app:app --reload --host 127.0.0.1 --port 8001
```

Open <http://127.0.0.1:8001>. If port 8001 is unavailable, choose another permitted local port and use that same port in the browser. Keep the terminal running while using the app.

The generator replaces the current synthetic images and `ground_truth.csv`. Run batch evaluation after regeneration so `data/results.csv` matches that new dataset.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/` | Local web UI |
| `GET` | `/api/health` | Health status |
| `GET` | `/api/providers` | Public widget sitekeys only (never provider secrets) |
| `POST` | `/api/solve` | Solve a PNG/JPEG image, maximum 5 MB |
| `POST` | `/api/verify` | Verify `{ "provider": "turnstile", "token": "..." }` |
| `POST` | `/api/detect` | Detect provider markers in supplied static HTML |
| `GET` | `/api/csv-stats` | Aggregate metadata from the supplied CSV only |
| `POST` | `/api/batch` | Evaluate current synthetic data and refresh `data/results.csv` |
| `GET` | `/api/stats` | In-memory session totals and workflow breakdown |

Example OCR request:

```powershell
curl.exe -X POST http://127.0.0.1:8001/api/solve `
  -F "file=@data/synthetic/captcha_001.png"
```

## Configuration and secrets

`.env.example` includes **public provider test secrets** for local assessment use. The corresponding sitekeys are public identifiers sent to the browser through `/api/providers`. Real provider secrets must stay in an untracked `.env`; never commit `.env` or use test keys to protect a production service.

## Project layout

```text
app.py                 FastAPI routes, upload validation, batch/stats reporting
solver.py              OpenCV preprocessing and Tesseract OCR
detector.py            Provider marker and challenge-type recognition
verify.py              Provider test configuration and server-side validation
captcha_generator.py   Synthetic challenge and ground-truth generator
static/index.html      Responsive local assessment UI
data/ground_truth.csv  Expected labels for generated samples
data/USA_Ecommerce_Platforms_200_Contact_Pages.csv  Supplied recognition data
```

Generated images and batch output are ignored by Git. A reviewer can create the synthetic set by running the generator as described above.

## Safety and limitations

- Test only generated synthetic challenges, locally hosted test pages, candidate-owned sites, or official provider test environments.
- Do not automate the listed live websites, submit their contact forms, or harvest tokens.
- Provider detection uses markers in supplied HTML; it does not fetch URLs or inspect dynamically rendered pages.
- Session counters are held in memory and reset when Uvicorn restarts.
- OCR confidence is not calibrated, and the current solver still makes character and omission errors.
