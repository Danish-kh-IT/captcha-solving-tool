# 3–5 minute assessment demo script

**Target duration: about 4 minutes 30 seconds.** Use the local app only. Keep the server running before recording, confirm the browser has internet for the official widgets, and do not regenerate the dataset just before the demo unless you also rerun batch evaluation.

## Before recording

1. Start the app at `http://127.0.0.1:8001` and open the page.
2. Make sure `data/synthetic/` contains the generated samples and the current `data/results.csv` corresponds to `data/ground_truth.csv`.
3. Select Turnstile once and confirm its official test widget loads. Select hCaptcha once and confirm its widget loads. Return to Turnstile for the success flow.
4. Close terminals or browser tabs containing secrets. The public test credentials are safe for the assessment, but do not show `.env` on screen.
5. Start a screen recording with system audio or voice-over. Do not record any real provider tokens in logs or terminal output.

## Timed walkthrough

| Time | On screen | Suggested narration |
|---|---|---|
| 0:00–0:20 | Dashboard overview and API status | “This is a locally hosted CAPTCHA assessment demo. It uses synthetic images and official provider test keys. It does not visit the company sites in the supplied CSV.” |
| 0:20–0:45 | Upload `data/synthetic/captcha_001.png`, run OCR | “The image is preprocessed with OpenCV and read by Tesseract. This returns an OCR candidate; exact correctness is measured separately against ground truth.” |
| 0:45–1:20 | Complete the Turnstile test widget and verify | “The browser acquires a token from Cloudflare’s test widget. The local backend sends it to the official Siteverify endpoint with the secret kept server-side.” Show the structured success response. |
| 1:20–1:50 | Select hCaptcha and use **Demo invalid token** | “This sends a fixed invalid value to hCaptcha’s official test verification endpoint. The app returns a structured rejection without logging the token.” Show `invalid_token`. |
| 1:50–2:10 | Load the provided CSV summary | “This is an aggregate of the supplied metadata. No company website or contact page is requested.” Show row count and CAPTCHA/platform counts. |
| 2:10–4:30 | Run batch evaluation; wait for completion | “The batch compares every OCR output with the generated labels. On this current 50-image dataset it measured 40 exact matches, or 80 percent, and took about 141 seconds. The generator is random, so the score may change for a new dataset.” Show the accuracy, counts, and a few mismatches. |
| 4:30–4:45 | Architecture/cost summary | “The OCR stack is local, provider tests use free public test keys, and the demonstrated workflow costs zero dollars. No paid CAPTCHA API is integrated.” |

## Recording note

Keep the full batch run visible or show its completed result after the run. If you trim pauses for the final cut, do not edit the accuracy value or imply the solver got every sample correct.
