import os
from pathlib import Path

import requests
from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parent / ".env")

# These are official public test credentials. Keep real secrets in .env.
CONFIG = {
    "recaptcha": {
        "name": "Google reCAPTCHA v2",
        "url": "https://www.google.com/recaptcha/api/siteverify",
        "sitekey": "6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI",
        "secret": os.getenv(
            "RECAPTCHA_SECRET",
            "6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe",
        ),
    },
    "hcaptcha": {
        "name": "hCaptcha",
        "url": "https://api.hcaptcha.com/siteverify",
        "sitekey": "10000000-ffff-ffff-ffff-000000000001",
        "secret": os.getenv(
            "HCAPTCHA_SECRET",
            "0x0000000000000000000000000000000000000000",
        ),
    },
    "turnstile": {
        "name": "Cloudflare Turnstile",
        "url": "https://challenges.cloudflare.com/turnstile/v0/siteverify",
        "sitekey": "1x00000000000000000000AA",
        "secret": os.getenv(
            "TURNSTILE_SECRET",
            "1x0000000000000000000000000000000AA",
        ),
    },
}


def public_provider_config():
    """Expose widget sitekeys only; secrets never leave the server."""
    return {
        key: {"name": value["name"], "sitekey": value["sitekey"]}
        for key, value in CONFIG.items()
    }


def verify_token(provider, token):
    if provider not in CONFIG:
        return {
            "provider": provider,
            "success": False,
            "error": "unsupported_provider",
            "message": f"Provider '{provider}' is not supported",
        }

    if not token or not str(token).strip():
        return {
            "provider": provider,
            "success": False,
            "error": "missing_token",
            "message": "No token provided",
        }

    cfg = CONFIG[provider]
    payload = {"secret": cfg["secret"], "response": token}
    if provider == "hcaptcha":
        # Binding verification to the expected widget sitekey is recommended.
        payload["sitekey"] = cfg["sitekey"]

    try:
        response = requests.post(cfg["url"], data=payload, timeout=8)
        response.raise_for_status()
        data = response.json()
    except requests.Timeout:
        return {
            "provider": provider,
            "success": False,
            "error": "verification_timeout",
            "message": "Provider verification timed out",
        }
    except ValueError:
        return {
            "provider": provider,
            "success": False,
            "error": "invalid_response",
            "message": "Verification service returned non-JSON",
        }
    except requests.RequestException as exc:
        return {
            "provider": provider,
            "success": False,
            "error": "verification_unavailable",
            "message": f"Provider request failed: {type(exc).__name__}",
        }

    success = bool(data.get("success"))
    error_codes = data.get("error-codes", []) or []
    if success:
        error = ""
        message = "Token valid"
    elif "timeout-or-duplicate" in error_codes:
        error = "expired_or_reused_token"
        message = "Token expired or already used; acquire a fresh token"
    elif "missing-input-response" in error_codes:
        error = "missing_token"
        message = "Provider did not receive a token"
    else:
        error = "invalid_token"
        message = "Token rejected by provider"

    return {
        "provider": provider,
        "success": success,
        "error": error,
        "error_codes": error_codes,
        "hostname": data.get("hostname", ""),
        "challenge_ts": data.get("challenge_ts", ""),
        "message": message,
    }
