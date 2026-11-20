import csv
import os
import sys
import time

import cv2
import pytesseract

# Windows par tesseract.exe ka full path set karo,
# taaki PATH par depend na rahe
TESSERACT_EXE = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(TESSERACT_EXE):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_EXE

ALLOWED = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CONFIG = "--psm 7 -c tessedit_char_whitelist=ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def clean_text(raw):
    text = "".join(ch for ch in raw.upper() if ch in ALLOWED)
    return text


def get_confidence(img):
    try:
        data = pytesseract.image_to_data(
            img, config=CONFIG, output_type=pytesseract.Output.DICT
        )
        confs = []
        for conf, txt in zip(data["conf"], data["text"]):
            if txt.strip() == "":
                continue
            try:
                c = float(conf)
            except ValueError:
                continue
            if c >= 0:
                confs.append(c)
        if not confs:
            return 0.0
        return sum(confs) / len(confs)
    except Exception:
        return 0.0


def preprocess_variants(path):
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(f"Image not found: {path}")
    big = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

    # Gaussian blur — noise reduce karo
    blurred = cv2.GaussianBlur(big, (3, 3), 0)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))

    variants = []
    # Variant 1: Otsu threshold on blurred
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants.append(("otsu", thresh))
    # Variant 2: Morphological open (noise dots remove)
    opened = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
    variants.append(("morph_open", opened))
    # Variant 3: plain grayscale, no threshold
    variants.append(("gray", big))
    # Variant 4: inverted Otsu
    _, inv = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    variants.append(("inv", inv))
    # Variant 5: adaptive threshold — uneven lighting handle karo
    adaptive = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )
    variants.append(("adaptive", adaptive))
    return variants


def solve_image(path):
    start = time.perf_counter()
    best = None

    try:
        variants = preprocess_variants(path)
    except (FileNotFoundError, cv2.error) as e:
        return {
            "text": "",
            "confidence": 0.0,
            "method": "none",
            "time_ms": 0,
            "success": False,
            "error": "unreadable_image",
            "message": str(e),
        }

    engine_errors = 0
    for method, img in variants:
        try:
            raw = pytesseract.image_to_string(img, config=CONFIG)
            text = clean_text(raw)
            conf = get_confidence(img)
            if not text:
                continue
            # Prefer a complete five-character answer first; confidence only
            # breaks ties. This prevents a partial result with confidence 0
            # from blocking a later complete candidate with confidence 0.
            score = (len(text) == 5, conf)
            if best is None or score > best[0]:
                best = (score, text, conf, method)
        except Exception:
            engine_errors += 1
            continue

    elapsed = int((time.perf_counter() - start) * 1000)
    if best is None:
        best_text, best_conf, best_method = "", 0.0, "none"
    else:
        _, best_text, best_conf, best_method = best

    return {
        "text": best_text,
        "confidence": round(float(best_conf), 1),
        "method": best_method,
        "time_ms": elapsed,
        "success": len(best_text) == 5,
        "challenge_type": "synthetic_text",
        "error": "ocr_failed" if best is None and engine_errors else "",
    }


def test_first_n(n=10):
    truth = {}
    with open("data/ground_truth.csv", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            truth[row["filename"]] = row["text"]

    correct = 0
    total = 0
    for filename in sorted(truth.keys())[:n]:
        expected = truth[filename]
        result = solve_image(os.path.join("data/synthetic", filename))
        ok = result["text"] == expected
        if ok:
            correct += 1
        total += 1
        mark = "OK " if ok else "FAIL"
        print(f"{mark} {filename} expected={expected} got={result['text']} conf={result['confidence']} method={result['method']} time={result['time_ms']}ms")

    print(f"Accuracy: {correct}/{total} = {correct * 100 // total if total else 0}%")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        result = solve_image(sys.argv[1])
        print(result)
    else:
        test_first_n(10)
