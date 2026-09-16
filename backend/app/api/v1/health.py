"""
Health Check Router Module
Provides GET /health and GET /health/db endpoints.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db
from app.schemas.schemas import HealthResponse, DBHealthResponse
from app.core.config import settings

router = APIRouter(tags=["Health & Status"])

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
