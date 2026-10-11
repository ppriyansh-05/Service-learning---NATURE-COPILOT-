"""
Structured security event logger.

Emits one JSON-friendly log line per security-relevant event (auth success,
auth failure, rate-limit hit, authorization refusal, security misconfig).
Secrets are never included in the log line — only metadata.
"""
from __future__ import annotations

import logging
from typing import Any

_log = logging.getLogger("van-udyan.security")


def _ensure_configured() -> None:
    if _log.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    _log.addHandler(handler)
    _log.setLevel(logging.INFO)
    _log.propagate = False


def log_event(event: str, *, level: str = "INFO", **fields: Any) -> None:
    """
    Structured security event. `fields` are rendered as key=value and MUST NOT
    include secrets (passwords, tokens, personal data unless strictly needed).
    """
    _ensure_configured()
    safe = {}
    for k, v in fields.items():
        if v is None:
            continue
        # Scrub keys that look like they carry a secret even if the caller slips.
        if any(bad in k.lower() for bad in ("password", "secret", "token", "apikey", "api_key")):
            continue
        s = str(v)
        if len(s) > 200:
            s = s[:197] + "..."
        safe[k] = s
    rendered = " ".join(f"{k}={v!r}" for k, v in safe.items())
    msg = f"event={event} {rendered}".strip()
    getattr(_log, level.lower(), _log.info)(msg)
