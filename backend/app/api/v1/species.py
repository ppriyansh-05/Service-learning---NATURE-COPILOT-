"""
Species / Taxonomy API Router Module
Provides GET /api/v1/species endpoint, plus NGO-approved species list endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.schemas.schemas import PaginatedSpeciesResponse
from app.services.data_service import DataService
from app.services import ngo_species_service
from app.core.security import verify_ngo_admin_password

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


# ---------------------------------------------------------------------------
# NGO-Approved Species List endpoints
# ---------------------------------------------------------------------------

@router.get("/ngo-approved")
def get_ngo_approved_species():
    """
    Returns the full NGO-approved species list sourced from the Devrai Foundation
    Sacred Grove master plan. Every PlantNet prediction is cross-checked against
    this list — a species not present here was never purchased for Bavdhan Van Udyan
    and therefore cannot be a valid planted-tree identification.
    """
    return ngo_species_service.get_approved_species_summary()


@router.get("/ngo-check")
def check_species_in_ngo_list(
    scientific_name: str = Query(..., description="Scientific name to look up, e.g. 'Mangifera indica'")
):
    """
    Quick lookup: is this scientific name in the NGO approved list?
    Returns the species record if found, or a 404-style JSON if not.
    """
    record = ngo_species_service.lookup_species(scientific_name)
    if record:
        return {
            "found": True,
            "scientific_name": scientific_name,
            "record": record,
            "note": f"✅ In NGO list — {record.get('marathi_name', '')} ({record.get('type', 'Plant')}, {record.get('qty_planned', '?')} planned)"
        }
    return {
        "found": False,
        "scientific_name": scientific_name,
        "record": None,
        "note": "⚠️ Not in NGO species list — this species was not purchased or planned for Bavdhan Van Udyan."
    }


@router.post("/ngo-reload")
def reload_ngo_species_list(auth: str = Depends(verify_ngo_admin_password)):
    """
    Admin-only: hot-reload the NGO approved species list from disk
    (data/processed/ngo_approved_species.json) without restarting the server.
    Call this after updating the JSON file.
    """
    count = ngo_species_service.reload()
    return {"reloaded": True, "species_count": count}
