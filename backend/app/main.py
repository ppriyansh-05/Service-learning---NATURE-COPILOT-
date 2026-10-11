"""
Main FastAPI Application Entry Point
Initializes FastAPI app, configures CORS middleware, registers v1 API routers, mounts the
photo serving layer, and exposes health and readiness endpoints.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from PIL import Image, ImageOps
import logging
import sys
import os
import re

# Ensure backend root is in python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.services import photo_storage, state_sync
from app.api.v1 import health, observations, species, zones, geography, map, statistics, planted_plants, export, analytics, reports, compliance

log = logging.getLogger("van-udyan")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup: pull the latest NGO stores from Postgres onto the local disk so an ephemeral host
    (Render free) starts with the data it had before the previous restart.
    Shutdown: nothing to clean up.
    """
    try:
        pulled = state_sync.pull_all()
        synced = [k for k, ok in pulled.items() if ok]
        if synced:
            log.info("state_sync: pulled %s from database", ", ".join(synced))
    except Exception as e:
        log.warning("state_sync: startup pull failed, using local JSON only (%s)", e)
    yield


# /docs, /redoc, /openapi.json default on off-production and off in production.
# Hiding them in production reduces attack-surface reconnaissance; they can be
# turned back on with ENABLE_DOCS=true in the environment for a short-lived
# debugging window.
_docs_enabled = settings.ENABLE_DOCS

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Geospatial Biodiversity Mapping, Monitoring & AI Analytics System for RSWF NGO",
    version="1.0.0",
    docs_url="/docs" if _docs_enabled else None,
    redoc_url="/redoc" if _docs_enabled else None,
    openapi_url="/openapi.json" if _docs_enabled else None,
    lifespan=lifespan,
)

# CORS: allowed origins come from config.CORS_ORIGINS (defaults + env-provided deployed URLs)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["Content-Type", "Authorization", "X-NGO-Admin-Password", "X-Requested-With"],
    expose_headers=["Content-Disposition"],
    max_age=600,
)


# ---------------------------------------------------------------------------
# Security hardening middleware
# ---------------------------------------------------------------------------
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Attaches a conservative set of security headers to every response.

    - X-Content-Type-Options: nosniff — prevents MIME-sniffing attacks.
    - X-Frame-Options: DENY — clickjacking defence.
    - Referrer-Policy: strict-origin-when-cross-origin — don't leak paths.
    - Permissions-Policy — explicitly deny powerful APIs we never use.
    - Strict-Transport-Security — HSTS, only on confirmed-HTTPS requests.
    - Cross-Origin-Resource-Policy: cross-origin — the frontend sits on a
      different Render subdomain and must be able to pull exports/photos.
    - Content-Security-Policy — a tight API-oriented CSP (default-src 'none',
      no scripts, no frames). The dashboard is a separate static site served
      by its own origin so this backend never renders HTML except /docs; the
      CSP is relaxed via `_docs_enabled` only when docs are turned on.
    - Cache-Control: no-store on auth/admin paths so proxies can't cache
      sensitive responses.
    """
    _SENSITIVE_PREFIXES = ("/api/v1/auth/", "/auth/")

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "geolocation=(), microphone=(), camera=(), payment=(), usb=(), magnetometer=(), gyroscope=(), accelerometer=()",
        )
        response.headers.setdefault("Cross-Origin-Resource-Policy", "cross-origin")
        if _docs_enabled:
            # Swagger UI / ReDoc need their own CDN + inline bootstrap style/script.
            response.headers.setdefault(
                "Content-Security-Policy",
                "default-src 'self'; "
                "script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
                "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
                "img-src 'self' data:; "
                "font-src 'self' data:; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'none'; "
                "form-action 'self'",
            )
        else:
            response.headers.setdefault(
                "Content-Security-Policy",
                "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
            )
        path = request.url.path or ""
        if any(path.startswith(p) for p in self._SENSITIVE_PREFIXES):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Pragma"] = "no-cache"
        proto = request.headers.get("x-forwarded-proto") if settings.TRUST_PROXY else None
        if request.url.scheme == "https" or proto == "https":
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains; preload",
            )
        return response


class RequestBodySizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Rejects requests with a declared Content-Length larger than
    MAX_REQUEST_BODY_BYTES before any body is read. Guards against trivial
    denial-of-service via oversize uploads; the per-file EXIF validator still
    enforces 10 MB per photo inside the bulk-upload loop.
    """
    def __init__(self, app, max_bytes: int) -> None:
        super().__init__(app)
        self.max_bytes = int(max_bytes)

    async def dispatch(self, request: Request, call_next):
        length = request.headers.get("content-length")
        if length:
            try:
                if int(length) > self.max_bytes:
                    return Response(
                        content="Request body too large.",
                        status_code=413,
                        headers={"Content-Type": "text/plain"},
                    )
            except ValueError:
                return Response(content="Bad Request.", status_code=400)
        return await call_next(request)


# Order matters: body-size check runs FIRST so oversize payloads never make it
# into the app pipeline. Security headers wrap everything else.
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestBodySizeLimitMiddleware, max_bytes=settings.MAX_REQUEST_BODY_BYTES)


# ---------------------------------------------------------------------------
# Global exception handler — never leak internals in production
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception):
    """
    Catches anything that escapes a route handler. In production we return a
    generic 500 and keep the stack trace in the server log; in development we
    include the exception string so the operator can see what broke.
    """
    log.exception("unhandled exception at %s %s", request.method, request.url.path)
    if settings.IS_PRODUCTION:
        return Response(
            content='{"detail":"Internal server error."}',
            status_code=500,
            media_type="application/json",
        )
    return Response(
        content=f'{{"detail":"Internal server error.","error":{repr(str(exc))}}}',
        status_code=500,
        media_type="application/json",
    )

# Photo storage: local filesystem by default; Supabase Storage when its env vars are set.
# Local mode mounts /uploads directly from the uploads directory for the fastest possible transfer.
if photo_storage.is_local():
    app.mount("/uploads", StaticFiles(directory=photo_storage.uploads_dir()), name="uploads")
else:
    @app.get("/uploads/{name}", include_in_schema=False)
    def photo_original(name: str):
        """Redirects to the Supabase Storage public URL (no backend bandwidth used)."""
        if not photo_storage.is_safe_name(name):
            raise HTTPException(status_code=404, detail="Not found")
        return RedirectResponse(url=photo_storage.public_url(name), status_code=307)


THUMB_NAME = re.compile(r"^upload_[A-Za-z0-9_]+\.(jpg|jpeg|png|webp)$", re.IGNORECASE)
THUMB_SIZE = 320


@app.get("/thumbs/{name}", include_in_schema=False)
def photo_thumbnail(name: str):
    """Small cached preview for tables and map popups. Falls back to generating on the fly."""
    if not THUMB_NAME.match(name):
        raise HTTPException(status_code=404, detail="Not found")

    thumbs_dir = photo_storage.thumbs_dir()
    os.makedirs(thumbs_dir, exist_ok=True)

    thumb = os.path.join(
        thumbs_dir,
        os.path.splitext(name)[0] + ".jpg"
    )

    if not os.path.exists(thumb):
        source_path = photo_storage.read_to_tempfile(name)

        if source_path is None:
            raise HTTPException(status_code=404, detail="Photo not found")

        try:
            with Image.open(source_path) as img:
                img = ImageOps.exif_transpose(img).convert("RGB")
                img.thumbnail(
                    (THUMB_SIZE, THUMB_SIZE),
                    Image.Resampling.LANCZOS
                )
                img.save(thumb, "JPEG", quality=82)
        finally:
            photo_storage.cleanup_tempfile(source_path)

    return FileResponse(
        thumb,
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=86400"}
    )


# Register Health Endpoints
app.include_router(health.router)

# Register API v1 Routers
api_v1_prefix = settings.API_V1_STR

# Dashboard unlock dialog hits /api/v1/auth/verify — expose the health router's
# /auth/verify endpoint under the versioned prefix as well
from fastapi import APIRouter as _APIRouter, Depends as _Depends
from fastapi.responses import Response as _Response
from app.core.security import verify_ngo_admin_password as _verify_pw, auth_probe_rate_limit as _auth_probe_rl

_auth_router = _APIRouter(tags=["Auth"])

@_auth_router.post("/auth/verify", include_in_schema=False)
def _auth_verify(
    _ratelimit: None = _Depends(_auth_probe_rl),
    _ok: str = _Depends(_verify_pw),
):
    return _Response(status_code=204)

app.include_router(_auth_router, prefix=api_v1_prefix)

app.include_router(observations.router, prefix=api_v1_prefix)
app.include_router(species.router, prefix=api_v1_prefix)
app.include_router(zones.router, prefix=api_v1_prefix)
app.include_router(geography.router, prefix=api_v1_prefix)
app.include_router(map.router, prefix=api_v1_prefix)
app.include_router(statistics.router, prefix=api_v1_prefix)
app.include_router(planted_plants.router, prefix=api_v1_prefix)
app.include_router(export.router, prefix=api_v1_prefix)
app.include_router(analytics.router, prefix=api_v1_prefix)
app.include_router(reports.router, prefix=api_v1_prefix)
app.include_router(compliance.router, prefix=api_v1_prefix)


@app.get("/", include_in_schema=False)
def root():
    return {
        "message": "Welcome to Van Udyan Biodiversity Intelligence Platform API",
        "documentation": "/docs",
        "health": "/health",
        "api_v1": settings.API_V1_STR,
        "photo_storage": settings.PHOTO_STORAGE_BACKEND,
    }


@app.get("/ready", include_in_schema=False)
def readiness():
    """Lightweight readiness check for cloud load balancers (does not hit the database)."""
    return Response(status_code=204)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
