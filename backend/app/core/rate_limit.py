"""
In-process sliding-window rate limiter.

Zero-dependency, thread-safe, bounded memory. Appropriate for a single-worker
deployment (Render free / starter runs one uvicorn worker). For multi-worker
or distributed deployments, replace with a Redis-backed limiter — the API
surface here (RateLimiter.hit) stays the same.

Keyed by *client IP + bucket name* so e.g. an auth brute-force attempt and a
burst of legitimate mutations don't share a budget.

Returns False from .hit() when the caller has exceeded its budget; the caller
raises HTTPException(429) with Retry-After.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from typing import Deque, Dict, Tuple

from fastapi import Request


def client_ip(request: Request, trust_proxy: bool) -> str:
    """
    Resolves the client IP for rate-limiting purposes.

    When behind a trusted reverse proxy (Render / Cloudflare), the leftmost
    entry of X-Forwarded-For is the originating client. Without that trust
    flag, the socket peer address is used — the X-Forwarded-* headers are
    user-controllable and must NOT be trusted when the server is reachable
    directly from the internet.
    """
    if trust_proxy:
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            first = fwd.split(",")[0].strip()
            if first:
                return first
    client = getattr(request, "client", None)
    return client.host if client else "unknown"


class RateLimiter:
    """
    Sliding-window counter. One instance per bucket (auth / mutations / …).
    """

    def __init__(self, limit_per_minute: int, window_seconds: float = 60.0,
                 max_keys: int = 50_000) -> None:
        self.limit = int(limit_per_minute)
        self.window = float(window_seconds)
        self.max_keys = int(max_keys)
        self._hits: Dict[str, Deque[float]] = {}
        self._lock = threading.Lock()
        # One in every ~1024 hits triggers an opportunistic prune of stale keys.
        self._prune_counter = 0

    def hit(self, key: str) -> Tuple[bool, int]:
        """
        Record one request from `key`. Returns (allowed, retry_after_seconds).
        retry_after is only meaningful when allowed is False.
        """
        if self.limit <= 0:
            return True, 0
        now = time.monotonic()
        cutoff = now - self.window
        with self._lock:
            dq = self._hits.get(key)
            if dq is None:
                dq = deque()
                self._hits[key] = dq
            # Drop timestamps outside the window
            while dq and dq[0] < cutoff:
                dq.popleft()
            if len(dq) >= self.limit:
                retry_after = max(1, int(dq[0] + self.window - now) + 1)
                return False, retry_after
            dq.append(now)
            # Periodic prune to cap memory under a flood of unique keys
            self._prune_counter = (self._prune_counter + 1) & 0x3FF
            if self._prune_counter == 0 and len(self._hits) > self.max_keys:
                self._prune_locked(cutoff)
            return True, 0

    def _prune_locked(self, cutoff: float) -> None:
        """Drop keys whose window has fully expired."""
        empty = [k for k, dq in self._hits.items() if not dq or dq[-1] < cutoff]
        for k in empty:
            del self._hits[k]
