"""
Security and Authorization Module for Van Udyan Biodiversity Intelligence Platform.

Enforces password protection for NGO data mutation endpoints (editing, status
changes, deletions). Public viewing, searching, uploads (behind their own
guards), exports and reports remain open to anonymous callers.

Security controls layered here:
  * Constant-time password comparison (resists timing side-channels).
  * Per-IP sliding-window rate limiting on the auth probe and on every
    admin-authenticated mutation.
  * Unified error messages — missing header and wrong password respond
    identically to prevent user-enumeration-style probing.
  * Structured security event logs for every failure.
"""

import hmac

from fastapi import Header, HTTPException, Request, status

from app.core.config import settings
from app.core.rate_limit import RateLimiter, client_ip
from app.core.security_logging import log_event

# Shared across the process; see rate_limit.py for the sliding-window logic.
_auth_limiter = RateLimiter(limit_per_minute=settings.AUTH_RATE_LIMIT_PER_MINUTE)
_mutation_limiter = RateLimiter(limit_per_minute=settings.MUTATION_RATE_LIMIT_PER_MINUTE)

# Deliberately identical message for every failure mode so a probe cannot tell
# "no password supplied" from "wrong password" from "rate limited" by text alone.
_UNAUTHORIZED_DETAIL = "Unauthorized."


def _rate_limit_or_raise(request: Request, limiter: RateLimiter, event_name: str) -> None:
    if request is None:
        return
    key = f"{event_name}:{client_ip(request, settings.TRUST_PROXY)}"
    allowed, retry_after = limiter.hit(key)
    if not allowed:
        log_event("rate_limit_block", level="WARNING",
                  bucket=event_name, ip=client_ip(request, settings.TRUST_PROXY),
                  path=str(request.url.path), retry_after=retry_after)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please retry shortly.",
            headers={"Retry-After": str(retry_after)},
        )


def verify_ngo_admin_password(
    request: Request,
    x_ngo_admin_password: str = Header(None, alias="X-NGO-Admin-Password"),
) -> str:
    """
    Dependency verifying that the provided X-NGO-Admin-Password header matches
    the configured RSWF NGO administrative password.

    Returns 429 if the per-IP mutation-rate-limit budget is exhausted.
    Returns 401 (unified message) for both a missing header and a wrong password.
    Uses hmac.compare_digest for constant-time comparison.
    Never exposes or logs the plaintext password.
    """
    _rate_limit_or_raise(request, _mutation_limiter, "mutation")

    expected = settings.NGO_ADMIN_PASSWORD or ""
    supplied = x_ngo_admin_password or ""

    # Always run compare_digest even when supplied is empty so the response
    # time of the "missing header" path matches the "wrong password" path.
    ok = bool(supplied) and hmac.compare_digest(supplied, expected)

    if not ok:
        log_event(
            "auth_failure",
            level="WARNING",
            ip=client_ip(request, settings.TRUST_PROXY) if request else None,
            path=str(request.url.path) if request else None,
            reason="missing" if not supplied else "mismatch",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_UNAUTHORIZED_DETAIL,
        )

    log_event(
        "auth_success",
        ip=client_ip(request, settings.TRUST_PROXY) if request else None,
        path=str(request.url.path) if request else None,
    )
    return supplied


def auth_probe_rate_limit(request: Request) -> None:
    """
    Dependency applied to the lightweight /auth/verify probe. Enforces the
    stricter per-IP auth-rate-limit budget before verify_ngo_admin_password
    runs, to blunt brute-force attempts against the shared admin password.
    """
    _rate_limit_or_raise(request, _auth_limiter, "auth")
