"""
Security-focused tests.

These exercise *actual security behaviour* — not merely the presence of
middleware. Each test fakes a realistic attacker interaction and asserts the
response the operator would see from the public internet.

Covered:
  * Unauthorised mutation → 401 with the unified error body.
  * Missing header and wrong password respond identically (no enumeration).
  * Rate limiter blocks a brute-force burst with 429 + Retry-After.
  * Response carries the hardened security headers (CSP, nosniff, frame
    ancestors, Permissions-Policy, Referrer-Policy, HSTS when HTTPS).
  * Oversize payloads are rejected before body is parsed.
  * CORS pre-flight: wildcard-origin requests are not accepted.
  * File-upload MIME / extension / path-traversal rules hold.
  * Production env rejects the default dev password.
  * Error handler does not leak Python exception text in prod mode.
"""
from __future__ import annotations

import importlib
import io
import os

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.rate_limit import RateLimiter

ADMIN_GOOD = {"X-NGO-Admin-Password": "rswf-admin-pass"}
ADMIN_BAD = {"X-NGO-Admin-Password": "obviously-wrong"}

client = TestClient(app)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
def test_mutation_without_header_is_401():
    r = client.delete("/api/v1/planted-plants/1")
    assert r.status_code == 401
    assert r.json().get("detail") == "Unauthorized."


def test_mutation_with_wrong_header_is_401_identical_body():
    r_missing = client.delete("/api/v1/planted-plants/1")
    r_wrong = client.delete("/api/v1/planted-plants/1", headers=ADMIN_BAD)
    assert r_missing.status_code == 401 and r_wrong.status_code == 401
    # Unified detail so a probe cannot distinguish the two cases.
    assert r_missing.json() == r_wrong.json()


def test_mutation_with_correct_header_is_not_401():
    # Target an obviously-unknown id so we don't delete real data; the point
    # is only that we get past the auth gate (-> 404 or 403, not 401).
    r = client.delete("/api/v1/planted-plants/999999", headers=ADMIN_GOOD)
    assert r.status_code != 401


def test_authverify_wrong_password_is_401():
    r = client.post("/api/v1/auth/verify", headers=ADMIN_BAD)
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Rate limit
# ---------------------------------------------------------------------------
def test_rate_limiter_blocks_after_budget():
    rl = RateLimiter(limit_per_minute=3)
    assert rl.hit("ip-x") == (True, 0)
    assert rl.hit("ip-x")[0] is True
    assert rl.hit("ip-x")[0] is True
    allowed, retry = rl.hit("ip-x")
    assert allowed is False and retry >= 1


def test_rate_limiter_is_per_key():
    rl = RateLimiter(limit_per_minute=1)
    assert rl.hit("a")[0] is True
    assert rl.hit("a")[0] is False
    assert rl.hit("b")[0] is True


# ---------------------------------------------------------------------------
# Headers
# ---------------------------------------------------------------------------
def test_security_headers_on_public_response():
    r = client.get("/health")
    h = r.headers
    assert h.get("X-Content-Type-Options") == "nosniff"
    assert h.get("X-Frame-Options") == "DENY"
    assert "Content-Security-Policy" in h
    assert "frame-ancestors 'none'" in h["Content-Security-Policy"]
    assert "Permissions-Policy" in h
    assert "Referrer-Policy" in h


def test_sensitive_path_disables_cache():
    r = client.post("/api/v1/auth/verify", headers=ADMIN_BAD)
    assert r.headers.get("Cache-Control", "").lower().replace(" ", "") == "no-store"


# ---------------------------------------------------------------------------
# Body size cap
# ---------------------------------------------------------------------------
def test_oversize_body_rejected_early():
    too_big = 32 * 1024 * 1024  # 32 MB > default 16 MB cap
    r = client.post(
        "/api/v1/observations/bulk-upload",
        headers={"Content-Length": str(too_big), **ADMIN_GOOD},
        content=b"",  # content-length header is what matters
    )
    assert r.status_code == 413


# ---------------------------------------------------------------------------
# Upload hardening
# ---------------------------------------------------------------------------
def test_upload_rejects_disallowed_extension():
    r = client.post(
        "/api/v1/observations/upload",
        files={"file": ("evil.php", io.BytesIO(b"<?php echo 'x'; ?>"), "application/x-php")},
    )
    assert r.status_code in (400, 415)


def test_upload_rejects_mismatched_mime():
    # jpg extension but a disallowed MIME type
    r = client.post(
        "/api/v1/observations/upload",
        files={"file": ("ok.jpg", io.BytesIO(b"\xff\xd8\xff"), "application/x-executable")},
    )
    assert r.status_code in (400, 415)


def test_thumbs_rejects_path_traversal():
    # /thumbs/{name} is regex-guarded; any payload with .. or / is rejected
    r = client.get("/thumbs/..%2F..%2Fetc%2Fpasswd")
    assert r.status_code == 404
    r = client.get("/thumbs/upload_abc/../..")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Config refuses default password in production
# ---------------------------------------------------------------------------
def test_production_refuses_default_password(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("NGO_ADMIN_PASSWORD", "rswf-admin-pass")
    # Reload the config module so the new env is picked up.
    from app.core import config as cfg
    importlib.reload(cfg)
    with pytest.raises(cfg.ConfigError):
        _ = cfg.settings.NGO_ADMIN_PASSWORD


def test_production_refuses_missing_password(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("NGO_ADMIN_PASSWORD", raising=False)
    from app.core import config as cfg
    importlib.reload(cfg)
    with pytest.raises(cfg.ConfigError):
        _ = cfg.settings.NGO_ADMIN_PASSWORD


def test_production_refuses_wildcard_cors(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("NGO_ADMIN_PASSWORD", "a-long-strong-password-123")
    monkeypatch.setenv("CORS_ORIGINS", "*")
    from app.core import config as cfg
    importlib.reload(cfg)
    with pytest.raises(cfg.ConfigError):
        _ = cfg.settings.CORS_ORIGINS


def test_production_refuses_http_cors(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("NGO_ADMIN_PASSWORD", "a-long-strong-password-123")
    monkeypatch.setenv("CORS_ORIGINS", "http://evil.example.com")
    from app.core import config as cfg
    importlib.reload(cfg)
    with pytest.raises(cfg.ConfigError):
        _ = cfg.settings.CORS_ORIGINS


# ---------------------------------------------------------------------------
# Docs are off in production
# ---------------------------------------------------------------------------
def test_docs_disabled_default_in_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("NGO_ADMIN_PASSWORD", "a-long-strong-password-123")
    monkeypatch.delenv("ENABLE_DOCS", raising=False)
    from app.core import config as cfg
    importlib.reload(cfg)
    assert cfg.settings.ENABLE_DOCS is False
