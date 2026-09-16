"""
Automated Validation Suite for Phase 2 — iNaturalist Data Collection & Spatial Verification
Verifies API response, file presence, CSV structure, ID uniqueness, spatial containment,
zone assignment accuracy, and Phase 1 geography preservation.
"""

import os
import json
import csv
import sys
from shapely.geometry import shape, Point

def validate_phase2():
    print("=" * 70)
    print("      PHASE 2 VALIDATION SUITE — iNATURALIST SPATIAL VERIFICATION")
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
    meta_json_path = os.path.join("data", "raw", "inaturalist", "ingestion_metadata.json")
    proc_csv_path = os.path.join("data", "processed", "inaturalist", "observations_van_udyan.csv")
    boundary_path = os.path.join("data", "raw", "van_udyan_boundary.geojson")
    zones_path = os.path.join("data", "raw", "van_udyan_zones.geojson")
    
    log("File Existence: observations_raw.json", os.path.exists(raw_json_path), raw_json_path)
    log("File Existence: ingestion_metadata.json", os.path.exists(meta_json_path), meta_json_path)
    log("File Existence: observations_van_udyan.csv", os.path.exists(proc_csv_path), proc_csv_path)
    log("File Existence: Phase 1 van_udyan_boundary.geojson", os.path.exists(boundary_path), boundary_path)
    log("File Existence: Phase 1 van_udyan_zones.geojson", os.path.exists(zones_path), zones_path)
    
    # 2. Verify GeoJSON Geometries
    with open(boundary_path, "r", encoding="utf-8") as f:
        boundary_json = json.load(f)
    boundary_shape = shape(boundary_json["features"][0]["geometry"])
    
    with open(zones_path, "r", encoding="utf-8") as f:
        zones_json = json.load(f)
    zones_shapes = {f["properties"]["name"]: shape(f["geometry"]) for f in zones_json["features"]}
    
    log("Phase 1 Boundary Geometry Load", boundary_shape.is_valid, f"Area: {boundary_shape.area:.8f}")
    log("Phase 1 Active Zones Load", len(zones_shapes) == 3, f"Zones: {list(zones_shapes.keys())}")

    # 3. Verify Metadata & Public API (No Auth)
    with open(meta_json_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    api_meta = metadata.get("api_metadata", {})
    
    no_auth = api_meta.get("authentication_required") is False
    log("Public API Authentication Check", no_auth, "Public iNaturalist endpoint worked without API key or auth token")
    
    retrieved_count = api_meta.get("total_retrieved", 0)
    log("Raw API Candidates Retrieved", retrieved_count > 0, f"Retrieved {retrieved_count} candidate records from API")

    # 4. Verify Processed CSV Structure & Field Headers
    expected_headers = [
        "observation_id", "taxon_id", "species_name", "scientific_name", "common_name",
        "taxon_rank", "latitude", "longitude", "observed_on", "quality_grade",
        "observer", "observation_url", "photo_url", "created_at", "updated_at",
        "source", "zone", "zone_status"
    ]
    
    with open(proc_csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        actual_headers = reader.fieldnames
        records = list(reader)
        
    headers_ok = actual_headers == expected_headers
    log("CSV Required Column Schema", headers_ok, f"Total headers: {len(actual_headers)}")
    
    records_cnt = len(records)
    log("Processed Dataset Non-Empty", records_cnt > 0, f"Contains {records_cnt} spatially verified records")

    # 5. Verify Uniqueness of Observation IDs
    obs_ids = [r["observation_id"] for r in records]
    unique_obs_ids = set(obs_ids)
    ids_unique = len(obs_ids) == len(unique_obs_ids)
    log("Observation ID Uniqueness", ids_unique, f"Total IDs: {len(obs_ids)}, Unique: {len(unique_obs_ids)}")

    # 6. Verify Coordinate Order & WGS84 Range
    coords_valid = True
    lat_lng_correct_order = True
    for r in records:
        try:
            lat = float(r["latitude"])
            lng = float(r["longitude"])
            if not (-90 <= lat <= 90 and -180 <= lng <= 180):
                coords_valid = False
            if not (18.0 <= lat <= 19.0 and 73.0 <= lng <= 74.5):
                lat_lng_correct_order = False
        except ValueError:
            coords_valid = False
            
    log("Coordinate Values & WGS84 Range", coords_valid, "All coordinates within valid [-90,90], [-180,180] bounds")
    log("Coordinate Order Check (Lat vs Lng)", lat_lng_correct_order, "Latitude (~18.5°N) and Longitude (~73.78°E) correctly ordered")

    # 7. Verify Spatial Point-in-Polygon Containment (All records MUST be inside Van Udyan)
    all_inside_boundary = True
    outside_records_found = []
    
    for r in records:
        lat = float(r["latitude"])
        lng = float(r["longitude"])
        pt = Point(lng, lat)
        
        inside = boundary_shape.intersects(pt) or boundary_shape.contains(pt)
        if not inside:
            all_inside_boundary = False
            outside_records_found.append(r["observation_id"])
            
    log("Spatial Containment (All Records Inside Van Udyan)", all_inside_boundary, f"Outside count: {len(outside_records_found)}")

    # 8. Verify Zone Assignment Accuracy & Retention of Outside Active Zone Records
    zone_assignment_accurate = True
    zone_counts = {"ZONE A": 0, "ZONE B": 0, "ZONE C": 0, "OUTSIDE_ACTIVE_ZONES": 0}
    
    for r in records:
        lat = float(r["latitude"])
        lng = float(r["longitude"])
        pt = Point(lng, lat)
        
        assigned_zone = r["zone"]
        zone_status = r["zone_status"]
        
        if zone_status == "ACTIVE_ZONE":
            zone_counts[assigned_zone] += 1
            # Check point is actually inside assigned zone geometry
            z_shape = zones_shapes.get(assigned_zone)
            if not z_shape or not (z_shape.intersects(pt) or z_shape.contains(pt)):
                zone_assignment_accurate = False
        elif zone_status == "OUTSIDE_ACTIVE_ZONES":
            zone_counts["OUTSIDE_ACTIVE_ZONES"] += 1
            # Check point is NOT inside any active zone geometry
            for z_shape in zones_shapes.values():
                if z_shape.intersects(pt) or z_shape.contains(pt):
                    zone_assignment_accurate = False
                    break
                    
    log("Zone Assignment Accuracy", zone_assignment_accurate, f"Distribution: {zone_counts}")
    
    outside_zones_retained = zone_counts["OUTSIDE_ACTIVE_ZONES"] > 0
    log("Retention of Outside-Active-Zone Records", outside_zones_retained, f"Retained {zone_counts['OUTSIDE_ACTIVE_ZONES']} valid observations in Van Udyan outside active zones")

    # 9. Verify Safety & Credentials
    no_hardcoded_creds = True
    for fpath in [raw_json_path, meta_json_path, proc_csv_path]:
        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            if "api_key" in content.lower() or "secret_token" in content.lower():
                no_hardcoded_creds = False
    log("No Hardcoded Credentials Check", no_hardcoded_creds, "No fake keys or credentials written to data files")

    print("-" * 70)
    all_passed = all(item[1] for item in results)
    overall_status = "PASSED — ALL PHASE 2 CHECKS SUCCESSFUL" if all_passed else "FAILED — ACTION REQUIRED"
    print(f"OVERALL STATUS: {overall_status}")
    print("=" * 70)
    
    return all_passed

if __name__ == "__main__":
    success = validate_phase2()
    sys.exit(0 if success else 1)
