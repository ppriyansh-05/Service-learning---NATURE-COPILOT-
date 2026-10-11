"""
Application Configuration Settings Module
Reads configuration settings from environment variables safely without hard-coded secrets.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load backend/.env if present (keeps secrets out of source code)
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path)

_log = logging.getLogger("van-udyan.config")


def _str_env(name: str, default: str = "") -> str:
    v = os.environ.get(name)
    return v.strip() if v else default


def _bool_env(name: str, default: bool = False) -> bool:
    v = os.environ.get(name, "").strip().lower()
    if not v:
        return default
    return v in ("1", "true", "yes", "on")


def _list_env(name: str) -> list:
    """Parses a comma-separated env var into a list of trimmed non-empty strings."""
    raw = os.environ.get(name, "")
    return [item.strip() for item in raw.split(",") if item.strip()]


class ConfigError(RuntimeError):
    """Raised when a security-critical setting is missing or clearly unsafe in production."""


_DEFAULT_DEV_PASSWORD = "rswf-admin-pass"


class Settings:
    PROJECT_NAME: str = "Van Udyan Biodiversity Intelligence Platform API"
    API_V1_STR: str = "/api/v1"

    @property
    def ENVIRONMENT(self) -> str:
        """'production' | 'staging' | 'development' | 'test'. Defaults to 'development'."""
        return _str_env("ENVIRONMENT", "development").lower()

    @property
    def IS_PRODUCTION(self) -> bool:
        return self.ENVIRONMENT in ("production", "prod")

    @property
    def DEBUG(self) -> bool:
        """Debug mode is forbidden in production regardless of env var."""
        if self.IS_PRODUCTION:
            return False
        return _bool_env("DEBUG", False)

    @property
    def ENABLE_DOCS(self) -> bool:
        """
        /docs, /redoc and /openapi.json are enabled by default off-production.
        In production they require an explicit ENABLE_DOCS=true opt-in.
        """
        if self.IS_PRODUCTION:
            return _bool_env("ENABLE_DOCS", False)
        return _bool_env("ENABLE_DOCS", True)

    # Trust the X-Forwarded-Proto / X-Forwarded-For headers from a reverse proxy
    # (Render, Cloudflare, etc. terminate TLS and set these). Required for correct
    # HTTPS enforcement and client-IP based rate limiting.
    @property
    def TRUST_PROXY(self) -> bool:
        return _bool_env("TRUST_PROXY", True if self.IS_PRODUCTION else False)

    # Per-IP rate limit for the authentication probe. Zero disables the limiter.
    @property
    def AUTH_RATE_LIMIT_PER_MINUTE(self) -> int:
        try:
            return max(0, int(_str_env("AUTH_RATE_LIMIT_PER_MINUTE", "20")))
        except ValueError:
            return 20

    # Per-IP rate limit for all admin-authenticated mutations.
    @property
    def MUTATION_RATE_LIMIT_PER_MINUTE(self) -> int:
        try:
            return max(0, int(_str_env("MUTATION_RATE_LIMIT_PER_MINUTE", "120")))
        except ValueError:
            return 120

    # Hard cap on request body size (bytes). Enforced early via Content-Length header.
    @property
    def MAX_REQUEST_BODY_BYTES(self) -> int:
        try:
            return max(1024, int(_str_env("MAX_REQUEST_BODY_BYTES", str(16 * 1024 * 1024))))
        except ValueError:
            return 16 * 1024 * 1024

    @property
    def DATABASE_URL(self) -> str:
        url = os.environ.get("DATABASE_URL")
        if url:
            # Supabase and some providers hand out "postgres://" URLs which SQLAlchemy no longer accepts
            if url.startswith("postgres://"):
                url = "postgresql://" + url[len("postgres://"):]
            return url

        host = os.environ.get("PGHOST", "localhost")
        port = os.environ.get("PGPORT", "5432")
        user = os.environ.get("PGUSER", "postgres")
        password = os.environ.get("PGPASSWORD", "postgres")
        dbname = os.environ.get("PGDATABASE", "van_udyan_db")

        return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"

    @property
    def PLANTNET_API_KEY(self) -> str:
        return _str_env("PLANTNET_API_KEY")

    @property
    def PLANTNET_PROJECT(self) -> str:
        # Regional flora queried for identification (list: GET https://my-api.plantnet.org/v2/projects)
        return _str_env("PLANTNET_PROJECT", "k-indian-subcontinent")

    @property
    def NGO_ADMIN_PASSWORD(self) -> str:
        """
        Admin password for mutation endpoints. In production the environment
        variable MUST be set to a non-trivial value: we refuse to fall back to
        the public dev default or to accept an empty value, so a mis-configured
        deployment fails loudly rather than silently exposing admin endpoints.
        """
        raw = _str_env("NGO_ADMIN_PASSWORD", "")
        if self.IS_PRODUCTION:
            if not raw:
                raise ConfigError(
                    "NGO_ADMIN_PASSWORD is not set. Refusing to start a production "
                    "server without an admin password configured in the environment."
                )
            if raw == _DEFAULT_DEV_PASSWORD:
                raise ConfigError(
                    "NGO_ADMIN_PASSWORD is set to the public development default. "
                    "Choose a strong, non-default value in production."
                )
            if len(raw) < 12:
                raise ConfigError(
                    "NGO_ADMIN_PASSWORD is too short (<12 characters). Choose a "
                    "stronger value in production."
                )
            return raw
        # Non-production: fall back to the published dev default so local dev,
        # tests, and the demo environment keep working out of the box.
        return raw or _DEFAULT_DEV_PASSWORD

    # Public base URL of this backend, used to build absolute photo URLs when needed.
    # When unset the frontend prefixes its API_BASE_URL itself (matches local dev).
    @property
    def BACKEND_PUBLIC_URL(self) -> str:
        return _str_env("BACKEND_PUBLIC_URL").rstrip("/")

    # Directory for uploaded photos; overridable so a cloud host can mount a volume elsewhere
    @property
    def UPLOADS_DIR(self) -> str:
        return _str_env("UPLOADS_DIR") or ""

    # Directory for cached photo thumbnails
    @property
    def THUMBS_DIR(self) -> str:
        return _str_env("THUMBS_DIR") or ""

    # Supabase Storage settings (optional). When configured, uploads go to the Supabase bucket
    # instead of the local disk, so photos survive host redeploys with no persistent volume.
    @property
    def SUPABASE_URL(self) -> str:
        return _str_env("SUPABASE_URL").rstrip("/")

    @property
    def SUPABASE_SERVICE_KEY(self) -> str:
        # Service role key: has write access to Storage. Keep secret, server-side only.
        return _str_env("SUPABASE_SERVICE_KEY")

    @property
    def SUPABASE_BUCKET(self) -> str:
        return _str_env("SUPABASE_BUCKET", "van-udyan-photos")

    @property
    def PHOTO_STORAGE_BACKEND(self) -> str:
        """'supabase' when Supabase credentials are set, otherwise 'local'."""
        if self.SUPABASE_URL and self.SUPABASE_SERVICE_KEY:
            return "supabase"
        return "local"

    @property
    def CORS_ORIGINS(self) -> list:
        """
        Allowed origins for browser requests. Localhost dev origins are only
        included off-production. The CORS_ORIGINS env var supplies the
        deployed frontend URL in production.
        """
        if self.IS_PRODUCTION:
            defaults = []
        else:
            defaults = [
                "http://localhost",
                "http://localhost:3000",
                "http://localhost:5173",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:5173",
            ]
        extra = _list_env("CORS_ORIGINS")
        # Reject the "*" wildcard in production — allow_credentials=True makes
        # it a security hole.
        if self.IS_PRODUCTION and "*" in extra:
            raise ConfigError("CORS_ORIGINS must not contain '*' in production.")
        # Reject plain-HTTP origins in production (except explicitly whitelisted
        # proxy-local hosts). Prevents an operator from accidentally allowing
        # mixed-content attack paths.
        if self.IS_PRODUCTION:
            bad = [o for o in extra if o.startswith("http://") and not o.startswith("http://localhost")]
            if bad:
                raise ConfigError(f"CORS_ORIGINS in production must use HTTPS: {bad}")
        seen = set()
        result = []
        for origin in defaults + extra:
            if origin and origin not in seen:
                seen.add(origin)
                result.append(origin)
        return result


settings = Settings()
