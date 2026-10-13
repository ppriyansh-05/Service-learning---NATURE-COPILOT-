# 🌳 Van Udyan Biodiversity Intelligence Platform
## Service Learning NGO Project — Progress & Roadmap Tracker

---

### 📌 Project Overview
**Goal:** Build a deployable **Biodiversity Mapping and Monitoring System** for **Van Udyan** for the **RSWF NGO**. The platform integrates existing public biodiversity data, newly planted species by RSWF, and ongoing field observations to support data-driven conservation.

---

### 👥 Project Contributors & Engineering Ownership
- **Phases 1 – 17:** Foundation team (Spatial boundaries, KMZ/GeoJSON pipelines, PostGIS DB, FastAPI backend, Leaflet GIS map, CRUD endpoints, export package generators, photo EXIF pipeline, Pl@ntNet AI integration, human verification loop, condition monitoring, biodiversity analytics, SDG/conservation reporting, and initial password protection).
- **Phases 18 – 23 & Data Hygiene Reset:** **Ranjan Verma** (Production cloud deployment on Render + Supabase, 12 live bug fixes across auth/zoning/UX, quality-of-life UI/UX features, Devrai Sacred Grove master-plan compliance grid engine, OWASP senior-level backend security hardening pass, final tracker sync, and clean data baseline reset).

---

### 🔄 Data Architecture & Integration Flow
```
 ┌───────────────────┐    ┌─────────────────────────┐    ┌──────────────────────┐
 │ iNaturalist Data  │    │  Planted Plants Data    │    │ New Field Uploads    │
 │ (Historical/Pub)  │    │  (RSWF Intervention)    │    │ (EXIF GPS + Photos)  │
 └─────────┬─────────┘    └────────────┬────────────┘    └──────────┬───────────┘
           │                           │                            │
           └───────────────────────────┼────────────────────────────┘
                                       ▼
                         ┌───────────────────────────┐
                         │ Central PostGIS Database  │
                         │ (PostgreSQL + Spatial Index)
                         └─────────────┬─────────────┘
                                       ▼
                         ┌───────────────────────────┐
                         │       FastAPI Backend     │
                         └─────────────┬─────────────┘
                                       ▼
                 ┌─────────────────────┴─────────────────────┐
                 ▼                                           ▼
      ┌─────────────────────┐                     ┌─────────────────────┐
      │ Interactive GIS Map │                     │  Analytics & AI     │
      │ (Source-coded pin)  │                     │ (EfficientNet-B0)   │
      └─────────────────────┘                     └─────────────────────┘
```

---

### 🏷️ 3 Key Data Sources & Marker Distinction
| Source | Map Pin Color | Description |
| :--- | :--- | :--- |
| **iNaturalist** | 🟢 Green | Historical/public biodiversity observations within Van Udyan boundary |
| **Planted Plants** | 🔵 Blue | Plants planted by RSWF/Team with tracked status (Alive/Dead/Unknown) |
| **New Uploads** | 🟠 Orange | Geotagged images uploaded by field volunteers & users |

---

### 📋 Master Execution Plan

| Phase | Phase Name | Status | Lead / Key Deliverables & Actions |
| :---: | :--- | :---: | :--- |
| **1** | **Van Udyan Boundary & Zones** | ✅ `COMPLETED` | Extracted KMZ polygons, generated raw & processed WGS84 GeoJSONs, created spatial validation script & docs |
| **2** | **iNaturalist Data Ingestion** | ✅ `COMPLETED` | Queried public API, performed exact WGS84 point-in-polygon verification, allocated active zones & created CSV |
| **3** | **Data Cleaning & Preprocessing** | ✅ `COMPLETED` | Standardized column schema, cleaned numeric IDs & dates, re-verified spatial containment & generated metadata |
| **4** | **PostgreSQL + PostGIS Schema** | ✅ `COMPLETED` | Built PostgreSQL/PostGIS DDL schema, GIST spatial indexes, multi-source tables, seed pipelines & validation suite |
| **5** | **FastAPI Backend Services** | ✅ `COMPLETED` | Built FastAPI REST backend API, SQLAlchemy ORM models, Pydantic schemas, versioned routes, GeoJSON map API & test suite |
| **6** | **Interactive Biodiversity Map** | ✅ `COMPLETED` | Built responsive frontend dashboard, Leaflet GIS map engine, Chart.js KPI charts, species catalog & observations table |
| **7** | **Data Management & CRUD Services** | ✅ `COMPLETED` | Built Planted Plants & NGO Observation CRUD endpoints, server-side status/geofence validation & provenance protection |
| **8** | **Dataset Export & Download System** | ✅ `COMPLETED` | Built CSV, GeoJSON & ZIP package exports from database, query filters & frontend export center |
| **9** | **New Observation Upload System** | ✅ `COMPLETED` | EXIF GPS extraction from photos, location validation inside zone, safe storage & dashboard upload modal |
| **10**| **Pl@ntNet AI Plant Identification** | ✅ `COMPLETED` | Integrated Pl@ntNet REST API, Top 3 predictions normalization, plant organ selection, confidence thresholds, human verification flow & Pytest suite |
| **11**| **Human Verification + AI Feedback** | ✅ `COMPLETED` | Verification workflow (confirm Top 1/2/3, manual correction, needs_review), separate decision audit storage, AI prediction retention & metrics API |
| **12**| **Plant Status & Survival Tracking**| ✅ `COMPLETED` | Condition monitoring visits (Alive, Dead, Unknown), chronological history preservation, survival rate calculations & zone-wise mortality analytics |
| **13**| **AI Biodiversity Insights** | ✅ `COMPLETED` | Dynamic recorded biodiversity analytics, zone comparisons, data coverage indicators, transparent rule-based action priorities & species distribution |
| **14**| **NGO Command Dashboard & Reports** | ✅ `COMPLETED` | Dynamic NGO Conservation Decision-Support & SDG Impact Reports, PDF generation via ReportLab, REST endpoints & download center |
| **15**| **Password-Protected Editing & Read-Only iNaturalist Data** | ✅ `COMPLETED` | Backend header auth for data editing/deletion, public open view/upload/export/reports, and permanent read-only iNaturalist protection |
| **16**| **Production Cleanup & Architecture Hardening** | ✅ `COMPLETED` | Security & iNaturalist read-only integrity, code modularization, baseline audit verification |
| **17**| **Complete NGO Data Entry, Photo Management & Field UX** | ✅ `COMPLETED` | Field UX enhancements, bulk photo handling, complete NGO data entry workflows |
| **18**| **Production Deployment & Live Bug-Fix Pass** | ✅ `COMPLETED` | **Ranjan Verma** · Render Docker backend + Supabase Postgres/Storage + static frontend deployment, State sync, 12 live end-to-end bug fixes |
| **19**| **Quality-of-Life Field Features & Verdant Atlas UI** | ✅ `COMPLETED` | **Ranjan Verma** · Live IST clock, Open-Meteo weather pill & popover, Tinder-style keyboard verify queue, species profile modals, bulk drag-drop photo dropzone, 120Hz perf tuning |
| **20**| **Devrai Master-Plan Compliance Grid Audit** | ✅ `COMPLETED` | **Ranjan Verma** · 20×20 Sacred Grove master grid audit engine, GPS-to-cell mapper, spacing violation detector, heatmap & CSV export |
| **21**| **Senior Backend Security Hardening Pass (OWASP)** | ✅ `COMPLETED` | **Ranjan Verma** · 20-point OWASP audit, sliding-window rate limiter, timing-safe auth, CSP, body-size limiter, non-root Docker, security test suite |
| **22**| **Final Polish Pass** | ✅ `COMPLETED` | **Ranjan Verma** · UI code consolidation, weather popover helpers, cache version bumps, tracker sync |
| **23**| **Data Hygiene Reset — iNaturalist Baseline** | ✅ `COMPLETED` | **Ranjan Verma** · Reset NGO/planted/monitoring stores so platform reflects strictly authoritative iNaturalist records |

---

### 🚀 Phase 24: Field Workflow Streamlining, Database Re-architecture & Live UI Polish (Completed October 2026)
- **Database Centralization**: Renamed "Manage Plantations" to "🗄️ Database" across navigation and section headers; surfaced direct "➕ Add Planted Plant" action alongside upload tools so RSWF team can edit, add, and monitor records without confusing submenus.
- **2-Button Upload Modal Interface**: Streamlined photo upload entry points into "Single Photo Upload" and "Bulk Upload", with universal `Sighted (Wild)` vs `Planted by RSWF` radio classification directly wired into backend persistence.
- **Custom Watering Date & Dynamic Due Date Calculation**:
  - Enhanced the Watering Queue (`frontend/js/app.js` and `frontend/index.html`) with dual action buttons: `✓ Today` for instant one-click logging and `✏️ Edit Date` for past/custom date corrections.
  - Added dedicated `water-date-modal` to select any past watering date.
  - Live recalculation of next due date, days overdue, and status bucket (`overdue`, `due_soon`, `ok`, `skip`) powered by `watering_service.py`.
- **iNaturalist Verification & Upload Workflow**:
  - Replaced legacy verification card with a bulk selectable queue table (`#tab-verify`) showing exclusively recent RSWF field observations (reference iNaturalist data strictly protected as read-only).
  - One-click launch opens pre-validated, pre-filled observation forms on `inaturalist.org` with GPS coordinates, taxonomic identification, and project metadata tags.
- **CDN Cache-Busting & Live Deploy Sync**:
  - Bumped frontend script tags to `?v=v2026.10.13-2` to eliminate Cloudflare/browser edge caching conflicts and stale DOM property errors (`setting 'textContent' of null`).
  - Synced and deployed cleanly across both `ppriyansh-05/Service-learning---NATURE-COPILOT-` and `ranjanvrma/van-udhyan` production repositories.

---

### 📍 Phase 1 Execution Summary & Geographical Foundation
- **Phase Status:** ✅ `COMPLETED`
- **Location:** Bavdhan Van Udyan (Plus Code: `GQ9J+74Q`, Address: Lantana Gardens, Bavdhan, Pune, Maharashtra 411021)
- **Primary Source:** `scripts/Bavdhan van udyan.kmz`
- **Files Created:**
  - `data/raw/van_udyan_boundary.geojson` (1 boundary feature)
  - `data/raw/van_udyan_zones.geojson` (3 active zone features: Zone A, B, C)
  - `data/processed/van_udyan_boundary.geojson`
  - `data/processed/van_udyan_zones.geojson`
  - `data/processed/van_udyan_master_geography.geojson`
  - `scripts/extract_kmz_to_geojson.py`
  - `scripts/validate_geography.py`
  - `scripts/generate_map_verification.py`
  - `docs/phase_1_geography.md`
  - `docs/map_verification.html`
- **Validation Suite Output:** `OVERALL STATUS: PASSED — ALL CHECKS SUCCESSFUL`
  - Boundary polygon valid: `PASS`
  - Active zones geometry valid: `PASS`
  - Zone A, B, C containment inside boundary: `PASS`
  - Zone A, B, C non-overlap / disjoint check: `PASS`
- **Geographical Interpretation:**
  > *"Van Udyan represents the complete geographical project area. Zone A, Zone B and Zone C represent the current RSWF intervention/monitoring areas within Van Udyan. Areas outside these active zones remain part of the overall Van Udyan project area and may be incorporated into future monitoring zones."*

---

### 🌿 Phase 2 Execution Summary & iNaturalist Spatial Verification
- **Phase Status:** ✅ `COMPLETED`
- **Official API Endpoint:** `https://api.inaturalist.org/v1/observations` (Public Read-Only, No Auth required)
- **Files Created:**
  - `scripts/inaturalist_api.py` (Reusable API client)
  - `scripts/run_inaturalist_ingestion.py` (Reproducible ingestion & spatial verification pipeline)
  - `scripts/validate_phase2.py` (Automated Phase 2 validation suite)
  - `data/raw/inaturalist/observations_raw.json` (331 raw API candidate records)
  - `data/raw/inaturalist/ingestion_metadata.json` (Ingestion metadata & execution parameters)
  - `data/processed/inaturalist/observations_van_udyan.csv` (227 spatially verified records inside Van Udyan)
  - `docs/phase_2_inaturalist.md` (Detailed Phase 2 data quality & spatial report)
- **Spatial Verification Results:**
  - Candidates Retrieved: 331
  - Usable Coordinates: 331 (0 missing)
  - Spatially Verified Inside Van Udyan Polygon: **227**
  - Excluded Outside Van Udyan Polygon: **104**
  - Unique Species / Taxa Count: **88**
  - Active Zone Breakdown: Zone A: 60 | Zone B: 37 | Zone C: 26 | Outside Active Zones (`OUTSIDE_ACTIVE_ZONES`): 104
- **Validation Suite Output:** `OVERALL STATUS: PASSED — ALL PHASE 2 CHECKS SUCCESSFUL`

---

### 🧹 Phase 3 Execution Summary & Data Cleaning & Standardization
- **Phase Status:** ✅ `COMPLETED`
- **Files Created:**
  - `scripts/clean_inaturalist_data.py` (Reproducible cleaning & standardization script)
  - `scripts/validate_phase3.py` (Automated Phase 3 validation suite)
  - `data/processed/inaturalist/observations_van_udyan_clean.csv` (227 standardized records)
  - `data/processed/inaturalist/cleaning_metadata.json` (Cleaning accounting & missing value metadata)
  - `docs/phase_3_data_cleaning.md` (Detailed Phase 3 data cleaning documentation)
- **Data Accounting & Lineage Results:**
  - Input Records: 227 | Output Records: **227** | Duplicates Removed: 0 | Records Removed: 0
  - Data Lineage: 100% preservation of `observation_id` and raw source files
  - Schema Standardization: Clean `snake_case` column headers and standardized ISO `YYYY-MM-DD` dates
  - Missing Values: Represented cleanly as empty strings (`""`) without fabricated placeholder text
- **Validation Suite Output:** `OVERALL STATUS: PASSED — ALL PHASE 3 CHECKS SUCCESSFUL`

---

### 🗄️ Phase 4 Execution Summary & Database Architecture
- **Phase Status:** ✅ `COMPLETED`
- **Database Engine:** PostgreSQL 15+ with PostGIS Extension (`EPSG:4326` WGS84 Spatial Data)
- **Files Created:**
  - `database/schema/01_init_postgis_schema.sql` (Production DDL schema definition)
  - `database/seeds/seed_geography.py` (Phase 1 WGS84 geography importer)
  - `database/seeds/seed_inaturalist_clean.py` (Phase 3 cleaned dataset importer)
  - `scripts/setup_database.py` (Automated database setup pipeline)
  - `scripts/validate_database.py` (Automated Phase 4 database validation suite)
  - `docs/phase_4_database.md` (Detailed Phase 4 architecture & ER documentation)
- **Architecture Highlights:**
  - Multi-source entity design supporting `iNaturalist`, `Planted`, and `New Upload` data streams
  - Distinct conceptual tables for `observations` vs `planted_plants` (with status `Alive`/`Dead`/`Unknown`)
  - Full schema support for Phase 10/11 AI ML predictions (`ai_predictions` table)
  - PostGIS `GIST` spatial indexing on `geom` columns (`Polygon` and `Point` geometries)
- **Validation Suite Output:** `STATIC SCHEMA ARCHITECTURE STATUS: PASSED`

---

### ⚡ Phase 5 Execution Summary & FastAPI Backend API
- **Phase Status:** ✅ `COMPLETED`
- **Backend Architecture:** FastAPI 0.135+, Python 3.10+, SQLAlchemy 2.0, Pydantic v2, Uvicorn
- **Files Created:**
  - `backend/app/main.py` (FastAPI app, CORS, OpenAPI router configuration)
  - `backend/app/core/config.py` (Environment & database settings)
  - `backend/app/db/session.py` (SQLAlchemy engine & session management)
  - `backend/app/models/models.py` (PostgreSQL/PostGIS ORM models)
  - `backend/app/schemas/schemas.py` (Pydantic request & response models)
  - `backend/app/services/data_service.py` (Business logic, spatial queries, and dynamic KPI calculator)
  - `backend/app/api/v1/` (`health.py`, `observations.py`, `species.py`, `zones.py`, `geography.py`, `map.py`, `statistics.py`)
  - `backend/tests/test_api.py` (Pytest API test suite — 12/12 passed)
  - `scripts/validate_phase5.py` (Automated Phase 5 validation suite)
  - `docs/phase_5_backend.md` (Detailed Phase 5 backend & API documentation)
- **API Features Implemented:**
  - Versioned `/api/v1/` REST endpoints
  - Paginated list APIs (`/observations`, `/species`)
  - GeoJSON spatial endpoints for frontend maps (`/zones`, `/geography`, `/map/observations`)
  - Dynamic KPI analytics endpoint (`/statistics/overview`)
  - Interactive OpenAPI UI documentation (`/docs`)
- **Validation Suite Output:** `OVERALL STATUS: PASSED — ALL PHASE 5 CHECKS SUCCESSFUL`

---

### 🌿 Phase 6 Execution Summary & Frontend Dashboard
- **Phase Status:** ✅ `COMPLETED`
- **Frontend Stack:** HTML5, CSS3 (Emerald dark theme, glassmorphism), JS (ES6+ SPA Engine), React / TypeScript, Leaflet.js, Chart.js
- **Files Created:**
  - `frontend/index.html` (Single Page Application layout & navigation)
  - `frontend/css/styles.css` (Custom responsive theme & glassmorphism styling)
  - `frontend/js/config.js` (Configurable `VITE_API_BASE_URL` API reader)
  - `frontend/js/api.js` (Centralized `ApiService` client layer consuming Phase 5 APIs)
  - `frontend/js/app.js` (SPA controller, Leaflet map engine, Chart.js engine, pagination & filters)
  - `frontend/package.json` & `frontend/src/` (`App.tsx`, `main.tsx`, `api.ts`, `vite.config.ts`)
  - `scripts/validate_phase6.py` (Automated Phase 6 validation suite)
  - `docs/phase_6_dashboard.md` (Detailed Phase 6 dashboard & GIS documentation)
- **Dashboard Views Implemented:**
  - Overview: Dynamic live KPI Cards (227 observations, 88 recorded species), Zone breakdown chart, Source breakdown chart, and Data Source Transparency Banner.
  - Biodiversity Map: WGS84 Leaflet map displaying Van Udyan boundary polygon, Zone A/B/C polygons, and observation point markers with click popups.
  - Species Catalog: Searchable & paginated species/taxa table.
  - Observations List: Filterable (species, zone, quality grade, source) & paginated observation table.
  - Active Zones: Dedicated RSWF active zone overview cards.
- **Validation Suite Output:** `OVERALL STATUS: PASSED — ALL PHASE 6 CHECKS SUCCESSFUL`

---

### 🛠️ Phase 7 Execution Summary & Data Management CRUD Services
- **Phase Status:** ✅ `COMPLETED`
- **Architecture Stack:** FastAPI 0.135+, Pydantic v2, Shapely WGS84 Geofencing, JavaScript SPA Engine, HTML5/CSS3 Modals
- **Files Created / Modified:**
  - `backend/app/api/v1/planted_plants.py` (Planted Plants CRUD router module)
  - `backend/app/api/v1/observations.py` (Extended with POST /ngo and iNaturalist record protection)
  - `backend/app/schemas/schemas.py` (Added Pydantic CRUD request/response models)
  - `backend/app/services/data_service.py` (Added Planted Plants & NGO CRUD methods, status & location validation)
  - `backend/tests/test_crud.py` (Phase 7 Pytest CRUD test suite — 9 unit tests)
  - `frontend/index.html` (Added Data Management tab `#tab-management`, `#plant-modal`, `#ngo-obs-modal`)
  - `frontend/css/styles.css` (Added modal backdrop, status badges, and action button styles)
  - `frontend/js/api.js` (Added `ApiService` client CRUD methods)
  - `frontend/js/app.js` (Added Data Management CRUD controller, modal handlers, pagination & filters)
  - `scripts/validate_phase7.py` (Automated Phase 7 validation suite)
  - `docs/phase_7_data_management.md` (Detailed Phase 7 architecture & CRUD documentation)
- **Features Implemented:**
  - Full Planted Plants CRUD (`POST`, `GET`, `GET/{id}`, `PUT/PATCH`, `DELETE /api/v1/planted-plants`)
  - NGO Field Observation creation (`POST /api/v1/observations/ngo`)
  - Server-side status validation (`Alive`, `Dead`, `Unknown`)
  - Server-side geofence location validation (coordinates outside Van Udyan rejected)
  - Data provenance protection (original `iNaturalist` records protected from deletion with HTTP `403 Forbidden`)
- **Validation Suite Output:** `OVERALL STATUS: PASSED — ALL PHASE 7 CHECKS SUCCESSFUL`

---

### 📥 Phase 8 Execution Summary & Dataset Export System
- **Phase Status:** ✅ `COMPLETED`
- **Architecture Stack:** FastAPI Response Streamers, Python `csv`, `json`, `io`, `zipfile`, JavaScript API Client, HTML5 Download Triggers
- **Files Created / Modified:**
  - `backend/app/api/v1/export.py` (Dataset Export API router module)
  - `backend/app/services/data_service.py` (Added Phase 8 CSV, GeoJSON, and ZIP package export generators)
  - `backend/app/main.py` (Registered `/api/v1/export` router)
  - `backend/tests/test_export.py` (Phase 8 Pytest export test suite — 8 unit tests)
  - `frontend/index.html` (Added Dataset Export tab `#tab-export` & filter controls)
  - `frontend/js/api.js` (Added export URL builder & download trigger helpers)
  - `frontend/js/app.js` (Added export download handlers)
  - `scripts/validate_phase8.py` (Automated Phase 8 validation suite)
  - `docs/phase_8_dataset_export.md` (Detailed Phase 8 dataset export documentation)
- **Features Implemented:**
  - Observations CSV export (`/api/v1/export/observations.csv`)
  - Planted Plants CSV export (`/api/v1/export/planted-plants.csv`)
  - Species Catalog CSV export (`/api/v1/export/species.csv`)
  - Observations WGS84 GeoJSON export (`/api/v1/export/observations.geojson`)
  - Planted Plants WGS84 GeoJSON export (`/api/v1/export/planted-plants.geojson`)
  - Complete Biodiversity Dataset Package ZIP Archive (`/api/v1/export/package.zip`)
  - Query parameter filtering for source stream, active zone, quality grade, status, and species
  - Dynamic database queries via service layer (raw/processed static CSV files are NOT read during export)
- **Validation Suite Output:** `OVERALL STATUS: PASSED — ALL PHASE 8 CHECKS SUCCESSFUL`

---

### 📷 Phase 9 Execution Summary & Photo Upload EXIF GPS Pipeline
- **Phase Status:** ✅ `COMPLETED`
- **Architecture Stack:** FastAPI UploadFile, Python Pillow (PIL) EXIF parser, Shapely WGS84 Geofencing, Local `data/uploads/` Storage, JavaScript SPA Upload Modal
- **Files Created / Modified:**
  - `backend/app/services/exif_service.py` (EXIF GPS extraction, DMS to decimal degree converter, MIME/size validator & safe filename generator)
  - `backend/app/api/v1/observations.py` (Added `POST /api/v1/observations/upload` multipart endpoint)
  - `backend/app/services/data_service.py` (Added `process_photo_upload` pipeline method)
  - `backend/app/main.py` (Mounted `/uploads` static directory)
  - `backend/tests/test_upload.py` (Phase 9 Pytest upload test suite — 11 unit tests)
  - `frontend/index.html` (Added Upload Photo button & `#upload-photo-modal`)
  - `frontend/js/api.js` (Added `uploadPhotoObservation` client method)
  - `frontend/js/app.js` (Added Photo Upload modal controllers, EXIF verification feedback & dynamic refresh)
  - `scripts/validate_phase9.py` (Automated Phase 9 validation suite)
  - `docs/phase_9_photo_upload.md` (Detailed Phase 9 photo upload & EXIF documentation)
- **Features Implemented:**
  - File format validation (JPG, JPEG, PNG, WEBP, Max 10MB)
  - EXIF GPS metadata extraction & N/S/E/W degree conversion
  - Van Udyan boundary containment verification & auto-zone allocation (`ZONE A`, `ZONE B`, `ZONE C`, `OUTSIDE_ACTIVE_ZONES`)
  - Error handling for missing EXIF GPS (HTTP 400), location outside boundary (HTTP 400), unsupported types (HTTP 415), and oversized files (HTTP 413)
  - Data provenance preservation (`source = "NGO / New Upload"`, original 227 iNaturalist observations protected)
- **Validation Suite Output:** `OVERALL STATUS: PASSED — ALL PHASE 9 CHECKS SUCCESSFUL`
- **Data Hygiene & Controlled Test Cleanup (Pre-Phase 10):**
  - Inspected NGO observation store: identified 26 synthetic test records (`NGO-228` to `NGO-253`) generated during Phase 7/9 Pytest and validation script executions.
  - Verified no legitimate NGO field observations existed; reset `ngo_observations_store.json` to 0 records (`[]`).
  - Removed 30 synthetic 100x100 test image files from `data/uploads/`.
  - Added module-level teardown fixtures to `test_crud.py` and `test_upload.py` ensuring unit test runs automatically purge transient test data.
  - Post-Cleanup Verification: iNaturalist Observations = `227`, NGO / New Upload Observations = `0`, Planted Plants = `3` (Unchanged).

---

### 🤖 Phase 10 Execution Summary — Pl@ntNet AI Plant Species Identification
- **Phase Status:** ✅ `COMPLETED`
- **Architecture Stack:** Pl@ntNet REST API Client, FastAPI Service Layer, Python `requests`, Pydantic Schemas, JSON AI Predictions Store, JavaScript SPA Modal Controllers
- **Files Created / Modified:**
  - `backend/app/services/plantnet_service.py` (Pl@ntNet REST client, organ parser, response normalizer & error handler)
  - `backend/app/api/v1/observations.py` (Added `POST /{id}/identify`, `GET /{id}/predictions`, and `POST /{id}/verify` endpoints)
  - `backend/app/services/data_service.py` (Added `identify_observation_plant`, `get_observation_ai_predictions`, and `confirm_observation_identification` service methods)
  - `backend/app/schemas/schemas.py` (Added `ObservationVerificationRequest` schema)
  - `backend/app/core/config.py` (Added `PLANTNET_API_KEY` setting property)
  - `backend/tests/test_plantnet.py` (Phase 10 Pytest suite — 9/9 passed, 100% mocked)
  - `.env.example` (Added `PLANTNET_API_KEY` environment variable placeholder)
  - `frontend/index.html` (Added plant organ selector `#upload-organ-select` & AI prediction card `#ai-prediction-card`)
  - `frontend/js/api.js` (Added `identifyObservationPlant`, `getObservationPredictions`, and `verifyObservation` client methods)
  - `frontend/js/app.js` (Added `triggerCurrentObsAI` & `confirmAiPrediction` UI event handlers)
  - `scripts/validate_phase10.py` (Automated Phase 10 validation suite — 11/11 passed)
  - `docs/phase_10_plantnet.md` (Detailed Phase 10 architecture & AI strategy documentation)
- **Features Implemented:**
  - Pl@ntNet REST API integration (`https://myapi.plantnet.org/v2/identify/all`)
  - Plant organ selection (`auto`, `leaf`, `flower`, `fruit`, `bark`, `habit`)
  - Top 3 predictions normalization (scientific name, common name, family, genus, score, confidence level)
  - Application confidence thresholds (`HIGH CONFIDENCE` >= 0.90, `MEDIUM CONFIDENCE` 0.60–0.89, `LOW CONFIDENCE` < 0.60)
  - Clear user wording: *"AI Suggestion — Pending Human Verification"*
  - Human verification flow (`POST /api/v1/observations/{id}/verify`) preserving original AI prediction intact
  - Failure resilience (Pl@ntNet outages/timeouts do NOT destroy valid uploaded photo observations)
  - Security (API key stored server-side only in `.env`, never exposed to frontend JS/logs)
- **Validation & Test Outputs:**
  - Pytest Suite: `49/49 PASSED` (100% backend test pass rate across all phases)
  - Validation Suite: `OVERALL STATUS: PASSED — 11/11 CHECKS SUCCESSFUL`
- **DEFERRED AI PLAN RECORD:**
  - **Deferred Feature:** Custom **EfficientNet-B0** transfer learning model training.
  - **Reason:** Insufficient verified image data from Bavdhan Van Udyan site currently.
  - **Future Trigger:** When sufficient verified plant photographs across classes are collected via field use, custom model training will be activated using PyTorch on Google Colab GPU instances.

- **Phase 10.1 — PostgreSQL AI Prediction Persistence Cleanup:**
  - **Objective Completed:** Migrated AI prediction persistence from static `ai_predictions_store.json` to central database repository / PostgreSQL `ai_predictions` table.
  - **Application Path:** Removed dependency on `ai_predictions_store.json` for normal prediction storage or retrieval.
  - **Multiple Attempt Traceability:** Prediction attempts for an observation remain saved sequentially in the database repository.
  - **Human Verification Preservation:** Human verification marks `user_confirmed = True` on matching observation records while keeping original AI prediction records preserved intact.
  - **Test Suite Updates:** Updated `backend/tests/test_plantnet.py` (10/10 passed), `scripts/validate_phase10.py` (11/11 passed), and `scripts/cleanup_test_ngo_data.py`.
  - **Regression Pass:** Pytest `50/50 PASSED`, All Phase 5–10 validation suites `PASSED`, Observations count: iNaturalist = `227`, NGO = `0`, Planted = `3`.

---

### 👤 Phase 11 Execution Summary — Human Verification & AI Feedback Loop
- **Phase Status:** ✅ `COMPLETED`
- **Architecture Stack:** FastAPI Verification Service, Pydantic `ObservationVerificationRequest` Schema, Database Prediction Audit Repository, SPA Verification Modal Controls, Pytest Suite
- **Files Created / Modified:**
  - `backend/app/schemas/schemas.py` (Enhanced `ObservationVerificationRequest` schema for Phase 11 decisions)
  - `backend/app/services/data_service.py` (Added `verify_observation_identification` & `get_ai_feedback_metrics`)
  - `backend/app/api/v1/observations.py` (Enhanced `POST /{id}/verify` & added `GET /ai-feedback`)
  - `backend/tests/test_verification.py` (Created Phase 11 Pytest verification suite — 13/13 passed)
  - `frontend/index.html` (Added Top 3 confirm buttons, manual species correction form, and needs review button)
  - `frontend/js/api.js` (Added `getAIFeedbackMetrics` client method)
  - `frontend/js/app.js` (Added `confirmAiPredictionRank`, `toggleCorrectionForm`, `submitManualCorrection`, `markNeedsReview`)
  - `scripts/validate_phase11.py` (Automated Phase 11 validation suite — 10/10 passed)
  - `docs/phase_11_human_verification.md` (Detailed Phase 11 architecture & verification workflow documentation)
- **Features Implemented:**
  - Formal human verification workflow distinguishing AI suggestion from human-confirmed taxonomy
  - Verification decisions: `CONFIRM` (Top 1, Top 2, Top 3), `CORRECT` (Manual species override), and `NEEDS_REVIEW` (Flagged for expert botanist review)
  - Preservation of original AI predictions: AI suggested species, score, rank, and confidence levels remain 100% UNCHANGED and preserved intact in the database repository
  - Separate human decision audit storage (`human_decision`, `verified_scientific_name`, `verified_common_name`, `verified_at`, `verification_notes`)
  - AI Feedback metrics endpoint (`GET /api/v1/observations/ai-feedback`)
  - Server-side input validation and read-only protection of iNaturalist observations (`403 Forbidden`)
- **Validation & Test Outputs:**
  - Pytest Suite: `63/63 PASSED` (100% backend test pass rate across all phases 5–11)
  - Validation Suite: `OVERALL STATUS: PASSED — 10/10 CHECKS SUCCESSFUL`
  - Controlled Cleanup: iNaturalist = `227`, NGO Test Observations = `0`, Planted Plants = `3`
- **DEFERRED EFFICIENTNET ROADMAP:**
  - Custom EfficientNet-B0 transfer learning model training remains a **FUTURE GOAL** until sufficient human-verified plant image samples are collected from Van Udyan field use.

---

### 📊 Phase 13 Execution Summary — Advanced Biodiversity & Conservation Analytics
- **Phase Status:** ✅ `COMPLETED`
- **Architecture Stack:** FastAPI Analytics Router, Python `AnalyticsService`, Pydantic Schemas, Rule-Based Priority Logic, Dashboard Action Panel, Pytest Suite
- **Files Created / Modified:**
  - `backend/app/services/analytics_service.py` (Calculates recorded biodiversity, zone comparison, coverage gaps, species frequency, temporal timeline & transparent action priorities)
  - `backend/app/api/v1/analytics.py` (Added `/biodiversity`, `/zones`, `/coverage`, `/action-priorities`, `/species`, and `/temporal` endpoints)
  - `backend/app/main.py` (Registered `analytics.router` under `/api/v1/analytics`)
  - `backend/tests/test_analytics.py` (Created Phase 13 Pytest test suite — 18/18 passed)
  - `frontend/index.html` (Added **`🌿 Areas Requiring Action`** dashboard card & Data Coverage disclaimers)
  - `frontend/js/api.js` (Added Phase 13 analytics client API methods)
  - `frontend/js/app.js` (Added `loadActionPriorities` & rendered field action recommendations dynamically)
  - `scripts/validate_phase13.py` (Automated Phase 13 validation suite — 10/10 passed)
  - `docs/phase_13_advanced_analytics.md` (Detailed Phase 13 architecture & scientific terminology documentation)
  - `PROJECT_TRACKER.md` (Updated status to COMPLETED and recorded execution summary)
- **Features Implemented:**
  - **Recorded Biodiversity Analytics:** Dynamic calculations for total observations (227), unique recorded taxa (88), species-level taxa, rank distribution, and source breakdown.
  - **Scientifically Safe Terminology:** Strictly enforced language (*"Recorded Taxa"*, *"Recorded Observations"*, *"Current Monitoring Records"*). Never infers ecological abundance or quality solely from sampling frequency.
  - **Data Coverage Indicators:** Clear indicators showing active working zones (~1.46 ha) vs outer unmonitored Van Udyan boundary (~11.04 ha). Safe wording: *"No recorded observations are currently available for this area."*
  - **`🌿 Areas Requiring Action` Panel:** Transparent, rule-based field action priority recommendations categorized into `SURVEY_PRIORITY`, `MONITORING_PRIORITY`, `DATA_COLLECTION_PRIORITY`, and `NO_IMMEDIATE_DATA_DRIVEN_PRIORITY`.
  - **Species Analytics:** Top recorded taxa by observation count (*"Most frequently recorded taxa in the dataset"*), taxonomic rank distribution, and multi-zone species occurrences.
  - **Temporal Timeline Analytics:** Derived strictly from database timestamps without fabricating predictive trends. Returns `"insufficient_data"` if dates are missing.
- **Validation & Test Outputs:**
  - Pytest Suite: `96/96 PASSED` (100% backend test pass rate across all phases 5–13)
  - Phase 13 Validation Suite: `OVERALL STATUS: PASSED — 10/10 CHECKS SUCCESSFUL`
  - All Phase 5–13 Validation Scripts: `ALL PASSED`
- **FINAL DATA INTEGRITY AUDIT:**
  - iNaturalist Observations = `227` (Spatially verified reference records intact)
  - NGO / New Upload Observations = `0` (Synthetic test records purged)
  - RSWF Planted Plants = `3` (Unchanged baseline)
  - Active Monitoring Zones = `3` (`ZONE A`, `ZONE B`, `ZONE C`)
  - Plant Status Editability = `VERIFIED` (`Alive`, `Dead`, `Unknown` editable with visit history preserved)

---

### 📊 Phase 14 Execution Summary — SDG & Conservation Decision-Support Reporting
- **Phase Status:** ✅ `COMPLETED`
- **Architecture Stack:** FastAPI Reports Router, Python `ReportService`, ReportLab Platypus Engine (`SimpleDocTemplate`, `Paragraph`, `Table`, `Spacer`, `colors`), Dashboard Download Center, Pytest Suite
- **Files Created / Modified:**
  - `backend/app/services/report_service.py` (Compiles NGO Conservation Decision-Support Report, SDG contribution payload, and PDF binary streams)
  - `backend/app/api/v1/reports.py` (Added `/reports/conservation`, `/reports/sdg`, `/reports/conservation.pdf`, and `/reports/sdg.pdf` endpoints)
  - `backend/app/main.py` (Registered `reports.router` under `/api/v1/reports`)
  - `backend/tests/test_reports.py` (Created Phase 14 Pytest test suite — 18/18 passed)
  - `frontend/index.html` (Added PDF report generation & download controls in Dataset Export Center)
  - `frontend/js/api.js` (Added Phase 14 report client API methods)
  - `frontend/js/app.js` (Added report download event handlers)
  - `scripts/validate_phase14.py` (Automated Phase 14 validation suite — 10/10 passed)
  - `docs/phase_14_conservation_report.md` (Detailed Phase 14 architecture & SDG contribution mapping documentation)
  - `PROJECT_TRACKER.md` (Updated status to COMPLETED and recorded execution summary)
- **Features Implemented:**
  - **Dynamic Decision-Support Report:** Dynamically compiles recorded biodiversity KPIs (227 obs, 88 taxa), zone breakdowns, survival statistics, transparent rule-based action priorities, potential plantation assessment areas, data gaps, and conservation recommendations.
  - **PDF Generation Engine:** ReportLab Platypus engine compiling formatted multi-page PDF documents.
  - **SDG Alignment Framework:** Direct mapping of measurable database state to **SDG 15 (Life on Land)**, **SDG 11 (Sustainable Cities)**, **SDG 13 (Climate Action)**, **SDG 17 (Partnerships)**, and **SDG 9 (Industry & Innovation)**.
  - **Report Data Consistency:** Verified `Dashboard == Report == Database` consistency with zero hard-coded statistics.
- **Validation & Test Outputs:**
  - Pytest Suite: `114/114 PASSED` (100% backend test pass rate across all phases 5–14)
  - Phase 14 Validation Suite: `OVERALL STATUS: PASSED — 10/10 CHECKS SUCCESSFUL`
  - All Phase 5–14 Validation Scripts: `ALL PASSED`
- **FINAL PERMANENT FINALIZATION REQUIREMENTS:**
  - **DATA INTEGRITY:** No false/fabricated data. (Baseline: iNaturalist = `227`, NGO = `0`, Planted = `3`, Active Zones = `3`).
  - **REPORT CONSISTENCY:** Dashboard = Report = Database (100% dynamic synchronization).
  - **PLANT STATUS:** `Alive` / `Dead` / `Unknown` remains editable.
  - **HISTORY:** Status corrections preserve full chronological monitoring visit history.
  - **DECISION SUPPORT:** Plantation and field action recommendations are transparently evidence-based.

---

### 🌿 Phase 14.1 Execution Summary — NGO Report Refinement, Plantation Impact & PDF Download Fix
- **Phase Status:** ✅ `COMPLETED`
- **Architecture Stack:** Refined FastAPI Reports Router, Python `ReportService` 14-Section Structure, ReportLab Platypus Engine, SPA Download Trigger Helper, Pytest Suite
- **Files Created / Modified:**
  - `backend/app/services/report_service.py` (Refined 14-section NGO Conservation & Plantation Planning Report structure, survival math, potential plantation assessment areas & ReportLab PDF compiler)
  - `backend/app/api/v1/reports.py` (Updated PDF response headers with explicit `Content-Disposition: attachment; filename="..."`)
  - `backend/tests/test_reports.py` (Updated Pytest report test suite — 17/17 passed)
  - `frontend/index.html` (Updated report card title and button labels for Phase 14.1)
  - `frontend/js/api.js` (Added missing static `triggerDownload(url, filename)` helper method to `ApiService` class resolving browser download `TypeError`)
  - `scripts/validate_phase14_1.py` (Created Phase 14.1 automated validation suite — 10/10 passed)
  - `docs/phase_14_1_ngo_report_refinement.md` (Detailed Phase 14.1 architecture & report structure documentation)
  - `PROJECT_TRACKER.md` (Updated status to COMPLETED and recorded execution summary)
- **Features & Fixes Implemented:**
  - **NGO Report Refinement:** Refined framing to **🌿 VAN UDYAN CONSERVATION & PLANTATION PLANNING REPORT**, practical 14-section structure tailored for RSWF field staff, short supporting SDG summary, and scientifically safe impact disclaimer (*"Direct biodiversity impact cannot yet be quantified from the available dataset."*).
  - **PDF Browser Download Fix:** Resolved root cause (`TypeError: this.triggerDownload is not a function` in JS) by defining `triggerDownload(url, filename)` on `ApiService` and setting quoted `Content-Disposition` headers in FastAPI.
  - **Potential Plantation Assessment Areas:** Identifies candidate zones for field assessment without making unverified automatic ecological claims (*"Conduct ground field assessment before scheduling new sapling plantation."*).
  - **Report Consistency:** Verified `Dashboard == Report == Database` consistency (`iNaturalist = 227`, `NGO = 0`, `Planted = 3`, `Active Zones = 3`).
- **Validation & Test Outputs:**
  - Pytest Suite: `113/113 PASSED` (100% backend test pass rate across all 9 test suites)
  - Phase 14.1 Validation Suite: `OVERALL STATUS: PASSED — 10/10 CHECKS SUCCESSFUL`
  - All Phase 5–14.1 Validation Scripts: `ALL PASSED`
- **FINAL PERMANENT FINALIZATION REQUIREMENTS:**
  1. **No false/fabricated data:** Baseline counts verified (`iNaturalist = 227`, `NGO = 0`, `Planted = 3`, `Active Zones = 3`).
  2. **Dashboard = Database = Report:** 100% dynamic synchronization.
  3. **Plant status remains editable:** `Alive`, `Dead`, `Unknown` editable via API.
  4. **Status history remains preserved:** Full chronological monitoring visit log preserved.
  5. **Plantation recommendations are field-assessment recommendations:** Avoids automatic ecological conclusions without ground assessment.
  6. **Final database audit required before submission:** Clean baseline audit verified.

### 🔒 Phase 15 Execution Summary — Password-Protected Editing & Read-Only iNaturalist Data
- **Phase Status:** ✅ `COMPLETED`
- **Architecture Stack:** FastAPI Security Dependency, Header Verification (`X-NGO-Admin-Password`), Pydantic Config, Session Storage Caching, Authorization Modal (`#ngo-auth-modal`), Pytest Suite
- **Files Created / Modified:**
  - `backend/app/core/config.py` (Added `NGO_ADMIN_PASSWORD` setting property with `rswf-admin-pass` fallback)
  - `backend/app/core/security.py` (Created `verify_ngo_admin_password` FastAPI header dependency)
  - `.env.example` (Updated with `NGO_ADMIN_PASSWORD=rswf-admin-pass` environment variable doc)
  - `backend/app/api/v1/planted_plants.py` (Applied `Depends(verify_ngo_admin_password)` to `POST`, `PUT`, `PATCH`, `DELETE`, and `POST /{id}/monitoring`)
  - `backend/app/api/v1/observations.py` (Applied `Depends(verify_ngo_admin_password)` to `POST /{id}/verify` and `DELETE /{id}`)
  - `backend/app/services/data_service.py` (Added `delete_ngo_observation` with `protect_inaturalist_record` check returning 403 Forbidden)
  - `backend/tests/test_authentication.py` (Created Phase 15 Pytest authentication suite — 11/11 passed)
  - `frontend/index.html` (Added `#ngo-auth-status-btn` top header toggle & `#ngo-auth-modal` password prompt dialog)
  - `frontend/js/api.js` (Added `getNgoPassword`, `setNgoPassword`, `clearNgoPassword`, header injection, and auto 401 cache clear)
  - `frontend/js/app.js` (Added auth UI handlers, modal controllers, and protected UI wrappers)
  - `scripts/validate_phase15.py` (Created Phase 15 automated validation suite — 10/10 passed)
  - `docs/phase_15_authentication.md` (Detailed Phase 15 architecture & security documentation)
  - `PROJECT_TRACKER.md` (Updated status to COMPLETED and recorded execution summary)
- **Features & Security Policies Implemented:**
  - **Public Access (No Password):** Dashboard, maps, species catalog, observation list, EXIF GPS photo upload, field sighting submission, dataset exports, and conservation PDF reports remain 100% open without password.
  - **Protected Actions (Password Required):** Planted plant creation/editing/deletion, condition monitoring visits, AI species verification, and NGO observation deletion require header `X-NGO-Admin-Password`.
  - **iNaturalist Read-Only Enforcement:** iNaturalist reference observations are permanently read-only (HTTP `403 Forbidden` on any edit or delete attempt, even WITH a valid password).
  - **Password Security Best Practices:** Stored server-side via `NGO_ADMIN_PASSWORD` env var, never hardcoded in frontend JS/HTML, never returned in API payloads, never logged.
  - **User Experience:** Frontend modal prompts for password when an RSWF user triggers protected actions, caching in `sessionStorage` with top header status indicator (`🔒 RSWF Admin Active` / `🔓 Public View Mode`).
- **Validation & Test Outputs:**
  - Pytest Suite: `124/124 PASSED` (100% backend test pass rate across all 10 test modules)
  - Phase 15 Validation Suite: `OVERALL STATUS: PASSED — 10/10 CHECKS SUCCESSFUL`
  - All Validation Scripts (`validate_phase5.py` to `validate_phase15.py`): `ALL PASSED`
- **FINAL DATABASE INTEGRITY AUDIT:**
  1. **iNaturalist Observations:** `227` (Spatially verified reference records intact)
  2. **NGO / New Upload Observations:** `0` (Synthetic test records purged)
  3. **RSWF Planted Plants:** `3` (`PL-001`, `PL-002`, `PL-003`)
  4. **Active Working Zones:** `3` (`ZONE A`, `ZONE B`, `ZONE C`)
  5. **Plant Status Editability:** `VERIFIED` (`Alive`, `Dead`, `Unknown` editable with visit history preserved)

---

### Phase 16 — Production Cleanup & Architecture Hardening
- **Status:** ✅ COMPLETED
- **Completed Date:** September 2026
- **Files Modified / Added:**
  - `backend/app/services/data_service.py` (Refactored to execute PostgreSQL/PostGIS ORM queries directly when `db_session` is active)
  - `frontend/src/` (Removed unused/legacy React scaffold directory; consolidated single frontend architecture)
  - `scripts/validate_phase16.py` (Created Phase 16 automated validation suite — 10/10 checks passed)
  - `docs/phase_16_production_cleanup.md` (Created detailed architecture, cleanup, and spatial area audit documentation)
  - `PROJECT_TRACKER.md` (Recorded Phase 16 completion and final baseline audit)
- **Key Accomplishments & Cleanups:**
  - **Backend Cleanup & DB Query Priority:** Refactored `DataService` so PostgreSQL/PostGIS is the primary production query target, with clean fallback for standalone unit tests.
  - **Single Frontend Architecture:** Established Vanilla HTML5/CSS3/JavaScript SPA as the single clear frontend architecture. Removed unused `frontend/src/` React/TypeScript scaffold.
  - **Security & iNaturalist Read-Only Integrity:** Verified Phase 15 header authorization security (`X-NGO-Admin-Password`), public open access, and permanent read-only protection for iNaturalist records (HTTP 403 Forbidden).
  - **Spatial Polygon Area Audit:** Evaluated PostGIS/KMZ geodesic boundary polygon geometry: Total Boundary = **3.58 ha**, Active Zones = **0.55 ha**, Outer Unmonitored Portion = **3.02 ha**. Documented discrepancy against historical estimate (~12.5 ha) with scientific clarity.
  - **Plant Status & Monitoring History:** Retained editable plant status with complete chronological monitoring visit history.
  - **Custom ML Postponed:** Confirmed custom ML/EfficientNet training is deferred as future scope pending local field dataset growth. Deployment postponed to final stage per project rules.
- **Validation & Testing Results:**
  - Pytest Suite: `124/124 PASSED` (100% pass rate)
  - Phase 16 Validation Suite (`scripts/validate_phase16.py`): `10/10 CHECKS SUCCESSFUL`
  - Complete Validation Pipeline (`validate_phase5.py` to `validate_phase16.py` + `cleanup_test_ngo_data.py`): `ALL 12 VALIDATION PIPELINE SCRIPTS PASSED 100%`
- **FINAL PRODUCTION BASELINE DATA INTEGRITY:**
  1. **iNaturalist Observations:** `227`
  2. **NGO / New Upload Observations:** `0`
  3. **RSWF Planted Plants:** `3` (`PL-001`, `PL-002`, `PL-003`)
  4. **Active Working Zones:** `3` (`ZONE A`, `ZONE B`, `ZONE C`)

---

### Phase 17 — Complete NGO Data Entry, Photo Management & Field UX
- **Status:** ✅ COMPLETED
- **Completed Date:** September 2026
- **Files Modified / Added:**
  - `backend/app/services/data_service.py` (Extended photo upload processing & photo URL handling for Planted Plants and NGO Field Sightings)
  - `backend/app/api/v1/planted_plants.py` & `observations.py` (Validated schema consistency and photo attachment parameters)
  - `frontend/index.html` (Updated `#plant-modal` with photo upload, `#ngo-obs-modal` with clear educational field guidance and photo upload, and `#upload-photo-modal` with full EXIF GPS & Pl@ntNet AI display UX)
  - `frontend/js/app.js` (Updated form submit handlers to support photo uploads and post-upload details card)
  - `scripts/validate_phase17.py` (Created Phase 17 automated validation suite — 10/10 checks passed)
  - `docs/phase_17_data_entry_photo_management.md` (Created detailed architecture & field workflow documentation)
  - `PROJECT_TRACKER.md` (Recorded Phase 17 completion and final baseline audit)
- **Key Accomplishments & UX Improvements:**
  - **Complete Planted Plant Form:** Exposed all database fields (`plant_code`, `scientific_name`, `common_name`, `planted_on`, `status`, `latitude`, `longitude`, `zone_code`, `notes`, and optional photo file upload attachment).
  - **NGO Field Sighting Form & Educational Guidance:** Added explicit field guidance in the UI distinguishing wild/spontaneous species observations from RSWF planted trees, with photo file upload attachment support.
  - **Unified Photo Storage Pipeline:** Reused the central safe photo upload pipeline (`process_photo_upload`, `exif_service.py`, `/data/uploads/`) for Planted Plants, NGO Field Sightings, and geotagged uploads.
  - **Post-Upload EXIF GPS & Pl@ntNet AI Display UX:** Displayed image preview thumbnail, extracted WGS84 lat/lng, geofence boundary check result, assigned zone, captured date, Pl@ntNet AI predicted species, confidence score, rank 1–3 list, and human verification controls.
  - **Security & Data Integrity Preservation:** Preserved Phase 15 password protection (`X-NGO-Admin-Password`), public open access, permanent read-only protection for original iNaturalist reference data (`HTTP 403 Forbidden`), and strict database baseline integrity (227 iNaturalist, 0 NGO test observations, 3 planted plants, 3 active zones).
- **Validation & Testing Results:**
  - Pytest Suite: `124/124 PASSED` (100% pass rate)
  - Phase 17 Validation Suite (`scripts/validate_phase17.py`): `10/10 CHECKS SUCCESSFUL`
  - Complete Validation Pipeline (`validate_phase5.py` to `validate_phase17.py` + `cleanup_test_ngo_data.py`): `ALL 13 VALIDATION PIPELINE SCRIPTS PASSED 100%`
- **FINAL PRODUCTION BASELINE DATA INTEGRITY:**
  1. **iNaturalist Observations:** `227`
  2. **NGO / New Upload Observations:** `0`
  3. **RSWF Planted Plants:** `3` (`PL-001`, `PL-002`, `PL-003`)
  4. **Active Working Zones:** `3` (`ZONE A`, `ZONE B`, `ZONE C`)

---

### Final Project Completion Phase — Pre-Deployment Readiness & Engineering Audit
- **Status:** ✅ COMPLETED
- **Completed Date:** September 2026
- **Files Modified / Added:**
  - `backend/app/services/analytics_service.py` (Updated to authoritative geodesic polygon areas: 3.58 ha total, 0.55 ha active zones)
  - `backend/app/services/report_service.py` (Harmonized area figures across SDG alignment, project area, and PDF generator)
  - `frontend/js/api.js` (Added rolling 30-minute inactivity timeout to `sessionStorage` credential management with auto-clearing)
  - `scripts/validate_pre_deployment.py` (Created comprehensive 12-check pre-deployment readiness validation suite)
  - `docs/final_system_architecture_and_readiness.md` (Created master system architecture, security & deployment readiness document)
  - `PROJECT_TRACKER.md` (Updated master source of truth)
- **Key Accomplishments & Audits:**
  - **All Engineering Work Complete:** All core platform features, CRUD forms, photo upload pipelines, Pl@ntNet AI workflows, and PDF reports verified end-to-end.
  - **Password Session Security:** Added rolling 30-minute inactivity timeout with immediate manual lock button (`🔒 RSWF Admin Active (Click to Lock)`). No plaintext secrets in frontend or API.
  - **Permanent iNaturalist Protection:** Confirmed original 227 iNaturalist reference observations are permanently read-only (`HTTP 403 Forbidden` on all edit/delete attempts).
  - **Authoritative Geodesic Geometry:** Unified 3.58 ha total boundary and 0.55 ha active zones across analytics, reports, and PDFs.
  - **Pristine Real Data Baseline:** Verified production database holds strictly real data: 227 iNaturalist records, 0 NGO test records, 3 planted plants, 3 active working zones.
- **Validation & Testing Results:**
  - Pytest Backend Suite: `124/124 PASSED` (100% pass rate)
  - Pre-Deployment Audit (`scripts/validate_pre_deployment.py`): `12/12 CHECKS SUCCESSFUL`
  - Full Regression Pipeline (14 Scripts): `ALL 14 SCRIPTS PASSED 100%`


### Final Required Fix — Robust GPS / Geotag Photo Workflow
- **Status:** ✅ COMPLETED
- **Completed Date:** September 2026
- **Purpose:** Corrected the photo-upload workflow to match the real RSWF field workflow where photos may be shared via WhatsApp (which strips EXIF metadata), leaving only a visible GPS/geotag overlay on the image.
- **Files Modified / Added:**
  - `backend/app/services/exif_service.py` — Added `parse_gps_from_text()` (multi-format regex GPS parser), `extract_visible_image_geotag()` (Windows native OCR via `winsdk` + pytesseract fallback), `extract_photo_location()` (strict 3-step priority: EXIF → Image Geotag → None)
  - `backend/app/services/data_service.py` — Updated `process_photo_upload()` to use `extract_photo_location()`; added `confirm_geotag_observation()` for user-confirmed geotag coordinates; added `inspect_photo_file()` for GPS auto-fill in plant/sighting forms
  - `backend/app/api/v1/observations.py` — Added `POST /observations/confirm-location` endpoint; added `POST /observations/inspect-photo` endpoint; updated `/upload` to handle `requires_confirmation` flow
  - `backend/app/schemas/schemas.py` — Added `GeotagLocationConfirmRequest` schema
  - `frontend/index.html` — Updated upload modal with clear EXIF vs Image Geotag terminology; added `#geotag-confirmation-box` with `[Confirm Location]` button; added GPS badge to Plant and NGO Sighting photo fields
  - `frontend/js/api.js` — Added `confirmGeotagLocation()` and `inspectPhoto()` methods to `ApiService`
  - `frontend/js/app.js` — Added `setupPhotoGpsListeners()` for auto GPS-fill in forms; added `handlePhotoSelectionChanged()`, `handleConfirmGeotagLocation()`; updated `handlePhotoUploadSubmit()` to render 3 distinct cases (EXIF, Image Geotag, No Location)
  - `scripts/validate_gps_workflow.py` — Created 14-case GPS workflow validation suite
  - `backend/tests/test_upload.py` — Added 2 new unit tests: `test_upload_visible_image_geotag_workflow`, `test_exif_gps_bypasses_image_geotag`
- **GPS Priority Logic Implemented (Strict):**
  1. **EXIF GPS** (`gps_source = "EXIF"`) → Used directly, OCR never triggered, `requires_confirmation = False`
  2. **Visible Image Geotag** (`gps_source = "IMAGE_GEOTAG"`) → Detected via OCR, coordinates shown to user, `requires_confirmation = True`, observation created only after `[Confirm Location]` is clicked
  3. **Location Not Available** → No coordinates fabricated, no zone assigned, clear message shown
- **UI Messages (Exact Terminology):**
  - EXIF GPS: `✓ GPS detected from photo metadata`
  - Image Geotag: `✓ GPS detected from visible geotag on image`
  - No GPS: `Location not available. GPS information could not be found in the photo metadata (EXIF) or visible image geotag.`
- **Validation Results:**
  - GPS Workflow Audit (`scripts/validate_gps_workflow.py`): **14/14 CHECKS SUCCESSFUL**
  - Pytest Backend Suite: **126/126 PASSED** (100% pass rate, up from 124)
  - Full Regression Pipeline (17 Scripts): **ALL 17 SCRIPTS PASSED 100%**
- **Data Integrity Verified (Post-Fix):**
  - iNaturalist Observations: `227` (read-only, untouched)
  - NGO / New Upload Observations: `0`
  - Planted Plants: `3`
  - Active Zones: `3`

---

### Configuration Update — Pl@ntNet API Key
- **Status:** ✅ COMPLETED
- **Completed Date:** September 2026
- **Change:** Updated `PLANTNET_API_KEY` in `backend/.env` with the new key provided by RSWF.
- **Files Modified / Added:**
  - `backend/.env` — Created with `PLANTNET_API_KEY` and `NGO_ADMIN_PASSWORD` (not committed to version control)
  - `backend/app/core/config.py` — Added `load_dotenv()` call so `backend/.env` is auto-loaded at startup
- **Notes:**
  - Key is stored exclusively in `backend/.env`. Not hard-coded in any source file.
  - `backend/.env` must remain in `.gitignore` and must never be committed.
  - No Pl@ntNet service code, endpoints, tests, or frontend changed.

---

### Configuration Fix — Pl@ntNet API Hostname
- **Status:** ✅ COMPLETED
- **Completed Date:** September 2026
- **Root Cause:** `plantnet_service.py` contained incorrect API hostname `https://myapi.plantnet.org` (missing hyphen), causing all Pl@ntNet identification requests to fail with a connection error.
- **Fix Applied:**
  - `backend/app/services/plantnet_service.py` — Corrected `PLANTNET_API_URL` from `https://myapi.plantnet.org/v2/identify/all` → `https://my-api.plantnet.org/v2/identify/all`
- **Live Test Result:**
  - API key loaded: **YES**
  - API URL: `https://my-api.plantnet.org/v2/identify/all`
  - Test result: **SUCCESS** — 3 predictions returned from Pl@ntNet API
- **Nothing else changed:** GPS/EXIF logic, geofence, zone assignment, AI prediction normalization, confidence thresholds, human verification, database, frontend, and all other endpoints are untouched.

---

### Phase 18 — Production Deployment & Live Bug-Fix Pass (Implemented by Ranjan Verma)
**Lead Engineer:** Ranjan Verma · **Date:** 2026-10-05 · **Scope:** Shipped the platform to a live Render deployment and ran a complete end-to-end bug sweep against the deployed frontend + backend.

Deployment stack: FastAPI backend on Render Docker (Singapore region) + Supabase Postgres (PostGIS) + Supabase Storage for photos + static frontend on Render's CDN. `render.yaml` provisions both services from the repo; `backend/Dockerfile` builds a slim-bookworm image with Tesseract preinstalled for the OCR fallback. State sync (`backend/app/services/state_sync.py`) was turned on so NGO stores survive a redeploy on the ephemeral free tier.

Bug-sweep results — 12 issues found and fixed in one commit:
| # | Severity | Area | Fix |
|---|---|---|---|
| 1 | 🔴 | Unlock dialog hit `/api/v1/auth/verify` → 404 | Mounted `/auth/verify` under the `/api/v1` prefix as well |
| 2 | 🔴 | Monitoring Zones tab stuck after a cold-start fetch failure | Promise.all swallows per-tab failures; Retry button re-runs the current tab |
| 3 | 🟠 | Broken photo images rendered as text alt | onerror swaps to a `.popup-photo-empty` placeholder |
| 4 | 🟠 | Add Field Sighting bypassed the 1 m same-plant guard | Added `allow_nearby_duplicate` query param + confirm-dialog override UX |
| 5 | 🟠 | Admin unlock UX & cached-password handling | Eye toggle + cached password invalidation on 401 |
| 6 | 🟡 | Stale "Not yet confirmed by RSWF" note after a verify | Verification review strips the phrase |
| 7 | 🟡 | Plant `zone_code` could disagree with the boundary polygon | Zone always derived from the boundary check |
| 8 | 🟡 | Watering fields missing in Add/Edit Plant modal | Added watering_interval_days + last_watered_on |
| 9 | 🟡 | Mobile nav discoverability | Right-edge arrow + fade hint |
| 10 | 🟡 | Content-Disposition filename clipped by CORS | Exposed via `expose_headers` |
| 11 | 🔵 | Noisy console errors on 401 | 401s on protected endpoints no longer logged |
| 12 | 🔵 | Dev test records lingering on prod | Cleaned |

Production URL (live): `https://van-udyan-dashboard.onrender.com` → `https://van-udyan-backend.onrender.com`

---

### Phase 19 — Quality-of-Life Features: Weather, Verify Queue, Species Profiles & Bulk Upload (Implemented by Ranjan Verma)
**Lead Engineer:** Ranjan Verma · **Date:** 2026-10-05 → 2026-10-07 · **Scope:** Four field-productivity and insight features chosen after a feature-brainstorm with the mentor.

- **Weather pill** in the top header (every tab) — direct browser fetch to Open-Meteo (CORS-open, no key), floating popover with current conditions + 7-day rainfall bars + 3-day forecast + auto-pause callout when ≥5 mm fell in 24h. Backend was briefly a proxy, then removed once we discovered Render was blocking the backend's outbound HTTPS to the API — moving the fetch to the browser dodged the restriction entirely and eliminated a backend dependency.
- **Live header clock** — IST wall clock updating every second, formatted `Tue, Oct 7 · 10:21:09 PM`; aligned to the whole-second boundary so digits don't jitter.
- **Verification queue (`#verify` tab)** — Tinder-style card stack of unverified field uploads; keyboard shortcuts `C` confirm · `X` correct · `R` needs-review · `→` skip · `←` prev. Prefetches 50 at a time via `/analytics/verification-queue`. Clears a 50-item backlog in ~5 minutes.
- **Per-species profile modal** — click any row in the Species tab → modal with rarity badge, zone distribution pills, phenology bar chart (sightings per calendar month), first/last-seen, planted count, and a direct Wikipedia link. Backed by `/analytics/species-profile`.
- **Bulk photo dropzone** — new `📂 Bulk Upload` button on Manage Plantations opens a drag-drop modal; up to 50 files/batch. Each file runs the full EXIF/GPS/boundary/dedup/1 m guard pipeline. Returns a per-file status grid (saved / needs-confirmation / duplicate / rejected / error). Backend endpoint: `/observations/bulk-upload`.
- **Perf-tuning pass** — removed every always-on animation and nearly every `backdrop-filter`, cut the ambient particle canvas, slashed cards' shadow stacks and transitions, dropped the fixed body gradient. Result: the dashboard scrolls smoothly at 120 Hz on mid-range laptops. Removed ~1300 lines of CSS from theme-verdant and the legacy "Premium Glass" layer in styles.css.

**Three features that were briefly shipped and then removed on scope-trim** (reverted in commit 86cc263): biodiversity indices (Shannon / Simpson / Pielou), public landing page at `/visit`, and 3D terrain view with MapLibre + Terrarium DEM. Code and endpoints removed; concept notes retained in `docs/` for future revival.

---

### Phase 20 — Devrai Master-Plan Compliance (Grid Audit) (Implemented by Ranjan Verma)
**Lead Engineer:** Ranjan Verma · **Date:** 2026-10-07 · **Scope:** Audit tool comparing every planted plant on site against the Devrai Foundation's prescribed master plan.

Inputs ingested from the mentor:
- **Devrai Model v7 PDF** — a 20×20 grid of 10 ft × 10 ft cells (400 cells, 1 acre) with each cell tagged with a 2-letter species acronym.
- **Sacred Grove Plant List v2 XLSX** — 115 species / 515 individuals, scientific + Marathi + acronym + grid-number assignments.

Pipeline:
1. Parsed the messy XLSX "Grid Number" column (`43.44.63..64`, `129.132..149.152`) into `data/processed/grid_cells.json` — the authoritative cell → prescribed species table (364 cells assigned, 36 reserved for the bamboo hut, water body, pathways, entrance). Resolved 2-letter acronym collisions (`AL` was used by 4 species, `AR` by 2) using grid position.
2. Hand-curated `data/processed/grid_species.json` — 115-species catalogue with large/small canopy classification (used by the spacing-warnings check).
3. `data/processed/grid_calibration.json` — the four corner GPS of the physical plot + grid dims + spacing rules. Defaults to a 61 m × 61 m square at the Van Udyan centroid; mentor overrides via the UI modal.

Backend (`backend/app/services/compliance_service.py` + `backend/app/api/v1/compliance.py`):
- `cell_for_point(lat, lon)` — axis-aligned GPS → cell 1-400 using the calibrated rectangle.
- `audit_all()` — per-plant status: ✅ correct · 🔄 misplaced_species (right species, wrong cell) · ❌ wrong_species · ⚪ empty_cell · ⚫ non_plantable_cell · outside_plot.
- `heatmap()` — 400-cell colour status payload for the UI grid.
- `spacing_warnings()` — nearest-neighbour sweep over every pair of large-canopy plants; haversine distance < 6 m (default, configurable via calibration) flags a warning.
- Admin-only `PUT /compliance/calibration` so the mentor can paste the four surveyed corners once and recompute everything.

Frontend (`#compliance` tab):
- KPI row (planted total, correct, wrong/misplaced, outside plot).
- 20×20 CSS-grid heatmap, hover shows cell number + prescribed + actual + status.
- Mismatch table listing every wrong-species / misplaced plant with the cells it should've been in.
- Spacing warnings panel listing each too-close pair with its exact metre distance.
- CSV export of the full audit for printable field use.
- Calibration modal for the mentor's one-time corner-GPS setup.

---

### Phase 21 — Backend Security Hardening Pass (OWASP) (Implemented by Ranjan Verma)
**Lead Engineer:** Ranjan Verma · **Date:** 2026-10-09 · **Scope:** Full senior-security-engineer audit against the 20-area OWASP checklist, followed by implementation of every code-level and configuration-level fix found.

Hardening implemented (details in `backend/app/core/*` + commit `db46411`):
- **Config invariants.** New `ENVIRONMENT` setting; in production `NGO_ADMIN_PASSWORD` must be set, non-default, and ≥12 chars (backend refuses to start otherwise). CORS rejects `*` and plain-HTTP origins, drops the localhost defaults, and no longer silently fails open.
- **In-process rate limiter** (`core/rate_limit.py`) — zero-dependency sliding-window counter, keyed by client IP + bucket (auth vs mutation). Honours `X-Forwarded-For` only when `TRUST_PROXY=true`. Default 20 req/min on `/auth/verify`, 120 req/min on every admin-protected mutation.
- **Timing side-channels closed.** `hmac.compare_digest` now runs unconditionally even when the header is empty; both failures return the identical body `{"detail": "Unauthorized."}` — no missing-vs-wrong-password enumeration.
- **Request body size cap.** `RequestBodySizeLimitMiddleware` rejects any request whose declared `Content-Length` exceeds `MAX_REQUEST_BODY_BYTES` (default 16 MB) before any body is read.
- **Docs locked down.** `/docs`, `/redoc`, `/openapi.json` are off by default in production; `ENABLE_DOCS=true` for a short-lived debug window.
- **Content-Security-Policy** added (`default-src 'none'; frame-ancestors 'none'; base-uri 'none'`). The policy opens to Swagger CDN only when docs are explicitly on.
- **HSTS `preload`**, `Cross-Origin-Resource-Policy`, expanded `Permissions-Policy`, and `Cache-Control: no-store` + `Pragma: no-cache` on `/auth/*` paths.
- **Error-leak cleanup.** Global exception handler returns generic `500` in production (stack trace stays in the server log); bulk-upload per-file errors no longer surface raw Python exception text; Supabase upload failures no longer embed the remote response body.
- **Structured security logger** (`core/security_logging.py`) emits `auth_success`, `auth_failure`, `rate_limit_block` events with IP + path, scrubs any field whose name hints at a secret.
- **Dockerfile non-root.** Dedicated `vanudyan` uid 1001 user; writable dirs explicitly chown'd.
- **Security test suite** (`backend/tests/test_security.py`, 12 new tests) covering actual attack-pattern behaviour: unified-401 body, per-key rate-limiter blocking, security headers on every response, no-store on `/auth/*`, 413 on oversize `Content-Length`, upload MIME/extension refusal, path traversal in `/thumbs`, and production config failing fast on default/missing/short password / wildcard-CORS / plain-HTTP CORS / docs on.

Final self-rated security score: **B — Mostly production ready**. The remaining risks are operator / infra (log aggregation, Supabase PITR + restore drill, dependency scanning in CI, decision on multi-user accounts) and documented in the audit report.

---

### Phase 22 — Final Polish & Tracker Update (Implemented by Ranjan Verma)
**Lead Engineer:** Ranjan Verma · **Date:** 2026-10-09 · **Scope:** Project tracker brought current (this file), tiny code tidy-up, cache versions bumped so the latest JS/CSS is served on the next page load. No new features; no regressions.

---

### Phase 23 — Data Hygiene Reset to iNaturalist Baseline (Implemented by Ranjan Verma)
**Lead Engineer:** Ranjan Verma · **Date:** 2026-10-11 (Commit `8b0366d`) · **Scope:** Cleared NGO/planted/monitoring test data so the platform strictly reflects the genuine, authoritative iNaturalist records.

Key Changes:
- **Cleaned Data Stores:**
  - `data/processed/ngo_observations_store.json` — 43 test records reset to 0
  - `data/processed/planted_plants_store.json` — 3 seed records reset to 0
  - `data/processed/plant_monitoring_store.json` — reset to 0
- **Data Service Loader Fix (`backend/app/services/data_service.py`):**
  - Updated `load_planted_plants_store()` so an empty list `[]` is recognized as a legitimate empty state rather than forcing re-seeding of the 3 demo plants.
- **Untouched Master References:**
  - `data/processed/inaturalist/observations_van_udyan_clean.csv` (227 verified records)
  - `data/processed/van_udyan_boundary.geojson` and zone boundary GeoJSONs
  - `data/processed/grid_cells.json`, `grid_species.json`, and `grid_calibration.json`

---

## 🎯 Final Project Status & Remaining Roadmap

### 1. COMPLETED ENGINEERING
- **Backend** — FastAPI on Python 3.11, PostgreSQL/PostGIS, SQLAlchemy ORM, Supabase Storage for photos, Pl@ntNet REST integration, EXIF + OCR geotag extraction, content-addressed photo filenames with SHA-256 + perceptual-hash dedup, 1 m same-plant guard, monsoon-aware watering reminders, Postgres-backed state sync for ephemeral hosts, structured security logging, in-process rate limiter, request-size cap middleware, production-safe config invariants (phases 1-21).
- **Frontend** — Vanilla HTML + CSS + JS SPA, hash-routed tabs (Overview · Map · Species · Observations · Zones · Watering · Verify · Compliance · Manage · Reports), Leaflet GIS, Chart.js analytics, floating weather popover with live Open-Meteo data, live IST clock, verification queue with keyboard shortcuts, per-species profile modal with phenology chart, bulk photo dropzone, Plan Compliance 20×20 heatmap, calibration modal, data-source transparency note.
- **Analytics & reporting** — Observation search with multi-source filters, species catalogue, action-priority recommendations, dataset CSV + GeoJSON exports, Conservation PDF, SDG PDF.
- **Compliance tool** — Devrai master-plan ingestion, GPS → grid-cell mapping, per-plant audit, spacing warnings, CSV export, admin calibration.
- **Security** — Shared-secret admin auth with timing-safe compare, unified unauthorized response, per-IP rate limits on auth + mutations, security-header middleware (CSP, HSTS, nosniff, DENY frames, Referrer, Permissions, CORP, no-store on /auth), body-size cap, non-root Docker user, secure error handling.
- **Deployment** — Live on Render.com (backend Docker + static-site frontend) backed by Supabase Postgres + Storage. `render.yaml` configures env vars; `.env.example` documents every setting.

### 2. REMAINING / RECOMMENDED OPERATOR TASKS
1. **GENUINE NGO DATASET MIGRATION** — When RSWF delivers the authoritative field records + plant catalogue + photographs, run the bulk-upload pipeline + the state-sync migration script. The platform already runs on seeded development data; swapping to the real dataset is a one-session operator task.
2. **PLOT CORNER SURVEY** — Walk the four corners of the 1-acre Sacred Grove plot with a handheld GPS, enter the readings into the Plan Compliance calibration modal. Until this is done, cell assignments are approximate (defaulted to the Van Udyan centroid).
3. **OPERATIONAL HARDENING** — Point Render logs at an external aggregator and alert on `event=auth_failure` bursts / `event=rate_limit_block`. Enable Supabase PITR and run one restore drill. Enable Dependabot / `pip-audit` in CI.
4. **MULTI-USER AUTH (optional future)** — Replace the single shared admin password with per-user accounts if RSWF scales beyond one field team.

---

### 🔮 FUTURE SCOPE ONLY (Not Implemented / Not Part of Remaining Implementation)
- **CUSTOM ML / EFFICIENTNET TRANSFER LEARNING:**
  - A custom Van Udyan-specific plant classification model may be developed in the future after sufficient genuine, human-verified local images are collected across classes through ongoing field usage.
  - **This is NOT implemented in the current project.** The existing Pl@ntNet REST API serves all current plant identification needs reliably.

---

### 📂 Work Directory Map
- `data/` : Datasets (iNaturalist raw/cleaned data, plantation records)
- `backend/` : FastAPI Python server (app, models, services, routers)
- `frontend/` : Vanilla HTML5/CSS3/JavaScript responsive SPA
- `scripts/` : Data validation, EXIF parsing & automated regression test runners
- `docs/` : Master technical documentation & architectural guides

---

### Production Fix — Docker Runtime Permissions for Field Upload Persistence (2026-10-14)
- Root cause confirmed from the Render traceback: PermissionError [Errno 13] on /app/data/processed/ngo_observations_store.json inside the persistence function after POST /api/v1/observations/upload reached the save step. The Docker image runs the API as unprivileged UID/GID 1001 but only grants write access to uploads, thumbnails, and logs. The mutable processed JSON stores and their parent directory remained root-owned.
- Fix prepared on branch fix/gps-visible-geotag-bulk-upload: update backend/Dockerfile so the runtime user owns the processed directory and the four mutable JSON state files (NGO observations, planted plants, monitoring, and AI predictions). Static iNaturalist CSV and geographic reference files are not chowned by this change.
- Data safety: no observations, planted-plant records, iNaturalist data, or stored photos were deleted or seeded. No test uploads were sent to production.
- Verification status: Docker build, automated tests, deployment, and live upload verification have not yet been run in this environment. Do not mark this fix as deployed until Render builds the branch and the live upload is verified.
- Related separate issue: bulk requests can exceed the configured 16 MiB request-body limit even when each photo is below the 10 MiB per-file limit. This is distinct from the confirmed filesystem permission failure and needs a separate bounded-batch fix / validation.

---

### Follow-up Fix — Dockerfile Line Continuations (2026-10-14)
- The previous deployment of commit ee2a31f failed. Inspection of the committed backend/Dockerfile found doubled backslashes at the shell line-continuation points in the new `RUN ... find ...` block. Dockerfile continuation syntax requires one backslash at the end of each continued line; doubled backslashes can break parsing/execution of that block.
- Prepared correction on branch `fix/dockerfile-line-continuations`: normalize the affected continuation points to one backslash per line. The change is limited to Dockerfile syntax.
- Verification status: this environment has not run a Docker build. Deployment remains unverified until Render builds the corrected commit.
- No production data was changed or test observations uploaded.

---

### Follow-up UX and Data Integrity Fixes — 2026-10-14
- **Duplicate compliance counts:** `compliance_service._collect_planted()` previously counted both the managed planted-plant register and every GPS-tagged NGO observation as separate plants. Compliance now counts only managed planted-plant records; sightings remain in observation views. This prevents one physical plant/photo represented in both stores from being counted twice.
- **Automatic RSWF planted registration:** uploads explicitly marked `planted_rswf` now create a linked planted-plant management record after the observation is saved, including after visible-geotag confirmation. The generated code format is `VU-A-001` / `VU-B-001` / `VU-C-001` (or `VU-X-001` when not assigned to an active zone). Species and planting date are left blank; health is `Unknown`; the record is flagged `needs_review`. No species, planting date, or health was fabricated. The unknown status suppresses watering reminders until RSWF staff verify the record.
- **Compliance unknowns:** unidentified managed plants are now marked `needs_review` rather than incorrectly classified as a wrong species. The compliance UI exposes a “Needs identification” count and red review status.
- **Map:** managed RSWF planted plants now use red marker fills; the outline continues to indicate health status.
- **iNaturalist queue:** fixed response parsing to read the API's `data` array, which could prevent the upload queue from loading. The navigation item already exists in the sidebar.
- **iNaturalist submission workflow:** the existing button opens prefilled iNaturalist draft pages; it does not submit automatically. Added a flow to save the resulting iNaturalist observation URL against the NGO record and open that record externally for edits/deletion. Direct remote editing/deletion from Nature Copilot is not implemented because the app does not currently have iNaturalist OAuth/API write authorization.
- **State sync:** NGO observation edits/deletes now use the shared save helper so changes are also pushed to configured cloud state sync. Photo objects are not automatically deleted as part of record deletion.
- **Data safety:** no production data was deleted, no live test records/photos were created, and no iNaturalist reference data was changed.
- **Verification:** code reviewed through GitHub. No local test suite, frontend runtime test, live API test, or deployment was run from this environment. Changes remain on branch `fix/planted-registration-compliance-inat-ux` pending review and deployment.

### Follow-up — Biodiversity Map and iNaturalist Button Clarity — 2026-10-14
- Exposed the persisted `observation_type` in observation GeoJSON and changed the Biodiversity Map marker fill to red only for RSWF uploads explicitly marked `planted_rswf`. Other RSWF sightings remain orange and iNaturalist observations remain green; the separate planted-register markers remain red as well.
- Renamed the UI action from “Upload Selected to iNaturalist” to “Prepare iNaturalist Drafts” to accurately describe its current behavior. It opens prefilled iNaturalist creation pages; a user must sign in, review, attach/confirm photos and submit on iNaturalist. The app does not yet perform an authenticated API upload.
- Verification: source edits committed to the existing feature branch. No runtime tests or deployment were run.

### Follow-up — iNaturalist Verification Queue — 2026-10-14
- The queue now reads the actual `identification_status` field written by the RSWF verification workflow (rather than relying only on the unrelated `verification_status` field). Verified/corrected observations are labelled accurately.
- Unverified observations remain visible for transparency but their selection checkboxes are disabled. Only verified/corrected records can be used to prepare iNaturalist draft pages.
- Button copy now says “Prepare Selected Verified Drafts” to avoid implying an API submission. The app still opens prefilled iNaturalist pages; user review and submission on iNaturalist are required.
- The dashboard screenshot showing “Loading…” appears to be the deployed version, while these fixes are on the unmerged feature branch. The queue fixes will not appear in production until the PR is reviewed, merged, and deployed.
- Direct API submission is not implemented. iNaturalist write endpoints require authenticated authorization; no OAuth flow or user token storage has been added. Existing API read/import functionality is separate.
- Verification: GitHub source inspection and edits only. No live API tests, automated tests, or deployment performed.
