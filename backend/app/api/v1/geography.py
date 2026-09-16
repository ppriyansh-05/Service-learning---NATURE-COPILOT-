"""
Van Udyan Geography API Router Module
Provides GET /api/v1/geography endpoint returning Van Udyan boundary GeoJSON.
"""

from fastapi import APIRouter
from app.schemas.schemas import GeoJSONFeatureCollection
from app.services.data_service import DataService

router = APIRouter(prefix="/geography", tags=["Project Site Geography"])

@router.get("", response_model=GeoJSONFeatureCollection)
def get_geography():
    """Retrieve complete Bavdhan Van Udyan site boundary GeoJSON for GIS map applications."""
    return DataService.get_boundary_geojson()
