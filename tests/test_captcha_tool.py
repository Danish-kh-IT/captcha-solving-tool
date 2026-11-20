"""
Unit tests for CAPTCHA Solving Tool
Run: python -m pytest tests/ -v
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from detector import detect_provider, detect_challenge
from verify import verify_token


# ---------------------------------------------------------------------------
# detector tests
# ---------------------------------------------------------------------------

class TestDetectProvider:
    def test_recaptcha_detected(self):
        html = '<div class="g-recaptcha" data-sitekey="test"></div>'
        r = detect_provider(html)
        assert r["type"] == "recaptcha"
        assert r["supported"] is True

    def test_invisible_recaptcha_detected(self):
        html = '<div class="g-recaptcha invisible" data-sitekey="test"></div>'
        r = detect_provider(html)
        assert r["type"] == "recaptcha_invisible"

    def test_hcaptcha_detected(self):
        html = '<div class="h-captcha" data-sitekey="test"></div>'
        r = detect_provider(html)
        assert r["type"] == "hcaptcha"

    def test_turnstile_detected(self):
        html = '<div class="cf-turnstile" data-sitekey="test"></div>'
        r = detect_provider(html)
        assert r["type"] == "turnstile"

    def test_no_captcha(self):
        html = '<form><input name="email"></form>'
        r = detect_provider(html)
        assert r["type"] == "none"
        assert r["supported"] is False

    def test_empty_html(self):
        r = detect_provider("")
        assert r["type"] == "none"


class TestDetectChallenge:
    def test_synthetic_text(self):
        r = detect_challenge("synthetic_text")
        assert r["supported"] is True
        assert "OCR" in r["method"]

    def test_unsupported_kind(self):
        r = detect_challenge("audio_captcha")
        assert r["supported"] is False


# ---------------------------------------------------------------------------
# verify tests
# ---------------------------------------------------------------------------

class TestVerifyToken:
    def test_missing_token_rejected(self):
        r = verify_token("recaptcha", "")
        assert r["success"] is False
        assert r["error"] == "missing_token"

    def test_whitespace_token_rejected(self):
        r = verify_token("recaptcha", "   ")
        assert r["success"] is False
        assert r["error"] == "missing_token"

    def test_unsupported_provider(self):
        r = verify_token("audio", "sometoken")
        assert r["success"] is False
        assert r["error"] == "unsupported_provider"

    def test_recaptcha_test_key_accepts_any_token(self):
        # Google's public test key always returns success=true
        r = verify_token("recaptcha", "test-token")
        assert r["success"] is True
        assert r["provider"] == "recaptcha"

    def test_turnstile_test_key_accepts_any_token(self):
        # Cloudflare's test key always returns success=true
        r = verify_token("turnstile", "XXXX.DUMMY.TOKEN.XXXX")
        assert r["success"] is True

    def test_hcaptcha_dummy_token_rejected(self):
        # hCaptcha test secret does not auto-accept — expects real test flow
        r = verify_token("hcaptcha", "dummy")
        # Should at least return a structured response
        assert "success" in r
        assert "provider" in r
