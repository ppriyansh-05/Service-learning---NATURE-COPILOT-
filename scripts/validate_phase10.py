"""
Phase 10 Validation Suite — Pl@ntNet AI Plant Identification
Verifies core service modules, environment configuration, Pl@ntNet API client parsing,
confidence level classification thresholds, error handling, endpoints, human verification flow,
data provenance preservation, and dashboard UI controls.
"""

import sys
import os
import json
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from fastapi.testclient import TestClient
from app.main import app
from app.services.plantnet_service import PlantNetService

client = TestClient(app)

def run_validation():
    print("=" * 70)
    print("    PHASE 10 VALIDATION SUITE — PL@NTNET AI PLANT IDENTIFICATION")
    print("=" * 70)

    passed_count = 0
    total_checks = 0

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    def check(name, status, details=""):
        nonlocal passed_count, total_checks
        total_checks += 1
        tag = "[PASS]" if status else "[FAIL]"
        if status:
            passed_count += 1
        print(f"{tag} {name}")
        if details:
            print(f"       Details: {details}")

    # 1. File Structure Check
    req_files = [
        "backend/app/services/plantnet_service.py",
        "backend/tests/test_plantnet.py",
        "docs/phase_10_plantnet.md",
        ".env.example",
        "frontend/index.html",
        "frontend/js/api.js",
        "frontend/js/app.js"
    ]
    missing = [f for f in req_files if not os.path.exists(os.path.join(base_dir, f))]
    check(
        "Phase 10 Core Architecture & Documentation Files",
        len(missing) == 0,
        "All required files present." if not missing else f"Missing: {missing}"
    )

    # 2. Environment Configuration Check (.env.example)
    env_ex_path = os.path.join(base_dir, ".env.example")
    env_ok = False
    if os.path.exists(env_ex_path):
        with open(env_ex_path, "r", encoding="utf-8") as f:
            content = f.read()
            if "PLANTNET_API_KEY" in content:
                env_ok = True
    check("Environment Configuration (.env.example PLANTNET_API_KEY)", env_ok)

    # 3. Confidence Classification Thresholds Check
    c1 = PlantNetService.classify_confidence(0.95) == "HIGH CONFIDENCE"
    c2 = PlantNetService.classify_confidence(0.75) == "MEDIUM CONFIDENCE"
    c3 = PlantNetService.classify_confidence(0.40) == "LOW CONFIDENCE"
    check("Confidence Level Thresholds (HIGH >=0.90, MED 0.60-0.89, LOW <0.60)", c1 and c2 and c3)

    # 4. Missing API Key Error Handling
    with patch.dict(os.environ, {"PLANTNET_API_KEY": ""}):
        res_missing = PlantNetService.identify_plant("fake.jpg")
        check("Missing API Key Graceful Error Handling", res_missing["error_code"] == "MISSING_API_KEY")

    # 5. Invalid API Key Error Handling
    mock_401 = MagicMock()
    mock_401.status_code = 401
    mock_401.text = "Unauthorized"
    uploads_dir = os.path.join(base_dir, "data", "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    dummy_img = os.path.join(uploads_dir, "val_dummy.jpg")
    with open(dummy_img, "wb") as f:
        f.write(b"dummy image")

    with patch.dict(os.environ, {"PLANTNET_API_KEY": "invalid_key"}):
        with patch("requests.post", return_value=mock_401):
            res_inv = PlantNetService.identify_plant(dummy_img)
            check("Invalid API Key Error Handling (HTTP 401)", res_inv["error_code"] == "INVALID_API_KEY")

    # 6. Response Parsing & Top 3 Normalization (Mocked Provider)
    mock_success = MagicMock()
    mock_success.status_code = 200
    mock_success.json.return_value = {
        "results": [
            {
                "score": 0.92,
                "species": {
                    "scientificNameWithoutAuthor": "Azadirachta indica",
                    "commonNames": ["Neem"],
                    "family": {"scientificNameWithoutAuthor": "Meliaceae"}
                }
            },
            {
                "score": 0.70,
                "species": {
                    "scientificNameWithoutAuthor": "Melia azedarach",
                    "commonNames": ["Chinaberry"]
                }
            },
            {
                "score": 0.25,
                "species": {
                    "scientificNameWithoutAuthor": "Swietenia mahagoni"
                }
            }
        ]
    }

    with patch.dict(os.environ, {"PLANTNET_API_KEY": "valid_key"}):
        with patch("requests.post", return_value=mock_success):
            res = PlantNetService.identify_plant(dummy_img, organ="leaf")
            check(
                "Pl@ntNet Response Parsing & Top 3 Normalization",
                res["success"] is True and len(res["predictions"]) == 3 and res["top_prediction"]["scientific_name"] == "Azadirachta indica",
                f"Top prediction: {res['top_prediction']['scientific_name']} ({res['top_prediction']['confidence_percentage']})"
            )

    # 7. Endpoint POST /api/v1/observations/{id}/identify (Mocked)
    ngo_store = os.path.join(base_dir, "data", "processed", "ngo_observations_store.json")
    dummy_obs = [{
        "id": 888,
        "source": "NGO / New Upload",
        "source_id": "NGO-888",
        "latitude": 18.5195,
        "longitude": 73.7800,
        "photo_url": "/uploads/val_dummy.jpg",
        "scientific_name": None,
        "common_name": None
    }]
    with open(ngo_store, "w", encoding="utf-8") as f:
        json.dump(dummy_obs, f, indent=2)

    with patch.dict(os.environ, {"PLANTNET_API_KEY": "valid_key"}):
        with patch("requests.post", return_value=mock_success):
            ep_res = client.post("/api/v1/observations/888/identify?organ=leaf")
            check(
                "POST /api/v1/observations/{id}/identify Endpoint",
                ep_res.status_code == 200 and ep_res.json()["identification_status"] == "ai_suggested",
                f"Status Code: {ep_res.status_code}"
            )

    # 8. Human Verification Endpoint POST /api/v1/observations/{id}/verify
    verify_res = client.post("/api/v1/observations/888/verify", json={
        "scientific_name": "Azadirachta indica",
        "common_name": "Neem Tree",
        "verification_status": "verified"
    }, headers={"X-NGO-Admin-Password": "rswf-admin-pass"})
    check(
        "POST /api/v1/observations/{id}/verify Endpoint (Human Verification)",
        verify_res.status_code == 200 and verify_res.json()["identification_status"] == "verified"
    )

    # 9. AI Prediction Record Intact in Store
    pred_res = client.get("/api/v1/observations/888/predictions")
    check(
        "AI Prediction Record Preserved Intact After Verification",
        pred_res.status_code == 200 and pred_res.json()["provider"] == "Pl@ntNet"
    )

    # 10. Data Provenance & iNaturalist Protection Check
    obs1 = client.get("/api/v1/observations/1").json()
    check(
        "Data Provenance (iNaturalist Records Read-Only Intact)",
        obs1["source"] == "iNaturalist"
    )

    # 11. Dashboard UI Controls Check
    with open(os.path.join(base_dir, "frontend", "index.html"), "r", encoding="utf-8") as f:
        html = f.read()
        ui_ok = "upload-organ-select" in html and "ai-prediction-card" in html and "btn-trigger-ai" in html
    check("Dashboard Pl@ntNet AI UI Controls & Prediction Card Defined", ui_ok)

    # Cleanup temp dummy test file & stores
    if os.path.exists(dummy_img):
        try:
            os.remove(dummy_img)
        except Exception:
            pass
    with open(ngo_store, "w", encoding="utf-8") as f:
        json.dump([], f, indent=2)
    ai_store = os.path.join(base_dir, "data", "processed", "ai_predictions_store.json")
    if os.path.exists(ai_store):
        with open(ai_store, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)

    print("-" * 70)
    print(f"OVERALL STATUS: {'PASSED' if passed_count == total_checks else 'FAILED'} — {passed_count}/{total_checks} CHECKS SUCCESSFUL")
    print("=" * 70)

    return passed_count == total_checks

if __name__ == "__main__":
    success = run_validation()
    sys.exit(0 if success else 1)
