"""
Phase 10 & 10.1 Pl@ntNet AI Plant Identification Pytest Suite
Tests Pl@ntNet API response normalization, Top 3 parsing, confidence level thresholds,
missing/invalid API key error handling, HTTP timeout/rate limit handling, database repository prediction storage,
multiple prediction attempt traceability, separation of AI prediction vs human verification, and provenance preservation.
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
from app.services.plantnet_service import PlantNetService
from app.services.data_service import DataService

client = TestClient(app)

@pytest.fixture(autouse=True, scope="module")
def cleanup_after_plantnet_tests():
    yield
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    ngo_store = os.path.join(base_dir, "data", "processed", "ngo_observations_store.json")
    uploads_dir = os.path.join(base_dir, "data", "uploads")
    ai_file_store = os.path.join(base_dir, "data", "processed", "ai_predictions_store.json")

    # Reset repository memory store
    DataService._ai_predictions_repository.clear()

    if os.path.exists(ngo_store):
        with open(ngo_store, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)

    if os.path.exists(ai_file_store):
        try:
            os.remove(ai_file_store)
        except Exception:
            pass

    if os.path.exists(uploads_dir):
        for fname in os.listdir(uploads_dir):
            if fname.startswith("upload_"):
                try:
                    os.remove(os.path.join(uploads_dir, fname))
                except Exception:
                    pass

@pytest.fixture(scope="module")
def temp_dummy_image():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    uploads_dir = os.path.join(base_dir, "data", "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    img_path = os.path.join(uploads_dir, "upload_fake_test_plant.jpg")
    with open(img_path, "wb") as f:
        f.write(b"dummy image content for pytest")
    yield img_path
    if os.path.exists(img_path):
        try:
            os.remove(img_path)
        except Exception:
            pass

# Mock Pl@ntNet API response payload
MOCK_PLANTNET_SUCCESS_RESPONSE = {
    "query": {"project": "all", "images": ["test.jpg"], "organs": ["auto"]},
    "results": [
        {
            "score": 0.9452,
            "species": {
                "scientificNameWithoutAuthor": "Azadirachta indica",
                "scientificName": "Azadirachta indica A.Juss.",
                "commonNames": ["Neem", "Neem tree"],
                "family": {"scientificNameWithoutAuthor": "Meliaceae"},
                "genus": {"scientificNameWithoutAuthor": "Azadirachta"}
            }
        },
        {
            "score": 0.7210,
            "species": {
                "scientificNameWithoutAuthor": "Melia azedarach",
                "commonNames": ["Chinaberry"],
                "family": {"scientificNameWithoutAuthor": "Meliaceae"},
                "genus": {"scientificNameWithoutAuthor": "Melia"}
            }
        },
        {
            "score": 0.3540,
            "species": {
                "scientificNameWithoutAuthor": "Swietenia mahagoni",
                "commonNames": ["Mahogany"],
                "family": {"scientificNameWithoutAuthor": "Meliaceae"},
                "genus": {"scientificNameWithoutAuthor": "Swietenia"}
            }
        }
    ]
}

# 1. Confidence Classification Thresholds
def test_confidence_classification():
    assert PlantNetService.classify_confidence(0.95) == "HIGH CONFIDENCE"
    assert PlantNetService.classify_confidence(0.90) == "HIGH CONFIDENCE"
    assert PlantNetService.classify_confidence(0.75) == "MEDIUM CONFIDENCE"
    assert PlantNetService.classify_confidence(0.60) == "MEDIUM CONFIDENCE"
    assert PlantNetService.classify_confidence(0.45) == "LOW CONFIDENCE"

# 2. Missing API Key Handling
def test_missing_api_key_handling(temp_dummy_image):
    with patch.dict(os.environ, {"PLANTNET_API_KEY": ""}):
        res = PlantNetService.identify_plant(temp_dummy_image)
        assert res["success"] is False
        assert res["error_code"] == "MISSING_API_KEY"

# 3. Invalid API Key Response Handling
def test_invalid_api_key_response(temp_dummy_image):
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "Unauthorized"

    with patch.dict(os.environ, {"PLANTNET_API_KEY": "invalid_key"}):
        with patch("requests.post", return_value=mock_resp):
            res = PlantNetService.identify_plant(temp_dummy_image)
            assert res["success"] is False
            assert res["error_code"] == "INVALID_API_KEY"

# 4. Rate Limit Response Handling
def test_rate_limit_response(temp_dummy_image):
    mock_resp = MagicMock()
    mock_resp.status_code = 429

    with patch.dict(os.environ, {"PLANTNET_API_KEY": "valid_key"}):
        with patch("requests.post", return_value=mock_resp):
            res = PlantNetService.identify_plant(temp_dummy_image)
            assert res["success"] is False
            assert res["error_code"] == "RATE_LIMIT_EXCEEDED"

# 5. Network Timeout Handling
def test_network_timeout_handling(temp_dummy_image):
    with patch.dict(os.environ, {"PLANTNET_API_KEY": "valid_key"}):
        with patch("requests.post", side_effect=Exception("Connection timed out")):
            res = PlantNetService.identify_plant(temp_dummy_image)
            assert res["success"] is False
            assert res["error_code"] == "REQUEST_FAILED"

# 6. Valid Pl@ntNet Response Parsing & Top 3 Extraction
def test_plantnet_response_parsing(temp_dummy_image):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_PLANTNET_SUCCESS_RESPONSE

    with patch.dict(os.environ, {"PLANTNET_API_KEY": "test_key_123"}):
        with patch("requests.post", return_value=mock_resp):
            res = PlantNetService.identify_plant(temp_dummy_image, organ="leaf")
            assert res["success"] is True
            assert res["total_predictions"] == 3
            
            top = res["top_prediction"]
            assert top["scientific_name"] == "Azadirachta indica"
            assert top["common_name"] == "Neem"
            assert top["confidence"] == 0.9452
            assert top["confidence_level"] == "HIGH CONFIDENCE"

            pred2 = res["predictions"][1]
            assert pred2["scientific_name"] == "Melia azedarach"
            assert pred2["confidence_level"] == "MEDIUM CONFIDENCE"

            pred3 = res["predictions"][2]
            assert pred3["confidence_level"] == "LOW CONFIDENCE"

# 7. Endpoint POST /api/v1/observations/{id}/identify integration & Database Repository Storage
def test_identify_observation_endpoint_and_db_repository(temp_dummy_image):
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    ngo_store = os.path.join(base_dir, "data", "processed", "ngo_observations_store.json")
    
    fname = os.path.basename(temp_dummy_image)
    dummy_obs = [{
        "id": 999,
        "source": "NGO / New Upload",
        "source_id": "NGO-999",
        "latitude": 18.5195,
        "longitude": 73.7800,
        "photo_url": f"/uploads/{fname}",
        "scientific_name": None,
        "common_name": None
    }]
    with open(ngo_store, "w", encoding="utf-8") as f:
        json.dump(dummy_obs, f, indent=2)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_PLANTNET_SUCCESS_RESPONSE

    with patch.dict(os.environ, {"PLANTNET_API_KEY": "test_key"}):
        with patch("requests.post", return_value=mock_resp):
            response = client.post("/api/v1/observations/999/identify?organ=leaf")
            assert response.status_code == 200
            data = response.json()
            assert data["observation_id"] == 999
            assert data["identification_status"] == "ai_suggested"
            assert len(data["predictions"]) == 3
            assert data["top_prediction"]["scientific_name"] == "Azadirachta indica"

    # Verify prediction is stored in database repository
    db_preds = DataService.get_observation_ai_predictions(999)
    assert db_preds is not None
    assert db_preds["observation_id"] == 999
    assert db_preds["provider"] == "Pl@ntNet"
    assert db_preds["predicted_scientific_name"] == "Azadirachta indica"

# 8. Test Multiple Prediction Attempts Traceability
def test_multiple_prediction_attempts_traceable(temp_dummy_image):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_PLANTNET_SUCCESS_RESPONSE

    with patch.dict(os.environ, {"PLANTNET_API_KEY": "test_key"}):
        with patch("requests.post", return_value=mock_resp):
            res2 = client.post("/api/v1/observations/999/identify?organ=flower")
            assert res2.status_code == 200

    # Ensure repository contains both attempts for observation #999
    obs_attempts = [r for r in DataService._ai_predictions_repository if r.get("observation_id") == 999]
    assert len(obs_attempts) >= 2
    assert obs_attempts[0]["organ_used"] == "leaf"
    assert obs_attempts[1]["organ_used"] == "flower"

# 9. Human Verification Endpoint POST /api/v1/observations/{id}/verify
def test_human_verification_preserves_ai_prediction():
    verify_payload = {
        "scientific_name": "Azadirachta indica",
        "common_name": "Neem Tree",
        "verification_status": "verified"
    }
    response = client.post("/api/v1/observations/999/verify", json=verify_payload, headers={"X-NGO-Admin-Password": "rswf-admin-pass"})
    assert response.status_code == 200
    data = response.json()
    assert data["scientific_name"] == "Azadirachta indica"
    assert data["identification_status"] == "verified"

    # Verify AI prediction record remains intact in database repository
    pred_res = client.get("/api/v1/observations/999/predictions")
    assert pred_res.status_code == 200
    pred_data = pred_res.json()
    assert pred_data["provider"] == "Pl@ntNet"
    assert pred_data["user_confirmed"] is True

# 10. iNaturalist records protection check
def test_inaturalist_records_unchanged():
    obs1 = client.get("/api/v1/observations/1").json()
    assert obs1["source"] == "iNaturalist"
