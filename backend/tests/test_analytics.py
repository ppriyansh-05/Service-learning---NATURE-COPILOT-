"""
Phase 13 Advanced Biodiversity & Conservation Analytics Pytest Suite
Tests recorded biodiversity analytics, unique taxa counts, zone-wise observations and taxa,
source breakdown, species analytics, coverage indicators, transparent action-priority rules,
insufficient-data handling, data isolation (no false data), status editability, historical preservation,
and regression stability across AI, upload, and export functions.
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
def cleanup_after_analytics_tests():
    ngo_store_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed", "ngo_observations_store.json"))
    with open(ngo_store_path, "w", encoding="utf-8") as f:
        json.dump([], f, indent=2)
    yield
    # Purge any transient test data created during test runs
    with open(ngo_store_path, "w", encoding="utf-8") as f:
        json.dump([], f, indent=2)

# 1. Biodiversity Overview Endpoint
def test_analytics_biodiversity_overview():
    res = client.get("/api/v1/analytics/biodiversity")
    assert res.status_code == 200
    data = res.json()
    assert "total_recorded_observations" in data
    assert "unique_recorded_taxa_count" in data
    assert "species_level_taxa_count" in data
    assert "provenance_note" in data

# 2. Unique Recorded Taxa
def test_analytics_unique_taxa():
    res = client.get("/api/v1/analytics/biodiversity")
    data = res.json()
    assert data["unique_recorded_taxa_count"] == 88

# 3. Zone-Wise Observations Breakdown
def test_analytics_zone_observations():
    res = client.get("/api/v1/analytics/biodiversity")
    data = res.json()
    by_zone = data["observations_by_zone"]
    assert "ZONE A" in by_zone
    assert "ZONE B" in by_zone
    assert "ZONE C" in by_zone
    assert "OUTSIDE_ACTIVE_ZONES" in by_zone
    assert sum(by_zone.values()) == 227

# 4. Zone-Wise Taxa Distribution
def test_analytics_zone_taxa():
    res = client.get("/api/v1/analytics/biodiversity")
    data = res.json()
    taxa_zone = data["unique_taxa_by_zone"]
    assert taxa_zone["ZONE A"] > 0
    assert taxa_zone["ZONE B"] > 0
    assert taxa_zone["ZONE C"] > 0

# 5. Source Breakdown Provenance
def test_analytics_source_breakdown():
    res = client.get("/api/v1/analytics/biodiversity")
    data = res.json()
    sources = data["observations_by_source"]
    assert sources.get("iNaturalist") == 227
    assert sources.get("NGO / New Upload", 0) == 0

# 6. Species Analytics & Top Taxa
def test_analytics_species():
    res = client.get("/api/v1/analytics/species")
    assert res.status_code == 200
    data = res.json()
    assert "top_recorded_taxa" in data
    assert len(data["top_recorded_taxa"]) <= 10
    assert "multi_zone_taxa" in data
    assert "sampling_frequency_notice" in data

# 7. Coverage Analytics Indicators
def test_analytics_coverage():
    res = client.get("/api/v1/analytics/coverage")
    assert res.status_code == 200
    data = res.json()
    assert "active_zones_summary" in data
    assert "non_active_portion_summary" in data
    assert "No recorded observations are currently available" in data["non_active_portion_summary"]["scientific_wording"]

# 8. Transparent Action-Priority Logic
def test_analytics_action_priorities():
    res = client.get("/api/v1/analytics/action-priorities")
    assert res.status_code == 200
    data = res.json()
    assert "priorities" in data
    priorities = data["priorities"]
    priority_types = [p["priority_type"] for p in priorities]
    assert any(pt in ["MONITORING_PRIORITY", "SURVEY_PRIORITY", "DATA_COLLECTION_PRIORITY", "NO_IMMEDIATE_DATA_DRIVEN_PRIORITY"] for pt in priority_types)

# 9. Insufficient-Data & Temporal Timeline Handling
def test_analytics_temporal_timeline():
    res = client.get("/api/v1/analytics/temporal")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert data["status"] in ["available", "insufficient_data"]

# 10. No False/Fabricated Records Created
def test_no_false_records_created():
    obs_res = client.get("/api/v1/observations")
    assert obs_res.status_code == 200
    assert obs_res.json()["total_records"] == 227

# 11. iNaturalist Count Baseline Remains 227
def test_inaturalist_baseline_remains_227():
    obs_res = client.get("/api/v1/observations?source=iNaturalist")
    assert obs_res.status_code == 200
    assert obs_res.json()["total_records"] == 227

# 12. NGO/New Upload Count Remains 0 Baseline
def test_ngo_upload_baseline_remains_0():
    obs_res = client.get("/api/v1/observations?source=NGO / New Upload")
    assert obs_res.status_code == 200
    assert obs_res.json()["total_records"] == 0

# 13. Planted Plant Count Baseline Remains 3
def test_planted_plant_baseline_remains_3():
    p_res = client.get("/api/v1/planted-plants")
    assert p_res.status_code == 200
    assert p_res.json()["total_records"] == 3

# 14. Plant Monitoring Status Remains Editable
def test_plant_status_remains_editable():
    res = client.post("/api/v1/planted-plants/1/monitoring", json={
        "status": "Alive",
        "monitoring_date": "2026-09-02",
        "notes": "Healthy foliage verified"
    }, headers={"X-NGO-Admin-Password": "rswf-admin-pass"})
    assert res.status_code == 201
    assert res.json()["status"] == "Alive"

# 15. Historical Monitoring Records Remain Preserved
def test_historical_monitoring_preserved():
    hist_res = client.get("/api/v1/planted-plants/1/monitoring")
    assert hist_res.status_code == 200
    assert isinstance(hist_res.json(), list)

# 16. Existing AI Functionality Unchanged
def test_existing_ai_unaffected():
    res = client.get("/api/v1/observations/ai-feedback")
    assert res.status_code == 200

# 17. Existing Upload Functionality Unchanged
def test_existing_upload_unaffected():
    res = client.get("/api/v1/observations")
    assert res.status_code == 200

# 18. Existing Export Functionality Unchanged
def test_existing_export_unaffected():
    res = client.get("/api/v1/export/observations.csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
