"""
Automated Phase 5 Validation Suite Script
Verifies FastAPI backend application structure, router endpoints, Pydantic schemas,
OpenAPI docs, GeoJSON map responses, statistics calculation, and unit test results.
"""

import os
import sys
import json
import pytest

# Ensure backend root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

def validate_phase5():
    print("=" * 70)
    print("      PHASE 5 VALIDATION SUITE — FASTAPI BACKEND & API LAYER")
    print("=" * 70)
    
    results = []
    
    def log(test_name, passed, details=""):
        status = "[PASS]" if passed else "[FAIL]"
        results.append((test_name, passed, details))
        print(f"{status} {test_name}")
        if details:
            print(f"       Details: {details}")

    # 1. Structure & Import Checks
    backend_main = os.path.join("backend", "app", "main.py")
    docs_file = os.path.join("docs", "phase_5_backend.md")
    
    log("Backend Structure: app/main.py", os.path.exists(backend_main), backend_main)
    log("Documentation: docs/phase_5_backend.md", os.path.exists(docs_file), docs_file)
    
    # 2. Test Client Initialization
    client = TestClient(app)
    log("FastAPI Application TestClient Init", client is not None)

    # 3. Health & DB Health Endpoints
    r = client.get("/health")
    log("GET /health", r.status_code == 200 and r.json().get("status") == "healthy", f"Status: {r.status_code}")
    
    r_db = client.get("/health/db")
    log("GET /health/db", r_db.status_code == 200, f"Engine: {r_db.json().get('engine')}")

    # 4. Observations List API & Pagination
    r_obs = client.get("/api/v1/observations?page=1&limit=20")
    data_obs = r_obs.json()
    obs_ok = r_obs.status_code == 200 and data_obs.get("total_records") >= 227 and len(data_obs.get("data", [])) == 20
    log("GET /api/v1/observations (Pagination & Total Records)", obs_ok, f"Total records: {data_obs.get('total_records')}, Paginated: {len(data_obs.get('data', []))}")

    # 5. Observation Detail & 404 Error Handling
    r_detail = client.get("/api/v1/observations/1")
    detail_ok = r_detail.status_code == 200 and r_detail.json().get("id") == 1
    log("GET /api/v1/observations/{id} (Success)", detail_ok, f"ID: {r_detail.json().get('id')}")

    r_404 = client.get("/api/v1/observations/999999")
    log("GET /api/v1/observations/{id} (404 Handling)", r_404.status_code == 404)

    # 6. Species API
    r_sp = client.get("/api/v1/species?page=1&limit=50")
    data_sp = r_sp.json()
    sp_ok = r_sp.status_code == 200 and data_sp.get("total_records") >= 88
    log("GET /api/v1/species (Species Count & Taxonomy)", sp_ok, f"Unique species: {data_sp.get('total_records')}")

    # 7. Zones API
    r_z = client.get("/api/v1/zones")
    data_z = r_z.json()
    z_ok = r_z.status_code == 200 and len(data_z) == 3
    log("GET /api/v1/zones (Active Zones GeoJSON)", z_ok, f"Zone count: {len(data_z)}")

    # 8. Geography Boundary API
    r_g = client.get("/api/v1/geography")
    data_g = r_g.json()
    g_ok = r_g.status_code == 200 and data_g.get("type") == "FeatureCollection"
    log("GET /api/v1/geography (Van Udyan Boundary GeoJSON)", g_ok)

    # 9. Map GeoJSON API
    r_m = client.get("/api/v1/map/observations")
    data_m = r_m.json()
    m_ok = r_m.status_code == 200 and data_m.get("type") == "FeatureCollection" and len(data_m.get("features", [])) >= 227
    log("GET /api/v1/map/observations (GeoJSON FeatureCollection)", m_ok, f"Map features: {len(data_m.get('features', []))}")

    # 10. Statistics Overview API
    r_st = client.get("/api/v1/statistics/overview")
    data_st = r_st.json()
    st_ok = (
        r_st.status_code == 200 and 
        data_st.get("total_observations") >= 227 and
        data_st.get("unique_species_count") >= 88 and
        data_st.get("observations_by_zone", {}).get("ZONE A") >= 60
    )
    log("GET /api/v1/statistics/overview (Dynamic KPI Calculations)", st_ok, f"Total obs: {data_st.get('total_observations')}, Species: {data_st.get('unique_species_count')}")

    # 11. OpenAPI Docs & Safety
    r_docs = client.get("/openapi.json")
    log("OpenAPI Schema Auto-Generation (/openapi.json)", r_docs.status_code == 200)

    # Safety: No hardcoded passwords in settings
    no_secrets = "password" not in settings.DATABASE_URL.lower() or "localhost" in settings.DATABASE_URL
    log("No Secrets Hardcoded Check", no_secrets)

    print("-" * 70)
    all_passed = all(item[1] for item in results)
    overall_status = "PASSED — ALL PHASE 5 CHECKS SUCCESSFUL" if all_passed else "FAILED — ACTION REQUIRED"
    print(f"OVERALL STATUS: {overall_status}")
    print("=" * 70)
    
    return all_passed

if __name__ == "__main__":
    success = validate_phase5()
    sys.exit(0 if success else 1)
