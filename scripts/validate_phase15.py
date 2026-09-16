"""
Automated Validation Suite for Phase 15 — Password-Protected Editing & Read-Only iNaturalist Data.
Validates public open access (GET, upload, exports, reports), protected mutation rejection (HTTP 401 missing/wrong password),
protected mutation authorization success (HTTP 201/200/204 with valid X-NGO-Admin-Password header),
strict iNaturalist read-only protection (HTTP 403 Forbidden even WITH valid password header),
monitoring visit history retention, and baseline data integrity.
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
INVALID_HEADER = {"X-NGO-Admin-Password": "invalid-pass-123"}

def run_phase15_validation():
    print("=" * 70)
    print("    PHASE 15 VALIDATION SUITE — AUTHENTICATION & iNATURALIST READ-ONLY")
    print("=" * 70)

    passed_checks = 0
    total_checks = 10
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    # 1. File existence check
    req_files = [
        "backend/app/core/security.py",
        "backend/app/core/config.py",
        ".env.example",
        "backend/tests/test_authentication.py",
        "docs/phase_15_authentication.md",
        "PROJECT_TRACKER.md"
    ]
    all_files_found = True
    for rel_path in req_files:
        full_p = os.path.join(base_dir, rel_path)
        if not os.path.exists(full_p):
            print(f"[FAIL] Missing required file: {rel_path}")
            all_files_found = False

    if all_files_found:
        print("[PASS] Core Architecture, Security & Documentation Files Present")
        passed_checks += 1
    else:
        print("[FAIL] Missing required Phase 15 files.")

    # 2. Public GET Endpoints Open
    res_obs = client.get("/api/v1/observations")
    res_spec = client.get("/api/v1/species")
    res_zones = client.get("/api/v1/zones")
    if res_obs.status_code == 200 and res_spec.status_code == 200 and res_zones.status_code == 200:
        print("[PASS] Public GET Endpoints Accessible Without Password (HTTP 200)")
        passed_checks += 1
    else:
        print("[FAIL] Public GET endpoints failed.")

    # 3. Public Export & Report Endpoints Open
    res_export = client.get("/api/v1/export/observations.csv")
    res_report = client.get("/api/v1/reports/conservation")
    if res_export.status_code == 200 and res_report.status_code == 200:
        print("[PASS] Public Exports & Reports Accessible Without Password (HTTP 200)")
        passed_checks += 1
    else:
        print("[FAIL] Public exports or reports failed.")

    # 4. Protected Mutation Rejection — Missing Password (HTTP 401)
    res_no_auth = client.post("/api/v1/planted-plants", json={
        "plant_code": "PL-NOAUTH", "status": "Alive", "latitude": 18.5195, "longitude": 73.7800
    })
    if res_no_auth.status_code == 401:
        print("[PASS] Protected Mutation Rejected Without Password (HTTP 401 Unauthorized)")
        passed_checks += 1
    else:
        print(f"[FAIL] Missing password returned unexpected status {res_no_auth.status_code}")

    # 5. Protected Mutation Rejection — Incorrect Password (HTTP 401)
    res_bad_auth = client.post("/api/v1/planted-plants", json={
        "plant_code": "PL-BADAUTH", "status": "Alive", "latitude": 18.5195, "longitude": 73.7800
    }, headers=INVALID_HEADER)
    if res_bad_auth.status_code == 401:
        print("[PASS] Protected Mutation Rejected With Incorrect Password (HTTP 401 Unauthorized)")
        passed_checks += 1
    else:
        print(f"[FAIL] Incorrect password returned unexpected status {res_bad_auth.status_code}")

    # 6. Protected Mutation Success — Valid Password (HTTP 201)
    code = f"PL-VAL-{uuid.uuid4().hex[:4].upper()}"
    res_ok = client.post("/api/v1/planted-plants", json={
        "plant_code": code, "status": "Alive", "latitude": 18.5195, "longitude": 73.7800
    }, headers=VALID_HEADER)
    if res_ok.status_code == 201 and res_ok.json()["plant_code"] == code:
        print("[PASS] Protected Mutation Authorized With Valid RSWF Password Header (HTTP 201)")
        passed_checks += 1
        # Clean up created plant
        client.delete(f"/api/v1/planted-plants/{res_ok.json()['id']}", headers=VALID_HEADER)
    else:
        print(f"[FAIL] Valid password mutation failed: {res_ok.status_code}")

    # 7. iNaturalist Deletion Blocked (HTTP 403 Forbidden Even WITH Password)
    res_del_inat = client.delete("/api/v1/observations/1", headers=VALID_HEADER)
    if res_del_inat.status_code == 403 and "read-only" in res_del_inat.json()["detail"].lower():
        print("[PASS] iNaturalist Deletion Blocked (HTTP 403 Forbidden Even With Valid Password)")
        passed_checks += 1
    else:
        print(f"[FAIL] iNaturalist deletion test returned {res_del_inat.status_code}")

    # 8. iNaturalist Verification Blocked (HTTP 403 Forbidden Even WITH Password)
    res_verif_inat = client.post("/api/v1/observations/1/verify", json={"decision": "confirm"}, headers=VALID_HEADER)
    if res_verif_inat.status_code == 403 and "read-only" in res_verif_inat.json()["detail"].lower():
        print("[PASS] iNaturalist Verification Edit Blocked (HTTP 403 Forbidden Even With Valid Password)")
        passed_checks += 1
    else:
        print(f"[FAIL] iNaturalist verification test returned {res_verif_inat.status_code}")

    # 9. Plant Status Editability & Monitoring History Retention
    save_planted_plants_store(DEFAULT_PLANTED_PLANTS)
    res_mon = client.post("/api/v1/planted-plants/1/monitoring", json={
        "status": "Dead", "monitoring_date": "2026-09-02", "notes": "Validation test"
    }, headers=VALID_HEADER)
    res_hist = client.get("/api/v1/planted-plants/1/monitoring")
    if res_mon.status_code == 201 and res_hist.status_code == 200 and len(res_hist.json()) >= 1:
        print("[PASS] Plant Status Editable & Monitoring Visit History Preserved")
        passed_checks += 1
    else:
        print("[FAIL] Plant status update or history preservation failed.")

    # 10. Baseline Data Integrity Audit
    save_planted_plants_store(DEFAULT_PLANTED_PLANTS)
    res_db_obs = client.get("/api/v1/observations")
    res_ngo = client.get("/api/v1/observations?source=NGO / New Upload")
    res_db_plant = client.get("/api/v1/planted-plants")

    if (
        res_db_obs.json()["total_records"] == 227 and
        res_ngo.json()["total_records"] == 0 and
        res_db_plant.json()["total_records"] == 3
    ):
        print("[PASS] Baseline Data Integrity Verified (iNaturalist: 227, NGO Uploads: 0, Planted: 3)")
        passed_checks += 1
    else:
        print("[FAIL] Baseline data counts mismatch during validation.")

    print("-" * 70)
    print(f"OVERALL STATUS: {'PASSED — ' + str(passed_checks) + '/' + str(total_checks) + ' CHECKS SUCCESSFUL' if passed_checks == total_checks else 'FAILED'}")
    print("=" * 70)
    return passed_checks == total_checks

if __name__ == "__main__":
    success = run_phase15_validation()
    sys.exit(0 if success else 1)
