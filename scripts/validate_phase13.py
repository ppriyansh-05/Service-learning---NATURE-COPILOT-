"""
Automated Validation Suite for Phase 13 — Advanced Biodiversity & Conservation Analytics
Validates recorded biodiversity analytics, unique recorded taxa, zone comparison metrics,
coverage indicators, transparent rule-based action priorities, species distribution,
temporal timeline analytics, dashboard UI panels, and baseline data integrity.
"""

import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def run_phase13_validation():
    print("=" * 70)
    print("    PHASE 13 VALIDATION SUITE — ADVANCED BIODIVERSITY ANALYTICS")
    print("=" * 70)

    passed_checks = 0
    total_checks = 10
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    # 1. File existence check
    req_files = [
        "backend/app/services/analytics_service.py",
        "backend/app/api/v1/analytics.py",
        "backend/tests/test_analytics.py",
        "docs/phase_13_advanced_analytics.md",
        "PROJECT_TRACKER.md"
    ]
    all_files_found = True
    for rel_path in req_files:
        full_p = os.path.join(base_dir, rel_path)
        if not os.path.exists(full_p):
            print(f"[FAIL] Missing required file: {rel_path}")
            all_files_found = False

    if all_files_found:
        print("[PASS] Core Analytics Architecture & Documentation Files Present")
        passed_checks += 1
    else:
        print("[FAIL] Missing required Phase 13 files.")

    # 2. Recorded Biodiversity Analytics Endpoint
    res_bio = client.get("/api/v1/analytics/biodiversity")
    if res_bio.status_code == 200 and res_bio.json()["total_recorded_observations"] == 227:
        print("[PASS] GET /api/v1/analytics/biodiversity (Total Observations: 227)")
        passed_checks += 1
    else:
        print(f"[FAIL] Biodiversity analytics endpoint failed: {res_bio.status_code}")

    # 3. Unique Recorded Taxa Baseline Check
    if res_bio.status_code == 200 and res_bio.json()["unique_recorded_taxa_count"] == 88:
        print("[PASS] Unique Recorded Taxa Baseline Verified (88 Taxa)")
        passed_checks += 1
    else:
        print("[FAIL] Unique recorded taxa count did not match baseline.")

    # 4. Zone Analytics & Safe Terminology Check
    res_zones = client.get("/api/v1/analytics/zones")
    if res_zones.status_code == 200 and "zones" in res_zones.json():
        print("[PASS] GET /api/v1/analytics/zones (Zone Comparison Analytics)")
        passed_checks += 1
    else:
        print(f"[FAIL] Zone analytics endpoint failed: {res_zones.status_code}")

    # 5. Coverage Analytics Indicators
    res_cov = client.get("/api/v1/analytics/coverage")
    if res_cov.status_code == 200 and "non_active_portion_summary" in res_cov.json():
        print("[PASS] GET /api/v1/analytics/coverage (Data Coverage Indicators)")
        passed_checks += 1
    else:
        print(f"[FAIL] Coverage analytics endpoint failed: {res_cov.status_code}")

    # 6. Rule-Based Action Priorities (Areas Requiring Action)
    res_act = client.get("/api/v1/analytics/action-priorities")
    if res_act.status_code == 200 and "priorities" in res_act.json() and len(res_act.json()["priorities"]) >= 4:
        print("[PASS] GET /api/v1/analytics/action-priorities (Areas Requiring Action)")
        passed_checks += 1
    else:
        print(f"[FAIL] Action priorities endpoint failed: {res_act.status_code}")

    # 7. Species & Taxonomic Analytics
    res_spec = client.get("/api/v1/analytics/species")
    if res_spec.status_code == 200 and "top_recorded_taxa" in res_spec.json():
        print("[PASS] GET /api/v1/analytics/species (Species Analytics & Frequency)")
        passed_checks += 1
    else:
        print(f"[FAIL] Species analytics endpoint failed: {res_spec.status_code}")

    # 8. Temporal Timeline Analytics
    res_temp = client.get("/api/v1/analytics/temporal")
    if res_temp.status_code == 200 and "status" in res_temp.json():
        print("[PASS] GET /api/v1/analytics/temporal (Temporal Analytics)")
        passed_checks += 1
    else:
        print(f"[FAIL] Temporal analytics endpoint failed: {res_temp.status_code}")

    # 9. Dashboard UI Action Panel Integration
    with open(os.path.join(base_dir, "frontend", "index.html"), "r", encoding="utf-8") as f:
        html = f.read()

    if "Areas Requiring Action" in html and "action-priorities-container" in html:
        print("[PASS] Dashboard Action Panel UI Controls Defined in index.html")
        passed_checks += 1
    else:
        print("[FAIL] Areas Requiring Action panel missing from index.html.")

    # 10. Baseline Real-Data Integrity Check
    res_obs = client.get("/api/v1/observations")
    res_plant = client.get("/api/v1/planted-plants")
    res_ngo = client.get("/api/v1/observations?source=NGO / New Upload")

    if (
        res_obs.status_code == 200 and res_obs.json()["total_records"] == 227 and
        res_ngo.status_code == 200 and res_ngo.json()["total_records"] == 0 and
        res_plant.status_code == 200 and res_plant.json()["total_records"] == 3
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
    success = run_phase13_validation()
    sys.exit(0 if success else 1)
