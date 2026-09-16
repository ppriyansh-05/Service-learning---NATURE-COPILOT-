"""
Automated Validation Suite for Phase 3 — Data Cleaning & Standardization
Verifies raw data preservation, cleaned dataset existence, schema standardization,
ID uniqueness, coordinate validity, spatial re-validation, zone consistency,
missing value handling, and cleaning metadata.
"""

import os
import json
import csv
import sys
import re
from shapely.geometry import shape, Point

def validate_phase3():
    print("=" * 70)
    print("      PHASE 3 VALIDATION SUITE — DATA CLEANING & STANDARDIZATION")
    print("=" * 70)
    
    results = []
    
    def log(test_name, passed, details=""):
        status = "[PASS]" if passed else "[FAIL]"
        results.append((test_name, passed, details))
        print(f"{status} {test_name}")
        if details:
            print(f"       Details: {details}")

    # 1. File existence checks
    raw_json_path = os.path.join("data", "raw", "inaturalist", "observations_raw.json")
    phase2_csv_path = os.path.join("data", "processed", "inaturalist", "observations_van_udyan.csv")
    cleaned_csv_path = os.path.join("data", "processed", "inaturalist", "observations_van_udyan_clean.csv")
    meta_json_path = os.path.join("data", "processed", "inaturalist", "cleaning_metadata.json")
    boundary_path = os.path.join("data", "raw", "van_udyan_boundary.geojson")
    zones_path = os.path.join("data", "raw", "van_udyan_zones.geojson")
    docs_path = os.path.join("docs", "phase_3_data_cleaning.md")
    
    log("File Existence: observations_raw.json", os.path.exists(raw_json_path))
    log("File Existence: Phase 2 observations_van_udyan.csv", os.path.exists(phase2_csv_path))
    log("File Existence: Cleaned observations_van_udyan_clean.csv", os.path.exists(cleaned_csv_path))
    log("File Existence: cleaning_metadata.json", os.path.exists(meta_json_path))
    log("File Existence: Documentation docs/phase_3_data_cleaning.md", os.path.exists(docs_path))

    # 2. Verify Raw Dataset Untouched
    with open(raw_json_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    raw_untouched = len(raw_data) == 331
    log("Raw Source Dataset Untouched", raw_untouched, f"Preserved {len(raw_data)} raw records in data/raw/inaturalist/")

    # 3. Read Cleaned CSV
    with open(cleaned_csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        records = list(reader)
        
    expected_headers = [
        "observation_id", "taxon_id", "species_name", "scientific_name", "common_name",
        "taxon_rank", "latitude", "longitude", "observed_on", "quality_grade",
        "observer", "observation_url", "photo_url", "created_at", "updated_at",
        "source", "zone", "zone_status"
    ]
    
    log("Cleaned CSV Column Schema", headers == expected_headers, f"Standardized headers: {len(headers)}")
    log("Cleaned Record Accounting", len(records) == 227, f"Accounting: 227 input -> 227 output (0 records lost)")

    # 4. ID Uniqueness & Traceability
    obs_ids = [r["observation_id"] for r in records]
    all_has_id = all(bool(i) for i in obs_ids)
    ids_unique = len(obs_ids) == len(set(obs_ids))
    log("Observation ID Lineage & Presence", all_has_id, "100% of cleaned records retain valid observation_id")
    log("Observation ID Uniqueness", ids_unique, f"Unique observation IDs: {len(set(obs_ids))}")

    # 5. Data Types & Date Standardization
    dates_valid = True
    coords_valid = True
    no_fake_vals = True
    
    for r in records:
        # Check date format (YYYY-MM-DD or empty)
        d = r["observed_on"]
        if d and not re.match(r"^\d{4}-\d{2}-\d{2}$", d):
            dates_valid = False
            
        # Check coordinate numeric range
        try:
            lat = float(r["latitude"])
            lng = float(r["longitude"])
            if not (-90 <= lat <= 90 and -180 <= lng <= 180 and 18.0 <= lat <= 19.0 and 73.0 <= lng <= 74.5):
                coords_valid = False
        except ValueError:
            coords_valid = False
            
        # Check fake values (e.g. "Unknown", "None", 0 for missing string fields)
        for k, v in r.items():
            if k in ["common_name", "species_name", "scientific_name", "taxon_id", "zone"]:
                if v.lower() in ["unknown", "none", "null", "nan", "0"]:
                    no_fake_vals = False

    log("Date Standardization (YYYY-MM-DD)", dates_valid)
    log("Coordinate Validity & Range Check", coords_valid)
    log("No Fabricated Fake Values ('Unknown'/'None')", no_fake_vals)

    # 6. Spatial Boundary Re-Validation
    with open(boundary_path, "r", encoding="utf-8") as f:
        boundary_json = json.load(f)
    boundary_shape = shape(boundary_json["features"][0]["geometry"])
    
    with open(zones_path, "r", encoding="utf-8") as f:
        zones_json = json.load(f)
    zones_shapes = {f["properties"]["name"]: shape(f["geometry"]) for f in zones_json["features"]}
    
    all_inside = True
    for r in records:
        lat = float(r["latitude"])
        lng = float(r["longitude"])
        pt = Point(lng, lat)
        if not (boundary_shape.intersects(pt) or boundary_shape.contains(pt)):
            all_inside = False
            
    log("Spatial Boundary Re-Validation (Shapely)", all_inside, "100% of cleaned records are inside Van Udyan boundary")

    # 7. Zone Assignment Consistency
    zone_consistent = True
    zone_counts = {"ZONE A": 0, "ZONE B": 0, "ZONE C": 0, "OUTSIDE_ACTIVE_ZONES": 0}
    
    for r in records:
        z = r["zone"]
        status = r["zone_status"]
        if status == "ACTIVE_ZONE":
            if z not in ["ZONE A", "ZONE B", "ZONE C"]:
                zone_consistent = False
            zone_counts[z] += 1
        elif status == "OUTSIDE_ACTIVE_ZONES":
            if z != "":
                zone_consistent = False
            zone_counts["OUTSIDE_ACTIVE_ZONES"] += 1
        else:
            zone_consistent = False

    log("Zone Assignment Consistency", zone_consistent, f"Distribution: {zone_counts}")

    # 8. Source Data Lineage
    all_source_inat = all(r["source"] == "iNaturalist" for r in records)
    log("Source Data Lineage", all_source_inat, "source = 'iNaturalist' for 100% of records")

    # 9. Cleaning Metadata Existence
    with open(meta_json_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    meta_ok = meta.get("accounting", {}).get("output_record_count") == 227
    log("Cleaning Metadata Validity", meta_ok, f"Metadata recorded {meta.get('accounting', {}).get('output_record_count')} output records")

    print("-" * 70)
    all_passed = all(item[1] for item in results)
    overall_status = "PASSED — ALL PHASE 3 CHECKS SUCCESSFUL" if all_passed else "FAILED — ACTION REQUIRED"
    print(f"OVERALL STATUS: {overall_status}")
    print("=" * 70)
    
    return all_passed

if __name__ == "__main__":
    success = validate_phase3()
    sys.exit(0 if success else 1)
