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
import zipfile
from typing import Dict, Any, List, Optional, Tuple
from shapely.geometry import shape, Point

def get_base_dir():
    current = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(current, "..", "..", ".."))

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
                
    # Append NGO created observations if present
    ngo_store_path = os.path.join(get_base_dir(), "data", "processed", "ngo_observations_store.json")
    if os.path.exists(ngo_store_path):
        try:
            with open(ngo_store_path, "r", encoding="utf-8") as f:
                ngo_records = json.load(f)
                records.extend(ngo_records)
        except Exception:
            pass

    return records

DEFAULT_PLANTED_PLANTS = [
    {
        "id": 1,
        "plant_code": "PL-001",
        "source": "Planted Plants",
        "scientific_name": "Ficus religiosa",
        "common_name": "Peepal Tree",
        "planted_on": "2026-01-15",
        "status": "Alive",
        "latitude": 18.5195,
        "longitude": 73.7802,
        "zone_code": "ZONE A",
        "notes": "Healthy baseline plantation specimen",
        "photo_url": None
    },
    {
        "id": 2,
        "plant_code": "PL-002",
        "source": "Planted Plants",
        "scientific_name": "Azadirachta indica",
        "common_name": "Neem Tree",
        "planted_on": "2026-02-10",
        "status": "Alive",
        "latitude": 18.5200,
        "longitude": 73.7808,
        "zone_code": "ZONE B",
        "notes": "Healthy baseline plantation specimen",
        "photo_url": None
    },
    {
        "id": 3,
        "plant_code": "PL-003",
        "source": "Planted Plants",
        "scientific_name": "Santalum album",
        "common_name": "Sandalwood",
        "planted_on": "2026-03-01",
        "status": "Alive",
        "latitude": 18.5190,
        "longitude": 73.7815,
        "zone_code": "ZONE C",
        "notes": "Healthy baseline plantation specimen",
        "photo_url": None
    }
]

def load_planted_plants_store() -> List[Dict[str, Any]]:
    store_path = os.path.join(get_base_dir(), "data", "processed", "planted_plants_store.json")
    if not os.path.exists(store_path):
        return list(DEFAULT_PLANTED_PLANTS)
    try:
        with open(store_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not data:
                return list(DEFAULT_PLANTED_PLANTS)
            return data
    except Exception:
        return list(DEFAULT_PLANTED_PLANTS)

def save_planted_plants_store(records: List[Dict[str, Any]]):
    store_dir = os.path.join(get_base_dir(), "data", "processed")
    os.makedirs(store_dir, exist_ok=True)
    store_path = os.path.join(store_dir, "planted_plants_store.json")
    with open(store_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)

def save_ngo_observations_store(records: List[Dict[str, Any]]):
    store_dir = os.path.join(get_base_dir(), "data", "processed")
    os.makedirs(store_dir, exist_ok=True)
    store_path = os.path.join(store_dir, "ngo_observations_store.json")
    with open(store_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)

def load_monitoring_store() -> List[Dict[str, Any]]:
    return list(DataService._plant_monitoring_repository)

def save_monitoring_store(records: List[Dict[str, Any]]):
    DataService._plant_monitoring_repository = list(records)

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

                total_records = query.count()
                if total_records > 0:
                    limit = max(1, min(limit, 10000))
                    page = max(1, page)
                    total_pages = math.ceil(total_records / limit) if total_records > 0 else 1
                    offset = (page - 1) * limit
                    obs_objs = query.offset(offset).limit(limit).all()

                    data = [
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
                    return data, total_records, total_pages
            except Exception:
                pass

        records = load_clean_csv_records()
        
        # Apply Filters
        filtered = records
        if source:
            filtered = [r for r in filtered if r["source"].lower() == source.lower()]
        if species:
            filtered = [
                r for r in filtered 
                if species.lower() in (r.get("scientific_name") or "").lower() or species.lower() in (r.get("common_name") or "").lower()
            ]
        if zone:
            if zone.upper() in ["ZONE A", "ZONE B", "ZONE C"]:
                filtered = [r for r in filtered if (r.get("zone") or "").upper() == zone.upper()]
            elif zone.upper() == "OUTSIDE":
                filtered = [r for r in filtered if r.get("zone_status") == "OUTSIDE_ACTIVE_ZONES"]
        if quality_grade:
            filtered = [r for r in filtered if (r.get("quality_grade") or "").lower() == quality_grade.lower()]
            
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
                    "photo_url": r.get("photo_url")
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

        assigned_zone = data.get("zone_code") or auto_zone

        new_id = max([r["id"] for r in records], default=0) + 1
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
            "photo_url": safe_str(data.get("photo_url"))
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
            current["zone_code"] = update_data.get("zone_code") or auto_zone

        for field in ["plant_code", "scientific_name", "common_name", "planted_on", "notes", "photo_url"]:
            if field in update_data and update_data[field] is not None:
                current[field] = safe_str(update_data[field])

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
    def create_ngo_observation(data: Dict[str, Any]) -> Dict[str, Any]:
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
        ngo_records = []
        ngo_store_path = os.path.join(get_base_dir(), "data", "processed", "ngo_observations_store.json")
        if os.path.exists(ngo_store_path):
            try:
                with open(ngo_store_path, "r", encoding="utf-8") as f:
                    ngo_records = json.load(f)
            except Exception:
                pass

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

            with open(ngo_store_path, "w", encoding="utf-8") as f:
                json.dump(filtered, f, indent=2)

            return True
        except Exception:
            return False

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
        return DataService.get_map_observations_geojson(source=source, zone=zone)

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
        obs_csv = DataService.export_observations_csv()
        planted_csv = DataService.export_planted_plants_csv()
        species_csv = DataService.export_species_csv()
        obs_geojson = json.dumps(DataService.export_observations_geojson(), indent=2)
        planted_geojson = json.dumps(DataService.export_planted_plants_geojson(), indent=2)

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
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
    def process_photo_upload(
        file_bytes: bytes,
        original_filename: str,
        content_type: str,
        confirm_location: bool = False
    ) -> Dict[str, Any]:
        from app.services.exif_service import validate_upload_file, generate_safe_filename, extract_photo_location
        import datetime

        # 1. File Validation (Extension, MIME, Size)
        validate_upload_file(original_filename, content_type, len(file_bytes))

        # 2. Generate Safe Unique Filename & Save File
        safe_name = generate_safe_filename(original_filename)
        uploads_dir = os.path.join(get_base_dir(), "data", "uploads")
        os.makedirs(uploads_dir, exist_ok=True)
        file_path = os.path.join(uploads_dir, safe_name)

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
                "latitude": lat,
                "longitude": lng,
                "zone": zone_name,
                "zone_status": zone_status,
                "photo_url": f"/uploads/{safe_name}",
                "captured_at": obs_date,
                "status": "pending_confirmation",
                "message": "GPS detected from visible geotag on image. Please confirm coordinates to complete spatial verification."
            }

        # 6. Create NGO Observation Record (for EXIF GPS or Confirmed IMAGE_GEOTAG)
        records = load_clean_csv_records()
        ngo_records = []
        ngo_store_path = os.path.join(get_base_dir(), "data", "processed", "ngo_observations_store.json")
        if os.path.exists(ngo_store_path):
            try:
                with open(ngo_store_path, "r", encoding="utf-8") as f:
                    ngo_records = json.load(f)
            except Exception:
                pass

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
            "zone_status": zone_status
        }

        ngo_records.append(ngo_obs)
        save_ngo_observations_store(ngo_records)

        return {
            "success": True,
            "gps_available": True,
            "gps_source": gps_source,
            "gps_description": gps_description,
            "requires_confirmation": False,
            "observation_id": new_id,
            "source": "NGO / New Upload",
            "latitude": lat,
            "longitude": lng,
            "zone": zone_name,
            "zone_status": zone_status,
            "photo_url": f"/uploads/{safe_name}",
            "captured_at": obs_date,
            "status": "spatially_verified",
            "message": f"Photo observation successfully uploaded and spatially verified via {gps_description} inside {'Zone ' + auto_zone if auto_zone else 'Van Udyan site boundary'}."
        }

    @staticmethod
    def confirm_geotag_observation(
        photo_url: str,
        latitude: float,
        longitude: float,
        observed_on: Optional[str] = None,
        observer: Optional[str] = "RSWF Field Volunteer",
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Creates an NGO observation record for user-confirmed image geotag coordinates.
        Validates spatial location inside Van Udyan before persisting.
        """
        import datetime
        is_inside, auto_zone = validate_coordinates_location(latitude, longitude)
        if not is_inside:
            raise ValueError(f"Confirmed coordinates ({latitude}, {longitude}) are outside the Van Udyan project boundary.")

        records = load_clean_csv_records()
        ngo_records = []
        ngo_store_path = os.path.join(get_base_dir(), "data", "processed", "ngo_observations_store.json")
        if os.path.exists(ngo_store_path):
            try:
                with open(ngo_store_path, "r", encoding="utf-8") as f:
                    ngo_records = json.load(f)
            except Exception:
                pass

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
            "notes": notes
        }

        ngo_records.append(ngo_obs)
        save_ngo_observations_store(ngo_records)

        return {
            "success": True,
            "gps_available": True,
            "gps_source": "IMAGE_GEOTAG",
            "gps_description": "GPS detected from visible geotag on image (User Confirmed)",
            "requires_confirmation": False,
            "observation_id": new_id,
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
        from app.services.exif_service import validate_upload_file, generate_safe_filename, extract_photo_location

        validate_upload_file(original_filename, content_type, len(file_bytes))
        safe_name = generate_safe_filename(original_filename)
        uploads_dir = os.path.join(get_base_dir(), "data", "uploads")
        os.makedirs(uploads_dir, exist_ok=True)
        file_path = os.path.join(uploads_dir, safe_name)

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

        # Resolve local physical image file path
        filename = os.path.basename(photo_url)
        file_path = os.path.join(get_base_dir(), "data", "uploads", filename)

        if not os.path.exists(file_path):
            raise ValueError(f"Image file '{filename}' for observation #{obs_id} was not found on server.")

        # Call Pl@ntNet AI identification service
        ai_res = PlantNetService.identify_plant(file_path, organ=organ)

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

        # 1. Retrieve observation
        records = load_clean_csv_records()
        obs = None
        for r in records:
            if r.get("id") == obs_id:
                obs = r
                break

        if not obs:
            raise ValueError(f"Observation with ID {obs_id} not found.")

        if obs.get("source") == "iNaturalist":
            raise PermissionError(f"Original iNaturalist observation #{obs_id} is read-only reference data and cannot be modified.")

        # 2. Get latest AI prediction from repository
        latest_pred = DataService.get_observation_ai_predictions(obs_id)

        verified_sci = None
        verified_com = None
        status_code = "pending"
        quality_grade = "needs_id"

        if decision_clean == "confirm":
            rank = selected_prediction_rank or 1
            if not latest_pred or "predictions" not in latest_pred or len(latest_pred["predictions"]) == 0:
                raise ValueError(f"No AI predictions available for Observation #{obs_id} to confirm.")
            
            preds_list = latest_pred["predictions"]
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

        # 3. Update NGO Observation Record in Store
        ngo_store_path = os.path.join(get_base_dir(), "data", "processed", "ngo_observations_store.json")
        if os.path.exists(ngo_store_path):
            with open(ngo_store_path, "r", encoding="utf-8") as f:
                ngo_records = json.load(f)

            for r in ngo_records:
                if r.get("id") == obs_id:
                    r["scientific_name"] = verified_sci
                    r["common_name"] = verified_com
                    r["identification_status"] = status_code
                    r["quality_grade"] = quality_grade
                    r["verification_notes"] = notes
                    break

            with open(ngo_store_path, "w", encoding="utf-8") as f:
                json.dump(ngo_records, f, indent=2)

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

        # Store in historical repository
        DataService._plant_monitoring_repository.append(record)

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
