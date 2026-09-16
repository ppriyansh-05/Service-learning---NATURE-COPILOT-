# 🌳 Van Udyan Biodiversity Intelligence Platform

> **A Geospatial Biodiversity Mapping, Monitoring & AI Analytics System for RSWF NGO**

---

## 📌 Project Overview

The **Van Udyan Biodiversity Intelligence Platform** is a web-based geospatial system built for the **RSWF NGO** to digitally map, monitor, and analyze plant biodiversity in Van Udyan. 

---

## 🗺️ Phase 1 — Geographical Foundation

- **Location:** Bavdhan Van Udyan, Lantana Gardens, Bavdhan, Pune, Maharashtra 411021
- **Plus Code:** `GQ9J+74Q`
- **Geographic Source:** `scripts/Bavdhan van udyan.kmz`
- **Coordinate Reference System:** WGS84 (`EPSG:4326`)
- **Site Boundaries & Active Zones:**
  - **Outer Boundary (`VAN UDHYAN`):** Represents the complete project area boundary.
  - **Active Work Zones (`ZONE A`, `ZONE B`, `ZONE C`):** Current active intervention/monitoring areas where RSWF operates.
  - **Spatial Rule:** Areas outside Zone A/B/C but inside Van Udyan remain part of the project site and are retained in spatial queries.
- **Geographical Documentation:** See [`docs/phase_1_geography.md`](./docs/phase_1_geography.md) and [`docs/map_verification.html`](./docs/map_verification.html).

---

## 🌿 Phase 2 — iNaturalist Data Collection & Spatial Verification

- **Data Source:** Official public iNaturalist API (`https://api.inaturalist.org/v1/observations`)
- **Authentication:** Public Read-Only Endpoint (No API key required)
- **Candidates Retrieved:** 331 observation candidate records
- **Spatially Verified Inside Van Udyan:** **227** records across 88 unique species
- **Active Zone Breakdown:**
  - **Zone A:** 60 records
  - **Zone B:** 37 records
  - **Zone C:** 26 records
  - **Outside Active Zones (Retained):** 104 records
- **Primary Processed Dataset:** [`data/processed/inaturalist/observations_van_udyan.csv`](./data/processed/inaturalist/observations_van_udyan.csv)
- **Detailed Ingestion Report:** See [`docs/phase_2_inaturalist.md`](./docs/phase_2_inaturalist.md)

---

## 🧹 Phase 3 — Data Cleaning & Standardization

- **Input Processed Dataset:** [`data/processed/inaturalist/observations_van_udyan.csv`](./data/processed/inaturalist/observations_van_udyan.csv) (227 records)
- **Cleaned Production Dataset:** [`data/processed/inaturalist/observations_van_udyan_clean.csv`](./data/processed/inaturalist/observations_van_udyan_clean.csv) (227 records)
- **Data Lineage:** 100% preservation of `observation_id` and raw source files; 0 duplicate observation IDs, 0 records lost.
- **Standardization Highlights:**
  - Header schema standardized to `snake_case`
  - Taxon and Observation IDs cleaned to integer strings
  - Dates standardized to `YYYY-MM-DD` ISO format
  - 100% spatial containment re-validated against WGS84 Van Udyan boundary polygon
  - Missing values preserved cleanly as empty strings (`""`) without fabricated placeholder text
- **Detailed Cleaning Documentation:** See [`docs/phase_3_data_cleaning.md`](./docs/phase_3_data_cleaning.md)

---

## 🗄️ Phase 4 — Database Architecture & Initial Data Integration

- **Database Engine:** PostgreSQL 15+ with PostGIS spatial extension (`EPSG:4326` WGS84 coordinates)
- **Multi-Source Data Model:**
  - **Currently Implemented:** Cleaned iNaturalist observations (`observations` table, 227 records)
  - **Extensible Schema Ready For:** RSWF Planted Plants (`planted_plants` table with status `Alive`/`Dead`/`Unknown`), Field User Uploads, and AI predictions (`ai_predictions` table)
- **Spatial Indexing & Tables:** `GIST` indexes on `observations.geom`, `geography_boundaries.geom`, `geography_zones.geom`, `planted_plants.geom`
- **Database DDL Schema:** [`database/schema/01_init_postgis_schema.sql`](./database/schema/01_init_postgis_schema.sql)
- **Setup & Seeding Pipeline:** [`scripts/setup_database.py`](./scripts/setup_database.py)
- **Detailed Database Documentation:** See [`docs/phase_4_database.md`](./docs/phase_4_database.md)

---

## ⚡ Phase 5 — FastAPI Backend & API Layer

- **Framework:** FastAPI, Uvicorn, Pydantic v2, SQLAlchemy 2.0, GeoAlchemy2
- **CURRENTLY IMPLEMENTED (Read-Only API Layer):**
  - System Health: `GET /health` & `GET /health/db`
  - Observations: `GET /api/v1/observations` & `GET /api/v1/observations/{id}`
  - Species Taxonomy: `GET /api/v1/species`
  - Active Zones GIS: `GET /api/v1/zones`
  - Site Boundary GIS: `GET /api/v1/geography`
  - Interactive Map GeoJSON: `GET /api/v1/map/observations`
  - Dynamic Biodiversity Analytics: `GET /api/v1/statistics/overview`
  - OpenAPI Interactive Specs: `/docs` & `/openapi.json`
- **FUTURE (Planned for Later Phases):** User authentication, photo uploads, EXIF GPS extraction, AI classification inference, planted plant management UI, automated PDF reporting
- **Detailed Backend Documentation:** See [`docs/phase_5_backend.md`](./docs/phase_5_backend.md)

---

## 🌿 Phase 6 — Van Udyan Biodiversity Dashboard / Frontend

- **Technologies:** HTML5, CSS3, JavaScript (ES6+ SPA Engine), React / TypeScript, Leaflet.js, Chart.js, Tailwind CSS
- **CURRENTLY IMPLEMENTED:**
  - **Overview Dashboard:** Live KPI Cards (227 observations, 88 recorded taxa, 3 active monitoring zones, 123 observations inside zones), Zone breakdown bar chart, Source breakdown doughnut chart, and Data Source Transparency Banner.
  - **Interactive GIS Map:** WGS84 Leaflet map rendering Van Udyan boundary polygon (gold stroke), Zone A/B/C polygons (green/blue/purple), and point markers with click popups.
  - **Species Catalog:** Searchable & paginated species/taxa table with species observation counts.
  - **Observation Records:** Filterable (species, zone, quality grade, source) & paginated observation table.
  - **Active Monitoring Zones:** Dedicated RSWF active zone overview cards.
  - **Configurable API Integration:** Centralized `ApiService` consuming Phase 5 FastAPI backend via configurable `VITE_API_BASE_URL` (default: `http://localhost:8000`).
- **Detailed Dashboard Documentation:** See [`docs/phase_6_dashboard.md`](./docs/phase_6_dashboard.md)

---

## 🎯 Key Features & Core Capabilities

- 🗺️ **Interactive GIS Biodiversity Map:** Displays plant locations, boundary polygons, sub-zones, and species density using source-coded map pins:
  - 🟢 **Green Pins:** iNaturalist Historical Observations (Public Dataset)
  - 🔵 **Blue Pins:** RSWF Planted Plants (Verified Plantation Dataset)
  - 🟠 **Orange Pins:** New Geotagged Field Uploads (Community/Volunteer Dataset)
- 📸 **Geotagged Field Observation Upload:** Upload plant photos with automatic **EXIF GPS** extraction, location boundary validation, and zone assignment.
- 🤖 **AI-Powered Plant Classification:** Integrated **EfficientNet-B0** transfer learning model with confidence-based confirmation:
  - **> 90% Confidence:** Automatic prediction display with 1-click user confirmation.
  - **60% – 90% Confidence:** Top-3 species options presented for volunteer selection.
  - **< 60% Confidence:** Manual species identification fallback.
- 📊 **Biodiversity Analytics Engine:** Calculates species richness, species distribution, abundance, zone-wise counts, density hotspots, and historical observation trends.
- 🌿 **Plant Survival & Health Monitoring:** Tracks condition state histories (`Alive` → `Dead` → `Unknown`) over time for planted species to assess conservation intervention success.
- 📄 **NGO Automated Reporting:** Export comprehensive biodiversity reports in **PDF** and **CSV** formats for stakeholders and conservation planning.

---

## 🏗️ System Architecture

```
                                  DATA SOURCES
         ┌─────────────────────────────┼─────────────────────────────┐
         ▼                             ▼                             ▼
  iNaturalist API             RSWF Planted Database        Field Image Uploads
  (Historical Records)        (Plantation Baseline)        (EXIF GPS Parsing)
         │                             │                             │
         └─────────────────────────────┼─────────────────────────────┘
                                       ▼
                       ┌──────────────────────────────┐
                       │ Central PostGIS Database     │
                       │ (PostgreSQL + Spatial Index) │
                       └──────────────┬───────────────┘
                                      ▼
                       ┌──────────────────────────────┐
                       │       FastAPI Backend        │
                       └──────────────┬───────────────┘
                                      ▼
             ┌────────────────────────┴────────────────────────┐
             ▼                                                 ▼
  ┌──────────────────────┐                          ┌──────────────────────┐
  │ Next.js / React UI   │                          │ AI Classifier Engine │
  │ Interactive GIS Map  │                          │  (EfficientNet-B0)   │
  └──────────────────────┘                          └──────────────────────┘
```

---

## 🛠️ Technology Stack

| Layer | Technologies Used |
| :--- | :--- |
| **Frontend UI / Map** | React.js / Next.js, Leaflet / Mapbox GL, TailwindCSS / Vanilla CSS, Plotly / Chart.js |
| **Backend API** | Python 3.10+, FastAPI, Pydantic, Uvicorn |
| **Database & GIS** | PostgreSQL, PostGIS spatial extension, SQLAlchemy / GeoAlchemy2 |
| **AI / Machine Learning** | PyTorch / TensorFlow, EfficientNet-B0 Transfer Learning, OpenCV, Pillow |
| **Data & Utilities** | Pandas, GeoPandas, ExifRead / python-stat, Requests |
| **Deployment** | Docker, Nginx, PostgreSQL Container |

---

## 📂 Project Structure

```
.
├── ai/                     # AI/ML models, training scripts & inference engine
│   ├── models/             # Trained EfficientNet-B0 weights
│   └── inference.py        # Species prediction API service
├── backend/                # FastAPI application backend
│   ├── app/                # API routes, models, schemas, database services
│   └── main.py             # FastAPI application entry point
├── frontend/               # Next.js / React GIS frontend dashboard
│   ├── components/         # Map components, charts, popups, upload modal
│   └── pages/              # Dashboard overview, map, analytics, reports
├── data/                   # Data storage directory
│   ├── raw/                # Raw iNaturalist CSVs & plantation dumps
│   └── processed/          # Cleaned GeoJSONs & SQLite/PostGIS exports
├── scripts/                # Utility scripts (iNaturalist fetcher, EXIF parser)
├── docs/                   # Project documentation & user manuals
├── PROJECT_TRACKER.md      # Detailed 20-phase roadmap & task execution status
└── README.md               # Project guide and documentation
```

---

## 🚀 Quick Start & Development Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL with PostGIS extension (or Docker)

### 1. Backend Setup
```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup
```bash
# Navigate to frontend directory
cd frontend

# Install packages
npm install

# Run development server
npm run dev
```

---

## 🚦 Roadmap & Progress Tracking

The project implementation is structured into **20 defined phases**, ranging from boundary definition and iNaturalist ingestion to AI inference and production deployment.

See [**`PROJECT_TRACKER.md`**](./PROJECT_TRACKER.md) for the live phase-by-phase execution status and upcoming task list.

---

## 🤝 Project Credits & Acknowledgments

- **NGO Partner:** RSWF (Service Learning Project)
- **Data Credits:** iNaturalist API & OpenStreetMap contributors
