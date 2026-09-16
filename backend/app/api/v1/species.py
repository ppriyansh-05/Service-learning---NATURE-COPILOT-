"""
Species / Taxonomy API Router Module
Provides GET /api/v1/species endpoint.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.schemas.schemas import PaginatedSpeciesResponse
from app.services.data_service import DataService

router = APIRouter(prefix="/species", tags=["Species & Taxonomy"])

@router.get("", response_model=PaginatedSpeciesResponse)
def get_species(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=200, description="Records per page"),
    species_name: Optional[str] = Query(None, description="Filter by scientific or common name"),
    taxon_rank: Optional[str] = Query(None, description="Filter by taxon rank e.g. species, genus, family"),
    db: Session = Depends(get_db)
):
    """Retrieve paginated list of recorded species and taxonomic taxa."""
    data, total_records, total_pages = DataService.get_species_list(
        db_session=db,
        page=page,
        limit=limit,
        species_name=species_name,
        taxon_rank=taxon_rank
    )
    
    return PaginatedSpeciesResponse(
        page=page,
        limit=limit,
        total_records=total_records,
        total_pages=total_pages,
        data=data
    )
