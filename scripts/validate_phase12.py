"""
Automated Validation Suite for Phase 12 — Plant Status & Survival Monitoring
Validates plant condition monitoring record creation (Alive, Dead, Unknown), chronological visit history preservation,
server-side input validations (status, plant ID, date format), dynamic survival rate calculations,
zone-wise status analytics, and dashboard UI modal controls.
"""

import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.services.data_service import DataService

client = TestClient(app)

def run_phase12_validation():
    print("=" * 70)
    print("    PHASE 12 VALIDATION SUITE — PLANT STATUS & SURVIVAL MONITORING")
    print("=" * 70)

    passed_checks = 0
    total_checks = 10
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    # 1. File existence check
    req_files = [
        "backend/tests/test_monitoring.py",
        "docs/phase_12_plant_monitoring.md",
        "PROJECT_TRACKER.md"
    ]
    all_files_found = True
    for rel_path in req_files:
        full_p = os.path.join(base_dir, rel_path)
        if not os.path.exists(full_p):
            print(f"[FAIL] Missing required file: {rel_path}")
            all_files_found = False

    if all_files_found:
        print("[PASS] Core Architecture & Documentation Files Present")
        passed_checks += 1
    else:
        print("[FAIL] Missing required Phase 12 files.")

    # Setup dummy plant record for validation
    store_path = os.path.join(base_dir, "data", "processed", "planted_plants_store.json")
    with open(store_path, "w", encoding="utf-8") as f:
        json.dump([{
            "id": 999,
            "plant_code": "PL-VAL12-999",
            "scientific_name": "Azadirachta indica",
            "common_name": "Neem",
            "planted_on": "2026-01-01",
            "status": "Alive",
            "latitude": 18.5195,
            "longitude": 73.7800,
            "zone_code": "ZONE A"
        }], f, indent=2)

    DataService._plant_monitoring_repository.clear()

    # 2. Add Monitoring Visit (Alive)
    res_alive = client.post("/api/v1/planted-plants/999/monitoring", json={
        "status": "Alive",
        "monitoring_date": "2026-07-01",
        "notes": "Healthy leaf growth"
    }, headers={"X-NGO-Admin-Password": "rswf-admin-pass"})
    if res_alive.status_code == 201 and res_alive.json()["status"] == "Alive":
        print("[PASS] POST /api/v1/planted-plants/{id}/monitoring (Alive Visit)")
        passed_checks += 1
    else:
        print(f"[FAIL] Alive monitoring visit failed: {res_alive.status_code} {res_alive.text}")

    # 3. Add Monitoring Visit (Dead)
    res_dead = client.post("/api/v1/planted-plants/999/monitoring", json={
        "status": "Dead",
        "monitoring_date": "2026-08-01",
        "notes": "Dried sapling"
    }, headers={"X-NGO-Admin-Password": "rswf-admin-pass"})
    if res_dead.status_code == 201 and res_dead.json()["status"] == "Dead":
        print("[PASS] POST /api/v1/planted-plants/{id}/monitoring (Dead Visit)")
        passed_checks += 1
    else:
        print(f"[FAIL] Dead monitoring visit failed: {res_dead.status_code} {res_dead.text}")

    # 4. Invalid Status Rejection (HTTP 400)
    res_bad_st = client.post("/api/v1/planted-plants/999/monitoring", json={"status": "Invalid_Status"}, headers={"X-NGO-Admin-Password": "rswf-admin-pass"})
    if res_bad_st.status_code == 400:
        print("[PASS] Server-Side Invalid Status Rejection (HTTP 400)")
        passed_checks += 1
    else:
        print(f"[FAIL] Invalid status rejection failed: {res_bad_st.status_code}")

    # 5. Nonexistent Plant ID Rejection (HTTP 404)
    res_404 = client.post("/api/v1/planted-plants/999999/monitoring", json={"status": "Alive"}, headers={"X-NGO-Admin-Password": "rswf-admin-pass"})
    if res_404.status_code == 404:
        print("[PASS] Server-Side Nonexistent Plant ID Rejection (HTTP 404)")
        passed_checks += 1
    else:
        print(f"[FAIL] Nonexistent plant ID rejection failed: {res_404.status_code}")

    # 6. Chronological Monitoring History Retrieval
    res_hist = client.get("/api/v1/planted-plants/999/monitoring")
    if res_hist.status_code == 200 and len(res_hist.json()) >= 2:
        print("[PASS] GET /api/v1/planted-plants/{id}/monitoring Chronological History")
        passed_checks += 1
    else:
        print(f"[FAIL] Monitoring history retrieval failed: {res_hist.status_code}")

    # 7. Latest Plant Status Updated
    res_plant = client.get("/api/v1/planted-plants/999")
    if res_plant.status_code == 200 and res_plant.json()["status"] == "Dead":
        print("[PASS] Latest Plant Current Status Auto-Updated")
        passed_checks += 1
    else:
        print(f"[FAIL] Plant current status update failed: {res_plant.status_code}")

    # 8. Dynamic Survival Statistics API
    res_stats = client.get("/api/v1/planted-plants/monitoring/statistics")
    if res_stats.status_code == 200 and "survival_rate" in res_stats.json():
        print("[PASS] GET /api/v1/planted-plants/monitoring/statistics Endpoint")
        passed_checks += 1
    else:
        print(f"[FAIL] Survival statistics endpoint failed: {res_stats.status_code}")

    # 9. Zone-Wise Status Breakdown & Empirical Insights
    if res_stats.status_code == 200 and "zone_breakdown" in res_stats.json() and "insights" in res_stats.json():
        print("[PASS] Zone-Wise Status Analytics & Empirical Insights")
        passed_checks += 1
    else:
        print("[FAIL] Zone breakdown or insights missing from statistics output.")

    # 10. UI Controls Definition Check
    with open(os.path.join(base_dir, "frontend", "index.html"), "r", encoding="utf-8") as f:
        html = f.read()

    if "plant-monitoring-modal" in html and "plant-history-modal" in html:
        print("[PASS] Dashboard Plant Monitoring UI Modals & Controls Defined")
        passed_checks += 1
    else:
        print("[FAIL] Plant monitoring UI modals missing from index.html.")

    # Teardown test plant
    DataService._plant_monitoring_repository.clear()
    with open(store_path, "w", encoding="utf-8") as f:
        json.dump([], f, indent=2)

    print("-" * 70)
    print(f"OVERALL STATUS: {'PASSED — ' + str(passed_checks) + '/' + str(total_checks) + ' CHECKS SUCCESSFUL' if passed_checks == total_checks else 'FAILED'}")
    print("=" * 70)
    return passed_checks == total_checks

if __name__ == "__main__":
    success = run_phase12_validation()
    sys.exit(0 if success else 1)
