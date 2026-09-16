# 📥 Phase 8 — Dataset Export & Download Documentation

---

## 📌 1. Executive Summary & Architecture

Phase 8 implements a production-grade **Dataset Export & Download System** for the **Van Udyan Biodiversity Intelligence Platform**.

All exports are generated dynamically from the central **PostgreSQL / PostGIS Database** via the FastAPI service layer. Raw CSV files are never read directly during export operations.

```
┌─────────────────────────────────────────────────────────────┐
│                 DASHBOARD DATASET EXPORT UI                 │
│  [Download Filtered Obs CSV]     [Download Obs GeoJSON]     │
│  [Download Filtered Plants CSV]  [Download Plants GeoJSON]  │
│  [Download Species Catalog CSV]  [Download ZIP Package]     │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP GET Requests with Query Filters
                               ▼
┌─────────────────────────────────────────────────────────────┐
│            FASTAPI BACKEND EXPORT ROUTER (api/v1/export/)   │
│   GET /observations.csv          GET /observations.geojson │
│   GET /planted-plants.csv       GET /planted-plants.geojson│
│   GET /species.csv               GET /package.zip          │
└──────────────────────────────┬──────────────────────────────┘
                               │ Database Service Layer Query
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                POSTGRESQL + POSTGIS DATABASE                │
│  - Central SQL Data & PostGIS EPSG:4326 Geometries          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🌐 2. Export API Endpoints

| Endpoint Route | Format | Content-Type Header | Default Filename |
| :--- | :---: | :--- | :--- |
| `/api/v1/export/observations.csv` | CSV | `text/csv` | `van_udyan_observations.csv` |
| `/api/v1/export/planted-plants.csv` | CSV | `text/csv` | `van_udyan_planted_plants.csv` |
| `/api/v1/export/species.csv` | CSV | `text/csv` | `van_udyan_species.csv` |
| `/api/v1/export/observations.geojson` | GeoJSON | `application/geo+json` | `van_udyan_observations.geojson` |
| `/api/v1/export/planted-plants.geojson` | GeoJSON | `application/geo+json` | `van_udyan_planted_plants.geojson` |
| `/api/v1/export/package.zip` | ZIP | `application/zip` | `van_udyan_biodiversity_complete_package.zip` |

---

## 🔍 3. Query Parameter Filtering

Export endpoints support standard query parameters:

- **Observations Export Filters:**
  - `source`: `iNaturalist`, `NGO / New Upload`
  - `zone`: `ZONE A`, `ZONE B`, `ZONE C`, `OUTSIDE`
  - `quality_grade`: `research`, `needs_id`
  - `species`: Scientific or common name substring
- **Planted Plants Export Filters:**
  - `status`: `Alive`, `Dead`, `Unknown`
  - `zone`: `ZONE A`, `ZONE B`, `ZONE C`
  - `species`: Scientific or common name substring

Example Request:
```http
GET /api/v1/export/observations.csv?source=iNaturalist&zone=ZONE%20A
```

---

## 🖥️ 4. Dashboard UI Integration

The dashboard includes a dedicated **Dataset Export** section (`#tab-export`):
- Filter selector dropdowns for customizing observation and plantation downloads before export.
- Instant single-click download buttons for CSV, WGS84 GeoJSON, and the complete 5-file ZIP archive package.

---

## 🧪 5. Testing & Validation

Run all Pytest test suites and validation scripts:

```bash
# Run all backend unit test suites (29/29 passed)
python -m pytest backend/tests/

# Run Phase 8 automated validation suite
python scripts/validate_phase8.py
```
