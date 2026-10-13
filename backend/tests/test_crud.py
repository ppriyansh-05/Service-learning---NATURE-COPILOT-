"""
Phase 7 CRUD & Data Management Pytest Suite
Tests Planted Plants CRUD operations, status validation, location boundary checks,
NGO observation creation, and iNaturalist reference record protection.
"""

import sys
import os
import uuid
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture(autouse=True, scope="module")
def cleanup_after_crud_tests():
    import json
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    planted_path = os.path.join(base_dir, "data", "processed", "planted_plants_store.json")
    ngo_path = os.path.join(base_dir, "data", "processed", "ngo_observations_store.json")
    
    # Snapshot existing records before test
    init_planted = []
    init_ngo = []
    if os.path.exists(planted_path):
        try:
            with open(planted_path, "r", encoding="utf-8") as f: init_planted = json.load(f)
        except Exception: pass
    if os.path.exists(ngo_path):
        try:
            with open(ngo_path, "r", encoding="utf-8") as f: init_ngo = json.load(f)
        except Exception: pass

    yield

    from app.services.data_service import save_planted_plants_store
    save_planted_plants_store(init_planted)
    if os.path.exists(ngo_path):
        with open(ngo_path, "w", encoding="utf-8") as f:
            json.dump(init_ngo, f, indent=2)

def test_create_planted_plant_success():
    unique_code = f"PL-TEST-{uuid.uuid4().hex[:6].upper()}"
    payload = {
        "plant_code": unique_code,
        "scientific_name": "Ficus benghalensis",
        "common_name": "Banyan Tree",
        "planted_on": "2026-08-20",
        "status": "Alive",
        "latitude": 18.5195,
        "longitude": 73.7800,
        "notes": "Plantation test specimen"
    }
    response = client.post("/api/v1/planted-plants", json=payload, headers={"X-NGO-Admin-Password": "rswf-admin-pass"})
    assert response.status_code == 201
    data = response.json()
    assert data["plant_code"] == unique_code
    assert data["source"] == "Planted Plants"
    assert data["status"] == "Alive"
    assert "id" in data

def test_get_planted_plants_list():
    response = client.get("/api/v1/planted-plants")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert data["total_records"] >= 1

def test_get_planted_plant_detail():
    response = client.get("/api/v1/planted-plants/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["source"] == "Planted Plants"

def test_update_planted_plant_status():
    payload = {
        "status": "Dead",
        "notes": "Updated health state to Dead"
    }
    response = client.put("/api/v1/planted-plants/1", json=payload, headers={"X-NGO-Admin-Password": "rswf-admin-pass"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Dead"
    assert data["notes"] == "Updated health state to Dead"

def test_invalid_status_rejection():
    payload = {
        "plant_code": f"PL-BAD-{uuid.uuid4().hex[:4].upper()}",
        "status": "SuperAlive", # Invalid status!
        "latitude": 18.5195,
        "longitude": 73.7800
    }
    response = client.post("/api/v1/planted-plants", json=payload, headers={"X-NGO-Admin-Password": "rswf-admin-pass"})
    assert response.status_code in [400, 422]

def test_outside_boundary_coordinates_rejection():
    payload = {
        "plant_code": f"PL-GEO-{uuid.uuid4().hex[:4].upper()}",
        "status": "Alive",
        "latitude": 19.0760, # Mumbai coordinates (Outside Van Udyan!)
        "longitude": 72.8777
    }
    response = client.post("/api/v1/planted-plants", json=payload, headers={"X-NGO-Admin-Password": "rswf-admin-pass"})
    assert response.status_code == 400
    assert "outside" in response.json()["detail"].lower()

def test_delete_planted_plant():
    target_code = f"PL-DEL-{uuid.uuid4().hex[:6].upper()}"
    payload = {
        "plant_code": target_code,
        "status": "Alive",
        "latitude": 18.5195,
        "longitude": 73.7800
    }
    create_res = client.post("/api/v1/planted-plants", json=payload, headers={"X-NGO-Admin-Password": "rswf-admin-pass"})
    target_id = create_res.json()["id"]

    del_res = client.delete(f"/api/v1/planted-plants/{target_id}", headers={"X-NGO-Admin-Password": "rswf-admin-pass"})
    assert del_res.status_code == 204

    get_res = client.get(f"/api/v1/planted-plants/{target_id}")
    assert get_res.status_code == 404

def test_inaturalist_record_protection():
    response = client.delete("/api/v1/observations/1", headers={"X-NGO-Admin-Password": "rswf-admin-pass"})
    assert response.status_code == 403
    assert "read-only" in response.json()["detail"].lower()

def test_create_ngo_observation():
    payload = {
        "scientific_name": "Azadirachta indica",
        "common_name": "Neem Tree",
        "observed_on": "2026-08-25",
        "observer": "RSWF NGO Team",
        "latitude": 18.5195,
        "longitude": 73.7800
    }
    response = client.post("/api/v1/observations/ngo", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["source"] == "NGO / New Upload"
    assert data["scientific_name"] == "Azadirachta indica"
