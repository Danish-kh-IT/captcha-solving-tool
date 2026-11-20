import csv
import io
import os
import tempfile
import time
from collections import Counter
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from detector import detect_challenge, detect_provider
from solver import solve_image
from verify import public_provider_config, verify_token


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MAX_IMAGE_BYTES = 5 * 1024 * 1024

app = FastAPI(title="CAPTCHA Solving & Verification Tool")

# In-memory, process-local demo statistics. They reset when the server restarts.
STATS = {
    "total": 0,
    "success": 0,
    "failed": 0,
    "total_time_ms": 0,
    "by_workflow": {},
}


class VerifyRequest(BaseModel):
    provider: str
    token: str = Field(default="", max_length=8192)


class DetectRequest(BaseModel):
    html: str = ""


def record_attempt(workflow, success, time_ms):
    STATS["total"] += 1
    STATS["success" if success else "failed"] += 1
    STATS["total_time_ms"] += time_ms
    section = STATS["by_workflow"].setdefault(
        workflow, {"total": 0, "success": 0, "failed": 0, "total_time_ms": 0}
    )
    section["total"] += 1
    section["success" if success else "failed"] += 1
    section["total_time_ms"] += time_ms


def stats_snapshot():
    result = dict(STATS)
    result["by_workflow"] = {name: dict(values) for name, values in STATS["by_workflow"].items()}
    result["average_time_ms"] = round(STATS["total_time_ms"] / STATS["total"], 1) if STATS["total"] else 0
    for values in result["by_workflow"].values():
        values["average_time_ms"] = round(values["total_time_ms"] / values["total"], 1) if values["total"] else 0
        values["success_rate"] = round(values["success"] * 100 / values["total"], 1) if values["total"] else 0
    return result


@app.get("/")
def home():
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "captcha-solving-tool"}


@app.get("/api/providers")
def providers():
    """Return public widget sitekeys. Provider secret keys are never included."""
    return public_provider_config()


@app.post("/api/solve")
async def solve(file: UploadFile = File(...)):
    started = time.perf_counter()
    try:
        content = await file.read(MAX_IMAGE_BYTES + 1)
        if len(content) > MAX_IMAGE_BYTES:
            result = {
                "text": "", "confidence": 0.0, "method": "none", "time_ms": 0,
                "success": False, "error": "file_too_large",
                "message": "Image exceeds the 5 MB upload limit",
            }
        else:
            try:
                with Image.open(io.BytesIO(content)) as image:
                    image_format = image.format
                    image.verify()
                if image_format not in {"PNG", "JPEG"}:
                    raise ValueError("Only PNG and JPEG images are supported")
            except (UnidentifiedImageError, OSError, ValueError):
                result = {
                    "text": "", "confidence": 0.0, "method": "none", "time_ms": 0,
                    "success": False, "error": "invalid_image",
                    "message": "Upload a readable PNG or JPEG image",
                }
            else:
                suffix = ".jpg" if image_format == "JPEG" else ".png"
                tmp_path = None
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        tmp.write(content)
                        tmp_path = tmp.name
                    result = await run_in_threadpool(solve_image, tmp_path)
                    detection = detect_challenge("synthetic_text")
                    result["challenge_type"] = detection["type"]
                    result["challenge_recognition"] = detection
                finally:
                    if tmp_path and os.path.exists(tmp_path):
                        os.unlink(tmp_path)
    except Exception as exc:
        result = {
            "text": "", "confidence": 0.0, "method": "none", "time_ms": 0,
            "success": False, "error": "processing_failed",
            "message": type(exc).__name__,
        }

    elapsed = int((time.perf_counter() - started) * 1000)
    result["time_ms"] = elapsed
    result.setdefault("challenge_type", "synthetic_text")
    record_attempt("synthetic_text", result["success"], elapsed)
    return result


@app.post("/api/verify")
def verify(req: VerifyRequest):
    started = time.perf_counter()
    result = verify_token(req.provider, req.token)
    elapsed = int((time.perf_counter() - started) * 1000)
    result["time_ms"] = elapsed
    result["challenge_type"] = req.provider if req.provider in {"recaptcha", "hcaptcha", "turnstile"} else "unsupported"
    record_attempt("provider_verification", result["success"], elapsed)
    return result


@app.post("/api/detect")
def detect(req: DetectRequest):
    result = detect_provider(req.html)
    result["challenge"] = "provider_html"
    result["method"] = "static HTML marker detection"
    result["note"] = "Recognizes provider markers in supplied HTML; it does not inspect or contact websites."
    return result


@app.get("/api/csv-stats")
def csv_stats():
    """Summarize supplied CSV metadata without visiting any listed website."""
    path = DATA_DIR / "USA_Ecommerce_Platforms_200_Contact_Pages.csv"
    captcha_counts = Counter()
    platform_counts = Counter()
    with path.open(newline="", encoding="utf-8-sig") as source:
        for row in csv.DictReader(source):
            captcha_counts[row.get("Captcha", "Unknown")] += 1
            platform_counts[row.get("Platform", "Unknown")] += 1
    return {
        "total": sum(captcha_counts.values()),
        "captcha": dict(captcha_counts),
        "platform": dict(platform_counts),
        "scope": "CSV metadata summary only; no websites contacted",
    }


@app.post("/api/batch")
def batch():
    started = time.perf_counter()
    truth_path = DATA_DIR / "ground_truth.csv"
    image_dir = DATA_DIR / "synthetic"
    with truth_path.open(newline="", encoding="utf-8-sig") as source:
        truth = {row["filename"]: row["text"] for row in csv.DictReader(source)}

    results = []
    correct = 0
    processing_time_ms = 0
    for filename in sorted(truth):
        expected = truth[filename]
        result = solve_image(str(image_dir / filename))
        ok = result["text"] == expected
        correct += int(ok)
        processing_time_ms += result["time_ms"]
        record_attempt("synthetic_text_batch", ok, result["time_ms"])
        results.append({
            "filename": filename,
            "expected": expected,
            "predicted": result["text"],
            "correct": ok,
            "confidence": result["confidence"],
            "method": result["method"],
            "time_ms": result["time_ms"],
        })

    total = len(results)
    output_path = DATA_DIR / "results.csv"
    with output_path.open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(
            target,
            fieldnames=["filename", "expected", "predicted", "correct", "confidence", "method", "time_ms"],
        )
        writer.writeheader()
        writer.writerows(results)

    return {
        "challenge_type": "synthetic_text",
        "method": "Tesseract OCR + OpenCV",
        "total": total,
        "correct": correct,
        "failed": total - correct,
        "accuracy": round(correct * 100 / total, 1) if total else 0,
        "processing_time_ms": processing_time_ms,
        "wall_time_ms": int((time.perf_counter() - started) * 1000),
        "estimated_cost_per_challenge": 0,
        "results": results,
    }


@app.get("/api/stats")
def stats():
    return stats_snapshot()


app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
