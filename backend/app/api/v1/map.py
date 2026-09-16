"""
Interactive GIS Map API Router Module
Provides GET /api/v1/map/observations endpoint returning GeoJSON FeatureCollection.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.schemas.schemas import GeoJSONFeatureCollection
from app.services.data_service import DataService

router = APIRouter(prefix="/map", tags=["Interactive GIS Map Layer"])

@router.get("/observations", response_model=GeoJSONFeatureCollection)
def get_map_observations(
    source: Optional[str] = Query(None, description="Filter map observations by source e.g. iNaturalist, Planted, New Upload"),
    zone: Optional[str] = Query(None, description="Filter map observations by zone e.g. 'ZONE A', 'ZONE B', 'ZONE C', or 'OUTSIDE'"),
    db: Session = Depends(get_db)
):
    """Retrieve biodiversity observation points as a frontend-ready GeoJSON FeatureCollection."""
    return DataService.get_map_observations_geojson(db_session=db, source=source, zone=zone)
