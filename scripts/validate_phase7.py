"""
Automated Phase 7 Validation Suite Script
Verifies Planted Plants CRUD API endpoints, status validation, location boundary checks,
iNaturalist reference record protection, NGO observation creation, and dashboard CRUD UI elements.
"""

import os
import sys
import json
import pytest

# Ensure backend root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app

def validate_phase7():
    print("=" * 70)
    print("      PHASE 7 VALIDATION SUITE — DATA MANAGEMENT & CRUD")
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
        os.path.join("backend", "app", "api", "v1", "planted_plants.py"),
        os.path.join("backend", "tests", "test_crud.py"),
        os.path.join("docs", "phase_7_data_management.md"),
        os.path.join("frontend", "index.html"),
        os.path.join("frontend", "js", "api.js"),
        os.path.join("frontend", "js", "app.js")
    ]
    all_files_exist = all(os.path.exists(f) for f in files_to_check)
    log("Phase 7 Core Architecture Files Existence", all_files_exist, ", ".join(files_to_check))

    # 2. FastAPI TestClient Operations
    client = TestClient(app)
    AUTH_HEADER = {"X-NGO-Admin-Password": "rswf-admin-pass"}

    # 3. Create Planted Plant (POST /api/v1/planted-plants)
    payload = {
        "plant_code": "PL-VAL-100",
        "scientific_name": "Santalum album",
        "common_name": "Sandalwood",
        "planted_on": "2026-08-28",
        "status": "Alive",
        "latitude": 18.5195,
        "longitude": 73.7800,
        "notes": "Validation test sandalwood tree"
    }
    r_create = client.post("/api/v1/planted-plants", json=payload, headers=AUTH_HEADER)
    create_ok = r_create.status_code == 201 and r_create.json().get("plant_code") == "PL-VAL-100"
    log("POST /api/v1/planted-plants (Create Planted Plant)", create_ok, f"Created plant ID: {r_create.json().get('id') if create_ok else 'Failed'}")

    created_id = r_create.json().get("id") if create_ok else None

    # 4. Read Planted Plants List (GET /api/v1/planted-plants)
    r_list = client.get("/api/v1/planted-plants")
    log("GET /api/v1/planted-plants (List Planted Plants)", r_list.status_code == 200 and r_list.json().get("total_records") >= 1)

    # 5. Read Planted Plant Detail (GET /api/v1/planted-plants/{id})
    if created_id:
        r_detail = client.get(f"/api/v1/planted-plants/{created_id}")
        log("GET /api/v1/planted-plants/{id} (Plant Detail)", r_detail.status_code == 200 and r_detail.json().get("plant_code") == "PL-VAL-100")

    # 6. Update Planted Plant Status (PUT /api/v1/planted-plants/{id})
    if created_id:
        r_update = client.put(f"/api/v1/planted-plants/{created_id}", json={"status": "Dead", "notes": "Updated to Dead"}, headers=AUTH_HEADER)
        log("PUT /api/v1/planted-plants/{id} (Update Plant Status)", r_update.status_code == 200 and r_update.json().get("status") == "Dead")

    # 7. Invalid Status Validation Test
    r_bad_status = client.post("/api/v1/planted-plants", json={"plant_code": "PL-BAD-ST", "status": "UnknownStatus", "latitude": 18.5195, "longitude": 73.7800}, headers=AUTH_HEADER)
    log("Status Validation (Rejecting Arbitrary Status Values)", r_bad_status.status_code in [400, 422])

    # 8. Location Geofence Validation Test (Outside Coordinates Rejection)
    r_bad_geo = client.post("/api/v1/planted-plants", json={"plant_code": "PL-OUT", "status": "Alive", "latitude": 19.0760, "longitude": 72.8777}, headers=AUTH_HEADER) # Mumbai coordinates!
    log("Geofence Location Validation (Rejecting Coordinates Outside Van Udyan)", r_bad_geo.status_code == 400)

    # 9. iNaturalist Reference Protection Test
    r_protect = client.delete("/api/v1/observations/1", headers=AUTH_HEADER)
    log("Data Provenance Protection (Preventing Deletion of Original iNaturalist Records)", r_protect.status_code == 403)

    # 10. Delete Planted Plant (DELETE /api/v1/planted-plants/{id})
    if created_id:
        r_del = client.delete(f"/api/v1/planted-plants/{created_id}", headers=AUTH_HEADER)
        log("DELETE /api/v1/planted-plants/{id} (Delete Planted Plant)", r_del.status_code == 204)

    # 11. Create NGO Field Observation (POST /api/v1/observations/ngo)
    r_ngo = client.post("/api/v1/observations/ngo", json={"scientific_name": "Syzygium cumini", "common_name": "Jamun", "latitude": 18.5195, "longitude": 73.7800})
    log("POST /api/v1/observations/ngo (Create NGO Field Sighting)", r_ngo.status_code == 201 and r_ngo.json().get("source") == "NGO / New Upload")

    # 12. Dashboard UI Elements Check
    html_path = os.path.join("frontend", "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        html_text = f.read()
    has_mgmt_tab = 'data-tab="management"' in html_text and 'id="tab-management"' in html_text and 'id="plant-modal"' in html_text
    log("Dashboard Data Management UI Tabs & Modals Defined", has_mgmt_tab)

    print("-" * 70)
    all_passed = all(item[1] for item in results)
    overall_status = "PASSED — ALL PHASE 7 CHECKS SUCCESSFUL" if all_passed else "FAILED — ACTION REQUIRED"
    print(f"OVERALL STATUS: {overall_status}")
    print("=" * 70)
    
    return all_passed

if __name__ == "__main__":
    success = validate_phase7()
    sys.exit(0 if success else 1)
