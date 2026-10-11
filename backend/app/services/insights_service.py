"""
Insights Service — species profiles + verification queue.

Pure analytics on top of the existing observation stores. No new data
sources, no DB migrations.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any, Dict, List

from app.services.data_service import (
    load_clean_csv_records,
    load_planted_plants_store,
    load_ngo_observations_store,
)


# ---------------------------------------------------------------------------
# Species profile
# ---------------------------------------------------------------------------
def _norm_name(s: str) -> str:
    return (s or "").strip().lower()


def species_profile(scientific_name: str) -> Dict[str, Any]:
    key = _norm_name(scientific_name)
    if not key:
        return {"found": False}

    all_obs = load_clean_csv_records()
    matches = [r for r in all_obs if _norm_name(r.get("scientific_name")) == key]
    if not matches:
        return {"found": False, "scientific_name": scientific_name}

    # Common name — pick most-frequent non-empty
    cn_counter = Counter(r.get("common_name") or "" for r in matches if r.get("common_name"))
    common_name = cn_counter.most_common(1)[0][0] if cn_counter else None

    # Zone distribution
    zones = Counter((r.get("zone") or "OUTSIDE").upper() for r in matches)

    # Source split
    sources = Counter(r.get("source") or "iNaturalist" for r in matches)

    # Phenology — observations per calendar month (1-12)
    phen = Counter()
    first_seen = None
    last_seen = None
    for r in matches:
        d = r.get("observed_on")
        if not d:
            continue
        try:
            dt = datetime.strptime(d, "%Y-%m-%d")
            phen[dt.month] += 1
            if first_seen is None or dt < first_seen:
                first_seen = dt
            if last_seen is None or dt > last_seen:
                last_seen = dt
        except ValueError:
            continue

    # Verified status split
    status_counter = Counter((r.get("identification_status") or r.get("quality_grade") or "unknown").lower() for r in matches)

    # Also-planted check — do we have any planted plants of this species?
    plants = [p for p in load_planted_plants_store() if _norm_name(p.get("scientific_name")) == key]

    # Pin coords for mini-map
    pins = []
    for r in matches:
        lat, lon = r.get("latitude"), r.get("longitude")
        try:
            lat_f, lon_f = float(lat), float(lon)
            if lat_f and lon_f:
                pins.append({
                    "id": r.get("id"),
                    "lat": lat_f,
                    "lon": lon_f,
                    "zone": (r.get("zone") or "").upper(),
                    "observed_on": r.get("observed_on"),
                    "source": r.get("source"),
                    "photo_url": r.get("photo_url"),
                })
        except (TypeError, ValueError):
            continue

    # Rarity label — crude: fewer than 3 sightings = rare, 4-10 = uncommon, else common
    n = len(matches)
    if n < 3:
        rarity = "rare"
    elif n <= 10:
        rarity = "uncommon"
    elif n <= 50:
        rarity = "common"
    else:
        rarity = "very_common"

    return {
        "found": True,
        "scientific_name": matches[0].get("scientific_name") or scientific_name,
        "common_name": common_name,
        "total_observations": n,
        "first_seen": first_seen.strftime("%Y-%m-%d") if first_seen else None,
        "last_seen": last_seen.strftime("%Y-%m-%d") if last_seen else None,
        "rarity": rarity,
        "zones": [{"zone": z, "count": c} for z, c in zones.most_common()],
        "sources": [{"source": s, "count": c} for s, c in sources.most_common()],
        "phenology": [{"month": m, "count": phen.get(m, 0)} for m in range(1, 13)],
        "status_breakdown": [{"status": k, "count": v} for k, v in status_counter.most_common()],
        "planted_count": len(plants),
        "pins": pins,
    }


# ---------------------------------------------------------------------------
# Verification queue
# ---------------------------------------------------------------------------
def verification_queue(limit: int = 50) -> List[Dict[str, Any]]:
    """Returns NGO observations awaiting review (anything not yet confirmed/corrected)."""
    rows = load_ngo_observations_store()
    out: List[Dict[str, Any]] = []
    for r in rows:
        status = (r.get("identification_status") or "").lower()
        qg = (r.get("quality_grade") or "").lower()
        if status in ("verified", "corrected", "needs_review"):
            # already acted on — skip (except needs_review which stays)
            if status != "needs_review":
                continue
        if qg == "research":
            continue
        out.append({
            "id": r.get("id"),
            "scientific_name": r.get("scientific_name"),
            "common_name": r.get("common_name"),
            "observed_on": r.get("observed_on"),
            "observer": r.get("observer"),
            "latitude": r.get("latitude"),
            "longitude": r.get("longitude"),
            "zone": r.get("zone"),
            "zone_code": r.get("zone_code"),
            "photo_url": r.get("photo_url"),
            "notes": r.get("notes") or r.get("verification_notes"),
            "ai_prediction": None,  # populated below if present
        })
        if len(out) >= limit:
            break
    return out
