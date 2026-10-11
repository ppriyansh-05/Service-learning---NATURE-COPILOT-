"""
Observations API Router Module
Provides GET /api/v1/observations, GET /api/v1/observations/{id}, POST /api/v1/observations/ngo,
POST /api/v1/observations/upload (EXIF GPS photo upload pipeline),
and provenance protection preventing modification of original iNaturalist records.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status, Response
from typing import List as _List
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.schemas.schemas import (
    PaginatedObservationsResponse, ObservationResponse, NGOObservationCreate, GeotagLocationConfirmRequest
)
from app.services.data_service import DataService, DuplicateObservationError

router = APIRouter(prefix="/observations", tags=["Observations"])

@router.get("", response_model=PaginatedObservationsResponse)
def get_observations(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=200, description="Records per page"),
    source: Optional[str] = Query(None, description="Filter by source stream e.g. iNaturalist, Planted, New Upload"),
    species: Optional[str] = Query(None, description="Filter by species or common name substring"),
    zone: Optional[str] = Query(None, description="Filter by zone e.g. 'ZONE A', 'ZONE B', 'ZONE C', or 'OUTSIDE'"),
    quality_grade: Optional[str] = Query(None, description="Filter by quality grade e.g. research, needs_id"),
    db: Session = Depends(get_db)
):
    """Retrieve paginated list of biodiversity observations with multi-source filtering."""
    data, total_records, total_pages = DataService.get_observations(
        db_session=db,
        page=page,
        limit=limit,
        source=source,
        species=species,
        zone=zone,
        quality_grade=quality_grade
    )
    
    return PaginatedObservationsResponse(
        page=page,
        limit=limit,
        total_records=total_records,
        total_pages=total_pages,
        data=data
    )

@router.get("/ai-feedback")
def get_ai_feedback_statistics():
    """Retrieves aggregated AI feedback metrics (confirmation rate, correction rate, review counts)."""
    return DataService.get_ai_feedback_metrics()

@router.get("/{id}", response_model=ObservationResponse)
def get_observation_detail(id: int, db: Session = Depends(get_db)):
    """Retrieve detailed observation by internal database ID."""
    record = DataService.get_observation_by_id(db_session=db, obs_id=id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Observation with ID {id} not found")
    return record

@router.post("/ngo", response_model=ObservationResponse, status_code=status.HTTP_201_CREATED)
def create_ngo_observation(
    obs_data: NGOObservationCreate,
    allow_nearby_duplicate: bool = Query(
        False,
        description="Override the 1 metre same-plant guard (see /observations/upload for details).",
    ),
):
    """Create a new NGO-owned field observation record (source = 'NGO / New Upload')."""
    try:
        record = DataService.create_ngo_observation(obs_data.model_dump(), allow_nearby_duplicate=allow_nearby_duplicate)
        return record
    except DuplicateObservationError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.to_detail())
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_photo_observation(
    response: Response,
    file: UploadFile = File(...),
    confirm_location: bool = Query(False, description="Set to true if user confirms visible image geotag coordinates"),
    allow_nearby_duplicate: bool = Query(
        False,
        description=(
            "By default, uploading a photo within ~1 metre of an existing plant observation is "
            "rejected as the same plant (409 Conflict). Set true when two plants genuinely grow "
            "that close together and you want to record the new one anyway."
        ),
    ),
):
    """
    Upload a plant/biodiversity photo.
    Extracts location using strict priority:
    1. EXIF GPS metadata
    2. Visible image geotag overlay (via OCR)
    3. Location not available
    """
    contents = await file.read()
    filename = file.filename or "uploaded_photo.jpg"
    content_type = file.content_type or "image/jpeg"

    try:
        res = DataService.process_photo_upload(
            contents, filename, content_type,
            confirm_location=confirm_location,
            allow_nearby_duplicate=allow_nearby_duplicate,
        )
        if not res.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=res.get("message", "Location not available. GPS information could not be found in the photo metadata or visible image geotag.")
            )

        if res.get("requires_confirmation"):
            response.status_code = status.HTTP_200_OK

        return res

    except DuplicateObservationError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.to_detail())
    except ValueError as e:
        msg = str(e)
        if "exceeds maximum allowed limit" in msg:
            raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail=msg)
        elif "Unsupported file type" in msg:
            raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=msg)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

@router.post("/confirm-location", status_code=status.HTTP_201_CREATED)
def confirm_geotag_location(
    req: GeotagLocationConfirmRequest,
    allow_nearby_duplicate: bool = Query(
        False,
        description="Override the 1 metre same-plant guard (see /observations/upload for details)."
    ),
):
    """
    Confirms user-verified coordinates detected from a visible image geotag overlay.
    Validates boundary containment inside Van Udyan and persists the observation.
    """
    try:
        res = DataService.confirm_geotag_observation(
            photo_url=req.photo_url,
            latitude=req.latitude,
            longitude=req.longitude,
            observed_on=req.observed_on,
            observer=req.observer,
            notes=req.notes,
            allow_nearby_duplicate=allow_nearby_duplicate,
        )
        return res
    except DuplicateObservationError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.to_detail())
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/bulk-upload", status_code=status.HTTP_200_OK)
async def bulk_upload_photos(
    files: _List[UploadFile] = File(..., description="Up to 50 photos — EXIF/GPS, zone, dedup are run per file"),
    allow_nearby_duplicate: bool = Query(False, description="Skip the 1 m same-plant guard for every file"),
):
    """
    Batch EXIF/GPS pipeline for a folder-drop of photos.
    Each file is processed through the same guards as /upload; the response
    is one row per file so the frontend can render a review grid.
    Nothing is auto-persisted when GPS confirmation is still pending — the
    user acts on each row in the UI.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    if len(files) > 50:
        raise HTTPException(status_code=413, detail="At most 50 files per batch")

    import logging as _logging
    _log = _logging.getLogger("van-udyan.upload")

    results = []
    for f in files:
        name = f.filename or "unnamed.jpg"
        ctype = f.content_type or "image/jpeg"
        try:
            contents = await f.read()
        except Exception as read_err:
            _log.warning("bulk-upload read failed for %r: %s", name, read_err)
            results.append({"filename": name, "ok": False, "status": "error", "error": "Could not read upload."})
            continue
        try:
            res = DataService.process_photo_upload(
                contents, name, ctype,
                confirm_location=False,
                allow_nearby_duplicate=allow_nearby_duplicate,
            )
            results.append({"filename": name, "ok": True, **res})
        except DuplicateObservationError as de:
            results.append({"filename": name, "ok": False, "status": "duplicate", "duplicate": de.to_detail()})
        except ValueError as ve:
            # ValueError messages here are the result of our own validators
            # (file-type / size / boundary / dedup) — safe to surface to the UI.
            results.append({"filename": name, "ok": False, "status": "rejected", "error": str(ve)})
        except Exception as ue:  # noqa: BLE001
            # Everything else: log server-side, never leak the exception to the client.
            _log.exception("bulk-upload unexpected failure for %r: %s", name, ue)
            results.append({"filename": name, "ok": False, "status": "error", "error": "Upload failed."})

    summary = {
        "total": len(files),
        "ok": sum(1 for r in results if r.get("ok")),
        "needs_confirmation": sum(1 for r in results if r.get("requires_confirmation")),
        "duplicates": sum(1 for r in results if r.get("status") == "duplicate"),
        "rejected": sum(1 for r in results if r.get("status") == "rejected"),
        "errors": sum(1 for r in results if r.get("status") == "error"),
    }
    return {"summary": summary, "results": results}


@router.post("/inspect-photo")
async def inspect_photo_file(file: UploadFile = File(...)):
    """
    Inspects an uploaded photo file for GPS coordinates (EXIF or visible geotag)
    and checks boundary containment without creating a database observation record.
    Useful for auto-populating coordinates in Planted Plant and NGO Sighting forms.
    """
    contents = await file.read()
    filename = file.filename or "uploaded_photo.jpg"
    content_type = file.content_type or "image/jpeg"

    try:
        res = DataService.inspect_photo_file(contents, filename, content_type)
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/{id}/identify")
def identify_observation_plant(
    id: int,
    organ: Optional[str] = Query("auto", description="Plant organ e.g. auto, leaf, flower, fruit, bark, habit")
):
    """
    Triggers Pl@ntNet AI species identification for an uploaded photo observation.
    Returns normalized Top 3 predictions with confidence levels without overwriting original data.
    """
    try:
        res = DataService.identify_observation_plant(obs_id=id, organ=organ or "auto")
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"AI Identification error: {str(e)}")

@router.get("/{id}/predictions")
def get_observation_predictions(id: int):
    """Retrieves stored Pl@ntNet AI predictions for an observation."""
    preds = DataService.get_observation_ai_predictions(obs_id=id)
    if not preds:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No AI predictions stored for Observation #{id}.")
    return preds

from app.core.security import verify_ngo_admin_password
from app.schemas.schemas import ObservationVerificationRequest

@router.post("/{id}/verify")
def verify_observation_identification(
    id: int,
    req: ObservationVerificationRequest,
    auth: str = Depends(verify_ngo_admin_password)
):
    """
    Phase 11 Human Verification Workflow & AI Feedback Loop (Password Protected).
    Supports decisions: 'confirm', 'correct', 'needs_review'.
    Original AI predictions remain 100% intact and preserved in database repository.
    """
    try:
        record = DataService.verify_observation_identification(
            obs_id=id,
            decision=req.decision,
            selected_prediction_rank=req.selected_prediction_rank,
            scientific_name=req.scientific_name,
            common_name=req.common_name,
            notes=req.notes
        )
        return record
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_observation(
    id: int,
    auth: str = Depends(verify_ngo_admin_password)
):
    """
    Attempt deletion of an observation record (Password Protected).
    iNaturalist records are permanently read-only reference data and cannot be deleted (HTTP 403).
    """
    try:
        DataService.protect_inaturalist_record(id)
        deleted = DataService.delete_ngo_observation(id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Observation with ID {id} not found.")
        return None
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
