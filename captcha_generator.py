import csv
import os
import random
import string

from PIL import Image, ImageDraw, ImageFont

CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
OUT_DIR = "data/synthetic"
GROUND_TRUTH = "data/ground_truth.csv"


def get_font(size=42):
    for path in [
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def random_text(length=5):
    return "".join(random.choice(CHARS) for _ in range(length))


def make_one(text, out_path):
    # Wider canvas so characters don't overlap / get clipped
    width, height = 220, 70
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    font = get_font(36)   # Slightly smaller font → less overlap risk

    # Fixed spacing — enough room for each char
    char_width = 38
    x_start = (width - char_width * len(text)) // 2
    for i, ch in enumerate(text):
        x = x_start + i * char_width
        y = random.randint(8, 20)
        color = (
            random.randint(0, 100),
            random.randint(0, 100),
            random.randint(0, 100),
        )
        draw.text((x, y), ch, font=font, fill=color)

    # Fewer / lighter noise lines — still realistic but OCR-friendlier
    for _ in range(2):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill=(210, 210, 210), width=1)

    # Noise dots
    for _ in range(80):
        x = random.randint(0, width)
        y = random.randint(0, height)
        draw.point((x, y), fill=(180, 180, 180))

    img.save(out_path)


def generate_dataset(n=50):
    os.makedirs(OUT_DIR, exist_ok=True)
    rows = []
    for i in range(1, n + 1):
        text = random_text(5)
        name = f"captcha_{i:03d}.png"
        make_one(text, os.path.join(OUT_DIR, name))
        rows.append((name, text))

    with open(GROUND_TRUTH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["filename", "text"])
        writer.writerows(rows)

    print(f"Generated {n} images in {OUT_DIR}")
    print(f"Ground truth saved to {GROUND_TRUTH}")


if __name__ == "__main__":
    generate_dataset(50)
