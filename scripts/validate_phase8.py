"""
Automated Phase 8 Validation Suite Script
Verifies Dataset Export API endpoints (CSV, GeoJSON, ZIP archive), Content-Type and Content-Disposition headers,
query parameter filtering, and dashboard Export UI elements.
"""

import os
import sys
import json
import zipfile
import io

# Ensure backend root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app

def validate_phase8():
    print("=" * 70)
    print("      PHASE 8 VALIDATION SUITE — DATASET EXPORT & DOWNLOAD")
    print("=" * 70)
    
    results = []
    
    def log(test_name, passed, details=""):
        status = "[PASS]" if passed else "[FAIL]"
        results.append((test_name, passed, details))
        print(f"{status} {test_name}")
        if details:
            print(f"       Details: {details}")

    # 1. File & Structure Checks
    files_to_check = [
        os.path.join("backend", "app", "api", "v1", "export.py"),
        os.path.join("backend", "tests", "test_export.py"),
        os.path.join("docs", "phase_8_dataset_export.md"),
        os.path.join("frontend", "index.html"),
        os.path.join("frontend", "js", "api.js"),
        os.path.join("frontend", "js", "app.js")
    ]
    all_files_exist = all(os.path.exists(f) for f in files_to_check)
    log("Phase 8 Core Architecture Files Existence", all_files_exist, ", ".join(files_to_check))

    # 2. FastAPI TestClient Operations
    client = TestClient(app)

    # 3. Observations CSV Export
    r_obs_csv = client.get("/api/v1/export/observations.csv")
    obs_csv_ok = (
        r_obs_csv.status_code == 200 and
        "text/csv" in r_obs_csv.headers.get("content-type", "") and
        "attachment; filename=" in r_obs_csv.headers.get("content-disposition", "") and
        "id,source,source_id" in r_obs_csv.text
    )
    log("GET /api/v1/export/observations.csv (Observations CSV Export)", obs_csv_ok, f"Content-Type: {r_obs_csv.headers.get('content-type')}")

    # 4. Planted Plants CSV Export
    r_planted_csv = client.get("/api/v1/export/planted-plants.csv")
    planted_csv_ok = (
        r_planted_csv.status_code == 200 and
        "text/csv" in r_planted_csv.headers.get("content-type", "") and
        "attachment; filename=" in r_planted_csv.headers.get("content-disposition", "")
    )
    log("GET /api/v1/export/planted-plants.csv (Planted Plants CSV Export)", planted_csv_ok)

    # 5. Species CSV Export
    r_sp_csv = client.get("/api/v1/export/species.csv")
    sp_csv_ok = (
        r_sp_csv.status_code == 200 and
        "text/csv" in r_sp_csv.headers.get("content-type", "") and
        "scientific_name" in r_sp_csv.text
    )
    log("GET /api/v1/export/species.csv (Species Catalog CSV Export)", sp_csv_ok)

    # 6. Observations GeoJSON Export
    r_obs_geo = client.get("/api/v1/export/observations.geojson")
    obs_geo_ok = (
        r_obs_geo.status_code == 200 and
        "application/geo+json" in r_obs_geo.headers.get("content-type", "") and
        r_obs_geo.json().get("type") == "FeatureCollection"
    )
    log("GET /api/v1/export/observations.geojson (Observations GeoJSON Export)", obs_geo_ok)

    # 7. Planted Plants GeoJSON Export
    r_planted_geo = client.get("/api/v1/export/planted-plants.geojson")
    planted_geo_ok = (
        r_planted_geo.status_code == 200 and
        "application/geo+json" in r_planted_geo.headers.get("content-type", "") and
        r_planted_geo.json().get("type") == "FeatureCollection"
    )
    log("GET /api/v1/export/planted-plants.geojson (Planted Plants GeoJSON Export)", planted_geo_ok)

    # 8. Complete ZIP Package Export
    r_zip = client.get("/api/v1/export/package.zip")
    zip_ok = False
    if r_zip.status_code == 200 and "application/zip" in r_zip.headers.get("content-type", ""):
        with zipfile.ZipFile(io.BytesIO(r_zip.content), "r") as z:
            names = z.namelist()
            zip_ok = all(f in names for f in [
                "van_udyan_observations.csv",
                "van_udyan_planted_plants.csv",
                "van_udyan_species.csv",
                "van_udyan_observations.geojson",
                "van_udyan_planted_plants.geojson"
            ])
    log("GET /api/v1/export/package.zip (Complete Dataset ZIP Package)", zip_ok, f"ZIP contains 5 files: {zip_ok}")

    # 9. Query Filtered Export Check
    r_filt = client.get("/api/v1/export/observations.csv?zone=ZONE%20A")
    log("Filtered CSV Export Query (e.g. ?zone=ZONE A)", r_filt.status_code == 200 and "ZONE A" in r_filt.text)

    # 10. Dashboard Export UI Elements Check
    html_path = os.path.join("frontend", "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        html_text = f.read()
    has_export_tab = 'data-tab="export"' in html_text and 'id="tab-export"' in html_text and 'downloadObsExport' in html_text
    log("Dashboard Dataset Export UI Controls Defined", has_export_tab)

    print("-" * 70)
    all_passed = all(item[1] for item in results)
    overall_status = "PASSED — ALL PHASE 8 CHECKS SUCCESSFUL" if all_passed else "FAILED — ACTION REQUIRED"
    print(f"OVERALL STATUS: {overall_status}")
    print("=" * 70)
    
    return all_passed

if __name__ == "__main__":
    success = validate_phase8()
    sys.exit(0 if success else 1)
