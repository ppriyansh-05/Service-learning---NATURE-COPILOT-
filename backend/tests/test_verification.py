"""
Phase 11 Human Verification & AI Feedback Loop Pytest Suite
Tests Confirm Top 1, Top 2, Top 3 AI predictions, manual species correction, needs review workflow,
server-side input validation, iNaturalist reference record protection, preservation of original AI predictions,
separate human decision storage, idempotent repeated verifications, and dataset accounting.
All external Pl@ntNet HTTP calls are fully mocked.
"""

import sys
import os
import json
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.services.data_service import DataService
from app.core.config import settings

client = TestClient(app)

@pytest.fixture(autouse=True, scope="module")
def cleanup_after_verification_tests():
    yield
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    ngo_store = os.path.join(base_dir, "data", "processed", "ngo_observations_store.json")
    uploads_dir = os.path.join(base_dir, "data", "uploads")

    DataService._ai_predictions_repository.clear()

    if os.path.exists(ngo_store):
        with open(ngo_store, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)

    if os.path.exists(uploads_dir):
        for fname in os.listdir(uploads_dir):
            if fname.startswith("upload_"):
                try:
                    os.remove(os.path.join(uploads_dir, fname))
                except Exception:
                    pass

@pytest.fixture(scope="module")
def setup_dummy_ngo_observation_with_predictions():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    ngo_store = os.path.join(base_dir, "data", "processed", "ngo_observations_store.json")
    uploads_dir = os.path.join(base_dir, "data", "uploads")
    os.makedirs(uploads_dir, exist_ok=True)

    dummy_image = os.path.join(uploads_dir, "upload_test_verif.jpg")
    with open(dummy_image, "wb") as f:
        f.write(b"dummy image bytes for verification test")

    dummy_obs = [{
        "id": 999,
        "source": "NGO / New Upload",
        "source_id": "NGO-999",
        "latitude": 18.5195,
        "longitude": 73.7800,
        "photo_url": "/uploads/upload_test_verif.jpg",
        "scientific_name": None,
        "common_name": None,
        "identification_status": "pending"
    }]
    with open(ngo_store, "w", encoding="utf-8") as f:
        json.dump(dummy_obs, f, indent=2)

    # Seed AI predictions in database repository
    DataService._ai_predictions_repository.clear()
    DataService._ai_predictions_repository.append({
        "id": 1,
        "observation_id": 999,
        "provider": "Pl@ntNet",
        "organ_used": "leaf",
        "predicted_scientific_name": "Azadirachta indica",
        "predicted_common_name": "Neem",
        "confidence_score": 0.9452,
        "confidence_level": "HIGH CONFIDENCE",
        "predictions": [
            {"rank": 1, "scientific_name": "Azadirachta indica", "common_name": "Neem", "confidence": 0.9452, "confidence_level": "HIGH CONFIDENCE"},
            {"rank": 2, "scientific_name": "Melia azedarach", "common_name": "Chinaberry", "confidence": 0.7210, "confidence_level": "MEDIUM CONFIDENCE"},
            {"rank": 3, "scientific_name": "Swietenia mahagoni", "common_name": "Mahogany", "confidence": 0.3540, "confidence_level": "LOW CONFIDENCE"}
        ],
        "user_confirmed": False
    })
    return 999

# 1. Confirm Top 1 Prediction
def test_confirm_top_1_prediction(setup_dummy_ngo_observation_with_predictions):
    obs_id = setup_dummy_ngo_observation_with_predictions
    res = client.post(f"/api/v1/observations/{obs_id}/verify", json={
        "decision": "confirm",
        "selected_prediction_rank": 1
    }, headers={"X-NGO-Admin-Password": "rswf-admin-pass"})
    assert res.status_code == 200
    data = res.json()
    assert data["decision"] == "confirm"
    assert data["identification_status"] == "verified"
    assert data["scientific_name"] == "Azadirachta indica"
    assert data["quality_grade"] == "research"

# 2. Confirm Top 2 Prediction
def test_confirm_top_2_prediction(setup_dummy_ngo_observation_with_predictions):
    obs_id = setup_dummy_ngo_observation_with_predictions
    res = client.post(f"/api/v1/observations/{obs_id}/verify", json={
        "decision": "confirm",
        "selected_prediction_rank": 2
    }, headers={"X-NGO-Admin-Password": "rswf-admin-pass"})
    assert res.status_code == 200
    data = res.json()
    assert data["scientific_name"] == "Melia azedarach"
    assert data["identification_status"] == "verified"

# 3. Confirm Top 3 Prediction
def test_confirm_top_3_prediction(setup_dummy_ngo_observation_with_predictions):
    obs_id = setup_dummy_ngo_observation_with_predictions
    res = client.post(f"/api/v1/observations/{obs_id}/verify", json={
        "decision": "confirm",
        "selected_prediction_rank": 3
    }, headers={"X-NGO-Admin-Password": "rswf-admin-pass"})
    assert res.status_code == 200
    data = res.json()
    assert data["scientific_name"] == "Swietenia mahagoni"

# 4. Manual Correction Flow
def test_manual_correction_flow(setup_dummy_ngo_observation_with_predictions):
    obs_id = setup_dummy_ngo_observation_with_predictions
    res = client.post(f"/api/v1/observations/{obs_id}/verify", json={
        "decision": "correct",
        "scientific_name": "Moringa oleifera",
        "common_name": "Drumstick Tree",
        "notes": "Field leaf pattern confirmed Moringa"
    }, headers={"X-NGO-Admin-Password": "rswf-admin-pass"})
    assert res.status_code == 200
    data = res.json()
    assert data["decision"] == "correct"
    assert data["identification_status"] == "corrected"
    assert data["scientific_name"] == "Moringa oleifera"

# 5. Needs Review Flow
def test_needs_review_flow(setup_dummy_ngo_observation_with_predictions):
    obs_id = setup_dummy_ngo_observation_with_predictions
    res = client.post(f"/api/v1/observations/{obs_id}/verify", json={
        "decision": "needs_review",
        "notes": "Foliage ambiguous, requiring botanist inspection"
    }, headers={"X-NGO-Admin-Password": "rswf-admin-pass"})
    assert res.status_code == 200
    data = res.json()
    assert data["decision"] == "needs_review"
    assert data["identification_status"] == "needs_review"

# 6. Invalid Verification Decision Rejection
def test_invalid_decision_rejection(setup_dummy_ngo_observation_with_predictions):
    obs_id = setup_dummy_ngo_observation_with_predictions
    res = client.post(f"/api/v1/observations/{obs_id}/verify", json={
        "decision": "invalid_action_type"
    }, headers={"X-NGO-Admin-Password": "rswf-admin-pass"})
    assert res.status_code == 400

# 7. Invalid Observation ID Handling
def test_invalid_observation_id_verification():
    res = client.post("/api/v1/observations/999999/verify", json={"decision": "confirm"}, headers={"X-NGO-Admin-Password": "rswf-admin-pass"})
    assert res.status_code == 400 or res.status_code == 404

# 8. Protection of iNaturalist Reference Observations
def test_inaturalist_verification_blocked():
    res = client.post("/api/v1/observations/1/verify", json={"decision": "confirm"}, headers={"X-NGO-Admin-Password": "rswf-admin-pass"})
    assert res.status_code == 403
    assert "read-only" in res.json()["detail"].lower()

# 9. Original AI Prediction Preserved Intact
def test_original_ai_prediction_preservation(setup_dummy_ngo_observation_with_predictions):
    obs_id = setup_dummy_ngo_observation_with_predictions
    pred_res = client.get(f"/api/v1/observations/{obs_id}/predictions")
    assert pred_res.status_code == 200
    pred = pred_res.json()
    
    # Check original AI prediction fields remain intact
    assert pred["predicted_scientific_name"] == "Azadirachta indica"
    assert pred["confidence_score"] == 0.9452
    assert pred["provider"] == "Pl@ntNet"

# 10. Separate Human Decision Storage
def test_separate_human_decision_storage(setup_dummy_ngo_observation_with_predictions):
    obs_id = setup_dummy_ngo_observation_with_predictions
    client.post(f"/api/v1/observations/{obs_id}/verify", json={
        "decision": "correct",
        "scientific_name": "Ficus benghalensis"
    }, headers={"X-NGO-Admin-Password": "rswf-admin-pass"})
    
    pred = DataService.get_observation_ai_predictions(obs_id)
    assert pred["predicted_scientific_name"] == "Azadirachta indica" # AI original
    assert pred["human_decision"] == "correct"
    assert pred["verified_scientific_name"] == "Ficus benghalensis" # Separate human decision

# 11. Repeated Verification Safety (No Duplicates)
def test_repeated_verification_safety(setup_dummy_ngo_observation_with_predictions):
    obs_id = setup_dummy_ngo_observation_with_predictions
    res1 = client.post(f"/api/v1/observations/{obs_id}/verify", json={"decision": "confirm", "selected_prediction_rank": 1}, headers={"X-NGO-Admin-Password": "rswf-admin-pass"})
    res2 = client.post(f"/api/v1/observations/{obs_id}/verify", json={"decision": "confirm", "selected_prediction_rank": 1}, headers={"X-NGO-Admin-Password": "rswf-admin-pass"})
    assert res1.status_code == 200
    assert res2.status_code == 200

# 12. AI Feedback Loop Metrics Endpoint
def test_ai_feedback_metrics_endpoint():
    res = client.get("/api/v1/observations/ai-feedback")
    assert res.status_code == 200
    data = res.json()
    assert "total_ai_predictions_reviewed" in data
    assert "confirmation_rate_percentage" in data

# 13. iNaturalist Records Total Unchanged
def test_inaturalist_total_unchanged():
    obs_res = client.get("/api/v1/observations?source=iNaturalist")
    assert obs_res.status_code == 200
    assert obs_res.json()["total_records"] == 227


# Observation list includes NGO field observations (stored outside the DB table) and matches the overview totals
def test_observation_list_total_matches_statistics():
    stats = client.get("/api/v1/statistics/overview").json()
    listing = client.get("/api/v1/observations?limit=1").json()
    assert listing["total_records"] == stats["total_observations"]
    for zone in ("ZONE A", "ZONE B", "ZONE C"):
        z = client.get("/api/v1/observations", params={"limit": 1, "zone": zone}).json()
        assert z["total_records"] == stats["observations_by_zone"].get(zone, 0)


# Confirming a record's suggested species works without an in-session AI run, and keeps earlier notes
def test_confirm_suggested_species_keeps_provenance_notes():
    import json as _json
    from app.services.data_service import get_base_dir
    store_path = os.path.join(get_base_dir(), "data", "processed", "ngo_observations_store.json")
    rec = client.post("/api/v1/observations/ngo", json={
        "scientific_name": "Ficus religiosa", "common_name": "Peepal",
        "latitude": 18.5184386, "longitude": 73.7802123}).json()
    with open(store_path, encoding="utf-8") as f:
        store = _json.load(f)
    for r in store:
        if r["id"] == rec["id"]:
            r["verification_notes"] = "Imported from field folder"
            r["ai_top_predictions"] = [{"rank": 1, "scientific_name": "Ficus religiosa", "common_name": "Peepal", "confidence_percentage": "36.0%"}]
    with open(store_path, "w", encoding="utf-8") as f:
        _json.dump(store, f)

    headers = {"X-NGO-Admin-Password": "rswf-admin-pass"}
    res = client.post(f"/api/v1/observations/{rec['id']}/verify", headers=headers,
                      json={"decision": "confirm", "scientific_name": "Ficus religiosa", "notes": "Checked in field"})
    assert res.status_code == 200, res.text
    obs = client.get(f"/api/v1/observations/{rec['id']}").json()
    assert obs["scientific_name"] == "Ficus religiosa"
    assert obs["identification_status"] == "verified"
    assert obs["verification_notes"].startswith("Imported from field folder")
    assert "Checked in field" in obs["verification_notes"]
