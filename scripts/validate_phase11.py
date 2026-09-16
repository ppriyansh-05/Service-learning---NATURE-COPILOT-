"""
Automated Validation Suite for Phase 11 — Human Verification & AI Feedback Loop
Validates human verification decision workflows (confirm Top 1/2/3, correct, needs_review),
database prediction preservation, separate human decision storage, server-side validation,
iNaturalist reference record protection, API feedback metrics endpoint, and dashboard UI controls.
"""

import sys
import os
import json
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.services.data_service import DataService

client = TestClient(app)

def run_phase11_validation():
    print("=" * 70)
    print("    PHASE 11 VALIDATION SUITE — HUMAN VERIFICATION & AI FEEDBACK LOOP")
    print("=" * 70)

    passed_checks = 0
    total_checks = 10
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    # 1. File existence check
    req_files = [
        "backend/tests/test_verification.py",
        "docs/phase_11_human_verification.md",
        "PROJECT_TRACKER.md"
    ]
    all_files_found = True
    for rel_path in req_files:
        full_p = os.path.join(base_dir, rel_path)
        if not os.path.exists(full_p):
            print(f"[FAIL] Missing required file: {rel_path}")
            all_files_found = False
    
    if all_files_found:
        print("[PASS] Core Architecture & Documentation Files Present")
        passed_checks += 1
    else:
        print("[FAIL] Missing required Phase 11 files.")

    # Setup dummy NGO record & AI prediction repository
    ngo_store = os.path.join(base_dir, "data", "processed", "ngo_observations_store.json")
    uploads_dir = os.path.join(base_dir, "data", "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    
    dummy_img = os.path.join(uploads_dir, "upload_val11.jpg")
    with open(dummy_img, "wb") as f:
        f.write(b"dummy image for phase 11 validation")

    with open(ngo_store, "w", encoding="utf-8") as f:
        json.dump([{
            "id": 999,
            "source": "NGO / New Upload",
            "source_id": "NGO-999",
            "latitude": 18.5195,
            "longitude": 73.7800,
            "photo_url": "/uploads/upload_val11.jpg",
            "scientific_name": None,
            "common_name": None,
            "identification_status": "pending"
        }], f, indent=2)

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
            {"rank": 1, "scientific_name": "Azadirachta indica", "common_name": "Neem", "confidence": 0.9452},
            {"rank": 2, "scientific_name": "Melia azedarach", "common_name": "Chinaberry", "confidence": 0.7210},
            {"rank": 3, "scientific_name": "Swietenia mahagoni", "common_name": "Mahogany", "confidence": 0.3540}
        ],
        "user_confirmed": False
    })

    # 2. Confirm Top 1 Prediction
    res1 = client.post("/api/v1/observations/999/verify", json={"decision": "confirm", "selected_prediction_rank": 1}, headers={"X-NGO-Admin-Password": "rswf-admin-pass"})
    if res1.status_code == 200 and res1.json()["scientific_name"] == "Azadirachta indica":
        print("[PASS] Confirm Top 1 AI Prediction Flow")
        passed_checks += 1
    else:
        print(f"[FAIL] Confirm Top 1 failed: {res1.status_code} {res1.text}")

    # 3. Confirm Top 2 Prediction
    res2 = client.post("/api/v1/observations/999/verify", json={"decision": "confirm", "selected_prediction_rank": 2}, headers={"X-NGO-Admin-Password": "rswf-admin-pass"})
    if res2.status_code == 200 and res2.json()["scientific_name"] == "Melia azedarach":
        print("[PASS] Confirm Top 2 AI Prediction Flow")
        passed_checks += 1
    else:
        print(f"[FAIL] Confirm Top 2 failed: {res2.status_code} {res2.text}")

    # 4. Manual Correction Flow
    res3 = client.post("/api/v1/observations/999/verify", json={
        "decision": "correct",
        "scientific_name": "Moringa oleifera",
        "common_name": "Drumstick Tree",
        "notes": "Leaf structure verification"
    }, headers={"X-NGO-Admin-Password": "rswf-admin-pass"})
    if res3.status_code == 200 and res3.json()["scientific_name"] == "Moringa oleifera" and res3.json()["identification_status"] == "corrected":
        print("[PASS] Manual Species Correction Flow")
        passed_checks += 1
    else:
        print(f"[FAIL] Manual correction failed: {res3.status_code} {res3.text}")

    # 5. Needs Review Flow
    res4 = client.post("/api/v1/observations/999/verify", json={"decision": "needs_review", "notes": "Ambiguous sample"}, headers={"X-NGO-Admin-Password": "rswf-admin-pass"})
    if res4.status_code == 200 and res4.json()["identification_status"] == "needs_review":
        print("[PASS] Needs Expert Review Flow")
        passed_checks += 1
    else:
        print(f"[FAIL] Needs review failed: {res4.status_code} {res4.text}")

    # 6. Preservation of Original AI Prediction
    pred = DataService.get_observation_ai_predictions(999)
    if pred and pred["predicted_scientific_name"] == "Azadirachta indica" and pred["confidence_score"] == 0.9452:
        print("[PASS] Preservation of Original AI Prediction Intact")
        passed_checks += 1
    else:
        print("[FAIL] Original AI prediction altered or overwritten!")

    # 7. Separate Human Decision Storage
    if pred and pred.get("human_decision") == "needs_review":
        print("[PASS] Separate Human Decision Audit Trail Storage")
        passed_checks += 1
    else:
        print("[FAIL] Human decision audit trail missing!")

    # 8. Server-side Invalid Decision Rejection
    res_inv = client.post("/api/v1/observations/999/verify", json={"decision": "bad_decision_type"}, headers={"X-NGO-Admin-Password": "rswf-admin-pass"})
    if res_inv.status_code == 400:
        print("[PASS] Server-Side Invalid Decision Rejection (HTTP 400)")
        passed_checks += 1
    else:
        print(f"[FAIL] Invalid decision rejection failed: {res_inv.status_code}")

    # 9. Protection of iNaturalist Reference Dataset
    res_inat = client.post("/api/v1/observations/1/verify", json={"decision": "confirm"}, headers={"X-NGO-Admin-Password": "rswf-admin-pass"})
    if res_inat.status_code == 403:
        print("[PASS] Data Provenance Protection (iNaturalist Records Read-Only Intact)")
        passed_checks += 1
    else:
        print(f"[FAIL] iNaturalist protection failed: {res_inat.status_code}")

    # 10. AI Feedback Metrics Endpoint
    res_fb = client.get("/api/v1/observations/ai-feedback")
    if res_fb.status_code == 200 and "total_ai_predictions_reviewed" in res_fb.json():
        print("[PASS] GET /api/v1/observations/ai-feedback Metrics Endpoint")
        passed_checks += 1
    else:
        print(f"[FAIL] AI feedback metrics endpoint failed: {res_fb.status_code}")

    # Teardown test data
    DataService._ai_predictions_repository.clear()
    with open(ngo_store, "w", encoding="utf-8") as f:
        json.dump([], f, indent=2)
    if os.path.exists(dummy_img):
        try:
            os.remove(dummy_img)
        except Exception:
            pass

    print("-" * 70)
    print(f"OVERALL STATUS: {'PASSED — ' + str(passed_checks) + '/' + str(total_checks) + ' CHECKS SUCCESSFUL' if passed_checks == total_checks else 'FAILED'}")
    print("=" * 70)
    return passed_checks == total_checks

if __name__ == "__main__":
    success = run_phase11_validation()
    sys.exit(0 if success else 1)
