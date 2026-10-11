"""
Planted Plants CRUD Router Module
Provides POST, GET list, GET detail, PUT/PATCH, and DELETE endpoints for Planted Plants.
Protected mutation operations require RSWF NGO Administrative Password verification.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional
from app.schemas.schemas import (
    PlantedPlantCreate, PlantedPlantUpdate, PlantedPlantResponse, PaginatedPlantedPlantsResponse,
    PlantMonitoringCreate, PlantMonitoringResponse
)
from app.services.data_service import DataService, load_planted_plants_store, save_planted_plants_store
from app.services import watering_service
from app.core.security import verify_ngo_admin_password

router = APIRouter(prefix="/planted-plants", tags=["Planted Plants CRUD"])

@router.get("/monitoring/statistics")
def get_plant_survival_statistics():
    """Retrieves dynamic plant survival rate, status counts, and zone-wise mortality analytics."""
    return DataService.get_plant_survival_statistics()


@router.get("/watering")
def get_watering_queue():
    """
    Watering reminder queue: every planted plant with its current watering status
    (overdue / due_soon / ok / skip), sorted most urgent first. Public read-only.
    """
    plants = load_planted_plants_store() or []
    return {
        "summary": watering_service.watering_overview(plants),
        "queue": watering_service.compute_watering_queue(plants),
    }


@router.post("/{id}/watered", status_code=status.HTTP_201_CREATED)
def mark_plant_watered(
    id: int,
    on_date: Optional[str] = Query(None, description="ISO date YYYY-MM-DD; defaults to today."),
    observer: Optional[str] = Query(None, description="Who watered it."),
    auth: str = Depends(verify_ngo_admin_password),
):
    """
    Mark a planted plant as watered on the given date (defaults to today).
    Protected: needs the RSWF admin password.
    """
    import datetime as _dt

    plants = load_planted_plants_store() or []
    plant = next((p for p in plants if p.get("id") == id), None)
    if not plant:
        raise HTTPException(status_code=404, detail=f"Planted plant {id} not found.")

    try:
        when = _dt.date.fromisoformat((on_date or "").strip()) if on_date else _dt.date.today()
    except ValueError:
        raise HTTPException(status_code=400, detail="on_date must be an ISO date YYYY-MM-DD.")
    if when > _dt.date.today():
        raise HTTPException(status_code=400, detail="Cannot mark a plant as watered on a future date.")

    plant["last_watered_on"] = when.isoformat()
    plant["last_watered_by"] = (observer or "").strip() or plant.get("last_watered_by")
    save_planted_plants_store(plants)
    status_dict = watering_service.watering_status_for(plant, _dt.date.today())
    return {
        "plant_id": id,
        "plant_code": plant.get("plant_code"),
        "last_watered_on": plant["last_watered_on"],
        "last_watered_by": plant.get("last_watered_by"),
        "watering": status_dict,
    }

@router.post("", response_model=PlantedPlantResponse, status_code=status.HTTP_201_CREATED)
def create_planted_plant(
    plant_data: PlantedPlantCreate,
    auth: str = Depends(verify_ngo_admin_password)
):
    """Create a new Planted Plant record (RSWF NGO Plantation Dataset - Password Protected)."""
    try:
        record = DataService.create_planted_plant(plant_data.model_dump())
        return record
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("", response_model=PaginatedPlantedPlantsResponse)
def get_planted_plants(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=200, description="Records per page"),
    status: Optional[str] = Query(None, description="Filter by status: Alive, Dead, Unknown"),
    zone: Optional[str] = Query(None, description="Filter by zone e.g. ZONE A, ZONE B, ZONE C"),
    species: Optional[str] = Query(None, description="Filter by scientific or common name")
):
    """Retrieve paginated list of Planted Plant records (Public Access)."""
    data, total_records, total_pages = DataService.get_planted_plants(
        page=page, limit=limit, status=status, zone=zone, species=species
    )
    return PaginatedPlantedPlantsResponse(
        page=page,
        limit=limit,
        total_records=total_records,
        total_pages=total_pages,
        data=data
    )

@router.post("/{id}/monitoring", status_code=status.HTTP_201_CREATED)
def add_plant_monitoring_visit(
    id: int,
    req: PlantMonitoringCreate,
    auth: str = Depends(verify_ngo_admin_password)
):
    """
    Creates a new condition monitoring visit record for a planted plant (Password Protected).
    Updates the plant's current status while preserving full chronological visit history.
    """
    try:
        record = DataService.add_plant_monitoring_record(
            plant_id=id,
            status=req.status,
            monitoring_date=req.monitoring_date,
            notes=req.notes,
            photo_url=req.photo_url,
            observer=req.observer
        )
        return record
    except ValueError as e:
        msg = str(e)
        if "not found" in msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

@router.get("/{id}/monitoring")
def get_plant_monitoring_history(id: int):
    """Retrieves chronological monitoring visit history for a planted plant (Public Access)."""
    try:
        history = DataService.get_plant_monitoring_history(plant_id=id)
        return history
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/{id}", response_model=PlantedPlantResponse)
def get_planted_plant_detail(id: int):
    """Retrieve single Planted Plant detail by ID (Public Access)."""
    record = DataService.get_planted_plant_by_id(id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Planted plant with ID {id} not found.")
    return record

@router.put("/{id}", response_model=PlantedPlantResponse)
@router.patch("/{id}", response_model=PlantedPlantResponse)
def update_planted_plant(
    id: int,
    plant_data: PlantedPlantUpdate,
    auth: str = Depends(verify_ngo_admin_password)
):
    """Update an existing Planted Plant record (Password Protected)."""
    try:
        updated = DataService.update_planted_plant(id, plant_data.model_dump(exclude_unset=True))
        return updated
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_planted_plant(
    id: int,
    auth: str = Depends(verify_ngo_admin_password)
):
    """Delete a Planted Plant record (Password Protected)."""
    deleted = DataService.delete_planted_plant(id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Planted plant with ID {id} not found.")
    return None
