def detect_provider(html):
    text = (html or "").lower()

    if "cf-turnstile" in text or "turnstile" in text:
        return {
            "provider": "Cloudflare Turnstile",
            "type": "turnstile",
            "recognized": True,
            "supported": True,
            "support_mode": "official_token_verification",
        }
    if "h-captcha" in text or "hcaptcha" in text:
        return {
            "provider": "hCaptcha",
            "type": "hcaptcha",
            "recognized": True,
            "supported": True,
            "support_mode": "official_token_verification",
        }
    if "g-recaptcha" in text or "recaptcha" in text:
        if "invisible" in text:
            return {
                "provider": "Google reCAPTCHA (invisible)",
                "type": "recaptcha_invisible",
                "recognized": True,
                "supported": True,
                "support_mode": "official_token_verification",
            }
        return {
            "provider": "Google reCAPTCHA",
            "type": "recaptcha",
            "recognized": True,
            "supported": True,
            "support_mode": "official_token_verification",
        }
    return {
        "provider": "None / Unknown",
        "type": "none",
        "recognized": False,
        "supported": False,
        "support_mode": "none",
    }


def detect_challenge(kind, html=""):
    if kind == "synthetic_text":
        return {
            "challenge": "synthetic_text",
            "provider": "Custom synthetic CAPTCHA",
            "type": "synthetic_text",
            "supported": True,
            "method": "Tesseract OCR + OpenCV",
        }
    if kind == "provider_html":
        result = detect_provider(html)
        result["challenge"] = "provider_html"
        result["method"] = "Official test-key verification"
        return result
    return {
        "challenge": kind,
        "provider": "Unknown",
        "type": "unsupported",
        "supported": False,
        "method": "none",
    }


if __name__ == "__main__":
    tests = [
        ("reCAPTCHA", '<div class="g-recaptcha" data-sitekey="test"></div>'),
        ("invisible", '<div class="g-recaptcha invisible" data-sitekey="test"></div>'),
        ("hCaptcha", '<div class="h-captcha" data-sitekey="test"></div>'),
        ("Turnstile", '<div class="cf-turnstile" data-sitekey="test"></div>'),
        ("none", '<form><input name="email"></form>'),
    ]
    for name, html in tests:
        print(name, "->", detect_provider(html))

    print("synthetic ->", detect_challenge("synthetic_text"))
    print("audio ->", detect_challenge("audio_captcha"))
