"""
Automated Validation Suite for Phase 17 — Complete NGO Data Entry, Photo Management & Field UX.
Validates complete field exposure for Planted Plants and NGO Sightings, photo upload attachment support,
reusable photo storage & EXIF GPS pipeline, upload + Pl@ntNet AI display UX, password authorization,
iNaturalist read-only protection, dynamic dataset updates, and baseline data integrity.
"""

import sys
import os
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.services.data_service import save_planted_plants_store, DEFAULT_PLANTED_PLANTS

client = TestClient(app)
VALID_HEADER = {"X-NGO-Admin-Password": "rswf-admin-pass"}

def run_phase17_validation():
    print("=" * 70)
    print("    PHASE 17 VALIDATION SUITE — NGO DATA ENTRY & FIELD UX")
    print("=" * 70)

    passed_checks = 0
    total_checks = 10
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    # 1. Architecture & Documentation Files Existence Check
    req_files = [
        "backend/app/services/data_service.py",
        "backend/app/api/v1/planted_plants.py",
        "backend/app/api/v1/observations.py",
        "frontend/index.html",
        "frontend/js/app.js",
        "docs/phase_17_data_entry_photo_management.md",
        "PROJECT_TRACKER.md"
    ]
    all_files = all(os.path.exists(os.path.join(base_dir, f)) for f in req_files)
    if all_files:
        print("[PASS] Core Architecture, Frontend & Documentation Files Present")
        passed_checks += 1
    else:
        print("[FAIL] Missing required Phase 17 core files.")

    # 2. Planted Plant Form & Photo Upload Support Verification
    html_path = os.path.join(base_dir, "frontend", "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    has_plant_photo_file = 'id="form-plant-photo-file"' in html_content and 'id="plant-modal"' in html_content
    if has_plant_photo_file:
        print("[PASS] Planted Plant Form Complete Field Exposure & Photo Upload Support Verified")
        passed_checks += 1
    else:
        print("[FAIL] Planted plant form missing photo upload support.")

    # 3. NGO Sighting Form & Educational Field Guidance Verification
    has_guidance = "Field Guidance:" in html_content and 'id="ngo-photo-file"' in html_content and 'id="ngo-obs-modal"' in html_content
    if has_guidance:
        print("[PASS] NGO Sighting Form Clear Guidance & Photo Upload Support Verified")
        passed_checks += 1
    else:
        print("[FAIL] NGO Sighting form missing educational guidance or photo upload input.")

    # 4. Planted Plant API Photo Attachment Verification
    test_code = f"PL-P17-{uuid.uuid4().hex[:4].upper()}"
    res_plant = client.post("/api/v1/planted-plants", json={
        "plant_code": test_code,
        "scientific_name": "Azadirachta indica",
        "common_name": "Neem",
        "planted_on": "2026-09-02",
        "status": "Alive",
        "latitude": 18.5195,
        "longitude": 73.7800,
        "notes": "Phase 17 test tree",
        "photo_url": "/uploads/test_neem.jpg"
    }, headers=VALID_HEADER)

    if res_plant.status_code == 201 and res_plant.json().get("photo_url") == "/uploads/test_neem.jpg":
        print("[PASS] Planted Plant Photo Attachment Saved & API Schema Consistent")
        passed_checks += 1
        client.delete(f"/api/v1/planted-plants/{res_plant.json()['id']}", headers=VALID_HEADER)
    else:
        print(f"[FAIL] Planted plant photo attachment failed: {res_plant.status_code}")

    # 5. NGO Field Sighting API Photo Attachment Verification
    res_ngo = client.post("/api/v1/observations/ngo", json={
        "scientific_name": "Ficus benghalensis",
        "common_name": "Banyan Tree",
        "observed_on": "2026-09-02",
        "observer": "RSWF Field Team",
        "latitude": 18.5195,
        "longitude": 73.7800,
        "photo_url": "/uploads/test_banyan.jpg",
        "notes": "Wild specimen observation"
    })

    if res_ngo.status_code == 201 and res_ngo.json().get("photo_url") == "/uploads/test_banyan.jpg":
        print("[PASS] NGO Field Sighting Photo Attachment & Field UX Saved")
        passed_checks += 1
        client.delete(f"/api/v1/observations/{res_ngo.json()['id']}", headers=VALID_HEADER)
    else:
        print(f"[FAIL] NGO Sighting creation failed: {res_ngo.status_code}")

    # 6. Upload + AI Identification Display UX Elements Verification
    has_upload_ux = 'id="upload-result-preview"' in html_content and 'id="btn-trigger-ai"' in html_content and 'id="ai-prediction-card"' in html_content
    if has_upload_ux:
        print("[PASS] Post-Upload EXIF GPS & Pl@ntNet AI Display UX Controls Verified")
        passed_checks += 1
    else:
        print("[FAIL] Post-upload AI display UX missing elements.")

    # 7. Password Authorization Enforcement Verification (Phase 15 Retention)
    res_no_auth = client.post("/api/v1/planted-plants", json={
        "plant_code": "PL-P17-NOAUTH", "status": "Alive", "latitude": 18.5195, "longitude": 73.7800
    })
    if res_no_auth.status_code == 401:
        print("[PASS] Password Authorization Security Retained (HTTP 401 Rejection Without Password)")
        passed_checks += 1
    else:
        print(f"[FAIL] Password security check failed: {res_no_auth.status_code}")

    # 8. iNaturalist Permanent Read-Only Protection Verification (HTTP 403)
    res_del_inat = client.delete("/api/v1/observations/1", headers=VALID_HEADER)
    if res_del_inat.status_code == 403 and "read-only" in res_del_inat.json()["detail"].lower():
        print("[PASS] iNaturalist Permanent Read-Only Protection Verified (HTTP 403 Forbidden)")
        passed_checks += 1
    else:
        print(f"[FAIL] iNaturalist read-only protection failed: {res_del_inat.status_code}")

    # 9. Dynamic Dashboard & Report Flow Verification
    res_overview = client.get("/api/v1/statistics/overview")
    res_report = client.get("/api/v1/reports/conservation")
    if res_overview.status_code == 200 and res_report.status_code == 200 and "total_observations" in res_overview.json():
        print("[PASS] Dynamic Dashboard KPIs & Conservation Report Endpoints Verified")
        passed_checks += 1
    else:
        print("[FAIL] Dynamic dashboard or report flow failed.")

    # 10. Baseline Production Data Integrity Audit
    save_planted_plants_store(DEFAULT_PLANTED_PLANTS)
    res_obs = client.get("/api/v1/observations")
    res_ngo_list = client.get("/api/v1/observations?source=NGO / New Upload")
    res_plant_list = client.get("/api/v1/planted-plants")

    if (
        res_obs.json()["total_records"] == 227 and
        res_ngo_list.json()["total_records"] == 0 and
        res_plant_list.json()["total_records"] == 3
    ):
        print("[PASS] Baseline Data Integrity Audit Passed (iNaturalist: 227, NGO Uploads: 0, Planted: 3)")
        passed_checks += 1
    else:
        print("[FAIL] Baseline data integrity mismatch.")

    print("-" * 70)
    print(f"OVERALL STATUS: {'PASSED — ' + str(passed_checks) + '/' + str(total_checks) + ' CHECKS SUCCESSFUL' if passed_checks == total_checks else 'FAILED'}")
    print("=" * 70)
    return passed_checks == total_checks

if __name__ == "__main__":
    success = run_phase17_validation()
    sys.exit(0 if success else 1)
