# 🌿 Phase 6 — Van Udyan Biodiversity Dashboard / Frontend Documentation

---

## 📌 1. Executive Summary & Dashboard Architecture

Phase 6 implements a responsive frontend dashboard for the **Van Udyan Biodiversity Intelligence Platform**.

The dashboard consumes the Phase 5 FastAPI backend REST endpoints exclusively (`/health`, `/health/db`, `/api/v1/observations`, `/api/v1/species`, `/api/v1/zones`, `/api/v1/geography`, `/api/v1/map/observations`, `/api/v1/statistics/overview`). Direct database connections from the frontend are strictly prohibited.

```
┌─────────────────────────────────────────────────────────────┐
│                 FASTAPI BACKEND API LAYER                   │
│          http://localhost:8000/api/v1/statistics            │
└──────────────────────────────┬──────────────────────────────┘
                               │ REST JSON API
                               ▼
┌─────────────────────────────────────────────────────────────┐
│         CENTRALIZED API CLIENT LAYER (js/api.js)            │
│               Configurable VITE_API_BASE_URL                 │
└──────────────────────────────┬──────────────────────────────┘
                               │ Dynamic Rendering Engine
                               ▼
┌─────────────────────────────────────────────────────────────┐
│            VAN UDYAN DASHBOARD INTERFACE (SPA)              │
│  [Overview KPIs] [Interactive GIS Map] [Species] [Records]  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ 2. Technology Stack

- **Framework & Libraries:** HTML5, CSS3 (Emerald dark theme, glassmorphism, responsive grid), JavaScript (ES6+ SPA Engine), Leaflet.js 1.9+, Chart.js 4.4+.
- **React / Vite Support:** Standard React + TypeScript source files provided in `frontend/src/` (`App.tsx`, `main.tsx`, `api.ts`, `package.json`, `vite.config.ts`).
- **GIS Mapping Engine:** Leaflet JS + OpenStreetMap tiles + PostGIS EPSG:4326 WGS84 GeoJSON layer rendering.

---

## 🚀 3. How to Run Locally

### Option A: Immediate Browser View (No Build Tools Required)
Open [`frontend/index.html`](file:///c:/Users/ppriy/OneDrive/Desktop/semester%205/Service%20Learning%20NGO/frontend/index.html) in any modern browser.

### Option B: Node / Vite Server (Standard React Workflow)
```bash
# Navigate to frontend directory
cd frontend

# Install Node dependencies
npm install

# Run development server
npm run dev
```

---

## 🌐 4. Environment Configuration

- **`VITE_API_BASE_URL`**: Configurable API Base URL for FastAPI backend connection (default: `http://localhost:8000`).
- Configured in `frontend/js/config.js` and `frontend/src/services/api.ts`. No hardcoded `localhost` URLs inside UI components.

---

## 📊 5. Dashboard Pages & Features

### 1. Overview & Live KPIs
- **Dynamic KPI Cards:** Total Recorded Observations (`227`), Recorded Species/Taxa (`88`), Active Monitoring Zones (`3`), Observations Inside Active Zones (`123`).
- **Interactive Charts:** Observations Breakdown by Zone (Chart.js Bar Chart), Observations Breakdown by Data Source Stream (Chart.js Doughnut Chart).
- **Data Source Transparency Notice:** Wording clearly indicates current data is based on spatially verified iNaturalist sightings.

### 2. Interactive GIS Biodiversity Map
- **Boundary Layer:** Golden dashed polygon displaying complete Bavdhan Van Udyan site boundary.
- **Zones Layer:** Color-coded polygons for Active Monitoring Zones (`ZONE A`, `ZONE B`, `ZONE C`).
- **Observations Layer:** Point markers for observations inside active zones (`#10b981`) and observations outside active zones (`#f97316`).
- **Popups:** Clicking markers displays species name, scientific name, observer, date, zone assignment, quality grade, and photo reference links.

### 3. Species Catalog Page
- **Searchable Table:** Live search by scientific name or common name.
- **Pagination:** Clean page navigation with species record counts.

### 4. Observations Records Page
- **Multi-Filter Bar:** Filters by species search, zone select (`ZONE A`, `ZONE B`, `ZONE C`, `OUTSIDE`), quality grade (`research`, `needs_id`), and source stream (`iNaturalist`, `Planted`, `New Upload`).
- **Paginated Table:** DB ID, scientific name, common name, observer, date, zone assignment, quality grade, and source.

---

## 🧪 6. Testing & Automated Validation

To run the Phase 6 automated validation suite:

```bash
python scripts/validate_phase6.py
```
