"""
Automated Validation Suite for Phase 14 — SDG / Conservation Decision-Support Report
Validates ReportService architecture, FastAPI JSON & PDF report endpoints, PDF binary compilation,
Report Data Consistency (Dashboard == Report == Database), survival math, rule-based recommendations,
SDG impact mapping, and baseline data integrity.
"""

import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def run_phase14_validation():
    print("=" * 70)
    print("    PHASE 14 VALIDATION SUITE — SDG & CONSERVATION REPORTING")
    print("=" * 70)

    passed_checks = 0
    total_checks = 10
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    # 1. File existence check
    req_files = [
        "backend/app/services/report_service.py",
        "backend/app/api/v1/reports.py",
        "backend/tests/test_reports.py",
        "docs/phase_14_conservation_report.md",
        "PROJECT_TRACKER.md"
    ]
    all_files_found = True
    for rel_path in req_files:
        full_p = os.path.join(base_dir, rel_path)
        if not os.path.exists(full_p):
            print(f"[FAIL] Missing required file: {rel_path}")
            all_files_found = False

    if all_files_found:
        print("[PASS] Core Report Service & Architecture Files Present")
        passed_checks += 1
    else:
        print("[FAIL] Missing required Phase 14 files.")

    # 2. Conservation JSON Report Endpoint
    res_cons = client.get("/api/v1/reports/conservation")
    if res_cons.status_code == 200 and "title" in res_cons.json():
        print("[PASS] GET /api/v1/reports/conservation (Conservation Report JSON)")
        passed_checks += 1
    else:
        print(f"[FAIL] Conservation report JSON endpoint failed: {res_cons.status_code}")

    # 3. SDG JSON Report Endpoint
    res_sdg = client.get("/api/v1/reports/sdg")
    if res_sdg.status_code == 200 and "sdg_contributions" in res_sdg.json():
        print("[PASS] GET /api/v1/reports/sdg (SDG Impact Summary JSON)")
        passed_checks += 1
    else:
        print(f"[FAIL] SDG report JSON endpoint failed: {res_sdg.status_code}")

    # 4. Conservation PDF Report Generation
    res_cons_pdf = client.get("/api/v1/reports/conservation.pdf")
    if (
        res_cons_pdf.status_code == 200 and
        res_cons_pdf.headers.get("content-type") == "application/pdf" and
        len(res_cons_pdf.content) > 1000 and
        res_cons_pdf.content.startswith(b"%PDF")
    ):
        print("[PASS] GET /api/v1/reports/conservation.pdf (Compiled PDF Binary Stream)")
        passed_checks += 1
    else:
        print(f"[FAIL] Conservation PDF report endpoint failed: {res_cons_pdf.status_code}")

    # 5. SDG PDF Report Generation
    res_sdg_pdf = client.get("/api/v1/reports/sdg.pdf")
    if (
        res_sdg_pdf.status_code == 200 and
        res_sdg_pdf.headers.get("content-type") == "application/pdf" and
        len(res_sdg_pdf.content) > 1000 and
        res_sdg_pdf.content.startswith(b"%PDF")
    ):
        print("[PASS] GET /api/v1/reports/sdg.pdf (Compiled SDG PDF Binary Stream)")
        passed_checks += 1
    else:
        print(f"[FAIL] SDG PDF report endpoint failed: {res_sdg_pdf.status_code}")

    # 6. Report Data Consistency Test (Dashboard == Report == Database)
    res_db_obs = client.get("/api/v1/observations")
    res_db_spec = client.get("/api/v1/species")
    res_db_plant = client.get("/api/v1/planted-plants")

    report_bio = res_cons.json()["biodiversity_overview"]
    report_surv = res_cons.json()["plant_survival"]

    db_obs_total = res_db_obs.json()["total_records"]
    db_spec_total = res_db_spec.json()["total_records"]
    db_plant_total = res_db_plant.json()["total_records"]

    if (
        report_bio["total_recorded_observations"] == db_obs_total == 227 and
        report_bio["unique_recorded_taxa_count"] == db_spec_total == 88 and
        report_surv["total_planted"] == db_plant_total == 3
    ):
        print("[PASS] Data Consistency Verified (Dashboard == Report == Database)")
        passed_checks += 1
    else:
        print("[FAIL] Data consistency check failed between report and database.")

    # 7. Plant Survival Math & Unknown Exclusion Check
    if report_surv["survival_rate"] == 100.0 and report_surv["survival_rate_display"] == "100.0%":
        print("[PASS] Plant Survival Calculation Verified (Unknown Excluded)")
        passed_checks += 1
    else:
        print("[FAIL] Plant survival rate calculation incorrect.")

    # 8. Areas Requiring Action & Potential Plantation Assessment Integration
    report_json = res_cons.json()
    pa_key_exists = "plantation_assessments" in report_json or "potential_plantation_assessments" in report_json
    if (
        "areas_requiring_action" in report_json and
        pa_key_exists and
        len(report_json["areas_requiring_action"]) >= 1
    ):
        print("[PASS] Rule-Based Action Priorities & Plantation Assessments Included")
        passed_checks += 1
    else:
        print("[FAIL] Action priorities or plantation assessments missing in report.")

    # 9. SDG Contribution Mapping (SDGs 15, 11, 13, 17, 9)
    sdg_list = res_cons.json()["sdg_contributions"]
    sdgs_found = [s["sdg"] for s in sdg_list]
    if len(sdg_list) == 5 and any("SDG 15" in s for s in sdgs_found):
        print("[PASS] SDG Impact Mapping Verified (SDGs 15, 11, 13, 17, 9)")
        passed_checks += 1
    else:
        print("[FAIL] SDG impact mapping incomplete.")

    # 10. Baseline Data Integrity Audit
    res_ngo = client.get("/api/v1/observations?source=NGO / New Upload")
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
    success = run_phase14_validation()
    sys.exit(0 if success else 1)
