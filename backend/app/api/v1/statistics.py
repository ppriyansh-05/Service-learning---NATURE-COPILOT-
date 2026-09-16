"""
Biodiversity Statistics API Router Module
Provides GET /api/v1/statistics/overview endpoint calculating dynamic metrics from database.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.schemas import OverviewStatisticsResponse
from app.services.data_service import DataService

router = APIRouter(prefix="/statistics", tags=["Biodiversity Analytics & KPIs"])

@router.get("/overview", response_model=OverviewStatisticsResponse)
def get_statistics_overview(db: Session = Depends(get_db)):
    """Retrieve dynamically calculated biodiversity KPI summary statistics."""
    return DataService.get_statistics_overview(db_session=db)
