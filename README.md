# 🌳 Van Udyan Biodiversity Intelligence Platform

> **Biodiversity mapping, plantation monitoring and AI-assisted plant identification for Bavdhan Van Udyan, Pune, built for the RSWF NGO.**

A web dashboard and API that bring together public iNaturalist records, RSWF's planted trees and geotagged field photos on one map. Field teams upload photos, the system reads the location, checks it lies inside Van Udyan, suggests the species with Pl@ntNet AI, and RSWF staff confirm or correct the result. Planting health, zone statistics, downloads and PDF reports all update from the same live data.

---

## 📌 At a Glance

| | |
| :--- | :--- |
| **Site** | Bavdhan Van Udyan, Lantana Gardens, Bavdhan, Pune, Maharashtra 411021 (Plus Code `GQ9J+74Q`) |
| **Project Area** | ≈ 3.58 ha outer boundary, with three active RSWF work zones (A, B, C) covering ≈ 0.55 ha |
| **Data Baseline** | 227 verified iNaturalist records · 88 unique species · 0 synthetic/fabricated records (clean data baseline) |
| **Partner** | Reform Social Welfare Foundation (RSWF), as a Service Learning project |
| **Engineering Status**| All 23 Phases Completed · Fully Tested · Ready for Field Handover |

---

## 🎯 Features

### Dashboard (10 Integrated Sections & Tools)
- **Header Live Widgets:** Live 12-hour IST clock (`Tue, Oct 7 · 10:21:09 PM`) and real-time Open-Meteo Bavdhan weather pill with interactive rainfall popover (7-day rain bars, 3-day forecast, auto-pause alerts when $\ge 5\text{ mm}$ rain falls).
- **Overview:** Live KPIs, observations by zone and data source, unverified upload count, and dynamic rule-based "Areas Requiring Action".
- **Biodiversity Map:** Leaflet GIS map with Van Udyan boundary, Zones A/B/C, and source-coded markers (🟢 iNaturalist, 🟠 RSWF Field Uploads, 🔵 RSWF Planted Trees), layer controls, satellite view, and photo popups.
- **Species Catalogue:** Searchable directory of recorded species with sighting frequency and click-to-view **Species Profile Modal** featuring monthly phenology bar charts, zone distribution badges, and Wikipedia links.
- **Observations:** Filterable records table with photo thumbnails and detailed review drawer (confirm species, select Pl@ntNet AI prediction, correct taxonomy, or flag for expert review).
- **Monitoring Zones:** Zone-specific areas, taxa richness, planted tree survival counts (Alive / Dead / Unknown), and habitat notes.
- **Plant Watering Tracker:** Intelligent watering schedule accounting for species interval and recent local rainfall, with overdue alerts and monsoon pause flags.
- **Rapid Verification Queue (`#verify`):** Tinder-style deck for rapid field photo reviews using keyboard shortcuts: <kbd>C</kbd> Confirm, <kbd>X</kbd> Correct, <kbd>R</kbd> Mark for Review, <kbd>→</kbd> Skip, <kbd>←</kbd> Prev.
- **Devrai Plan Compliance (`#compliance`):** 20×20 Sacred Grove master-grid audit engine (400 cells of $10\text{ ft} \times 10\text{ ft}$, 1 acre), interactive visual heatmap, GPS-to-cell mapping, spacing violation detector ($<6\text{ m}$ for large canopies), and CSV audit export.
- **Manage Plantations:** Add/edit planted saplings, log condition monitoring visits, add field sightings, and **📂 Bulk Upload** up to 50 geotagged photos per batch.
- **Downloads & Reports:** Dynamic CSV, GeoJSON, and ZIP package export engine, plus two professional ReportLab PDF generators: *Conservation Planning & Decision-Support* and *UN SDG 15 Impact Summary*.

### Geotagged Photo Pipeline & Integrity Guards
- **Location:** Automated EXIF GPS extraction with fallback to Windows OCR / Tesseract for printed GPS camera stamps.
- **Boundary Containment:** Every photo is validated against the exact Van Udyan boundary polygon.
- **Proximity & Duplicate Guard:** Prevents duplicate uploads using SHA-256 and perceptual hashing, with a 1-meter proximity warning guard.
- **Strict Data Hygiene:** Zero fabricated or false data. iNaturalist records are permanently read-only (HTTP 403 Forbidden on edits). Password-protected administration for all record modifications.

---

## 🏗️ Architecture

```
  iNaturalist API        RSWF planted plants       Geotagged field photos
  (public records)       & health-check visits     (EXIF GPS / printed stamp OCR)
         │                        │                           │
         ▼                        ▼                           ▼
  PostgreSQL + PostGIS    JSON data stores in data/processed/  +  data/uploads/
  (iNaturalist, zones)    (NGO observations, planted plants)      (photos, thumbnails)
         └────────────────────────┬───────────────────────────┘
                                  ▼
                    FastAPI backend  (port 8000)  ──►  Pl@ntNet API
                    REST API · PDF reports (ReportLab) · exports
                                  │
                                  ▼
                    Web dashboard  (port 5173)
                    HTML/CSS/JavaScript · Leaflet · Chart.js
```

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | HTML5, CSS3, vanilla JavaScript (single-page app), Leaflet 1.9, Chart.js 4 |
| **Backend** | Python 3.10+ (tested on 3.14), FastAPI, Uvicorn, Pydantic v2, SQLAlchemy 2, GeoAlchemy2 |
| **Database & GIS** | PostgreSQL with PostGIS (WGS84 / EPSG:4326 coordinates), Shapely |
| **Images & AI** | Pillow, Windows OCR (`winsdk`, optional `pytesseract` fallback), Pl@ntNet REST API |
| **Reports** | ReportLab (PDF), CSV, GeoJSON, ZIP |
| **Testing** | Pytest (140 tests) |

---

## 🚀 Setup & Running

### Prerequisites
- Python 3.10+
- PostgreSQL with the PostGIS extension
- A free Pl@ntNet API key from [my.plantnet.org](https://my.plantnet.org/), for AI identification
- Windows is recommended, for the built-in OCR that reads printed location stamps

### 1. Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```

Create `backend/.env`, using [`.env.example`](./.env.example) as the template:
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/van_udyan_db
PLANTNET_API_KEY=your_plantnet_api_key_here
PLANTNET_PROJECT=k-indian-subcontinent
NGO_ADMIN_PASSWORD=choose-a-strong-password
```

Create the database schema and load the boundary, zones and iNaturalist data (one time):
```bash
python scripts/setup_database.py
```

Start the API:
```bash
backend\venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --port 8000
```
Interactive API docs: http://localhost:8000/docs

### 2. Dashboard
```bash
backend\venv\Scripts\python.exe scripts\serve_frontend.py 5173
```
Open http://localhost:5173. This small server disables browser caching, so edits show up on reload.

### 3. Start automatically at Windows login (optional)
```bash
powershell -ExecutionPolicy Bypass -File scripts\install_autostart.ps1
```
This registers a scheduled task that runs [`scripts/run_services.py`](./scripts/run_services.py) in the background. It starts both servers at login, restarts them if they crash, and writes logs to `logs/`. Remove it with the same command plus `-Uninstall`.

### 4. Tests
```bash
cd backend
venv\Scripts\python.exe -m pytest tests -q
```
[`backend/tests/conftest.py`](./backend/tests/conftest.py) backs up the NGO data and photos before the test run and restores them afterwards, so running the tests never deletes real field records.

---

## 🔌 API Overview

Every route below starts with `/api/v1`, except health and photo files. Full interactive documentation is at `/docs`.

| Area | Endpoints |
| :--- | :--- |
| **Health** | `GET /health`, `GET /health/db` |
| **Observations** | `GET /observations` (filters: source, species, zone, quality_grade), `GET /observations/{id}`, `POST /observations/ngo`, `POST /observations/upload`, `POST /observations/confirm-location`, `POST /observations/inspect-photo` |
| **AI & review** | `POST /observations/{id}/identify`, `GET /observations/{id}/predictions`, `POST /observations/{id}/verify` 🔒, `GET /observations/ai-feedback` |
| **Planted plants** | `GET/POST /planted-plants`, `GET/PUT/DELETE /planted-plants/{id}` 🔒, `GET/POST /planted-plants/{id}/monitoring`, `GET /planted-plants/monitoring/statistics` |
| **Geography** | `GET /geography`, `GET /zones`, `GET /map/observations` |
| **Statistics & analytics** | `GET /statistics/overview`, `GET /analytics/{biodiversity, zones, coverage, action-priorities, species, temporal}` |
| **Exports** | `GET /export/{observations, planted-plants}.{csv, geojson}`, `GET /export/species.csv`, `GET /export/package.zip` |
| **Reports** | `GET /reports/conservation(.pdf)`, `GET /reports/sdg(.pdf)` |
| **Photos** | `GET /uploads/{file}` (original), `GET /thumbs/{file}` (cached 320 px preview) |

🔒 = requires the `X-NGO-Admin-Password` header.

---

## 📂 Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/v1/          # Route modules (observations, planted plants, analytics, export, reports, ...)
│   │   ├── core/            # Settings (.env) and admin-password security
│   │   ├── db/              # SQLAlchemy session
│   │   ├── models/          # ORM models (PostGIS geometries)
│   │   ├── schemas/         # Pydantic request/response models
│   │   ├── services/        # Data, EXIF/OCR, Pl@ntNet, analytics and report services
│   │   └── main.py          # FastAPI app, CORS, photo and thumbnail serving
│   ├── tests/               # Pytest suite (140 tests)
│   └── requirements.txt
├── frontend/
│   ├── index.html           # Dashboard page (all sections and dialogs)
│   ├── css/styles.css       # Responsive dark theme
│   └── js/                  # config.js (API URL), api.js (API client), app.js (dashboard logic)
├── database/                # PostGIS schema and seed scripts
├── data/
│   ├── raw/                 # Boundary/zone GeoJSON, raw iNaturalist download
│   ├── processed/           # Cleaned iNaturalist CSV, NGO observation & planted plant stores
│   └── uploads/             # Uploaded field photos (not committed)
├── scripts/                 # Setup, ingestion, validation, frontend server, autostart
├── docs/                    # Phase-by-phase documentation, architecture notes, import review
├── PROJECT_TRACKER.md       # Phase-by-phase execution status
└── README.md
```

---

## 🗺️ Project History

| Phase | Work | Documentation |
| :---: | :--- | :--- |
| 1 | Site boundary and Zones A/B/C extracted from the RSWF KMZ survey into GeoJSON | [phase_1_geography.md](./docs/phase_1_geography.md) |
| 2 | 331 iNaturalist candidates fetched; 227 verified inside Van Udyan | [phase_2_inaturalist.md](./docs/phase_2_inaturalist.md) |
| 3 | Data cleaning and standardisation, with no records lost | [phase_3_data_cleaning.md](./docs/phase_3_data_cleaning.md) |
| 4 | PostgreSQL + PostGIS schema, spatial indexes and seeding | [phase_4_database.md](./docs/phase_4_database.md) |
| 5 | FastAPI REST backend | [phase_5_backend.md](./docs/phase_5_backend.md) |
| 6 | Dashboard, map, charts and tables | [phase_6_dashboard.md](./docs/phase_6_dashboard.md) |
| 7 | Planted plant and field sighting management | [phase_7_data_management.md](./docs/phase_7_data_management.md) |
| 8 | CSV / GeoJSON / ZIP exports | [phase_8_dataset_export.md](./docs/phase_8_dataset_export.md) |
| 9 | Geotagged photo upload | [phase_9_photo_upload.md](./docs/phase_9_photo_upload.md) |
| 10 | Pl@ntNet AI identification | [phase_10_plantnet.md](./docs/phase_10_plantnet.md) |
| 11 | Human verification of AI results | [phase_11_human_verification.md](./docs/phase_11_human_verification.md) |
| 12 | Plant health monitoring and survival statistics | [phase_12_plant_monitoring.md](./docs/phase_12_plant_monitoring.md) |
| 13 | Biodiversity analytics and action priorities | [phase_13_advanced_analytics.md](./docs/phase_13_advanced_analytics.md) |
| 14 | Conservation and SDG PDF reports | [phase_14_conservation_report.md](./docs/phase_14_conservation_report.md), [phase_14_1](./docs/phase_14_1_ngo_report_refinement.md) |
| 15 | Password-protected editing, read-only iNaturalist data | [phase_15_authentication.md](./docs/phase_15_authentication.md) |
| 16 | Production cleanup & architecture hardening | [phase_16_production_cleanup.md](./docs/phase_16_production_cleanup.md) |
| 17 | Data entry and photo management | [phase_17_data_entry_photo_management.md](./docs/phase_17_data_entry_photo_management.md) |
| 18 | Production deployment on Render (Docker) + Supabase (PostGIS & Storage) & 12 bug fixes | [DEPLOYMENT.md](./docs/DEPLOYMENT.md) |
| 19 | Quality-of-life features: Open-Meteo live weather popover, 12-hour IST clock, verification queue, species profiles, 50-photo bulk upload | [PROJECT_TRACKER.md](./PROJECT_TRACKER.md) |
| 20 | Devrai Sacred Grove master-plan compliance: 20×20 grid audit, spacing warning detection, visual heatmap & CSV audit export | [PROJECT_TRACKER.md](./PROJECT_TRACKER.md) |
| 21 | Senior backend security hardening pass (OWASP audit, rate limiter, timing attack defense, CSP, request-size limiter, non-root container) | [PROJECT_TRACKER.md](./PROJECT_TRACKER.md) |
| 22 | Final code polish and tracker synchronization | [PROJECT_TRACKER.md](./PROJECT_TRACKER.md) |
| 23 | Clean data hygiene baseline reset: 0 synthetic/test records; platform strictly reflects authoritative 227 iNaturalist records | [PROJECT_TRACKER.md](./PROJECT_TRACKER.md) |

Full phase-by-phase execution tracking is documented in [PROJECT_TRACKER.md](./PROJECT_TRACKER.md). The deployment architecture is described in [DEPLOYMENT.md](./docs/DEPLOYMENT.md).

---

## ⚠️ Notes & Limitations

- **AI suggestions depend heavily on the photo.** Close-ups of a single leaf, flower or fruit identify far better than distant shots of a whole sapling. The upload window includes photo tips.
- **Record counts measure sampling, not abundance.** Areas with no records are monitoring gaps, not places without plants.
- **GPS Map Camera can reuse a stale location**, so several photos may share identical coordinates. Wait for a GPS fix before taking photos.
- **NGO observations and planted plants are stored in JSON files** in `data/processed/`, alongside the PostGIS database. Back up `data/` regularly.

---

## 🤝 Team & Credits

**Built by**
- Priyansh Pandey
- Ranjan Verma
- Rahul Narkhede
- Chaitanya Gaur

**Partner NGO:** Reform Social Welfare Foundation (RSWF), Service Learning project

**Data & services:** [iNaturalist](https://www.inaturalist.org/) observers and API · [Pl@ntNet](https://plantnet.org/) identification API · [OpenStreetMap](https://www.openstreetmap.org/) contributors · Esri World Imagery
