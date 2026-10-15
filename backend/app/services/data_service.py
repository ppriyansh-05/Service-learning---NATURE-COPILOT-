"""
Business Logic Data Service Module
Handles data retrieval, filtering, spatial GeoJSON formatting, dynamic statistics calculation,
Phase 7 Planted Plants & NGO Observations CRUD management, and Phase 8 Dataset Export Generators.
"""

import os
import json
import csv
import math
import io
import re
import zipfile
from typing import Dict, Any, List, Optional, Tuple
from shapely.geometry import shape, Point

from app.services import photo_storage

def get_base_dir():
    current = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(current, "..", "..", ".."))

def _inat_observation_id(value: Any) -> Optional[str]:
    """Extract an iNaturalist observation ID from an ID value or public observation URL."""
    text = str(value or "").strip()
    if not text:
        return None
    match = re.search(r"(?:/observations/|^|:)(\d+)(?:/edit)?(?:[?#].*)?$", text)
    return match.group(1) if match else None


def exclude_linked_inaturalist_observations(
    records: List[Dict[str, Any]],
    ngo_records: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Hide imported iNaturalist copies already linked to NGO-owned records.

    This is a presentation-layer de-duplication only: it never deletes or mutates
    the source CSV, database rows, NGO register, or the observation on iNaturalist.
    Match only on the explicit iNaturalist observation ID/URL, never on species or
    coordinates, because different observations can legitimately share both.
    """
    if ngo_records is None:
        ngo_records = load_ngo_observations_store()

    # Some installations may store the cross-reference on the managed planted
    # plant record instead of the field-observation record. Honour either link.
    linked_records = list(ngo_records or []) + load_planted_plants_store()

    linked_ids = set()
    for ngo_record in linked_records:
        remote_id = _inat_observation_id(ngo_record.get("inaturalist_observation_id"))
        if not remote_id:
            remote_id = _inat_observation_id(ngo_record.get("observation_url"))
        if remote_id:
            linked_ids.add(remote_id)

    if not linked_ids:
        return records

    visible = []
    for record in records:
        if str(record.get("source") or "").strip().lower() == "inaturalist":
            remote_id = _inat_observation_id(record.get("source_id"))
            if not remote_id:
                remote_id = _inat_observation_id(record.get("observation_url"))
            if remote_id and remote_id in linked_ids:
                continue
        visible.append(record)
    return visible


def load_clean_csv_records() -> List[Dict[str, Any]]:
    csv_path = os.path.join(get_base_dir(), "data", "processed", "inaturalist", "observations_van_udyan_clean.csv")
    records = []
    if os.path.exists(csv_path):
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader, start=1):
                records.append({
                    "id": idx,
                    "source": row.get("source", "iNaturalist"),
                    "source_id": str(row.get("observation_id")),
                    "taxon_id": str(row.get("taxon_id", "")),
                    "scientific_name": row.get("scientific_name", ""),
                    "species_name": row.get("species_name", ""),
                    "common_name": row.get("common_name", ""),
                    "taxon_rank": row.get("taxon_rank", ""),
                    "observed_on": row.get("observed_on", ""),
                    "quality_grade": row.get("quality_grade", ""),
                    "observer": row.get("observer", ""),
                    "observation_url": row.get("observation_url", ""),
                    "photo_url": row.get("photo_url", ""),
                    "latitude": float(row.get("latitude", 0.0)),
                    "longitude": float(row.get("longitude", 0.0)),
                    "zone": row.get("zone", ""),
                    "zone_status": row.get("zone_status", "OUTSIDE_ACTIVE_ZONES")
                })
                
    # Append NGO-created observations if present. Keep the NGO register intact,
    # while hiding any iNaturalist API copy that has the same explicitly linked ID.
    ngo_records = []
    ngo_store_path = os.path.join(get_base_dir(), "data", "processed", "ngo_observations_store.json")
    if os.path.exists(ngo_store_path):
        try:
            with open(ngo_store_path, "r", encoding="utf-8") as f:
                ngo_records = json.load(f) or []
                records.extend(ngo_records)
        except Exception:
            pass

    return exclude_linked_inaturalist_observations(records, ngo_records)

DEFAULT_PLANTED_PLANTS = []

def load_planted_plants_store() -> List[Dict[str, Any]]:
    """
    Returns the persisted list of RSWF planted plants. An empty list in the
    store is honoured as a legitimate "no RSWF plantings yet" state — the
    DEFAULT_PLANTED_PLANTS seed is only used when the file is missing or
    unreadable, so clearing the store doesn't silently re-create the demo
    data.
    """
    store_path = os.path.join(get_base_dir(), "data", "processed", "planted_plants_store.json")
    if not os.path.exists(store_path):
        return list(DEFAULT_PLANTED_PLANTS)
    try:
        with open(store_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return list(DEFAULT_PLANTED_PLANTS)
    except Exception:
        return list(DEFAULT_PLANTED_PLANTS)

def _write_store(filename: str, records: Any, sync_key: str):
    """
    Writes a JSON store under data/processed/, then upserts the same blob into Postgres via
    state_sync so it survives redeploys on ephemeral hosts. DB sync is a silent no-op in local-only
    runs (no DATABASE_URL) and in tests.
    """
    store_dir = os.path.join(get_base_dir(), "data", "processed")
    os.makedirs(store_dir, exist_ok=True)
    store_path = os.path.join(store_dir, filename)
    with open(store_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
    from app.services import state_sync
    synced = state_sync.push(sync_key, records)
    if settings_is_production() and not synced:
        # Do not report success for data that only exists on ephemeral container disk.
        # The local file is retained for recovery, but the API must fail visibly.
        raise RuntimeError(
            f"Durable save failed for {sync_key}. The local recovery copy was written, "
            "but the production database sync failed; contact the administrator before retrying."
        )


def settings_is_production() -> bool:
    from app.core.config import settings
    return settings.IS_PRODUCTION

def save_planted_plants_store(records: List[Dict[str, Any]]):
    _write_store("planted_plants_store.json", records, "planted_plants")

def save_ngo_observations_store(records: List[Dict[str, Any]]):
    _write_store("ngo_observations_store.json", records, "ngo_observations")

_monitoring_hydrated = False

def load_monitoring_store() -> List[Dict[str, Any]]:
    """
    Returns the plant-monitoring visits. Hydrates from data/processed/plant_monitoring_store.json
    on first access, so visits logged in previous runs are still visible after a restart.
    """
    global _monitoring_hydrated
    if not _monitoring_hydrated:
        _monitoring_hydrated = True
        store_path = os.path.join(get_base_dir(), "data", "processed", "plant_monitoring_store.json")
        if os.path.exists(store_path):
            try:
                with open(store_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    DataService._plant_monitoring_repository = data
            except Exception:
                pass
    return list(DataService._plant_monitoring_repository)

def save_monitoring_store(records: List[Dict[str, Any]]):
    global _monitoring_hydrated
    _monitoring_hydrated = True
    DataService._plant_monitoring_repository = list(records)
    _write_store("plant_monitoring_store.json", records, "plant_monitoring")

# =====================================================================
# Duplicate Photo Observation Detection
# =====================================================================

# Max dhash bit difference for two photos to count as the same image (recompressed / re-forwarded copy)
DUPLICATE_DHASH_MAX_DISTANCE = 6
# A visually identical photo within this distance of an existing one is the same sighting
DUPLICATE_SAME_SPOT_METERS = 10.0
# Within this radius, two different photos are treated as the SAME physical plant by default.
# A volunteer walking around a tree takes several photos from different angles — we don't want
# each one to become its own observation. The uploader can override with allow_nearby_duplicate
# when two plants really do grow this close together (e.g. dense plantings).
SAME_PLANT_RADIUS_METERS = 0.5

class DuplicateObservationError(ValueError):
    """
    Raised when an uploaded photo matches an existing NGO observation.

    Two flavours of match:
      - `kind="exact"`: the same photo (byte-identical or a near-identical re-encoded copy).
                        No way around this — the backend always rejects it.
      - `kind="nearby"`: a different photo taken within SAME_PLANT_RADIUS_METERS of an existing
                        plant record. The caller can retry with allow_nearby_duplicate=true to
                        tell the backend "this is really a different plant, record it anyway".
    """

    def __init__(self, message: str, existing: Dict[str, Any], kind: str = "exact"):
        super().__init__(message)
        self.existing = existing
        self.kind = kind  # "exact" or "nearby"

    def to_detail(self) -> Dict[str, Any]:
        e = self.existing
        return {
            "message": str(self),
            "duplicate": True,
            "duplicate_kind": self.kind,
            "overridable": self.kind == "nearby",
            "existing_observation_id": e.get("id"),
            "photo_url": e.get("photo_url"),
            "latitude": e.get("latitude"),
            "longitude": e.get("longitude"),
            "zone": e.get("zone") or "Outside Active Zones",
            "observed_on": e.get("observed_on"),
            "scientific_name": e.get("scientific_name"),
            "identification_status": e.get("identification_status"),
        }

def load_ngo_observations_store() -> List[Dict[str, Any]]:
    store_path = os.path.join(get_base_dir(), "data", "processed", "ngo_observations_store.json")
    if not os.path.exists(store_path):
        return []
    try:
        with open(store_path, "r", encoding="utf-8") as f:
            return json.load(f) or []
    except Exception:
        return []

def resolve_upload_path(photo_url: Optional[str]) -> Optional[str]:
    """
    Returns a local file path for the photo referenced by '/uploads/<name>'.
    - Local-storage mode: returns the file inside the uploads directory.
    - Supabase-storage mode: downloads the photo into the uploads directory on first use
      (small cache that survives for the life of the instance), so OCR, fingerprinting and
      Pl@ntNet can keep working with a local path.
    Returns None if the URL is malformed or the photo cannot be found.
    """
    if not photo_url:
        return None
    name = os.path.basename(str(photo_url))
    if not name.startswith("upload_"):
        return None
    local = os.path.join(photo_storage.uploads_dir(), name)
    if os.path.exists(local):
        return local
    if not photo_storage.is_local():
        data = photo_storage.read_bytes(name)
        if data is not None:
            try:
                with open(local, "wb") as f:
                    f.write(data)
                return local
            except OSError:
                return None
    return None

_fingerprint_cache: Dict[Tuple[str, float], Tuple[str, Optional[str]]] = {}

def _record_fingerprint(record: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """Returns a stored record's (sha256, dhash), computing it from its photo file for older records."""
    if record.get("photo_sha256"):
        return record.get("photo_sha256"), record.get("photo_dhash")

    from app.services.exif_service import compute_photo_fingerprint
    path = resolve_upload_path(record.get("photo_url"))
    if not path or not os.path.exists(path):
        return None, None
    key = (path, os.path.getmtime(path))
    if key not in _fingerprint_cache:
        with open(path, "rb") as f:
            _fingerprint_cache[key] = compute_photo_fingerprint(f.read())
    return _fingerprint_cache[key]

def distance_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))

def find_duplicate_photo_observation(
    ngo_records: List[Dict[str, Any]],
    sha256_hex: str,
    dhash_hex: Optional[str],
    lat: Optional[float] = None,
    lng: Optional[float] = None
) -> Optional[Dict[str, Any]]:
    """
    Finds an existing NGO observation for the same photo:
    1. Byte-identical file (same SHA-256), regardless of location.
    2. Visually identical image (dhash within threshold) at the same spot — catches re-compressed copies.
    """
    from app.services.exif_service import dhash_distance

    for rec in ngo_records:
        rec_sha, rec_dhash = _record_fingerprint(rec)
        if rec_sha and rec_sha == sha256_hex:
            return rec
        if lat is None or lng is None or rec.get("latitude") is None or rec.get("longitude") is None:
            continue
        if (dhash_distance(dhash_hex, rec_dhash) <= DUPLICATE_DHASH_MAX_DISTANCE
                and distance_meters(lat, lng, float(rec["latitude"]), float(rec["longitude"])) <= DUPLICATE_SAME_SPOT_METERS):
            return rec
    return None

def find_nearby_observation_ids(ngo_records: List[Dict[str, Any]], lat: float, lng: float,
                                 radius_m: float = SAME_PLANT_RADIUS_METERS) -> List[int]:
    """IDs of existing NGO observations recorded within radius_m of the given coordinates."""
    return [
        rec["id"] for rec in ngo_records
        if rec.get("latitude") is not None and rec.get("longitude") is not None
        and distance_meters(lat, lng, float(rec["latitude"]), float(rec["longitude"])) <= radius_m
    ]

def find_same_plant_observation(ngo_records: List[Dict[str, Any]], lat: float, lng: float) -> Optional[Dict[str, Any]]:
    """Returns the closest existing NGO observation within SAME_PLANT_RADIUS_METERS, or None."""
    closest: Optional[Dict[str, Any]] = None
    closest_d = SAME_PLANT_RADIUS_METERS + 1
    for rec in ngo_records:
        if rec.get("latitude") is None or rec.get("longitude") is None:
            continue
        d = distance_meters(lat, lng, float(rec["latitude"]), float(rec["longitude"]))
        if d <= SAME_PLANT_RADIUS_METERS and d < closest_d:
            closest = rec
            closest_d = d
    return closest

def duplicate_observation_error(existing: Dict[str, Any]) -> DuplicateObservationError:
    return DuplicateObservationError(
        f"This photo has already been uploaded as Observation #{existing['id']} "
        f"({existing.get('zone') or 'Outside Active Zones'}, {existing.get('latitude')}, {existing.get('longitude')}). "
        f"A duplicate observation was not created.",
        existing,
        kind="exact",
    )

def same_plant_error(existing: Dict[str, Any]) -> DuplicateObservationError:
    name = existing.get("common_name") or existing.get("scientific_name") or "a plant"
    return DuplicateObservationError(
        f"A plant ({name}) is already recorded within {SAME_PLANT_RADIUS_METERS:g} metre of "
        f"this spot as Observation #{existing['id']}. Looks like the same plant from a different angle. "
        f"If this really is a different plant, upload again and choose 'record anyway'.",
        existing,
        kind="nearby",
    )

def raise_if_duplicate(ngo_records, sha256_hex, dhash_hex, lat=None, lng=None):
    existing = find_duplicate_photo_observation(ngo_records, sha256_hex, dhash_hex, lat, lng)
    if existing:
        raise duplicate_observation_error(existing)

def filter_observation_records(records, source=None, species=None, zone=None, quality_grade=None) -> List[Dict[str, Any]]:
    """Applies the observation list filters (source, species text, zone, quality grade) to record dicts."""
    filtered = records
    if source:
        filtered = [r for r in filtered if (r.get("source") or "").lower() == source.lower()]
    if species:
        s = species.lower()
        filtered = [r for r in filtered if s in (r.get("scientific_name") or "").lower() or s in (r.get("common_name") or "").lower()]
    if zone:
        if zone.upper() in ["ZONE A", "ZONE B", "ZONE C"]:
            filtered = [r for r in filtered if (r.get("zone") or "").upper() == zone.upper()]
        elif zone.upper() == "OUTSIDE":
            filtered = [r for r in filtered if r.get("zone_status") == "OUTSIDE_ACTIVE_ZONES"]
    if quality_grade:
        filtered = [r for r in filtered if (r.get("quality_grade") or "").lower() == quality_grade.lower()]
    return filtered

def photo_has_geotag_overlay(record: Dict[str, Any], file_path: str) -> bool:
    """
    True when the photo carries a printed geotag box (address, coordinates, map thumbnail):
    its location was read from that box, or its EXIF says it was taken with GPS Map Camera
    (which prints the box even when it also writes EXIF GPS).
    """
    if record.get("gps_source") == "IMAGE_GEOTAG":
        return True
    try:
        from PIL import Image
        exif = Image.open(file_path).getexif()
        # 271 Make, 272 Model, 305 Software, 270 ImageDescription
        text = " ".join(str(exif.get(tag, "")) for tag in (270, 271, 272, 305))
        return "gps map camera" in text.lower()
    except Exception:
        return False

def validate_coordinates_location(lat: float, lng: float) -> Tuple[bool, Optional[str]]:
    boundary_path = os.path.join(get_base_dir(), "data", "raw", "van_udyan_boundary.geojson")
    zones_path = os.path.join(get_base_dir(), "data", "raw", "van_udyan_zones.geojson")

    point = Point(lng, lat)

    # 1. Verify boundary containment
    if os.path.exists(boundary_path):
        with open(boundary_path, "r", encoding="utf-8") as f:
            b_json = json.load(f)
            b_poly = shape(b_json["features"][0]["geometry"])
            if not b_poly.contains(point) and not b_poly.intersects(point):
                return False, None

    # 2. Determine active zone assignment
    assigned_zone = None
    if os.path.exists(zones_path):
        with open(zones_path, "r", encoding="utf-8") as f:
            z_json = json.load(f)
            for feat in z_json.get("features", []):
                z_poly = shape(feat["geometry"])
                if z_poly.contains(point) or z_poly.intersects(point):
                    assigned_zone = feat["properties"]["name"]
                    break

    return True, assigned_zone

class DataService:
    @staticmethod
    def get_observations(
        db_session=None,
        page: int = 1,
        limit: int = 50,
        source: Optional[str] = None,
        species: Optional[str] = None,
        zone: Optional[str] = None,
        quality_grade: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        if db_session is not None:
            try:
                from sqlalchemy import or_
                from app.models.models import Observation
                query = db_session.query(Observation)
                if source:
                    query = query.filter(Observation.source.ilike(source))
                if species:
                    query = query.filter(
                        or_(
                            Observation.scientific_name.ilike(f"%{species}%"),
                            Observation.common_name.ilike(f"%{species}%")
                        )
                    )
                if zone:
                    if zone.upper() in ["ZONE A", "ZONE B", "ZONE C"]:
                        query = query.filter(Observation.zone_code.ilike(zone))
                    elif zone.upper() == "OUTSIDE":
                        query = query.filter(Observation.zone_status == "OUTSIDE_ACTIVE_ZONES")
                if quality_grade:
                    query = query.filter(Observation.quality_grade.ilike(quality_grade))

                obs_objs = query.order_by(Observation.id).all()
                if obs_objs or load_ngo_observations_store():
                    db_rows = [
                        {
                            "id": o.id,
                            "source": o.source,
                            "source_id": str(o.source_id or o.id),
                            "taxon_id": str(o.taxon_id or ""),
                            "scientific_name": o.scientific_name or "",
                            "species_name": o.scientific_name or "",
                            "common_name": o.common_name or "",
                            "taxon_rank": "species",
                            "observed_on": str(o.observed_on) if o.observed_on else "",
                            "quality_grade": o.quality_grade or "",
                            "observer": o.observer or "",
                            "observation_url": o.observation_url or "",
                            "photo_url": o.photo_url or "",
                            "latitude": float(o.latitude) if o.latitude else 0.0,
                            "longitude": float(o.longitude) if o.longitude else 0.0,
                            "zone": o.zone_code or "",
                            "zone_status": o.zone_status or "OUTSIDE_ACTIVE_ZONES"
                        }
                        for o in obs_objs
                    ]
                    # NGO field observations live in the NGO store, not in the database table:
                    # merge them in with the same filters so lists match the overview statistics.
                    db_ids = {r["id"] for r in db_rows}
                    ngo_rows = [r for r in filter_observation_records(load_ngo_observations_store(), source, species, zone, quality_grade)
                                if r.get("id") not in db_ids]
                    combined = exclude_linked_inaturalist_observations(
                        db_rows + ngo_rows,
                        load_ngo_observations_store(),
                    )
                    total_records = len(combined)
                    limit = max(1, min(limit, 10000))
                    page = max(1, page)
                    total_pages = math.ceil(total_records / limit) if total_records > 0 else 1
                    start_idx = (page - 1) * limit
                    return combined[start_idx:start_idx + limit], total_records, total_pages
            except Exception:
                pass

        filtered = filter_observation_records(load_clean_csv_records(), source, species, zone, quality_grade)
        total_records = len(filtered)
        limit = max(1, min(limit, 10000))
        page = max(1, page)
        total_pages = math.ceil(total_records / limit) if total_records > 0 else 1
        
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_data = filtered[start_idx:end_idx]
        
        return paginated_data, total_records, total_pages

    @staticmethod
    def get_observation_by_id(db_session=None, obs_id: int = 0) -> Optional[Dict[str, Any]]:
        if db_session is not None:
            try:
                from app.models.models import Observation
                o = db_session.query(Observation).filter(Observation.id == obs_id).first()
                if o:
                    return {
                        "id": o.id,
                        "source": o.source,
                        "source_id": str(o.source_id or o.id),
                        "taxon_id": str(o.taxon_id or ""),
                        "scientific_name": o.scientific_name or "",
                        "species_name": o.scientific_name or "",
                        "common_name": o.common_name or "",
                        "taxon_rank": "species",
                        "observed_on": str(o.observed_on) if o.observed_on else "",
                        "quality_grade": o.quality_grade or "",
                        "observer": o.observer or "",
                        "observation_url": o.observation_url or "",
                        "photo_url": o.photo_url or "",
                        "latitude": float(o.latitude) if o.latitude else 0.0,
                        "longitude": float(o.longitude) if o.longitude else 0.0,
                        "zone": o.zone_code or "",
                        "zone_status": o.zone_status or "OUTSIDE_ACTIVE_ZONES"
                    }
            except Exception:
                pass

        records = load_clean_csv_records()
        for r in records:
            if r["id"] == obs_id or str(r.get("source_id")) == str(obs_id):
                return r
        return None

    @staticmethod
    def protect_inaturalist_record(obs_id: int):
        obs = DataService.get_observation_by_id(None, obs_id)
        if obs and obs.get("source") == "iNaturalist":
            raise PermissionError("Original iNaturalist records are read-only reference data and cannot be modified or deleted.")

    @staticmethod
    def get_species_list(
        db_session=None,
        page: int = 1,
        limit: int = 50,
        species_name: Optional[str] = None,
        taxon_rank: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        records = load_clean_csv_records()
        
        taxa_dict = {}
        for r in records:
            sc = r.get("scientific_name")
            if not sc:
                continue
            if sc not in taxa_dict:
                taxa_dict[sc] = {
                    "id": len(taxa_dict) + 1,
                    "taxon_id": r.get("taxon_id"),
                    "scientific_name": sc,
                    "species_name": r.get("species_name"),
                    "common_name": r.get("common_name"),
                    "taxon_rank": r.get("taxon_rank"),
                    "record_count": 0
                }
            taxa_dict[sc]["record_count"] += 1
            
        species_list = list(taxa_dict.values())
        
        if species_name:
            species_list = [
                s for s in species_list 
                if species_name.lower() in s["scientific_name"].lower() or species_name.lower() in (s["common_name"] or "").lower()
            ]
        if taxon_rank:
            species_list = [s for s in species_list if (s["taxon_rank"] or "").lower() == taxon_rank.lower()]
            
        total_records = len(species_list)
        limit = max(1, min(limit, 200))
        page = max(1, page)
        total_pages = math.ceil(total_records / limit) if total_records > 0 else 1
        
        start_idx = (page - 1) * limit
        paginated = species_list[start_idx:start_idx + limit]
        
        return paginated, total_records, total_pages

    @staticmethod
    def get_zones_geojson() -> List[Dict[str, Any]]:
        zones_path = os.path.join(get_base_dir(), "data", "raw", "van_udyan_zones.geojson")
        if not os.path.exists(zones_path):
            return []
        with open(zones_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        zones = []
        for idx, feat in enumerate(data.get("features", []), start=1):
            zones.append({
                "id": idx,
                "zone_code": feat["properties"]["name"],
                "status": feat["properties"].get("status", "ACTIVE_ZONE"),
                "description": feat["properties"].get("description", ""),
                "geometry": feat["geometry"]
            })
        return zones

    @staticmethod
    def get_boundary_geojson() -> Dict[str, Any]:
        boundary_path = os.path.join(get_base_dir(), "data", "raw", "van_udyan_boundary.geojson")
        if not os.path.exists(boundary_path):
            return {"type": "FeatureCollection", "features": []}
        with open(boundary_path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def get_map_observations_geojson(
        db_session=None,
        source: Optional[str] = None,
        zone: Optional[str] = None
    ) -> Dict[str, Any]:
        records, _, _ = DataService.get_observations(source=source, zone=zone, limit=10000)
        
        features = []
        for r in records:
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [r["longitude"], r["latitude"]]
                },
                "properties": {
                    "id": r["id"],
                    "source": r["source"],
                    "source_id": r.get("source_id"),
                    "scientific_name": r.get("scientific_name"),
                    "common_name": r.get("common_name"),
                    "observed_on": r.get("observed_on"),
                    "quality_grade": r.get("quality_grade"),
                    "zone": r.get("zone"),
                    "zone_status": r.get("zone_status", "OUTSIDE_ACTIVE_ZONES"),
                    "photo_url": r.get("photo_url"),
                    "observation_type": r.get("observation_type", "sighted")
                }
            })
            
        return {
            "type": "FeatureCollection",
            "name": "Bavdhan_Van_Udyan_Observations_Map",
            "features": features
        }

    @staticmethod
    def get_statistics_overview(db_session=None) -> Dict[str, Any]:
        records = load_clean_csv_records()
        
        total_obs = len(records)
        unique_species = len(set(r["scientific_name"] for r in records if r.get("scientific_name")))
        
        zone_counts = {"ZONE A": 0, "ZONE B": 0, "ZONE C": 0, "OUTSIDE_ACTIVE_ZONES": 0}
        source_counts = {}
        quality_counts = {}
        
        for r in records:
            z = r.get("zone")
            if z in ["ZONE A", "ZONE B", "ZONE C"]:
                zone_counts[z] += 1
            else:
                zone_counts["OUTSIDE_ACTIVE_ZONES"] += 1
                
            src = r.get("source", "iNaturalist")
            source_counts[src] = source_counts.get(src, 0) + 1
            
            q = r.get("quality_grade") or "unspecified"
            quality_counts[q] = quality_counts.get(q, 0) + 1
            
        return {
            "total_observations": total_obs,
            "unique_species_count": unique_species,
            "observations_by_zone": zone_counts,
            "observations_by_source": source_counts,
            "observations_by_quality_grade": quality_counts
        }

    # =====================================================================
    # Phase 7 — Planted Plants CRUD Services
    # =====================================================================

    @staticmethod
    def create_planted_plant(data: Dict[str, Any]) -> Dict[str, Any]:
        records = load_planted_plants_store()
        
        def safe_str(val):
            if val is None:
                return None
            s = str(val).strip()
            return s if s else None

        code = str(data["plant_code"]).strip()
        if any(r["plant_code"].lower() == code.lower() for r in records):
            raise ValueError(f"Plant code '{code}' already exists. Plant codes must be unique.")

        status = data.get("status", "Alive")
        if status not in {"Alive", "Dead", "Unknown"}:
            raise ValueError(f"Invalid status '{status}'. Status must be 'Alive', 'Dead', or 'Unknown'.")

        lat, lng = float(data["latitude"]), float(data["longitude"])
        is_inside, auto_zone = validate_coordinates_location(lat, lng)
        if not is_inside:
            raise ValueError(f"Coordinates ({lat}, {lng}) are outside the Bavdhan Van Udyan project boundary polygon.")

        # Boundary check is authoritative: ignore user-supplied zone_code if it disagrees
        assigned_zone = auto_zone

        new_id = max([r["id"] for r in records], default=0) + 1
        watering_interval = data.get("watering_interval_days")
        if watering_interval is not None:
            watering_interval = int(watering_interval)
        plant_record = {
            "id": new_id,
            "plant_code": code,
            "source": "Planted Plants",
            "scientific_name": safe_str(data.get("scientific_name")),
            "common_name": safe_str(data.get("common_name")),
            "planted_on": safe_str(data.get("planted_on")),
            "status": status,
            "latitude": lat,
            "longitude": lng,
            "zone_code": assigned_zone,
            "notes": safe_str(data.get("notes")),
            "photo_url": safe_str(data.get("photo_url")),
            "watering_interval_days": watering_interval,
            "last_watered_on": safe_str(data.get("last_watered_on")),
        }

        records.append(plant_record)
        save_planted_plants_store(records)
        return plant_record

    @staticmethod
    def get_planted_plants(
        page: int = 1,
        limit: int = 50,
        status: Optional[str] = None,
        zone: Optional[str] = None,
        species: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        records = load_planted_plants_store()

        filtered = records
        if status:
            filtered = [r for r in filtered if r["status"].lower() == status.lower()]
        if zone:
            filtered = [r for r in filtered if (r.get("zone_code") or "").upper() == zone.upper()]
        if species:
            filtered = [
                r for r in filtered
                if species.lower() in (r.get("scientific_name") or "").lower() or species.lower() in (r.get("common_name") or "").lower()
            ]

        total_records = len(filtered)
        limit = max(1, min(limit, 200))
        page = max(1, page)
        total_pages = math.ceil(total_records / limit) if total_records > 0 else 1

        start_idx = (page - 1) * limit
        paginated_data = filtered[start_idx:start_idx + limit]

        return paginated_data, total_records, total_pages

    @staticmethod
    def get_planted_plant_by_id(plant_id: int) -> Optional[Dict[str, Any]]:
        records = load_planted_plants_store()
        for r in records:
            if r["id"] == plant_id or r["plant_code"].lower() == str(plant_id).lower():
                return r
        return None

    @staticmethod
    def update_planted_plant(plant_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
        records = load_planted_plants_store()
        target_idx = None
        for idx, r in enumerate(records):
            if r["id"] == plant_id:
                target_idx = idx
                break

        if target_idx is None:
            raise KeyError(f"Planted plant with ID {plant_id} not found.")

        current = records[target_idx]

        def safe_str(val):
            if val is None:
                return None
            s = str(val).strip()
            return s if s else None

        if "status" in update_data and update_data["status"] is not None:
            st = update_data["status"]
            if st not in {"Alive", "Dead", "Unknown"}:
                raise ValueError(f"Invalid status '{st}'. Status must be 'Alive', 'Dead', or 'Unknown'.")
            current["status"] = st

        new_lat = update_data.get("latitude", current["latitude"])
        new_lng = update_data.get("longitude", current["longitude"])
        if new_lat is not None or new_lng is not None:
            lat_val = float(new_lat) if new_lat is not None else current["latitude"]
            lng_val = float(new_lng) if new_lng is not None else current["longitude"]
            is_inside, auto_zone = validate_coordinates_location(lat_val, lng_val)
            if not is_inside:
                raise ValueError(f"Updated coordinates ({lat_val}, {lng_val}) are outside Van Udyan boundary polygon.")
            current["latitude"] = lat_val
            current["longitude"] = lng_val
            # Boundary check is authoritative on zone assignment
            current["zone_code"] = auto_zone

        for field in ["plant_code", "scientific_name", "common_name", "planted_on", "notes", "photo_url", "last_watered_on"]:
            if field in update_data and update_data[field] is not None:
                current[field] = safe_str(update_data[field])

        if "watering_interval_days" in update_data and update_data["watering_interval_days"] is not None:
            current["watering_interval_days"] = int(update_data["watering_interval_days"])

        current["source"] = "Planted Plants"

        records[target_idx] = current
        save_planted_plants_store(records)
        return current

    @staticmethod
    def delete_planted_plant(plant_id: int) -> bool:
        records = load_planted_plants_store()
        filtered = [r for r in records if r["id"] != plant_id]
        if len(filtered) == len(records):
            return False
        save_planted_plants_store(filtered)
        return True

    @staticmethod
    def create_ngo_observation(data: Dict[str, Any], allow_nearby_duplicate: bool = False) -> Dict[str, Any]:
        lat, lng = float(data["latitude"]), float(data["longitude"])
        is_inside, auto_zone = validate_coordinates_location(lat, lng)
        if not is_inside:
            raise ValueError(f"Coordinates ({lat}, {lng}) are outside Van Udyan project boundary.")

        def safe_str(val):
            if val is None:
                return None
            s = str(val).strip()
            return s if s else None

        records = load_clean_csv_records()
        ngo_records = load_ngo_observations_store()

        # 1-metre same-plant guard — the manual sighting path has to honour the same rule
        # the photo-upload path does, otherwise users can accidentally create duplicate records
        # by typing the same coordinates twice.
        nearby_plant = find_same_plant_observation(ngo_records, lat, lng)
        if nearby_plant and not allow_nearby_duplicate:
            raise same_plant_error(nearby_plant)

        new_id = max([r["id"] for r in records], default=227) + 1

        ngo_obs = {
            "id": new_id,
            "source": "NGO / New Upload",
            "source_id": f"NGO-{new_id}",
            "taxon_id": None,
            "scientific_name": safe_str(data.get("scientific_name")),
            "common_name": safe_str(data.get("common_name")),
            "observed_on": safe_str(data.get("observed_on")),
            "quality_grade": "needs_id",
            "observer": safe_str(data.get("observer")) or "RSWF NGO Volunteer",
            "photo_url": safe_str(data.get("photo_url")),
            "latitude": lat,
            "longitude": lng,
            "zone": auto_zone or "",
            "zone_status": "ACTIVE_ZONE" if auto_zone else "OUTSIDE_ACTIVE_ZONES"
        }

        ngo_records.append(ngo_obs)
        save_ngo_observations_store(ngo_records)
        return ngo_obs

    @staticmethod
    def delete_ngo_observation(obs_id: int) -> bool:
        """Deletes an NGO-created observation record from store (iNaturalist records are read-only)."""
        DataService.protect_inaturalist_record(obs_id)
        ngo_store_path = os.path.join(get_base_dir(), "data", "processed", "ngo_observations_store.json")
        if not os.path.exists(ngo_store_path):
            return False

        try:
            with open(ngo_store_path, "r", encoding="utf-8") as f:
                ngo_records = json.load(f)

            filtered = [r for r in ngo_records if r.get("id") != obs_id]
            if len(filtered) == len(ngo_records):
                return False

            save_ngo_observations_store(filtered)
            return True
        except Exception:
            return False

    @staticmethod
    def update_ngo_observation(obs_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Updates an NGO-created observation record in store (iNaturalist records are read-only)."""
        DataService.protect_inaturalist_record(obs_id)
        ngo_store_path = os.path.join(get_base_dir(), "data", "processed", "ngo_observations_store.json")
        if not os.path.exists(ngo_store_path):
            raise KeyError(f"Observation #{obs_id} not found.")

        with open(ngo_store_path, "r", encoding="utf-8") as f:
            ngo_records = json.load(f)

        target = None
        for r in ngo_records:
            if r.get("id") == obs_id:
                target = r
                break

        if not target:
            raise KeyError(f"Observation #{obs_id} not found.")

        def safe_str(val):
            if val is None:
                return None
            s = str(val).strip()
            return s if s else None

        for field in ["scientific_name", "common_name", "observed_on", "observer", "notes", "quality_grade"]:
            if field in update_data and update_data[field] is not None:
                target[field] = safe_str(update_data[field])

        if "observation_url" in update_data and update_data["observation_url"] is not None:
            url = safe_str(update_data["observation_url"])
            prefix = "https://www.inaturalist.org/observations/"
            observation_id = url[len(prefix):].split("?", 1)[0].split("#", 1)[0].strip("/") if url else ""
            if not url.startswith(prefix) or not observation_id.isdigit():
                raise ValueError("Use a valid iNaturalist observation URL, e.g. https://www.inaturalist.org/observations/123456.")
            target["observation_url"] = url

        if "observation_type" in update_data and update_data["observation_type"] is not None:
            observation_type = safe_str(update_data["observation_type"])
            if observation_type not in {"sighted", "planted_rswf"}:
                raise ValueError("observation_type must be 'sighted' or 'planted_rswf'.")
            target["observation_type"] = observation_type
            # This changes the observation classification only. It does not create or delete
            # a managed planted-plant record or alter existing monitoring history.

        save_ngo_observations_store(ngo_records)
        return target

    # =====================================================================
    # Phase 8 — Dataset Export Generators (CSV, GeoJSON, ZIP)
    # =====================================================================

    @staticmethod
    def export_observations_csv(
        source: Optional[str] = None,
        species: Optional[str] = None,
        zone: Optional[str] = None,
        quality_grade: Optional[str] = None
    ) -> str:
        records, _, _ = DataService.get_observations(
            source=source, species=species, zone=zone, quality_grade=quality_grade, limit=10000
        )
        
        output = io.StringIO()
        fieldnames = [
            "id", "source", "source_id", "taxon_id", "scientific_name", 
            "species_name", "common_name", "taxon_rank", "observed_on", 
            "quality_grade", "observer", "observation_url", "photo_url", 
            "latitude", "longitude", "zone", "zone_status"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()

        for r in records:
            writer.writerow({
                "id": r.get("id"),
                "source": r.get("source"),
                "source_id": r.get("source_id", ""),
                "taxon_id": r.get("taxon_id", ""),
                "scientific_name": r.get("scientific_name", ""),
                "species_name": r.get("species_name", ""),
                "common_name": r.get("common_name", ""),
                "taxon_rank": r.get("taxon_rank", ""),
                "observed_on": r.get("observed_on", ""),
                "quality_grade": r.get("quality_grade", ""),
                "observer": r.get("observer", ""),
                "observation_url": r.get("observation_url", ""),
                "photo_url": r.get("photo_url", ""),
                "latitude": r.get("latitude", 0.0),
                "longitude": r.get("longitude", 0.0),
                "zone": r.get("zone", ""),
                "zone_status": r.get("zone_status", "")
            })

        return output.getvalue()

    @staticmethod
    def export_planted_plants_csv(
        status: Optional[str] = None,
        zone: Optional[str] = None,
        species: Optional[str] = None
    ) -> str:
        records, _, _ = DataService.get_planted_plants(
            status=status, zone=zone, species=species, limit=10000
        )

        output = io.StringIO()
        fieldnames = [
            "id", "plant_code", "source", "scientific_name", "common_name", 
            "planted_on", "status", "latitude", "longitude", "zone_code", 
            "notes", "photo_url"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()

        for r in records:
            writer.writerow({
                "id": r.get("id"),
                "plant_code": r.get("plant_code"),
                "source": r.get("source", "Planted Plants"),
                "scientific_name": r.get("scientific_name", ""),
                "common_name": r.get("common_name", ""),
                "planted_on": r.get("planted_on", ""),
                "status": r.get("status", "Alive"),
                "latitude": r.get("latitude", 0.0),
                "longitude": r.get("longitude", 0.0),
                "zone_code": r.get("zone_code", ""),
                "notes": r.get("notes", ""),
                "photo_url": r.get("photo_url", "")
            })

        return output.getvalue()

    @staticmethod
    def export_species_csv(
        species_name: Optional[str] = None,
        taxon_rank: Optional[str] = None
    ) -> str:
        records, _, _ = DataService.get_species_list(
            species_name=species_name, taxon_rank=taxon_rank, limit=10000
        )

        output = io.StringIO()
        fieldnames = [
            "id", "taxon_id", "scientific_name", "species_name", "common_name", "taxon_rank", "record_count"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()

        for r in records:
            writer.writerow({
                "id": r.get("id"),
                "taxon_id": r.get("taxon_id", ""),
                "scientific_name": r.get("scientific_name", ""),
                "species_name": r.get("species_name", ""),
                "common_name": r.get("common_name", ""),
                "taxon_rank": r.get("taxon_rank", ""),
                "record_count": r.get("record_count", 0)
            })

        return output.getvalue()

    @staticmethod
    def export_observations_geojson(
        source: Optional[str] = None,
        species: Optional[str] = None,
        zone: Optional[str] = None,
        quality_grade: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Observations as a GeoJSON FeatureCollection — the full column set from the CSV, so
        downloads opened in QGIS, Google Earth or Felt show observer, species, source and
        identification state alongside the point.
        """
        records, _, _ = DataService.get_observations(
            source=source, zone=zone, species=species,
            quality_grade=quality_grade, limit=10000,
        )
        features = []
        for r in records:
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [r.get("longitude"), r.get("latitude")],
                },
                "properties": {
                    "id": r.get("id"),
                    "source": r.get("source"),
                    "source_id": r.get("source_id"),
                    "scientific_name": r.get("scientific_name") or None,
                    "common_name": r.get("common_name") or None,
                    "observed_on": r.get("observed_on") or None,
                    "observer": r.get("observer") or None,
                    "quality_grade": r.get("quality_grade") or None,
                    "identification_status": r.get("identification_status") or None,
                    "zone": r.get("zone") or None,
                    "zone_status": r.get("zone_status") or "OUTSIDE_ACTIVE_ZONES",
                    "observation_url": r.get("observation_url") or None,
                    "photo_url": r.get("photo_url") or None,
                },
            })
        return {
            "type": "FeatureCollection",
            "name": "Bavdhan_Van_Udyan_Observations",
            "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
            "features": features,
        }

    @staticmethod
    def export_planted_plants_geojson(
        status: Optional[str] = None,
        zone: Optional[str] = None,
        species: Optional[str] = None
    ) -> Dict[str, Any]:
        records, _, _ = DataService.get_planted_plants(
            status=status, zone=zone, species=species, limit=10000
        )

        features = []
        for r in records:
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [r["longitude"], r["latitude"]]
                },
                "properties": {
                    "id": r["id"],
                    "plant_code": r["plant_code"],
                    "source": r.get("source", "Planted Plants"),
                    "scientific_name": r.get("scientific_name"),
                    "common_name": r.get("common_name"),
                    "planted_on": r.get("planted_on"),
                    "status": r.get("status"),
                    "zone_code": r.get("zone_code"),
                    "notes": r.get("notes"),
                    "photo_url": r.get("photo_url")
                }
            })

        return {
            "type": "FeatureCollection",
            "name": "Bavdhan_Van_Udyan_Planted_Plants",
            "features": features
        }

    @staticmethod
    def export_complete_zip_package() -> bytes:
        """
        Complete dataset archive. Includes a README so recipients understand what each file
        is and how it was produced (open data, no licence restrictions, generated date).
        """
        import datetime as _dt

        obs_csv = DataService.export_observations_csv()
        planted_csv = DataService.export_planted_plants_csv()
        species_csv = DataService.export_species_csv()
        obs_geojson = json.dumps(DataService.export_observations_geojson(), indent=2)
        planted_geojson = json.dumps(DataService.export_planted_plants_geojson(), indent=2)

        readme = (
            "Van Udyan Biodiversity Dataset\n"
            "==============================\n\n"
            f"Generated: {_dt.datetime.now().strftime('%d %B %Y, %H:%M IST')}\n"
            "Source:    Van Udyan Biodiversity Platform, by RSWF (Reform Social Welfare\n"
            "           Foundation), Pune. Live project database.\n"
            "Site:      Bavdhan Van Udyan, Pune, Maharashtra 411021 (Plus Code GQ9J+74Q).\n"
            "Area:      3.58 ha outer boundary; 3 RSWF active work zones (A, B, C).\n\n"
            "Files in this archive\n"
            "---------------------\n"
            "  van_udyan_observations.csv       Every plant record (iNaturalist + RSWF uploads).\n"
            "                                   Columns include scientific_name, observer, zone,\n"
            "                                   observed_on, latitude, longitude, photo_url.\n"
            "  van_udyan_observations.geojson   The same records as GeoJSON points, ready to open\n"
            "                                   in QGIS, Google Earth or Felt. Coordinates in WGS84.\n"
            "  van_udyan_planted_plants.csv     Trees RSWF has planted, with plant codes, species,\n"
            "                                   planting dates and current health status.\n"
            "  van_udyan_planted_plants.geojson Same, as GeoJSON points.\n"
            "  van_udyan_species.csv            Deduplicated species list with observation counts.\n\n"
            "A note on numbers\n"
            "-----------------\n"
            "Record counts measure how often something was observed, not how abundant it is.\n"
            "Areas with no records are monitoring gaps, not areas without plants.\n\n"
            "Credits\n"
            "-------\n"
            "iNaturalist contributors (reference records), Pl@ntNet (AI identification),\n"
            "OpenStreetMap (base map), RSWF volunteers (field photos).\n"
            "Open data — reuse welcome; please credit RSWF when citing.\n"
        )

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr("README.txt", readme)
            zip_file.writestr("van_udyan_observations.csv", obs_csv)
            zip_file.writestr("van_udyan_planted_plants.csv", planted_csv)
            zip_file.writestr("van_udyan_species.csv", species_csv)
            zip_file.writestr("van_udyan_observations.geojson", obs_geojson)
            zip_file.writestr("van_udyan_planted_plants.geojson", planted_geojson)

        return zip_buffer.getvalue()

    # =====================================================================
    # Phase 9 — Photo Upload & EXIF GPS Pipeline
    # =====================================================================

    @staticmethod
    def _register_planted_upload(ngo_observation: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create one management record for an RSWF-planted upload without inventing species/date/health."""
        if ngo_observation.get("observation_type") != "planted_rswf":
            return None

        plants = load_planted_plants_store()
        observation_id = ngo_observation.get("id")
        existing = next(
            (p for p in plants if p.get("source_observation_id") == observation_id),
            None,
        )
        if existing:
            return existing

        zone = str(ngo_observation.get("zone") or "").upper()
        zone_letter = zone[-1] if zone in {"ZONE A", "ZONE B", "ZONE C"} else "X"
        prefix = f"VU-{zone_letter}-"
        used_codes = {
            str(p.get("plant_code") or "").upper()
            for p in plants
        }
        sequence = 1
        while f"{prefix}{sequence:03d}" in used_codes:
            sequence += 1

        plant = {
            "id": max((int(p.get("id", 0)) for p in plants), default=0) + 1,
            "plant_code": f"{prefix}{sequence:03d}",
            "source": "Planted Plants",
            "source_observation_id": observation_id,
            "scientific_name": None,
            "common_name": None,
            "planted_on": None,
            "status": "Unknown",
            "latitude": float(ngo_observation["latitude"]),
            "longitude": float(ngo_observation["longitude"]),
            "zone_code": ngo_observation.get("zone") or None,
            "notes": "Created from RSWF-planted photo upload. Species, planting date, and health require RSWF verification.",
            "photo_url": ngo_observation.get("photo_url"),
            "watering_interval_days": None,
            "last_watered_on": None,
            "identification_status": "needs_review",
        }
        plants.append(plant)
        save_planted_plants_store(plants)
        return plant

    @staticmethod
    def process_photo_upload(
        file_bytes: bytes,
        original_filename: str,
        content_type: str,
        confirm_location: bool = False,
        allow_nearby_duplicate: bool = False,
        observation_type: str = "sighted",
    ) -> Dict[str, Any]:
        from app.services.exif_service import validate_upload_file, generate_content_filename, extract_photo_location, compute_photo_fingerprint
        import datetime

        # 1. File Validation (Extension, MIME, Size)
        validate_upload_file(original_filename, content_type, len(file_bytes))

        # 2. Reject byte-identical re-uploads of an already recorded photo (before running OCR)
        sha256_hex, dhash_hex = compute_photo_fingerprint(file_bytes)
        ngo_records = load_ngo_observations_store()
        raise_if_duplicate(ngo_records, sha256_hex, dhash_hex)

        # 3. Save file under a content-addressed name on local disk so OCR / EXIF can read it.
        # In Supabase mode this stays as a cached copy; the cloud upload happens once we persist.
        safe_name = generate_content_filename(original_filename, sha256_hex)
        file_path = os.path.join(photo_storage.uploads_dir(), safe_name)
        if not os.path.exists(file_path):
            with open(file_path, "wb") as f:
                f.write(file_bytes)

        # 3. Extract GPS Location using Strict NGO Priority:
        # Priority 1: EXIF GPS (bypasses OCR)
        # Priority 2: Visible image geotag overlay (OCR)
        # Priority 3: Location not available
        loc = extract_photo_location(file_path)

        if not loc.get("gps_available") or loc.get("latitude") is None or loc.get("longitude") is None:
            return {
                "success": False,
                "gps_available": False,
                "gps_source": None,
                "gps_description": "Location not available",
                "photo_url": f"/uploads/{safe_name}",
                "latitude": None,
                "longitude": None,
                "message": "Location not available. GPS information could not be found in the photo metadata (EXIF) or visible image geotag."
            }

        lat = loc["latitude"]
        lng = loc["longitude"]
        gps_source = loc["gps_source"]
        gps_description = loc["gps_description"]

        # 4. Geofence Boundary Containment Verification
        is_inside, auto_zone = validate_coordinates_location(lat, lng)
        if not is_inside:
            raise ValueError(f"Uploaded photo location ({lat}, {lng}) is outside the Van Udyan project boundary.")

        # 5. Reject the same image re-compressed / re-forwarded at the same spot
        raise_if_duplicate(ngo_records, sha256_hex, dhash_hex, lat, lng)

        # 5a. Within SAME_PLANT_RADIUS_METERS we treat different photos as the same plant
        # (volunteer walked around the tree). Caller can override with allow_nearby_duplicate=true
        # when two plants really do grow this close (e.g. dense plantings).
        nearby_plant = find_same_plant_observation(ngo_records, lat, lng)
        if nearby_plant and not allow_nearby_duplicate:
            raise same_plant_error(nearby_plant)
        nearby_ids = find_nearby_observation_ids(ngo_records, lat, lng)

        # Persist the photo through the configured backend (Supabase upload in cloud mode).
        # Doing this before the "pending confirmation" return makes sure the confirm step
        # finds the photo even if the backend has restarted in between.
        if not photo_storage.is_local():
            try:
                photo_storage.write_bytes(safe_name, file_bytes, content_type=content_type)
            except Exception as upload_err:
                raise ValueError(f"Could not store photo in cloud storage: {upload_err}") from upload_err

        obs_date = loc.get("captured_at") or datetime.date.today().isoformat()
        zone_name = auto_zone or "Outside Active Zones"
        zone_status = "ACTIVE_ZONE" if auto_zone else "OUTSIDE_ACTIVE_ZONES"

        # 5. Handle Confirmation Requirement
        # For IMAGE_GEOTAG: if user hasn't confirmed yet, stage upload and require user confirmation
        if gps_source == "IMAGE_GEOTAG" and not confirm_location:
            return {
                "success": True,
                "gps_available": True,
                "gps_source": "IMAGE_GEOTAG",
                "gps_description": "GPS detected from visible geotag on image",
                "requires_confirmation": True,
                "observation_id": None,
                "source": "NGO / New Upload",
                "observation_type": observation_type or "sighted",
                "latitude": lat,
                "longitude": lng,
                "zone": zone_name,
                "zone_status": zone_status,
                "photo_url": f"/uploads/{safe_name}",
                "captured_at": obs_date,
                "status": "pending_confirmation",
                "nearby_observation_ids": nearby_ids,
                "message": "GPS detected from visible geotag on image. Please confirm coordinates to complete spatial verification."
            }

        # 7. Create NGO Observation Record (for EXIF GPS or Confirmed IMAGE_GEOTAG)
        records = load_clean_csv_records()
        new_id = max([r["id"] for r in records], default=227) + 1

        ngo_obs = {
            "id": new_id,
            "source": "NGO / New Upload",
            "source_id": f"NGO-UPLOAD-{safe_name.split('.')[0].replace('upload_', '')}",
            "taxon_id": None,
            "scientific_name": None,
            "common_name": None,
            "observed_on": obs_date,
            "quality_grade": "needs_id",
            "observer": "RSWF Field Volunteer",
            "photo_url": f"/uploads/{safe_name}",
            "latitude": lat,
            "longitude": lng,
            "gps_source": gps_source,
            "gps_description": gps_description,
            "zone": auto_zone or "",
            "zone_status": zone_status,
            "photo_sha256": sha256_hex,
            "photo_dhash": dhash_hex,
            "observation_type": observation_type or "sighted",
        }

        ngo_records.append(ngo_obs)
        save_ngo_observations_store(ngo_records)
        planted_record = DataService._register_planted_upload(ngo_obs)

        return {
            "success": True,
            "gps_available": True,
            "gps_source": gps_source,
            "gps_description": gps_description,
            "requires_confirmation": False,
            "observation_id": new_id,
            "plant_code": planted_record.get("plant_code") if planted_record else None,
            "planted_plant_id": planted_record.get("id") if planted_record else None,
            "source": "NGO / New Upload",
            "latitude": lat,
            "longitude": lng,
            "zone": zone_name,
            "zone_status": zone_status,
            "photo_url": f"/uploads/{safe_name}",
            "captured_at": obs_date,
            "status": "spatially_verified",
            "nearby_observation_ids": nearby_ids,
            "message": f"Photo observation successfully uploaded and spatially verified via {gps_description} inside {'Zone ' + auto_zone if auto_zone else 'Van Udyan site boundary'}."
        }

    @staticmethod
    def confirm_geotag_observation(
        photo_url: str,
        latitude: float,
        longitude: float,
        observed_on: Optional[str] = None,
        observer: Optional[str] = "RSWF Field Volunteer",
        notes: Optional[str] = None,
        allow_nearby_duplicate: bool = False,
        observation_type: str = "sighted",
    ) -> Dict[str, Any]:
        """
        Creates an NGO observation record for user-confirmed image geotag coordinates.
        Validates spatial location inside Van Udyan before persisting.
        """
        import datetime
        is_inside, auto_zone = validate_coordinates_location(latitude, longitude)
        if not is_inside:
            raise ValueError(f"Confirmed coordinates ({latitude}, {longitude}) are outside the Van Udyan project boundary.")

        # Guard against confirming the same photo twice (double click, re-upload + re-confirm)
        from app.services.exif_service import compute_photo_fingerprint
        ngo_records = load_ngo_observations_store()
        same_url = next((r for r in ngo_records if photo_url and r.get("photo_url") == photo_url), None)
        if same_url:
            raise duplicate_observation_error(same_url)

        sha256_hex, dhash_hex = None, None
        photo_path = resolve_upload_path(photo_url)
        if photo_path and os.path.exists(photo_path):
            with open(photo_path, "rb") as f:
                sha256_hex, dhash_hex = compute_photo_fingerprint(f.read())
            raise_if_duplicate(ngo_records, sha256_hex, dhash_hex, latitude, longitude)

        # Same 1-metre "same plant" guard that process_photo_upload applies, so the
        # geotag-confirm path can't sneak around it.
        nearby_plant = find_same_plant_observation(ngo_records, latitude, longitude)
        if nearby_plant and not allow_nearby_duplicate:
            raise same_plant_error(nearby_plant)

        records = load_clean_csv_records()
        new_id = max([r["id"] for r in records], default=227) + 1
        obs_date = observed_on or datetime.date.today().isoformat()
        zone_status = "ACTIVE_ZONE" if auto_zone else "OUTSIDE_ACTIVE_ZONES"
        clean_name = os.path.basename(photo_url).split(".")[0].replace("upload_", "")

        ngo_obs = {
            "id": new_id,
            "source": "NGO / New Upload",
            "source_id": f"NGO-GEOTAG-{clean_name}",
            "taxon_id": None,
            "scientific_name": None,
            "common_name": None,
            "observed_on": obs_date,
            "quality_grade": "needs_id",
            "observer": observer or "RSWF Field Volunteer",
            "photo_url": photo_url,
            "latitude": round(latitude, 6),
            "longitude": round(longitude, 6),
            "gps_source": "IMAGE_GEOTAG",
            "gps_description": "GPS detected from visible geotag on image (User Confirmed)",
            "zone": auto_zone or "",
            "zone_status": zone_status,
            "notes": notes,
            "photo_sha256": sha256_hex,
            "photo_dhash": dhash_hex,
            "observation_type": observation_type or "sighted",
        }

        ngo_records.append(ngo_obs)
        save_ngo_observations_store(ngo_records)
        planted_record = DataService._register_planted_upload(ngo_obs)

        return {
            "success": True,
            "gps_available": True,
            "gps_source": "IMAGE_GEOTAG",
            "gps_description": "GPS detected from visible geotag on image (User Confirmed)",
            "requires_confirmation": False,
            "observation_id": new_id,
            "plant_code": planted_record.get("plant_code") if planted_record else None,
            "planted_plant_id": planted_record.get("id") if planted_record else None,
            "source": "NGO / New Upload",
            "latitude": round(latitude, 6),
            "longitude": round(longitude, 6),
            "zone": auto_zone or "Outside Active Zones",
            "zone_status": zone_status,
            "photo_url": photo_url,
            "captured_at": obs_date,
            "status": "spatially_verified",
            "message": f"Geotag observation successfully confirmed and spatially verified inside {'Zone ' + auto_zone if auto_zone else 'Van Udyan site boundary'}."
        }

    @staticmethod
    def inspect_photo_file(file_bytes: bytes, original_filename: str, content_type: str) -> Dict[str, Any]:
        """
        Inspects an uploaded photo file for GPS coordinates (EXIF or visible geotag)
        and checks boundary containment without creating a database observation record.
        """
        from app.services.exif_service import validate_upload_file, generate_content_filename, extract_photo_location, compute_photo_fingerprint

        validate_upload_file(original_filename, content_type, len(file_bytes))
        sha256_hex, _ = compute_photo_fingerprint(file_bytes)
        safe_name = generate_content_filename(original_filename, sha256_hex)
        file_path = os.path.join(photo_storage.uploads_dir(), safe_name)
        if not os.path.exists(file_path):
            with open(file_path, "wb") as f:
                f.write(file_bytes)

        loc = extract_photo_location(file_path)
        lat = loc.get("latitude")
        lng = loc.get("longitude")

        is_inside = False
        zone = None
        if lat is not None and lng is not None:
            is_inside, auto_zone = validate_coordinates_location(lat, lng)
            zone = auto_zone or "Outside Active Zones"

        return {
            "photo_url": f"/uploads/{safe_name}",
            "gps_available": loc.get("gps_available", False),
            "gps_source": loc.get("gps_source"),
            "gps_description": loc.get("gps_description"),
            "requires_confirmation": loc.get("requires_confirmation", False),
            "latitude": lat,
            "longitude": lng,
            "is_inside": is_inside,
            "zone": zone,
            "captured_at": loc.get("captured_at")
        }

    # =====================================================================
    # Phase 10 & 10.1 — Pl@ntNet AI Plant Species Identification Services
    # Database Persistence Repository (PostgreSQL / In-Memory DB Repository)
    # =====================================================================

    _ai_predictions_repository: List[Dict[str, Any]] = []

    @staticmethod
    def identify_observation_plant(obs_id: int, organ: str = "auto") -> Dict[str, Any]:
        from app.services.plantnet_service import PlantNetService
        import datetime

        obs = DataService.get_observation_by_id(obs_id=obs_id)
        if not obs:
            raise ValueError(f"Observation with ID {obs_id} not found.")

        photo_url = obs.get("photo_url")
        if not photo_url:
            raise ValueError(f"Observation ID #{obs_id} does not have an attached photo for AI identification.")

        # Resolve to a local file path (downloads from Supabase on demand in cloud mode)
        file_path = resolve_upload_path(photo_url)
        if not file_path or not os.path.exists(file_path):
            raise ValueError(f"Image file for observation #{obs_id} is not available on the server.")

        # Call Pl@ntNet AI identification service (geotag overlay box removed from the photo first)
        ai_res = PlantNetService.identify_plant(
            file_path, organ=organ, crop_geotag_overlay=photo_has_geotag_overlay(obs, file_path)
        )

        top_pred = ai_res.get("top_prediction") or {}
        prediction_entry = {
            "id": len(DataService._ai_predictions_repository) + 1,
            "observation_id": obs_id,
            "provider": "Pl@ntNet",
            "organ_used": organ,
            "predicted_scientific_name": top_pred.get("scientific_name"),
            "predicted_common_name": top_pred.get("common_name"),
            "confidence_score": top_pred.get("confidence", 0.0),
            "confidence_level": top_pred.get("confidence_level", "LOW CONFIDENCE"),
            "prediction_rank": 1,
            "model_version": "Pl@ntNet-v2",
            "top_3_predictions": ai_res.get("predictions", []),
            "user_confirmed": False,
            "created_at": datetime.datetime.now().isoformat(),
            "status": "ai_suggested" if ai_res.get("success") else "identification_failed",
            "predictions": ai_res.get("predictions", []),
            "ai_response": ai_res
        }

        # Save prediction entry into central database repository (multiple attempts preserved for traceability)
        DataService._ai_predictions_repository.append(prediction_entry)

        return {
            "observation_id": obs_id,
            "identification_status": "ai_suggested" if ai_res.get("success") else "identification_failed",
            "identification_verified": False,
            "provider": "Pl@ntNet",
            "organ_used": organ,
            "top_prediction": ai_res.get("top_prediction"),
            "predictions": ai_res.get("predictions", []),
            "result_summary": ai_res
        }

    @staticmethod
    def get_observation_ai_predictions(obs_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves prediction history for an observation from database repository."""
        matching = [r for r in DataService._ai_predictions_repository if r.get("observation_id") == obs_id]
        if matching:
            return matching[-1] # Return latest prediction attempt
        return None

    @staticmethod
    def verify_observation_identification(
        obs_id: int,
        decision: str = "confirm",
        selected_prediction_rank: Optional[int] = 1,
        scientific_name: Optional[str] = None,
        common_name: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Phase 11 Human Verification Workflow & AI Feedback Loop.
        Supports decisions: 'confirm', 'correct', 'needs_review'.
        Original AI predictions remain 100% intact and preserved in database repository.
        """
        decision_clean = (decision or "confirm").lower().strip()
        if decision_clean not in {"confirm", "correct", "needs_review"}:
            raise ValueError(f"Invalid verification decision '{decision}'. Must be 'confirm', 'correct', or 'needs_review'.")

        # 1. Verification is only for RSWF-owned uploads. Look in that store first
        # so a numeric ID collision with an imported iNaturalist row cannot target the wrong record.
        ngo_records = load_ngo_observations_store()
        obs = next((r for r in ngo_records if r.get("id") == obs_id), None)
        if not obs:
            raise ValueError(
                f"RSWF observation #{obs_id} was not found. Only NGO-uploaded observations can be verified here; "
                "iNaturalist reference records are read-only."
            )

        # 2. Get latest AI prediction from repository
        latest_pred = DataService.get_observation_ai_predictions(obs_id)

        verified_sci = None
        verified_com = None
        status_code = "pending"
        quality_grade = "needs_id"

        if decision_clean == "confirm":
            if scientific_name and scientific_name.strip():
                # Reviewer confirms the species currently suggested on the record
                verified_sci = scientific_name.strip()
                verified_com = common_name.strip() if common_name else obs.get("common_name")
            else:
                rank = selected_prediction_rank or 1
                # Latest in-session AI run first, then suggestions stored on the record (e.g. bulk imports)
                preds_list = (latest_pred or {}).get("predictions") or obs.get("ai_top_predictions") or []
                if not preds_list:
                    raise ValueError(f"No AI predictions available for Observation #{obs_id} to confirm.")
                target_pred = next((p for p in preds_list if p.get("rank") == rank), preds_list[0])
                verified_sci = target_pred.get("scientific_name")
                verified_com = target_pred.get("common_name")
            status_code = "verified"
            quality_grade = "research"

        elif decision_clean == "correct":
            if not scientific_name or not scientific_name.strip():
                raise ValueError("Scientific name is required when submitting a manual species correction.")
            verified_sci = scientific_name.strip()
            verified_com = common_name.strip() if common_name else None
            status_code = "corrected"
            quality_grade = "needs_id"

        elif decision_clean == "needs_review":
            verified_sci = obs.get("scientific_name")
            verified_com = obs.get("common_name")
            status_code = "needs_review"
            quality_grade = "needs_id"

        # 3. Update the NGO store through its shared persistence helper so cloud state
        # sync is updated as well as the local JSON store.
        target = next((r for r in ngo_records if r.get("id") == obs_id), None)
        if not target:
            raise ValueError(f"RSWF observation #{obs_id} not found in NGO store.")

        target["scientific_name"] = verified_sci
        target["common_name"] = verified_com
        target["identification_status"] = status_code
        target["quality_grade"] = quality_grade
        # Strip stale "Not yet confirmed" phrases once the record is reviewed.
        existing_notes = (target.get("verification_notes") or "").strip()
        if decision_clean in ("confirm", "correct"):
            import re as _re
            existing_notes = _re.sub(
                r"Not yet confirmed by RSWF\.?",
                "",
                existing_notes,
                flags=_re.IGNORECASE,
            ).strip(" \n\t.;,")
        review_line = f"Review ({decision_clean}): {notes}" if notes else None
        if review_line and existing_notes:
            target["verification_notes"] = f"{existing_notes}\n{review_line}"
        elif review_line:
            target["verification_notes"] = review_line
        else:
            target["verification_notes"] = existing_notes or None

        save_ngo_observations_store(ngo_records)

        # 4. Update Database Repository Prediction Audit Record (preserving original AI prediction fields intact!)
        import datetime
        if latest_pred:
            latest_pred["user_confirmed"] = (decision_clean == "confirm")
            latest_pred["human_decision"] = decision_clean
            latest_pred["verified_scientific_name"] = verified_sci
            latest_pred["verified_common_name"] = verified_com
            latest_pred["verification_notes"] = notes
            latest_pred["verified_at"] = datetime.datetime.now().isoformat()

        return {
            "observation_id": obs_id,
            "decision": decision_clean,
            "identification_status": status_code,
            "scientific_name": verified_sci,
            "common_name": verified_com,
            "quality_grade": quality_grade,
            "original_ai_prediction": latest_pred.get("predicted_scientific_name") if latest_pred else None,
            "ai_confidence_score": latest_pred.get("confidence_score") if latest_pred else None,
            "verified_at": latest_pred.get("verified_at") if latest_pred else datetime.datetime.now().isoformat(),
            "notes": notes
        }

    @staticmethod
    def confirm_observation_identification(
        obs_id: int,
        scientific_name: str,
        common_name: Optional[str] = None,
        verification_status: str = "verified"
    ) -> Dict[str, Any]:
        """Backwards compatibility alias for confirm decision."""
        return DataService.verify_observation_identification(
            obs_id=obs_id,
            decision="confirm" if verification_status == "verified" else "correct",
            scientific_name=scientific_name,
            common_name=common_name
        )

    @staticmethod
    def get_ai_feedback_metrics() -> Dict[str, Any]:
        """Calculates AI feedback loop performance metrics from database repository records."""
        reviewed = [r for r in DataService._ai_predictions_repository if r.get("human_decision")]
        total = len(reviewed)
        confirmed = sum(1 for r in reviewed if r.get("human_decision") == "confirm")
        corrected = sum(1 for r in reviewed if r.get("human_decision") == "correct")
        needs_review = sum(1 for r in reviewed if r.get("human_decision") == "needs_review")

        conf_rate = f"{round((confirmed / total) * 100, 1)}%" if total > 0 else "0.0%"
        corr_rate = f"{round((corrected / total) * 100, 1)}%" if total > 0 else "0.0%"

        return {
            "total_ai_predictions_reviewed": total,
            "total_confirmed": confirmed,
            "total_corrected": corrected,
            "total_needs_review": needs_review,
            "confirmation_rate_percentage": conf_rate,
            "correction_rate_percentage": corr_rate,
            "evaluation_note": "Verified NGO AI feedback statistics" if total > 0 else "No verified NGO AI evaluation data yet."
        }

    # =====================================================================
    # Phase 12 — Plant Status & Survival Monitoring Services
    # =====================================================================

    _plant_monitoring_repository: List[Dict[str, Any]] = []

    @staticmethod
    def add_plant_monitoring_record(
        plant_id: int,
        status: str,
        monitoring_date: Optional[str] = None,
        notes: Optional[str] = None,
        photo_url: Optional[str] = None,
        observer: Optional[str] = "RSWF Field Team"
    ) -> Dict[str, Any]:
        """
        Creates a new plant condition monitoring visit record.
        Preserves full historical visit records while updating plant current status.
        """
        import datetime

        # 1. Validate status value
        valid_statuses = {"Alive", "Dead", "Unknown"}
        clean_status = (status or "").strip().capitalize()
        if clean_status not in valid_statuses:
            raise ValueError(f"Invalid plant status '{status}'. Allowed values: Alive, Dead, Unknown.")

        # 2. Retrieve plant record
        plants, _, _ = DataService.get_planted_plants(limit=10000)
        plant = next((p for p in plants if p.get("id") == plant_id), None)
        if not plant:
            raise ValueError(f"Planted plant record with ID {plant_id} not found.")

        # 3. Validate monitoring date format YYYY-MM-DD
        m_date = monitoring_date or datetime.date.today().isoformat()
        try:
            datetime.date.fromisoformat(m_date)
        except Exception:
            raise ValueError(f"Invalid monitoring date '{m_date}'. Must be ISO format YYYY-MM-DD.")

        # 4. Create visit record
        record = {
            "id": len(DataService._plant_monitoring_repository) + 1,
            "planted_plant_id": plant_id,
            "plant_code": plant.get("plant_code"),
            "status": clean_status,
            "monitoring_date": m_date,
            "notes": notes,
            "photo_url": photo_url,
            "observer": observer or "RSWF Field Team",
            "created_at": datetime.datetime.now().isoformat()
        }

        # Store in historical repository (hydrate from disk first so appends don't lose prior visits
        # after a restart on an ephemeral host) and persist through the sync layer
        load_monitoring_store()
        DataService._plant_monitoring_repository.append(record)
        save_monitoring_store(DataService._plant_monitoring_repository)

        # 5. Update plant current status in store
        store_path = os.path.join(get_base_dir(), "data", "processed", "planted_plants_store.json")
        if os.path.exists(store_path):
            try:
                with open(store_path, "r", encoding="utf-8") as f:
                    store_records = json.load(f)

                for p in store_records:
                    if p.get("id") == plant_id:
                        p["status"] = clean_status
                        p["updated_at"] = datetime.datetime.now().isoformat()
                        break

                with open(store_path, "w", encoding="utf-8") as f:
                    json.dump(store_records, f, indent=2)
            except Exception:
                pass

        return record

    @staticmethod
    def get_plant_monitoring_history(plant_id: int) -> List[Dict[str, Any]]:
        """Retrieves chronological monitoring history for a planted plant."""
        # Ensure plant exists
        plants, _, _ = DataService.get_planted_plants(limit=10000)
        plant = next((p for p in plants if p.get("id") == plant_id), None)
        if not plant:
            raise ValueError(f"Planted plant record with ID {plant_id} not found.")

        history = [r for r in DataService._plant_monitoring_repository if r.get("planted_plant_id") == plant_id]
        # Sort by monitoring_date ascending
        return sorted(history, key=lambda x: x.get("monitoring_date", ""))

    @staticmethod
    def get_plant_survival_statistics() -> Dict[str, Any]:
        """Calculates dynamic plant survival statistics and zone-wise mortality analytics."""
        plants, total_planted, _ = DataService.get_planted_plants(limit=10000)

        alive_count = sum(1 for p in plants if p.get("status") == "Alive")
        dead_count = sum(1 for p in plants if p.get("status") == "Dead")
        unknown_count = sum(1 for p in plants if p.get("status") == "Unknown")

        denominator = alive_count + dead_count
        survival_rate = f"{round((alive_count / denominator) * 100, 1)}%" if denominator > 0 else "No survival data"

        # Zone-wise status breakdown
        zones = ["ZONE A", "ZONE B", "ZONE C"]
        zone_breakdown = {}

        for z in zones:
            z_plants = [p for p in plants if p.get("zone_code") == z]
            z_total = len(z_plants)
            z_alive = sum(1 for p in z_plants if p.get("status") == "Alive")
            z_dead = sum(1 for p in z_plants if p.get("status") == "Dead")
            z_unk = sum(1 for p in z_plants if p.get("status") == "Unknown")
            z_denom = z_alive + z_dead
            z_rate = f"{round((z_alive / z_denom) * 100, 1)}%" if z_denom > 0 else "No survival data"

            zone_breakdown[z] = {
                "total_planted": z_total,
                "alive": z_alive,
                "dead": z_dead,
                "unknown": z_unk,
                "survival_rate": z_rate
            }

        # Empirical Insights Generation
        insights = []
        if total_planted == 0:
            insights.append("No planted plant records available for analysis.")
        elif denominator == 0:
            insights.append("Survival data is insufficient to compute survival rates.")
        else:
            highest_mortality_zone = None
            max_dead = -1
            for z, data in zone_breakdown.items():
                if data["dead"] > max_dead and data["dead"] > 0:
                    max_dead = data["dead"]
                    highest_mortality_zone = z

            if highest_mortality_zone:
                insights.append(f"{highest_mortality_zone} has the highest recorded plant mortality ({max_dead} dead).")
            else:
                insights.append(f"Overall plant survival rate across Van Udyan active zones stands at {survival_rate}.")

            if dead_count > 0:
                insights.append(f"{dead_count} planted plant(s) recorded as dead require replanting or field inspection.")

        return {
            "total_planted": total_planted,
            "alive_count": alive_count,
            "dead_count": dead_count,
            "unknown_count": unknown_count,
            "survival_rate": survival_rate,
            "zone_breakdown": zone_breakdown,
            "insights": insights
        }
