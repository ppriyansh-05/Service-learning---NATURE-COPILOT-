# Van Udyan Biodiversity Intelligence Platform — Final System Architecture & Pre-Deployment Readiness

## 1. Executive Summary & Project Status

The **Van Udyan Biodiversity Intelligence Platform** (developed for the Reform Social Welfare Foundation, Pune) has completed all engineering, architectural hardening, and pre-deployment readiness phases.

The platform provides a complete spatial intelligence, plant survival monitoring, and decision-support system for Bavdhan Van Udyan. It operates on real data without synthetic production records, preserves original reference data, and enforces strict access control.

---

## 2. System Architecture

```
                                 [ Web Browser Clients ]
                                            │
                      ┌─────────────────────┴─────────────────────┐
                      ▼                                           ▼
             [ Public Access ]                          [ RSWF Authorized ]
             • GIS Maps & Views                         • Add/Edit/Delete Plants
             • Species Catalog                          • Plant Condition Visits
             • Geotagged Photo Upload                   • Human AI Verification
             • Pl@ntNet AI Suggestions                  • Delete NGO Observations
             • Export Downloads & Reports               (Header: X-NGO-Admin-Password)
                      │                                           │
                      └─────────────────────┬─────────────────────┘
                                            ▼
                               [ FastAPI Backend Engine ]
                               (Python 3.10+, Port 8000)
                                            │
       ┌────────────────────┬───────────────┴───────────────┬────────────────────┐
       ▼                    ▼                               ▼                    ▼
[ GIS & EXIF Service ] [ Data Service ]          [ Pl@ntNet REST AI ]   [ ReportLab Engine ]
• WGS84 Geofencing   • PostgreSQL/PostGIS ORM     • External REST API    • 14-Section PDF
• EXIF GPS Extractor • Multi-source Provenance    • Species Suggestions  • SDG Alignment
• Safe Upload Dir    • Dynamic KPIs & Analytics   • Confidence Scores    • Platypus Layout
                            │
                            ▼
           [ PostgreSQL / PostGIS Spatial Database ]
           • observations (227 iNaturalist reference records - READ ONLY)
           • planted_plants (3 baseline RSWF plantation specimens)
           • plant_monitoring (Chronological visit inspection logs)
           • ai_predictions (AI suggestions & human verification audit)
           • zones & boundary (Authoritative PostGIS spatial polygons)
```

---

## 3. Database Architecture & Schema Integrity

### Central Source of Truth: PostgreSQL / PostGIS
- **`observations`**: Holds 227 spatially verified iNaturalist reference records (`source = "iNaturalist"`) and NGO sightings (`source = "NGO / New Upload"`). Original iNaturalist records are permanently read-only (`HTTP 403 Forbidden`).
- **`planted_plants`**: Holds RSWF planted tree specimens (`plant_code`, `scientific_name`, `common_name`, `planted_on`, `status`, `latitude`, `longitude`, `zone_code`, `photo_url`, `notes`).
- **`plant_monitoring`**: Preserves full chronological visit history (`planted_plant_id`, `status`, `monitoring_date`, `notes`, `photo_url`, `observer`).
- **`ai_predictions`**: Persists Pl@ntNet species suggestions (`predicted_scientific_name`, `confidence_score`, `rank`, `user_confirmed`, `human_decision`, `verified_scientific_name`).
- **Spatial Indexes**: PostGIS `GIST` indexes on `geom` (`Point` and `Polygon` geometries in WGS84 EPSG:4326).

---

## 4. GIS & Spatial Geometry Architecture

- **Authoritative Geometry:** Derived directly from official geodesic PostGIS boundary polygons (`van_udyan_boundary.geojson` and `van_udyan_zones.geojson`):
  - **Total Site Boundary:** **3.58 ha** (~35,770 m²)
  - **Zone A:** **0.20 ha** (2,019 m²)
  - **Zone B:** **0.11 ha** (1,123 m²)
  - **Zone C:** **0.24 ha** (2,408 m²)
  - **Total Active Working Zones:** **0.55 ha** (5,550 m²)
  - **Outer Unmonitored Portion:** **3.02 ha** (30,220 m²)
- **Geofence Enforcement:** Coordinates submitted via API or extracted from EXIF GPS must fall within the 3.58 ha Van Udyan boundary polygon. Coordinates outside the boundary are rejected (`HTTP 400 Bad Request`).

---

## 5. Public vs. RSWF Authorized Access Policy

| Functionality | Access Level | Authorization Mechanism |
| :--- | :--- | :--- |
| View Dashboard KPIs & Charts | **Public** | No password required |
| Interactive Leaflet GIS Map | **Public** | No password required |
| Species Catalog & Search | **Public** | No password required |
| Observation Records & Filters | **Public** | No password required |
| Active Working Zones Overview | **Public** | No password required |
| Dataset Exports (CSV, GeoJSON, ZIP) | **Public** | No password required |
| Decision-Support PDF Reports | **Public** | No password required |
| Geotagged Photo Upload (EXIF GPS) | **Public** | No password required |
| NGO Field Sighting Registration | **Public** | No password required |
| Pl@ntNet AI Species Identification | **Public** | No password required |
| Add / Edit / Delete Planted Plants | **Password Required** | Header: `X-NGO-Admin-Password` |
| Record Plant Monitoring Visit | **Password Required** | Header: `X-NGO-Admin-Password` |
| Human AI Verification & Correction | **Password Required** | Header: `X-NGO-Admin-Password` |
| Delete NGO Field Observation | **Password Required** | Header: `X-NGO-Admin-Password` |
| Edit or Delete iNaturalist Record | **PERMANENTLY FORBIDDEN** | Blocked (`HTTP 403 Forbidden`) |

### Password Session Security (Part 8 Details)
- **Mechanism:** Browser `sessionStorage` caching with rolling **30-minute inactivity timeout**.
- **Timeout Behavior:** Inactive sessions automatically expire after 30 minutes. Upon expiration, cached credentials are erased and the UI returns to Public View Mode.
- **Immediate Lock:** Top header toggle (`🔒 RSWF Admin Active (Click to Lock)`) allows instant logout at any time.
- **Security Best Practices:** Zero plaintext passwords in frontend HTML/JS, zero passwords in API responses or logs, and backend-enforced header verification.

---

## 6. Photo Storage & Pl@ntNet AI Pipeline

1. **Upload & Validation:** Accepts JPG, JPEG, PNG, WEBP files up to 10MB. Generates safe unique filenames (`upload_YYYYMMDD_HHMMSS_uuid.ext`).
2. **EXIF GPS Extraction:** Extracts GPS latitude/longitude and observation timestamp. Does not fabricate GPS coordinates if absent.
3. **Geofence Validation:** Verifies point containment within the 3.58 ha Van Udyan boundary and auto-assigns active zones (Zone A, B, C or Outside Active Zones).
4. **Pl@ntNet AI Identification:** Queries Pl@ntNet REST API (`/v2/identify/all`), returning normalized top 3 candidate species with confidence scores and badges (`HIGH`, `MEDIUM`, `LOW CONFIDENCE`).
5. **Human Verification Workflow:**
   - **Confirm:** Validates suggested species, sets status to `verified`, and upgrades quality grade to `research`.
   - **Correct:** Allows manual species override while preserving original AI suggestion in audit logs.
   - **Needs Review:** Flags observation for expert botanist inspection.
6. **Multi-Entity Photo Support:** Photo attachments are supported for Planted Plants, NGO Field Sightings, and public geotagged uploads.

---

## 7. Dynamic Decision-Support & SDG Reporting

- **Synchronization:** `Database == API == Dashboard == Analytics == PDF Reports`. All metrics are calculated dynamically from database state.
- **Safe Scientific Terminology:** Strictly enforces descriptive language (*"Recorded Taxa"*, *"Sampling Frequency"*, *"Potential Plantation Assessment Area"*, *"Field Assessment Required"*).
- **ReportLab Platypus Engine:** Compiles formatted multi-page PDF documents (`van_udyan_conservation_plantation_report.pdf` and `van_udyan_sdg_project_report.pdf`).
- **SDG Alignment:** Directly maps database records to **SDG 15 (Life on Land)**, **SDG 11 (Sustainable Cities)**, **SDG 13 (Climate Action)**, **SDG 17 (Partnerships)**, and **SDG 9 (Innovation)**.

---

## 8. Known Limitations & Technical Debt Audit

1. **iNaturalist Reference Snapshot:** The 227 iNaturalist records represent a verified snapshot. Ongoing seasonal updates require periodic manual sync or API ingestion.
2. **Field Dataset Pending:** Only 3 baseline plantation records currently exist in production. Genuine RSWF field records will be integrated upon receipt.
3. **Pl@ntNet API Dependency:** AI identification relies on external Pl@ntNet availability and rate limits. Outages gracefully fall back with informative user notices.

---

## 9. Genuine NGO Dataset Integration Procedure

When RSWF provides the genuine field dataset:
1. **Prepare Data Files:** Ensure CSV/Excel records contain plant identifiers, scientific names, planting dates, condition status, and WGS84 coordinates.
2. **Validate Geofence:** Run coordinates through boundary containment validation.
3. **Ingest via API or Script:** Use `POST /api/v1/planted-plants` (with admin password) or a dedicated database migration script.
4. **Attach Field Photographs:** Place genuine plant photos in `data/uploads/` and reference their URLs in the plantation records.
5. **Re-Run Baseline Audit:** Verify that total planted counts match genuine field inventory.

---

## 10. Future Scope — Custom ML / EfficientNet

> **FUTURE ML SCOPE NOTICE:**  
> A custom Van Udyan-specific plant classification model (e.g. transfer-learned EfficientNet-B0) may be developed in the future after sufficient genuine and human-verified local plant images are collected across classes through field usage.  
> **This is NOT implemented in the current project.** The existing Pl@ntNet REST API serves all AI identification requirements reliably.

---

## 11. Exact Post-Phase Implementation Activities

Following this phase, the **ONLY** remaining implementation activities are:
1. **Activity A: Genuine NGO Dataset Integration** (Ingesting RSWF field data and photos when delivered).
2. **Activity B: Final Production Deployment** (Deploying backend and frontend to staging/production server).
*(Future Goal: Custom ML only when sufficient genuine verified local images exist).*
