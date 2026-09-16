# ⚡ Phase 5 — FastAPI Backend & API Layer Documentation

---

## 📌 1. Executive Summary & Architecture

Phase 5 implements the **controlled application API backend** for the **Van Udyan Biodiversity Intelligence Platform** using **FastAPI**, **SQLAlchemy**, and **Pydantic**.

The backend serves as the single source of truth and security layer between database storage (PostgreSQL/PostGIS) and client applications (future React/Next.js dashboard). Direct database connections from the frontend are strictly prohibited.

```
┌──────────────────────────────────────────────────────────┐
│              FUTURE FRONTEND / CLIENT APPS               │
│               (React / Next.js GIS Dashboard)            │
└────────────────────────────┬─────────────────────────────┘
                             │ HTTP REST Requests
                             ▼
┌──────────────────────────────────────────────────────────┐
│                 FASTAPI BACKEND API LAYER                │
│   /health  │  /api/v1/observations  │  /api/v1/map/obs    │
└────────────────────────────┬─────────────────────────────┘
                             │ SQLAlchemy / GeoAlchemy2 ORM
                             ▼
┌──────────────────────────────────────────────────────────┐
│                POSTGRESQL + POSTGIS DATABASE             │
│        (Central Spatial Data & Multi-Source Store)       │
└──────────────────────────────────────────────────────────┘
```

---

## 🚀 2. Local Setup & Execution Commands

```bash
# Navigate to backend directory
cd backend

# Create & activate virtual environment (optional)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start FastAPI development server on port 8000
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 🌐 3. Versioned API Endpoints Summary (`/api/v1`)

| Endpoint Route | HTTP Method | Category | Description / Response Model |
| :--- | :---: | :--- | :--- |
| `/health` | `GET` | System | System application health check status (`HealthResponse`) |
| `/health/db` | `GET` | System | Database & PostGIS connectivity check (`DBHealthResponse`) |
| `/api/v1/observations` | `GET` | Observations | Paginated list of observations with source, species, zone, and quality filters |
| `/api/v1/observations/{id}` | `GET` | Observations | Single observation detail by internal database ID (`ObservationResponse`) |
| `/api/v1/species` | `GET` | Species | Paginated species/taxa list with species count (`PaginatedSpeciesResponse`) |
| `/api/v1/zones` | `GET` | GIS Map | Active RSWF working zones list with WGS84 GeoJSON polygons |
| `/api/v1/geography` | `GET` | GIS Map | Complete Bavdhan Van Udyan site boundary GeoJSON FeatureCollection |
| `/api/v1/map/observations` | `GET` | GIS Map | Interactive map observations GeoJSON FeatureCollection for Leaflet/Mapbox |
| `/api/v1/statistics/overview` | `GET` | Analytics | Dynamically calculated biodiversity KPIs and zone distributions |
| `/docs` | `GET` | Documentation | Auto-generated interactive Swagger / OpenAPI UI |
| `/openapi.json` | `GET` | Documentation | Machine-readable OpenAPI 3.0 specification |

---

## 🗺️ 4. Spatial GeoJSON Map Endpoints

### `GET /api/v1/map/observations`
Returns all spatially verified observation points inside Van Udyan as a standard **GeoJSON FeatureCollection**:

```json
{
  "type": "FeatureCollection",
  "name": "Bavdhan_Van_Udyan_Observations_Map",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [73.7791569722, 18.519406]
      },
      "properties": {
        "id": 1,
        "source": "iNaturalist",
        "source_id": "391717923",
        "scientific_name": "Fabaceae",
        "common_name": "Legumes",
        "observed_on": "2026-08-15",
        "quality_grade": "needs_id",
        "zone": "",
        "zone_status": "OUTSIDE_ACTIVE_ZONES",
        "photo_url": "https://inaturalist-open-data.s3.amazonaws.com/photos/717799265/square.jpg"
      }
    }
  ]
}
```

---

## 📊 5. Dynamic Biodiversity Analytics API

### `GET /api/v1/statistics/overview`
Calculates live biodiversity KPIs dynamically from the database without hard-coded static metrics:

- `total_observations`: `227`
- `unique_species_count`: `88`
- `observations_by_zone`:
  - `ZONE A`: `60`
  - `ZONE B`: `37`
  - `ZONE C`: `26`
  - `OUTSIDE_ACTIVE_ZONES`: `104`
- `observations_by_source`:
  - `iNaturalist`: `227`

---

## 🧪 6. Testing & Automated Validation

The backend includes a comprehensive unit test suite in [`backend/tests/test_api.py`](file:///c:/Users/ppriy/OneDrive/Desktop/semester%205/Service%20Learning%20NGO/backend/tests/test_api.py) using FastAPI `TestClient` and `pytest`.

To run the test suite and validation scripts:

```bash
# Execute Pytest backend test suite (12/12 passed)
python -m pytest backend/tests/test_api.py

# Execute Phase 5 automated validation suite
python scripts/validate_phase5.py
```
