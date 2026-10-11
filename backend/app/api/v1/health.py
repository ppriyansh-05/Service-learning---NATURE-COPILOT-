"""
Health Check Router Module
Provides GET /health and GET /health/db endpoints.
"""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db
from app.schemas.schemas import HealthResponse, DBHealthResponse
from app.core.config import settings
from app.core.security import verify_ngo_admin_password, auth_probe_rate_limit

router = APIRouter(tags=["Health & Status"])


@router.post("/auth/verify", include_in_schema=False)
def verify_admin_password(
    _ratelimit: None = Depends(auth_probe_rate_limit),
    _ok: str = Depends(verify_ngo_admin_password),
):
    """
    Lightweight password check used by the dashboard's unlock dialog.
    - 204 No Content when the X-NGO-Admin-Password header matches.
    - 401 Unauthorized when it does not (unified message — the response does
      not reveal whether the header was missing or wrong).
    - 429 Too Many Requests when the per-IP auth-rate-limit is exhausted.
    Does not touch the database or persist anything.
    """
    return Response(status_code=204)


@router.get("/health", response_model=HealthResponse)
def get_health():
    """System Application Health Check Endpoint."""
    return HealthResponse(
        status="healthy",
        service=settings.PROJECT_NAME,
        version="1.0.0"
    )

@router.get("/health/db", response_model=DBHealthResponse)
def get_db_health(db: Session = Depends(get_db)):
    """Database & PostGIS Health Check Endpoint."""
    db_connected = False
    postgis_ok = False
    
    try:
        res = db.execute(text("SELECT PostGIS_Version();")).fetchone()
        if res:
            db_connected = True
            postgis_ok = True
    except Exception:
        # Graceful connection handling
        db_connected = False
        postgis_ok = False

    return DBHealthResponse(
        status="healthy" if db_connected else "degraded_or_waiting",
        database_connected=db_connected,
        postgis_available=postgis_ok,
        engine="PostgreSQL 15+ / PostGIS 3.3+"
    )
