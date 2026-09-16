"""
Pytest Unit Tests for Phase 14 / 14.1 NGO Conservation & Plantation Planning Reports.
Tests JSON report structure, ReportLab PDF compilation, Content-Type headers,
Report Data Consistency (Dashboard == Report == Database), survival math, Unknown status exclusion,
rule-based action priorities, potential plantation assessments, insufficient data handling,
provenance preservation, plant status editability, and monitoring history retention.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.services.report_service import ReportService
from app.services.data_service import DataService, save_planted_plants_store, DEFAULT_PLANTED_PLANTS

client = TestClient(app)


@pytest.fixture(autouse=True, scope="module")
def cleanup_after_report_tests():
    yield
    # Restore baseline repository state
    DataService._plant_monitoring_repository.clear()
    save_planted_plants_store(DEFAULT_PLANTED_PLANTS)


# 1. Conservation Report JSON Success
def test_get_conservation_report_json_success():
    res = client.get("/api/v1/reports/conservation")
    assert res.status_code == 200
    data = res.json()
    assert "title" in data
    assert "Van Udyan Conservation & Plantation Planning Report" in data["title"]
    assert "project_area" in data
    assert "plantation_progress_impact" in data


# 2. Conservation Report PDF Download
def test_conservation_report_pdf_download():
    res = client.get("/api/v1/reports/conservation.pdf")
    assert res.status_code == 200


# 3. PDF Content Non-Empty
def test_pdf_content_non_empty():
    res = client.get("/api/v1/reports/conservation.pdf")
    assert res.status_code == 200
    assert len(res.content) > 1000
    assert res.content.startswith(b"%PDF")


# 4. PDF Content-Type Application/PDF
def test_pdf_content_type():
    res = client.get("/api/v1/reports/conservation.pdf")
    assert res.status_code == 200
    assert res.headers.get("content-type") == "application/pdf"
    assert 'filename=' in res.headers.get("content-disposition", "")


# 5. SDG Project Report JSON Success
def test_get_sdg_report_json_success():
    res = client.get("/api/v1/reports/sdg")
    assert res.status_code == 200
    data = res.json()
    assert "sdg_contributions" in data
    assert len(data["sdg_contributions"]) == 5


# 6. SDG Report PDF Download
def test_sdg_report_pdf_download():
    res = client.get("/api/v1/reports/sdg.pdf")
    assert res.status_code == 200
    assert res.headers.get("content-type") == "application/pdf"
    assert len(res.content) > 1000


# 7. Database Values Appear Correctly in Report
def test_database_values_appear_correctly():
    data = ReportService.get_conservation_report_data()
    bio = data["biodiversity_overview"]
    assert bio["total_recorded_observations"] == 227
    assert bio["unique_recorded_taxa_count"] == 88
    assert data["project_area"]["active_zones_count"] == 3


# 8. Planted Plant Values Appear Correctly
def test_planted_plant_values_appear_correctly():
    data = ReportService.get_conservation_report_data()
    surv = data["plant_survival"]
    assert surv["total_planted"] == 3
    assert surv["alive_count"] == 3
    assert surv["dead_count"] == 0


# 9. Survival Calculation Formula Correct
def test_survival_calculation_correct():
    data = ReportService.get_conservation_report_data()
    surv = data["plant_survival"]
    # 3 Alive out of 3 total = 100.0%
    assert surv["survival_rate"] == 100.0
    assert surv["survival_rate_display"] == "100.0%"


# 10. Unknown Excluded from Survival Denominator
def test_unknown_excluded_from_survival_denominator():
    # Simulate a plant with Unknown status
    dummy_records = [
        {"id": 1, "plant_code": "PL001", "status": "Alive"},
        {"id": 2, "plant_code": "PL002", "status": "Dead"},
        {"id": 3, "plant_code": "PL003", "status": "Unknown"}
    ]
    save_planted_plants_store(dummy_records)
    data = ReportService.get_conservation_report_data()
    surv = data["plant_survival"]
    # Alive = 1, Dead = 1, Unknown = 1 -> Denominator = 1 + 1 = 2 -> Survival = 1 / 2 = 50.0%
    assert surv["survival_rate"] == 50.0
    assert surv["survival_rate_display"] == "50.0%"
    # Restore baseline
    save_planted_plants_store(DEFAULT_PLANTED_PLANTS)


# 11. Areas Requiring Action Integration
def test_areas_requiring_action_integration():
    data = ReportService.get_conservation_report_data()
    priorities = data["areas_requiring_action"]
    assert len(priorities) >= 1
    for p in priorities:
        assert "area_code" in p
        assert "priority_type" in p
        assert "recommended_action" in p


# 12. Potential Plantation Assessment Areas
def test_potential_plantation_assessments():
    data = ReportService.get_conservation_report_data()
    assessments = data["potential_plantation_assessments"]
    assert len(assessments) >= 1
    for pa in assessments:
        assert "area_code" in pa
        assert "assessment_category" in pa
        assert "indicator" in pa


# 13. Insufficient Data Handling
def test_insufficient_data_handling():
    # Simulate zero plants with known status
    save_planted_plants_store([{
        "id": 1,
        "plant_code": "PL001",
        "scientific_name": "Ficus religiosa",
        "common_name": "Peepal Tree",
        "planted_on": "2026-01-15",
        "status": "Unknown",
        "latitude": 18.5195,
        "longitude": 73.7800,
        "zone_code": "ZONE A"
    }])
    data = ReportService.get_conservation_report_data()
    surv = data["plant_survival"]
    assert surv["survival_rate"] is None
    assert surv["survival_rate_display"] == "Insufficient monitoring data."
    save_planted_plants_store(DEFAULT_PLANTED_PLANTS)


# 14. Report Generation Does Not Modify Database
def test_report_does_not_modify_database():
    obs_before = client.get("/api/v1/observations").json()["total_records"]
    client.get("/api/v1/reports/conservation")
    client.get("/api/v1/reports/conservation.pdf")
    obs_after = client.get("/api/v1/observations").json()["total_records"]
    assert obs_before == obs_after


# 15. No Fake Records Remain (Baseline Data Integrity)
def test_no_fake_records_remain():
    save_planted_plants_store(DEFAULT_PLANTED_PLANTS)
    obs_res = client.get("/api/v1/observations")
    ngo_res = client.get("/api/v1/observations?source=NGO / New Upload")
    plant_res = client.get("/api/v1/planted-plants")

    assert obs_res.json()["total_records"] == 227
    assert ngo_res.json()["total_records"] == 0
    assert plant_res.json()["total_records"] == 3


# 16. Plant Status Remains Editable
def test_plant_status_remains_editable():
    save_planted_plants_store(DEFAULT_PLANTED_PLANTS)
    v_res = client.post("/api/v1/planted-plants/1/monitoring", json={
        "status": "Dead",
        "monitoring_date": "2026-09-02",
        "observer": "RSWF Inspector",
        "notes": "Plant dry check"
    }, headers={"X-NGO-Admin-Password": "rswf-admin-pass"})
    assert v_res.status_code == 201

    plant_res = client.get("/api/v1/planted-plants/1")
    assert plant_res.status_code == 200
    assert plant_res.json()["status"] == "Dead"

    # Restore baseline
    save_planted_plants_store(DEFAULT_PLANTED_PLANTS)


# 17. Monitoring History Preservation
def test_monitoring_history_remains_preserved():
    client.post("/api/v1/planted-plants/1/monitoring", json={
        "status": "Alive",
        "monitoring_date": "2026-09-02",
        "observer": "RSWF Inspector",
        "notes": "Foliage check"
    }, headers={"X-NGO-Admin-Password": "rswf-admin-pass"})

    hist_res = client.get("/api/v1/planted-plants/1/monitoring")
    assert hist_res.status_code == 200
    assert len(hist_res.json()) >= 1
