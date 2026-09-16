"""
Phase 12 Plant Status & Survival Monitoring Pytest Suite
Tests creation of monitoring records (Alive, Dead, Unknown), status validation, nonexistent plant ID handling,
date validation, chronological history preservation, current status updates, survival rate calculations,
zero-denominator handling, zone-wise analytics, and dataset isolation.
"""

import sys
import os
import json
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.services.data_service import DataService

client = TestClient(app)

@pytest.fixture(autouse=True, scope="module")
def cleanup_after_monitoring_tests():
    yield
    # Clear monitoring repository
    DataService._plant_monitoring_repository.clear()
    from app.services.data_service import save_planted_plants_store, DEFAULT_PLANTED_PLANTS
    save_planted_plants_store(DEFAULT_PLANTED_PLANTS)

@pytest.fixture(scope="module")
def setup_dummy_planted_plant():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    store_path = os.path.join(base_dir, "data", "processed", "planted_plants_store.json")
    
    records = []
    if os.path.exists(store_path):
        try:
            with open(store_path, "r", encoding="utf-8") as f:
                records = json.load(f)
        except Exception:
            pass

    dummy = {
        "id": 999,
        "plant_code": "PL-TEST-999",
        "scientific_name": "Ficus religiosa",
        "common_name": "Peepal Tree",
        "planted_on": "2026-01-01",
        "status": "Alive",
        "latitude": 18.5195,
        "longitude": 73.7800,
        "zone_code": "ZONE A"
    }
    records = [r for r in records if r.get("id") != 999]
    records.append(dummy)

    with open(store_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)

    yield 999

    # Teardown dummy plant
    if os.path.exists(store_path):
        try:
            with open(store_path, "r", encoding="utf-8") as f:
                recs = json.load(f)
            recs = [r for r in recs if r.get("id") != 999]
            with open(store_path, "w", encoding="utf-8") as f:
                json.dump(recs, f, indent=2)
        except Exception:
            pass

# 1. Create Monitoring Visit Record (Alive)
def test_create_monitoring_record_alive(setup_dummy_planted_plant):
    plant_id = setup_dummy_planted_plant
    res = client.post(f"/api/v1/planted-plants/{plant_id}/monitoring", json={
        "status": "Alive",
        "monitoring_date": "2026-07-01",
        "notes": "Healthy foliage development",
        "observer": "RSWF Inspector"
    }, headers={"X-NGO-Admin-Password": "rswf-admin-pass"})
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "Alive"
    assert data["planted_plant_id"] == plant_id

# 2. Create Monitoring Visit Record (Dead)
def test_create_monitoring_record_dead(setup_dummy_planted_plant):
    plant_id = setup_dummy_planted_plant
    res = client.post(f"/api/v1/planted-plants/{plant_id}/monitoring", json={
        "status": "Dead",
        "monitoring_date": "2026-08-01",
        "notes": "Stem dried completely"
    }, headers={"X-NGO-Admin-Password": "rswf-admin-pass"})
    assert res.status_code == 201
    assert res.json()["status"] == "Dead"

# 3. Create Monitoring Visit Record (Unknown)
def test_create_monitoring_record_unknown(setup_dummy_planted_plant):
    plant_id = setup_dummy_planted_plant
    res = client.post(f"/api/v1/planted-plants/{plant_id}/monitoring", json={
        "status": "Unknown",
        "monitoring_date": "2026-09-01",
        "notes": "Tag missing during visit"
    }, headers={"X-NGO-Admin-Password": "rswf-admin-pass"})
    assert res.status_code == 201
    assert res.json()["status"] == "Unknown"

# 4. Invalid Status Value Rejection
def test_invalid_status_rejection(setup_dummy_planted_plant):
    plant_id = setup_dummy_planted_plant
    res = client.post(f"/api/v1/planted-plants/{plant_id}/monitoring", json={
        "status": "Healthy_And_Thriving"
    }, headers={"X-NGO-Admin-Password": "rswf-admin-pass"})
    assert res.status_code == 400
    assert "Invalid plant status" in res.json()["detail"]

# 5. Nonexistent Plant ID Rejection
def test_nonexistent_plant_id_monitoring():
    res = client.post("/api/v1/planted-plants/999999/monitoring", json={
        "status": "Alive"
    }, headers={"X-NGO-Admin-Password": "rswf-admin-pass"})
    assert res.status_code == 404

# 6. Invalid Date Format Rejection
def test_invalid_date_format_rejection(setup_dummy_planted_plant):
    plant_id = setup_dummy_planted_plant
    res = client.post(f"/api/v1/planted-plants/{plant_id}/monitoring", json={
        "status": "Alive",
        "monitoring_date": "07/01/2026"
    }, headers={"X-NGO-Admin-Password": "rswf-admin-pass"})
    assert res.status_code == 400

# 7. Historical Monitoring Preservation (Multiple Visits)
def test_historical_monitoring_preservation(setup_dummy_planted_plant):
    plant_id = setup_dummy_planted_plant
    hist_res = client.get(f"/api/v1/planted-plants/{plant_id}/monitoring")
    assert hist_res.status_code == 200
    history = hist_res.json()
    assert len(history) >= 3
    assert history[0]["status"] == "Alive"
    assert history[1]["status"] == "Dead"
    assert history[2]["status"] == "Unknown"

# 8. Latest Status Updated on Plant Record
def test_latest_status_retrieved(setup_dummy_planted_plant):
    plant_id = setup_dummy_planted_plant
    plant_res = client.get(f"/api/v1/planted-plants/{plant_id}")
    assert plant_res.status_code == 200
    assert plant_res.json()["status"] == "Unknown"

# 9. Survival Statistics Calculation & Survival Rate
def test_survival_statistics_calculation():
    res = client.get("/api/v1/planted-plants/monitoring/statistics")
    assert res.status_code == 200
    data = res.json()
    assert "survival_rate" in data
    assert "alive_count" in data
    assert "dead_count" in data
    assert "zone_breakdown" in data

# 10. Zero Denominator Survival Rate Handling
def test_zero_denominator_survival_handling():
    DataService._plant_monitoring_repository.clear()
    stats = DataService.get_plant_survival_statistics()
    assert "survival_rate" in stats

# 11. Zone-Wise Statistics Breakdown
def test_zone_wise_analytics():
    stats = DataService.get_plant_survival_statistics()
    breakdown = stats["zone_breakdown"]
    assert "ZONE A" in breakdown
    assert "ZONE B" in breakdown
    assert "ZONE C" in breakdown

# 12. Historical Records Not Overwritten
def test_history_not_overwritten():
    DataService.add_plant_monitoring_record(1, "Alive", "2026-05-01")
    DataService.add_plant_monitoring_record(1, "Dead", "2026-06-01")
    hist = DataService.get_plant_monitoring_history(1)
    assert len(hist) == 2
    assert hist[0]["status"] == "Alive"
    assert hist[1]["status"] == "Dead"

# 13. Existing Planted Plants Baseline Intact
def test_planted_plants_count_intact():
    res = client.get("/api/v1/planted-plants")
    assert res.status_code == 200
    assert res.json()["total_records"] >= 2

# 14. iNaturalist Records Unchanged
def test_inaturalist_records_unchanged():
    res = client.get("/api/v1/observations?source=iNaturalist")
    assert res.status_code == 200
    assert res.json()["total_records"] == 227

# 15. AI Predictions & Verification Functionality Unchanged
def test_ai_verification_unaffected():
    res = client.get("/api/v1/observations/ai-feedback")
    assert res.status_code == 200
