"""
Pytest Unit Tests for Phase 15 Password-Protected Editing & Read-Only iNaturalist Data.
Tests public open access (GET, upload, exports, reports), protected mutation rejection (401 missing/wrong password),
protected mutation authorization success (201/200/204 with valid X-NGO-Admin-Password header),
and strict iNaturalist read-only protection (403 Forbidden even WITH valid password header).
"""

import sys
import os
import uuid
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.services.data_service import DataService, save_planted_plants_store, DEFAULT_PLANTED_PLANTS

client = TestClient(app)

VALID_AUTH_HEADER = {"X-NGO-Admin-Password": "rswf-admin-pass"}
INVALID_AUTH_HEADER = {"X-NGO-Admin-Password": "wrong-password-xyz"}

@pytest.fixture(autouse=True, scope="module")
def cleanup_after_auth_tests():
    yield
    DataService._plant_monitoring_repository.clear()
    save_planted_plants_store(DEFAULT_PLANTED_PLANTS)


# 1. Public GET Endpoints Open
def test_public_get_endpoints_open():
    endpoints = [
        "/health",
        "/health/db",
        "/api/v1/observations",
        "/api/v1/species",
        "/api/v1/zones",
        "/api/v1/geography",
        "/api/v1/map/observations",
        "/api/v1/statistics/overview",
        "/api/v1/planted-plants",
        "/api/v1/planted-plants/1",
        "/api/v1/planted-plants/1/monitoring",
        "/api/v1/planted-plants/monitoring/statistics"
    ]
    for ep in endpoints:
        res = client.get(ep)
        assert res.status_code == 200, f"Endpoint {ep} failed with status {res.status_code}"


# 2. Public Export & Report Endpoints Open
def test_public_export_and_reports_open():
    res_obs_csv = client.get("/api/v1/export/observations.csv")
    assert res_obs_csv.status_code == 200

    res_planted_csv = client.get("/api/v1/export/planted-plants.csv")
    assert res_planted_csv.status_code == 200

    res_cons_json = client.get("/api/v1/reports/conservation")
    assert res_cons_json.status_code == 200

    res_cons_pdf = client.get("/api/v1/reports/conservation.pdf")
    assert res_cons_pdf.status_code == 200
    assert res_cons_pdf.headers.get("content-type") == "application/pdf"


# 3. Protected Create Planted Plant — Missing Password Rejected (401)
def test_protected_create_plant_missing_password_rejected():
    payload = {
        "plant_code": f"PL-AUTH-{uuid.uuid4().hex[:4].upper()}",
        "status": "Alive",
        "latitude": 18.5195,
        "longitude": 73.7800
    }
    res = client.post("/api/v1/planted-plants", json=payload)
    assert res.status_code == 401
    assert "password is required" in res.json()["detail"].lower()


# 4. Protected Create Planted Plant — Wrong Password Rejected (401)
def test_protected_create_plant_wrong_password_rejected():
    payload = {
        "plant_code": f"PL-AUTH-{uuid.uuid4().hex[:4].upper()}",
        "status": "Alive",
        "latitude": 18.5195,
        "longitude": 73.7800
    }
    res = client.post("/api/v1/planted-plants", json=payload, headers=INVALID_AUTH_HEADER)
    assert res.status_code == 401
    assert "invalid" in res.json()["detail"].lower()


# 5. Protected Create Planted Plant — Valid Password Success (201)
def test_protected_create_plant_valid_password_success():
    code = f"PL-AUTH-{uuid.uuid4().hex[:4].upper()}"
    payload = {
        "plant_code": code,
        "status": "Alive",
        "latitude": 18.5195,
        "longitude": 73.7800
    }
    res = client.post("/api/v1/planted-plants", json=payload, headers=VALID_AUTH_HEADER)
    assert res.status_code == 201
    assert res.json()["plant_code"] == code


# 6. Protected Update Planted Plant — Password Required
def test_protected_update_plant_password_required():
    # Without header -> 401
    res_no_auth = client.put("/api/v1/planted-plants/1", json={"status": "Dead"})
    assert res_no_auth.status_code == 401

    # With invalid header -> 401
    res_bad_auth = client.put("/api/v1/planted-plants/1", json={"status": "Dead"}, headers=INVALID_AUTH_HEADER)
    assert res_bad_auth.status_code == 401

    # With valid header -> 200
    res_ok = client.put("/api/v1/planted-plants/1", json={"status": "Dead"}, headers=VALID_AUTH_HEADER)
    assert res_ok.status_code == 200
    assert res_ok.json()["status"] == "Dead"

    # Restore baseline
    save_planted_plants_store(DEFAULT_PLANTED_PLANTS)


# 7. Protected Delete Planted Plant — Password Required
def test_protected_delete_plant_password_required():
    code = f"PL-DEL-{uuid.uuid4().hex[:4].upper()}"
    create_res = client.post("/api/v1/planted-plants", json={
        "plant_code": code, "status": "Alive", "latitude": 18.5195, "longitude": 73.7800
    }, headers=VALID_AUTH_HEADER)
    target_id = create_res.json()["id"]

    # Without auth -> 401
    del_no_auth = client.delete(f"/api/v1/planted-plants/{target_id}")
    assert del_no_auth.status_code == 401

    # With valid auth -> 204
    del_ok = client.delete(f"/api/v1/planted-plants/{target_id}", headers=VALID_AUTH_HEADER)
    assert del_ok.status_code == 204


# 8. Protected Monitoring Visit — Password Required
def test_protected_monitoring_visit_password_required():
    # Without auth -> 401
    res_no_auth = client.post("/api/v1/planted-plants/1/monitoring", json={
        "status": "Alive", "monitoring_date": "2026-09-02"
    })
    assert res_no_auth.status_code == 401

    # With valid auth -> 201
    res_ok = client.post("/api/v1/planted-plants/1/monitoring", json={
        "status": "Alive", "monitoring_date": "2026-09-02"
    }, headers=VALID_AUTH_HEADER)
    assert res_ok.status_code == 201


# 9. iNaturalist Deletion Blocked Even WITH Valid Password (403)
def test_inaturalist_deletion_blocked_even_with_valid_password():
    res = client.delete("/api/v1/observations/1", headers=VALID_AUTH_HEADER)
    assert res.status_code == 403
    assert "read-only" in res.json()["detail"].lower()


# 10. iNaturalist Verification Edit Blocked Even WITH Valid Password (403)
def test_inaturalist_verification_blocked_even_with_valid_password():
    res = client.post("/api/v1/observations/1/verify", json={"decision": "confirm"}, headers=VALID_AUTH_HEADER)
    assert res.status_code == 403
    assert "read-only" in res.json()["detail"].lower()


# 11. Baseline Data Integrity Counts Intact
def test_baseline_data_counts_intact():
    save_planted_plants_store(DEFAULT_PLANTED_PLANTS)
    obs_res = client.get("/api/v1/observations")
    ngo_res = client.get("/api/v1/observations?source=NGO / New Upload")
    plant_res = client.get("/api/v1/planted-plants")

    assert obs_res.json()["total_records"] == 227
    assert ngo_res.json()["total_records"] == 0
    assert plant_res.json()["total_records"] == 3
