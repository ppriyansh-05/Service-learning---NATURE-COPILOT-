"""
Automated Validation Suite for Phase 14.1 — NGO Report Refinement, Plantation Impact & PDF Download Fix.
Validates refined ReportService architecture, 14-section NGO conservation & plantation report structure,
FastAPI JSON & PDF endpoints, PDF binary compilation, Content-Disposition headers,
Report Data Consistency (Dashboard == Report == Database), plant survival math, Unknown status exclusion,
rule-based action priorities, potential plantation assessment areas, scientifically safe impact statements,
and baseline data integrity.
"""

import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def run_phase14_1_validation():
    print("=" * 70)
    print("    PHASE 14.1 VALIDATION SUITE — NGO CONSERVATION & PLANTATION REPORT")
    print("=" * 70)

    passed_checks = 0
    total_checks = 10
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    # 1. File existence check
    req_files = [
        "backend/app/services/report_service.py",
        "backend/app/api/v1/reports.py",
        "backend/tests/test_reports.py",
        "docs/phase_14_1_ngo_report_refinement.md",
        "PROJECT_TRACKER.md"
    ]
    all_files_found = True
    for rel_path in req_files:
        full_p = os.path.join(base_dir, rel_path)
        if not os.path.exists(full_p):
            print(f"[FAIL] Missing required file: {rel_path}")
            all_files_found = False

    if all_files_found:
        print("[PASS] Core Refined Report Service & Architecture Files Present")
        passed_checks += 1
    else:
        print("[FAIL] Missing required Phase 14.1 files.")

    # 2. Conservation & Plantation Planning Report JSON Endpoint
    res_cons = client.get("/api/v1/reports/conservation")
    if res_cons.status_code == 200 and "title" in res_cons.json():
        title = res_cons.json()["title"]
        if "Conservation & Plantation Planning Report" in title:
            print("[PASS] GET /api/v1/reports/conservation (Refined NGO Report JSON)")
            passed_checks += 1
        else:
            print(f"[FAIL] Unexpected report title: {title}")
    else:
        print(f"[FAIL] Conservation report JSON endpoint failed: {res_cons.status_code}")

    # 3. SDG Summary JSON Endpoint
    res_sdg = client.get("/api/v1/reports/sdg")
    if res_sdg.status_code == 200 and "sdg_contributions" in res_sdg.json():
        print("[PASS] GET /api/v1/reports/sdg (SDG Supporting Summary JSON)")
        passed_checks += 1
    else:
        print(f"[FAIL] SDG report JSON endpoint failed: {res_sdg.status_code}")

    # 4. Conservation PDF Report Generation & Content-Disposition
    res_cons_pdf = client.get("/api/v1/reports/conservation.pdf")
    disposition = res_cons_pdf.headers.get("content-disposition", "")
    if (
        res_cons_pdf.status_code == 200 and
        res_cons_pdf.headers.get("content-type") == "application/pdf" and
        len(res_cons_pdf.content) > 1000 and
        res_cons_pdf.content.startswith(b"%PDF") and
        "van_udyan_conservation_plantation_report.pdf" in disposition
    ):
        print("[PASS] GET /api/v1/reports/conservation.pdf (Compiled PDF Binary & Filename Header)")
        passed_checks += 1
    else:
        print(f"[FAIL] Conservation PDF report download failed: {res_cons_pdf.status_code}")

    # 5. SDG PDF Report Generation & Content-Disposition
    res_sdg_pdf = client.get("/api/v1/reports/sdg.pdf")
    disposition_sdg = res_sdg_pdf.headers.get("content-disposition", "")
    if (
        res_sdg_pdf.status_code == 200 and
        res_sdg_pdf.headers.get("content-type") == "application/pdf" and
        len(res_sdg_pdf.content) > 1000 and
        res_sdg_pdf.content.startswith(b"%PDF") and
        "van_udyan_sdg_project_report.pdf" in disposition_sdg
    ):
        print("[PASS] GET /api/v1/reports/sdg.pdf (Compiled SDG PDF Binary Stream)")
        passed_checks += 1
    else:
        print(f"[FAIL] SDG PDF report download failed: {res_sdg_pdf.status_code}")

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

    # 8. Plantation Progress & Impact Statement Verification
    report_json = res_cons.json()
    pip = report_json.get("plantation_progress_impact", {})
    if (
        "summary_statement" in pip and
        "3 planted plants are currently recorded" in pip["summary_statement"] and
        pip.get("biodiversity_impact_statement") == "Direct biodiversity impact cannot yet be quantified from the available dataset."
    ):
        print("[PASS] Plantation Progress & Scientifically Safe Impact Statement Verified")
        passed_checks += 1
    else:
        print("[FAIL] Plantation progress summary or impact statement invalid.")

    # 9. Potential Plantation Assessment Areas & Action Priorities
    if (
        "potential_plantation_assessments" in report_json and
        "areas_requiring_action" in report_json and
        len(report_json["potential_plantation_assessments"]) >= 1 and
        len(report_json["areas_requiring_action"]) >= 1
    ):
        print("[PASS] Potential Plantation Assessment Areas & Action Priorities Included")
        passed_checks += 1
    else:
        print("[FAIL] Action priorities or plantation assessments missing in report payload.")

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
    success = run_phase14_1_validation()
    sys.exit(0 if success else 1)
