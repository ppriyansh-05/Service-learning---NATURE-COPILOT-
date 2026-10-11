"""
Plan compliance router — compares planted plants against the Devrai master
grid and surfaces mismatches + spacing warnings.
"""
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response
from app.core.security import verify_ngo_admin_password
from app.services.compliance_service import (
    audit_all,
    heatmap,
    load_calibration,
    load_grid,
    save_calibration,
    spacing_warnings,
)

router = APIRouter(prefix="/compliance", tags=["Plan Compliance"])


@router.get("/grid")
def get_grid():
    """The 400-cell master plan: cell → prescribed species / type / canopy."""
    return load_grid()


@router.get("/calibration")
def get_calibration():
    """Four-corner GPS + grid dims + spacing rules."""
    return load_calibration()


@router.put("/calibration")
def update_calibration(payload: dict = Body(...), auth: str = Depends(verify_ngo_admin_password)):
    """Admin-only: overwrite the calibration (corners, grid dims, spacing)."""
    required = ("corners", "grid")
    for k in required:
        if k not in payload:
            raise HTTPException(status_code=400, detail=f"Missing required key: {k}")
    for cname in ("nw", "ne", "se", "sw"):
        c = payload["corners"].get(cname) or {}
        if "lat" not in c or "lon" not in c:
            raise HTTPException(status_code=400, detail=f"corner {cname} needs lat & lon")
    save_calibration(payload)
    return Response(status_code=204)


@router.get("/audit")
def get_audit():
    """Per-plant status: correct / wrong_species / misplaced_species / outside_plot."""
    return audit_all()


@router.get("/heatmap")
def get_heatmap():
    """400-cell colour/status payload for the Plan Compliance grid view."""
    return heatmap()


@router.get("/spacing-warnings")
def get_spacing_warnings(min_distance_m: float = Query(None, ge=1.0, le=50.0)):
    """Pairs of large-canopy trees planted closer than the configured minimum."""
    return spacing_warnings(min_distance_m=min_distance_m)
