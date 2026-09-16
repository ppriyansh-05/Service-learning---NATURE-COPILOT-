"""
Phase 3 — Reproducible iNaturalist Data Cleaning & Standardization Script
Reads Phase 2 dataset (data/processed/inaturalist/observations_van_udyan.csv),
standardizes headers, data types, date representations, and taxonomic fields,
re-validates spatial containment and zone status, generates missing-value analysis,
and outputs data/processed/inaturalist/observations_van_udyan_clean.csv.
"""

import os
import json
import csv
import re
from datetime import datetime
from shapely.geometry import shape, Point

def parse_iso_date(date_str):
    if not date_str or str(date_str).lower() in ["nan", "none", "null", ""]:
        return ""
    date_str = str(date_str).strip()
    # If YYYY-MM-DD format
    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return date_str
    # Try parsing ISO datetime string
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return date_str

def clean_data():
    print("=" * 70)
    print("      VAN UDYAN BIODIVERSITY PLATFORM — PHASE 3 DATA CLEANING")
    print("=" * 70)
    
    input_csv_path = os.path.join("data", "processed", "inaturalist", "observations_van_udyan.csv")
    output_csv_path = os.path.join("data", "processed", "inaturalist", "observations_van_udyan_clean.csv")
    metadata_json_path = os.path.join("data", "processed", "inaturalist", "cleaning_metadata.json")
    
    boundary_geojson_path = os.path.join("data", "raw", "van_udyan_boundary.geojson")
    zones_geojson_path = os.path.join("data", "raw", "van_udyan_zones.geojson")
    
    if not os.path.exists(input_csv_path):
        raise FileNotFoundError(f"Input file missing: {input_csv_path}")
        
    # 1. Load Geometries for Spatial Re-Validation
    with open(boundary_geojson_path, "r", encoding="utf-8") as f:
        boundary_json = json.load(f)
    boundary_shape = shape(boundary_json["features"][0]["geometry"])
    
    with open(zones_geojson_path, "r", encoding="utf-8") as f:
        zones_json = json.load(f)
    zones_shapes = {
        feat["properties"]["name"]: shape(feat["geometry"])
        for feat in zones_json["features"]
    }
    
    # 2. Read Input CSV Records
    with open(input_csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        raw_records = list(reader)
        
    input_count = len(raw_records)
    print(f"Loaded Phase 2 processed CSV: {input_count} records")
    
    # Analyze missing values prior to cleaning
    fields_to_analyze = [
        "taxon_id", "species_name", "scientific_name", "common_name",
        "taxon_rank", "latitude", "longitude", "observed_on",
        "quality_grade", "observer", "photo_url", "zone", "zone_status"
    ]
    
    missing_before = {}
    for field in fields_to_analyze:
        cnt = sum(
            1 for r in raw_records
            if not r.get(field) or str(r.get(field)).strip().lower() in ["nan", "none", "null", ""]
        )
        missing_before[field] = cnt
        
    # 3. Clean & Standardize Records
    cleaned_records = []
    seen_ids = set()
    duplicate_ids = []
    removed_records = []
    
    spatial_fail_cnt = 0
    
    for r in raw_records:
        obs_id_str = str(r.get("observation_id", "")).strip()
        try:
            obs_id = int(float(obs_id_str))
        except ValueError:
            obs_id = obs_id_str
            
        if obs_id in seen_ids:
            duplicate_ids.append(obs_id)
            continue
        seen_ids.add(obs_id)
        
        # Clean Taxon ID
        t_id_raw = str(r.get("taxon_id", "")).strip()
        if t_id_raw and t_id_raw.lower() not in ["nan", "none", "null"]:
            try:
                taxon_id = str(int(float(t_id_raw)))
            except ValueError:
                taxon_id = t_id_raw
        else:
            taxon_id = ""
            
        # Clean Taxonomy Strings
        def clean_str(val):
            if not val or str(val).strip().lower() in ["nan", "none", "null"]:
                return ""
            return str(val).strip()

        species_name = clean_str(r.get("species_name"))
        scientific_name = clean_str(r.get("scientific_name"))
        common_name = clean_str(r.get("common_name"))
        taxon_rank = clean_str(r.get("taxon_rank"))
        quality_grade = clean_str(r.get("quality_grade"))
        observer = clean_str(r.get("observer"))
        obs_url = clean_str(r.get("observation_url"))
        photo_url = clean_str(r.get("photo_url"))
        
        # Clean Coordinates
        try:
            lat = float(r.get("latitude"))
            lng = float(r.get("longitude"))
        except (ValueError, TypeError):
            removed_records.append({"observation_id": obs_id, "reason": "Invalid coordinate numeric format"})
            continue
            
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            removed_records.append({"observation_id": obs_id, "reason": "Coordinate out of WGS84 range"})
            continue
            
        # Re-verify Point-in-Polygon containment
        pt = Point(lng, lat)
        is_inside_boundary = boundary_shape.intersects(pt) or boundary_shape.contains(pt)
        if not is_inside_boundary:
            spatial_fail_cnt += 1
            removed_records.append({"observation_id": obs_id, "reason": "Fails exact Van Udyan spatial boundary check"})
            continue
            
        # Re-verify Zone Assignment
        assigned_zone = None
        for z_name, z_shape in zones_shapes.items():
            if z_shape.intersects(pt) or z_shape.contains(pt):
                assigned_zone = z_name
                break
                
        if assigned_zone:
            zone = assigned_zone
            zone_status = "ACTIVE_ZONE"
        else:
            zone = ""
            zone_status = "OUTSIDE_ACTIVE_ZONES"
            
        # Standardize Dates
        observed_on = parse_iso_date(r.get("observed_on"))
        created_at = clean_str(r.get("created_at"))
        updated_at = clean_str(r.get("updated_at"))
        
        cleaned_record = {
            "observation_id": obs_id,
            "taxon_id": taxon_id,
            "species_name": species_name,
            "scientific_name": scientific_name,
            "common_name": common_name,
            "taxon_rank": taxon_rank,
            "latitude": round(lat, 8),
            "longitude": round(lng, 8),
            "observed_on": observed_on,
            "quality_grade": quality_grade,
            "observer": observer,
            "observation_url": obs_url,
            "photo_url": photo_url,
            "created_at": created_at,
            "updated_at": updated_at,
            "source": "iNaturalist",
            "zone": zone,
            "zone_status": zone_status
        }
        
        cleaned_records.append(cleaned_record)
        
    output_count = len(cleaned_records)
    
    # 4. Analyze Missing Values After Cleaning
    missing_after = {}
    for field in fields_to_analyze:
        cnt = sum(1 for r in cleaned_records if not r.get(field))
        missing_after[field] = cnt

    # 5. Write Output Cleaned CSV
    fieldnames = [
        "observation_id", "taxon_id", "species_name", "scientific_name", "common_name",
        "taxon_rank", "latitude", "longitude", "observed_on", "quality_grade",
        "observer", "observation_url", "photo_url", "created_at", "updated_at",
        "source", "zone", "zone_status"
    ]
    
    with open(output_csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(cleaned_records)
        
    # 6. Generate Metadata JSON
    metadata = {
        "phase": 3,
        "cleaning_timestamp_utc": datetime.utcnow().isoformat() + "Z",
        "input_dataset": input_csv_path,
        "output_dataset": output_csv_path,
        "accounting": {
            "input_record_count": input_count,
            "output_record_count": output_count,
            "duplicates_detected": len(duplicate_ids),
            "spatial_failures_detected": spatial_fail_cnt,
            "records_removed_count": len(removed_records),
            "records_removed_details": removed_records
        },
        "missing_value_analysis": {
            "before_cleaning": missing_before,
            "after_cleaning": missing_after
        },
        "transformations_applied": [
            "Standardized observation_id and taxon_id to clean integer strings",
            "Trimmed whitespace and replaced float NaN/null representations with empty strings",
            "Standardized observed_on date representation to YYYY-MM-DD format",
            "Re-validated spatial containment against WGS84 Van Udyan boundary geometry",
            "Re-validated zone assignments (ZONE A, B, C or OUTSIDE_ACTIVE_ZONES)",
            "Enforced source = 'iNaturalist' data lineage"
        ]
    }
    
    with open(metadata_json_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
        
    print(f"\nPhase 3 Data Cleaning Complete:")
    print(f"  - Input Records: {input_count}")
    print(f"  - Output Records: {output_count}")
    print(f"  - Duplicates Removed: {len(duplicate_ids)}")
    print(f"  - Records Removed: {len(removed_records)}")
    print(f"  - Saved Cleaned CSV: {output_csv_path}")
    print(f"  - Saved Metadata JSON: {metadata_json_path}")
    
    return metadata

if __name__ == "__main__":
    clean_data()
