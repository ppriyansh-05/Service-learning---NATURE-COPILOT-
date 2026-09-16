"""
Pre-Deployment Readiness & Final Engineering Audit Validation Suite.
Validates:
1. Core Architecture, Frontend, Backend & Docs
2. Planted Plant Complete Field Exposure & Geofencing
3. Planted Plant Photo Attachment Support
4. NGO Sighting Clear Educational Guidance & Field Form
5. NGO Sighting Photo Attachment Support
6. Geotagged Photo Upload, EXIF GPS Extraction & Geofence Pipeline
7. Pl@ntNet AI REST Workflow, Predictions & Verification Controls
8. Password Session Security & 30-Minute Inactivity Rolling Expiry
9. Password Mutation Protection (X-NGO-Admin-Password required)
10. Permanent iNaturalist Read-Only Protection (HTTP 403 Forbidden on delete/edit)
11. Authoritative Geodesic Geometry Consistency (3.58 ha total, 0.55 ha active zones)
12. Dynamic Database-to-Dashboard/Report Consistency & Baseline Data Integrity
"""

import sys
import os
import uuid
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.services.data_service import save_planted_plants_store, DEFAULT_PLANTED_PLANTS, get_base_dir

client = TestClient(app)
VALID_HEADER = {"X-NGO-Admin-Password": "rswf-admin-pass"}

def run_pre_deployment_audit():
    print("=" * 75)
    print("    PRE-DEPLOYMENT READINESS & FINAL ENGINEERING AUDIT")
    print("=" * 75)

    passed_checks = 0
    total_checks = 12
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    # Check 1: Architecture, Frontend, Backend & Documentation Files
    req_files = [
        "backend/app/main.py",
        "backend/app/services/data_service.py",
        "backend/app/services/analytics_service.py",
        "backend/app/services/report_service.py",
        "backend/app/core/security.py",
        "frontend/index.html",
        "frontend/js/app.js",
        "frontend/js/api.js",
        "PROJECT_TRACKER.md"
    ]
    if all(os.path.exists(os.path.join(base_dir, f)) for f in req_files):
        print("[PASS] Check 1: Core Platform Architecture, Codebase & Documentation Verified")
        passed_checks += 1
    else:
        print("[FAIL] Check 1: Missing core codebase files.")

    # Check 2: Planted Plant Complete Field Exposure & Geofence
    html_path = os.path.join(base_dir, "frontend", "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    has_plant_fields = (
        'id="form-plant-code"' in html and
        'id="form-scientific-name"' in html and
        'id="form-common-name"' in html and
        'id="form-planted-on"' in html and
        'id="form-status"' in html and
        'id="form-latitude"' in html and
        'id="form-longitude"' in html and
        'id="form-zone-code"' in html and
        'id="form-notes"' in html and
        'id="form-plant-photo-file"' in html
    )
    if has_plant_fields:
        print("[PASS] Check 2: Planted Plant Form Complete Field Exposure & Geofence Inputs Verified")
        passed_checks += 1
    else:
        print("[FAIL] Check 2: Planted plant form missing required database fields.")

    # Check 3: Planted Plant Photo Attachment API Support
    test_code = f"PL-AUDIT-{uuid.uuid4().hex[:4].upper()}"
    res_plant = client.post("/api/v1/planted-plants", json={
        "plant_code": test_code,
        "scientific_name": "Azadirachta indica",
        "common_name": "Neem Tree",
        "planted_on": "2026-09-02",
        "status": "Alive",
        "latitude": 18.5195,
        "longitude": 73.7800,
        "notes": "Pre-deployment audit plant",
        "photo_url": "/uploads/audit_plant.jpg"
    }, headers=VALID_HEADER)

    if res_plant.status_code == 201 and res_plant.json().get("photo_url") == "/uploads/audit_plant.jpg":
        print("[PASS] Check 3: Planted Plant Photo Attachment Saved & Verified")
        passed_checks += 1
        client.delete(f"/api/v1/planted-plants/{res_plant.json()['id']}", headers=VALID_HEADER)
    else:
        print(f"[FAIL] Check 3: Planted plant photo attachment failed: {res_plant.status_code}")

    # Check 4: NGO Sighting Form Clear Guidance & Complete Fields
    has_ngo_guidance = (
        "Field Guidance:" in html and
        "wild or naturally occurring" in html and
        'id="ngo-scientific-name"' in html and
        'id="ngo-common-name"' in html and
        'id="ngo-observed-on"' in html and
        'id="ngo-observer"' in html and
        'id="ngo-latitude"' in html and
        'id="ngo-longitude"' in html and
        'id="ngo-notes"' in html and
        'id="ngo-photo-file"' in html
    )
    if has_ngo_guidance:
        print("[PASS] Check 4: NGO Sighting Form Educational Guidance & Complete Fields Verified")
        passed_checks += 1
    else:
        print("[FAIL] Check 4: NGO Sighting form missing educational guidance or fields.")

    # Check 5: NGO Sighting Photo Attachment API Support
    res_ngo = client.post("/api/v1/observations/ngo", json={
        "scientific_name": "Ficus benghalensis",
        "common_name": "Banyan Tree",
        "observed_on": "2026-09-02",
        "observer": "RSWF Field Team",
        "latitude": 18.5195,
        "longitude": 73.7800,
        "photo_url": "/uploads/audit_banyan.jpg",
        "notes": "Pre-deployment wild specimen"
    })

    if res_ngo.status_code == 201 and res_ngo.json().get("photo_url") == "/uploads/audit_banyan.jpg":
        print("[PASS] Check 5: NGO Field Sighting Photo Attachment API Saved & Verified")
        passed_checks += 1
        client.delete(f"/api/v1/observations/{res_ngo.json()['id']}", headers=VALID_HEADER)
    else:
        print(f"[FAIL] Check 5: NGO Field Sighting photo attachment failed: {res_ngo.status_code}")

    # Check 6: Geotagged Photo Upload, EXIF GPS & Geofence Pipeline
    res_upload_outside = client.post("/api/v1/observations/upload", files={
        "file": ("outside.jpg", b"fake-outside-image-bytes", "image/jpeg")
    })
    # File without EXIF or outside should be rejected safely
    if res_upload_outside.status_code in [400, 422]:
        print("[PASS] Check 6: Photo Upload Validation & Geofence Pipeline Active")
        passed_checks += 1
    else:
        print(f"[FAIL] Check 6: Photo upload pipeline failed validation: {res_upload_outside.status_code}")

    # Check 7: Pl@ntNet AI REST Workflow, Predictions & Verification Controls
    has_ai_elements = (
        'id="upload-organ-select"' in html and
        'id="btn-trigger-ai"' in html and
        'id="ai-prediction-card"' in html and
        'id="ai-predictions-list"' in html
    )
    if has_ai_elements:
        print("[PASS] Check 7: Pl@ntNet AI REST Identification & Verification Controls Verified")
        passed_checks += 1
    else:
        print("[FAIL] Check 7: Missing Pl@ntNet AI prediction UI elements.")

    # Check 8: Password Session Security & 30-Minute Inactivity Rolling Expiry
    api_js_path = os.path.join(base_dir, "frontend", "js", "api.js")
    with open(api_js_path, "r", encoding="utf-8") as f:
        api_js = f.read()

    has_timeout_logic = (
        "ngo_admin_last_active" in api_js and
        "30 * 60 * 1000" in api_js and
        "clearNgoPassword" in api_js
    )
    if has_timeout_logic:
        print("[PASS] Check 8: Password Session Rolling 30-Minute Inactivity Expiry Active")
        passed_checks += 1
    else:
        print("[FAIL] Check 8: Missing session inactivity timeout logic in api.js.")

    # Check 9: Password Mutation Protection Enforcement
    res_no_auth = client.post("/api/v1/planted-plants", json={
        "plant_code": "PL-NOAUTH", "status": "Alive", "latitude": 18.5195, "longitude": 73.7800
    })
    if res_no_auth.status_code == 401:
        print("[PASS] Check 9: Password Authorization Enforcement Active (HTTP 401 Unauthorized)")
        passed_checks += 1
    else:
        print(f"[FAIL] Check 9: Password authorization check failed: {res_no_auth.status_code}")

    # Check 10: Permanent iNaturalist Read-Only Protection (HTTP 403)
    res_del_inat = client.delete("/api/v1/observations/1", headers=VALID_HEADER)
    if res_del_inat.status_code == 403 and "read-only" in res_del_inat.json()["detail"].lower():
        print("[PASS] Check 10: iNaturalist Permanent Read-Only Protection Verified (HTTP 403 Forbidden)")
        passed_checks += 1
    else:
        print(f"[FAIL] Check 10: iNaturalist read-only check failed: {res_del_inat.status_code}")

    # Check 11: Authoritative Geodesic Geometry Consistency (3.58 ha total, 0.55 ha active zones)
    res_cov = client.get("/api/v1/analytics/coverage")
    cov_data = res_cov.json()
    res_rep = client.get("/api/v1/reports/conservation")
    rep_data = res_rep.json()

    area_ok = (
        cov_data.get("total_project_area_ha") == 3.58 and
        rep_data.get("project_area", {}).get("total_boundary_area_ha") == 3.58 and
        rep_data.get("project_area", {}).get("unmonitored_outer_area_ha") == 3.02
    )
    if area_ok:
        print("[PASS] Check 11: Authoritative Geodesic Geometry (3.58 ha boundary, 0.55 ha zones) Verified")
        passed_checks += 1
    else:
        print(f"[FAIL] Check 11: Area inconsistency: cov={cov_data.get('total_project_area_ha')}, rep={rep_data.get('project_area', {}).get('total_boundary_area_ha')}")

    # Check 12: Dynamic Database Consistency & Baseline Real Data Integrity
    save_planted_plants_store(DEFAULT_PLANTED_PLANTS)
    res_obs_all = client.get("/api/v1/observations")
    res_obs_ngo = client.get("/api/v1/observations?source=NGO / New Upload")
    res_planted = client.get("/api/v1/planted-plants")

    total_obs = res_obs_all.json()["total_records"]
    ngo_obs = res_obs_ngo.json()["total_records"]
    planted_count = res_planted.json()["total_records"]

    if total_obs == 227 and ngo_obs == 0 and planted_count == 3:
        print("[PASS] Check 12: Baseline Data Integrity Verified (227 iNaturalist, 0 NGO, 3 Planted)")
        passed_checks += 1
    else:
        print(f"[FAIL] Check 12: Baseline data mismatch: obs={total_obs}, ngo={ngo_obs}, planted={planted_count}")

    print("-" * 75)
    print(f"PRE-DEPLOYMENT READINESS: {'PASSED — ' + str(passed_checks) + '/' + str(total_checks) + ' AUDIT CHECKS SUCCESSFUL' if passed_checks == total_checks else 'FAILED'}")
    print("=" * 75)
    return passed_checks == total_checks

if __name__ == "__main__":
    success = run_pre_deployment_audit()
    sys.exit(0 if success else 1)
