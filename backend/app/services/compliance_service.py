"""
Plan compliance service.

Compares what's actually planted (NGO observations + planted-plants store)
against the Sacred Grove / Devrai Foundation master plan (20x20 grid of
10 ft x 10 ft cells, each prescribing a specific species).

Produces three reports:
  - audit_all()         — mismatch table (right species? right cell?)
  - heatmap()           — 400-cell colour status for the UI grid
  - spacing_warnings()  — pairs of large-canopy trees planted too close

Grid calibration (four corner GPS + rows/cols/spacing rules) lives in
data/processed/grid_calibration.json and can be hot-edited by the admin.
"""
from __future__ import annotations

import json
import math
import os
from typing import Any, Dict, List, Optional, Tuple

from app.services.data_service import (
    get_base_dir,
    load_ngo_observations_store,
    load_planted_plants_store,
)


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------
def _grid_path() -> str:
    return os.path.join(get_base_dir(), "data", "processed", "grid_cells.json")


def _calibration_path() -> str:
    return os.path.join(get_base_dir(), "data", "processed", "grid_calibration.json")


def _species_path() -> str:
    return os.path.join(get_base_dir(), "data", "processed", "grid_species.json")


def load_grid() -> Dict[str, Any]:
    with open(_grid_path(), "r", encoding="utf-8") as f:
        return json.load(f)


def load_calibration() -> Dict[str, Any]:
    with open(_calibration_path(), "r", encoding="utf-8") as f:
        return json.load(f)


def save_calibration(cal: Dict[str, Any]) -> None:
    with open(_calibration_path(), "w", encoding="utf-8") as f:
        json.dump(cal, f, indent=2, ensure_ascii=False)


def load_species_catalog() -> Dict[str, Any]:
    try:
        with open(_species_path(), "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"species": [], "canopy_classification": {"large": [], "small": []}}


# ---------------------------------------------------------------------------
# Geometry — GPS <-> cell number
# ---------------------------------------------------------------------------
def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0
    phi1 = math.radians(lat1); phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1); dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def cell_for_point(lat: Optional[float], lon: Optional[float],
                   calibration: Optional[Dict[str, Any]] = None) -> Optional[int]:
    """
    Returns the 1..400 cell number that contains (lat, lon), or None if the
    point lies outside the calibrated rectangle. Assumes an axis-aligned
    rectangle in lon/lat; a rotation term can be added later if the real
    plot is skewed relative to true north.
    """
    if lat is None or lon is None:
        return None
    try:
        lat = float(lat); lon = float(lon)
    except (TypeError, ValueError):
        return None

    cal = calibration or load_calibration()
    corners = cal.get("corners") or {}
    rows = int(cal.get("grid", {}).get("rows", 20))
    cols = int(cal.get("grid", {}).get("cols", 20))

    try:
        lat_n = corners["nw"]["lat"]; lon_w = corners["nw"]["lon"]
        lat_s = corners["se"]["lat"]; lon_e = corners["se"]["lon"]
    except (KeyError, TypeError):
        return None

    # Normalise (lat_n > lat_s, lon_e > lon_w)
    if lat_n < lat_s: lat_n, lat_s = lat_s, lat_n
    if lon_e < lon_w: lon_e, lon_w = lon_w, lon_e

    if not (lon_w <= lon <= lon_e and lat_s <= lat <= lat_n):
        return None

    col = int(((lon - lon_w) / (lon_e - lon_w)) * cols)
    # Row 0 is north (top); latitude goes down as row index increases
    row = int(((lat_n - lat) / (lat_n - lat_s)) * rows)

    col = max(0, min(cols - 1, col))
    row = max(0, min(rows - 1, row))
    return row * cols + col + 1


def cell_center(cell: int, calibration: Optional[Dict[str, Any]] = None) -> Optional[Tuple[float, float]]:
    """Returns (lat, lon) at the geometric centre of the given cell."""
    if not (1 <= cell <= 400):
        return None
    cal = calibration or load_calibration()
    corners = cal.get("corners") or {}
    rows = int(cal.get("grid", {}).get("rows", 20))
    cols = int(cal.get("grid", {}).get("cols", 20))
    try:
        lat_n = corners["nw"]["lat"]; lon_w = corners["nw"]["lon"]
        lat_s = corners["se"]["lat"]; lon_e = corners["se"]["lon"]
    except (KeyError, TypeError):
        return None
    if lat_n < lat_s: lat_n, lat_s = lat_s, lat_n
    if lon_e < lon_w: lon_e, lon_w = lon_w, lon_e

    idx = cell - 1
    row = idx // cols
    col = idx % cols
    lon = lon_w + ((col + 0.5) / cols) * (lon_e - lon_w)
    lat = lat_n - ((row + 0.5) / rows) * (lat_n - lat_s)
    return lat, lon


# ---------------------------------------------------------------------------
# Data collection — planted plants + NGO observations
# ---------------------------------------------------------------------------
def _collect_planted() -> List[Dict[str, Any]]:
    """Combined list of plants and NGO observations that have GPS."""
    out: List[Dict[str, Any]] = []
    for p in load_planted_plants_store():
        if p.get("latitude") is None or p.get("longitude") is None:
            continue
        out.append({
            "source": "planted",
            "id": p.get("id"),
            "label": p.get("plant_code") or f"PL-{p.get('id')}",
            "scientific_name": (p.get("scientific_name") or "").strip(),
            "common_name": (p.get("common_name") or "").strip(),
            "latitude": p.get("latitude"),
            "longitude": p.get("longitude"),
            "zone_code": p.get("zone_code"),
            "grid_cell_override": p.get("grid_cell"),  # manual override if present
        })
    for o in load_ngo_observations_store():
        if o.get("latitude") is None or o.get("longitude") is None:
            continue
        out.append({
            "source": "ngo",
            "id": o.get("id"),
            "label": f"OBS-{o.get('id')}",
            "scientific_name": (o.get("scientific_name") or "").strip(),
            "common_name": (o.get("common_name") or "").strip(),
            "latitude": o.get("latitude"),
            "longitude": o.get("longitude"),
            "zone_code": o.get("zone") or o.get("zone_code"),
            "grid_cell_override": o.get("grid_cell"),
        })
    return out


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------
def _norm(s: Optional[str]) -> str:
    return (s or "").strip().lower()


def audit_all() -> Dict[str, Any]:
    """Compare every planted record against the master plan."""
    cal = load_calibration()
    grid = load_grid()
    cells_by_num = {c["cell"]: c for c in grid["cells"]}
    plants = _collect_planted()

    # Index: scientific_name (lowered) -> list of cells it belongs to
    rightful_cells: Dict[str, List[int]] = {}
    for c in grid["cells"]:
        sci = _norm(c.get("scientific_name"))
        if sci:
            rightful_cells.setdefault(sci, []).append(c["cell"])

    # Index: cell -> count of plants currently in it
    occupied: Dict[int, int] = {}

    rows: List[Dict[str, Any]] = []
    for p in plants:
        cell = p.get("grid_cell_override")
        if cell is None:
            cell = cell_for_point(p["latitude"], p["longitude"], cal)
        if cell:
            occupied[cell] = occupied.get(cell, 0) + 1

        prescribed = cells_by_num.get(cell) if cell else None
        pres_sci = prescribed.get("scientific_name") if prescribed else None
        pres_type = prescribed.get("type") if prescribed else None

        if cell is None:
            status = "outside_plot"
        elif pres_type in ("void", "non_plantable"):
            status = "non_plantable_cell"
        elif not pres_sci:
            status = "empty_cell"
        elif _norm(pres_sci) == _norm(p["scientific_name"]):
            status = "correct"
        elif _norm(p["scientific_name"]) in rightful_cells:
            status = "misplaced_species"  # right species but in wrong cell
        else:
            status = "wrong_species"

        suggested = rightful_cells.get(_norm(p["scientific_name"]), [])

        rows.append({
            "source": p["source"],
            "id": p["id"],
            "label": p["label"],
            "scientific_name": p["scientific_name"] or None,
            "common_name": p["common_name"] or None,
            "latitude": p["latitude"],
            "longitude": p["longitude"],
            "zone_code": p["zone_code"],
            "cell": cell,
            "prescribed_species": pres_sci,
            "prescribed_marathi": prescribed.get("marathi_name") if prescribed else None,
            "prescribed_type": pres_type,
            "status": status,
            "rightful_cells_for_species": suggested,
        })

    summary = {
        "total": len(rows),
        "correct": sum(1 for r in rows if r["status"] == "correct"),
        "wrong_species": sum(1 for r in rows if r["status"] == "wrong_species"),
        "misplaced_species": sum(1 for r in rows if r["status"] == "misplaced_species"),
        "empty_cell": sum(1 for r in rows if r["status"] == "empty_cell"),
        "non_plantable_cell": sum(1 for r in rows if r["status"] == "non_plantable_cell"),
        "outside_plot": sum(1 for r in rows if r["status"] == "outside_plot"),
    }
    return {"rows": rows, "summary": summary, "cells_filled_in_plan": sum(1 for c in grid["cells"] if c.get("scientific_name"))}


def heatmap() -> Dict[str, Any]:
    """
    400 cells with one of: planted-correct, planted-wrong, missing-plant,
    non-plantable, void. Powers the Plan Compliance grid view.
    """
    cal = load_calibration()
    grid = load_grid()
    cells_by_num = {c["cell"]: c for c in grid["cells"]}

    occupant: Dict[int, List[Dict[str, Any]]] = {}
    for p in _collect_planted():
        cell = p.get("grid_cell_override") or cell_for_point(p["latitude"], p["longitude"], cal)
        if cell:
            occupant.setdefault(cell, []).append({
                "source": p["source"], "id": p["id"], "label": p["label"],
                "scientific_name": p["scientific_name"] or None,
            })

    out: List[Dict[str, Any]] = []
    for n in range(1, 401):
        cell = cells_by_num.get(n, {})
        pres = cell.get("scientific_name")
        type_ = cell.get("type") or "void"
        here = occupant.get(n, [])

        if type_ in ("void", "non_plantable"):
            status = "non_plantable" if type_ == "non_plantable" else "void"
        elif here and any(_norm(x.get("scientific_name")) == _norm(pres) for x in here):
            status = "correct"
        elif here:
            status = "wrong"
        else:
            status = "missing"

        out.append({
            "cell": n,
            "prescribed": pres,
            "prescribed_marathi": cell.get("marathi_name"),
            "prescribed_type": type_,
            "status": status,
            "occupants": here,
            "note": cell.get("note"),
        })
    return {"cells": out, "calibration": cal}


def spacing_warnings(min_distance_m: Optional[float] = None) -> Dict[str, Any]:
    """
    Pairs of large-canopy trees that are closer than the configured minimum.
    Default minimum = calibration.spacing_rules.large_canopy_min_m or 6 m.
    """
    cal = load_calibration()
    min_d = min_distance_m or cal.get("spacing_rules", {}).get("large_canopy_min_m", 6.0)
    catalog = load_species_catalog()
    large = set((s or "").lower() for s in (catalog.get("canopy_classification", {}).get("large") or []))

    big = []
    for p in _collect_planted():
        sci = _norm(p["scientific_name"])
        if sci and sci in large:
            big.append(p)

    warnings = []
    for i in range(len(big)):
        for j in range(i + 1, len(big)):
            a, b = big[i], big[j]
            d = _haversine_m(a["latitude"], a["longitude"], b["latitude"], b["longitude"])
            if d < min_d:
                warnings.append({
                    "a": {"source": a["source"], "id": a["id"], "label": a["label"], "scientific_name": a["scientific_name"]},
                    "b": {"source": b["source"], "id": b["id"], "label": b["label"], "scientific_name": b["scientific_name"]},
                    "distance_m": round(d, 2),
                    "limit_m": min_d,
                })
    warnings.sort(key=lambda w: w["distance_m"])
    return {"min_distance_m": min_d, "pairs": warnings, "large_canopy_species_count": len(big)}
