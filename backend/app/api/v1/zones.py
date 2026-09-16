"""
Zones API Router Module
Provides GET /api/v1/zones endpoint.
"""

from fastapi import APIRouter
from typing import List
from app.schemas.schemas import ZoneResponse
from app.services.data_service import DataService

router = APIRouter(prefix="/zones", tags=["Geographical Zones"])

@router.get("", response_model=List[ZoneResponse])
def get_zones():
    """Retrieve list of active RSWF working zones with PostGIS/WGS84 polygon geometry."""
    return DataService.get_zones_geojson()
