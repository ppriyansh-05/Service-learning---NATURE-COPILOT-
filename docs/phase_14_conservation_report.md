# Phase 14 — SDG & Conservation Decision-Support Report Architecture

## 1. Executive Overview

Phase 14 of the **Van Udyan Biodiversity Intelligence Platform** introduces a dynamic, data-driven **NGO Conservation Decision-Support Report** and **SDG Impact Evaluation System**. The system dynamically compiles PostgreSQL/PostGIS biodiversity data, plant condition monitoring histories, spatial coverage indicators, and rule-based field action recommendations into professional multi-page PDF documents and JSON endpoints.

---

## 2. Core Non-Negotiable Rules & Data Principles

1. **No False Data (Baseline Data Integrity):**
   - Statistics are calculated directly from current database state. Zero fabricated or hard-coded figures exist.
   - Verified baseline data counts:
     - `iNaturalist Spatially Verified Observations` = **227**
     - `NGO / New Upload Observations` = **0**
     - `RSWF Monitored Planted Plants` = **3** (`PL-001`, `PL-002`, `PL-003`)
     - `Active Monitoring Zones` = **3** (`ZONE A`, `ZONE B`, `ZONE C`)
2. **Plant Status Editability & History Preservation:**
   - Plant health status (`Alive`, `Dead`, `Unknown`) remains fully editable.
   - When a status correction occurs, the chronological visit history in `plant_monitoring` remains 100% preserved.
3. **Data Provenance Transparency:**
   - Clearly distinguishes `iNaturalist` reference data (read-only) from `RSWF Planted Plants` and `NGO / New Upload` field records.
4. **Scientifically Safe Terminology:**
   - Enforces terms: *"Recorded Taxa"*, *"Recorded Observations"*, *"Current Monitoring Records"*.
   - Never asserts total site biodiversity census from dataset sampling frequency alone.
5. **Exact Survival Rate Formula:**
   $$\text{Survival Rate \%} = \frac{\text{Alive}}{\text{Alive} + \text{Dead}} \times 100$$
   - `Unknown` status specimens are strictly excluded from the denominator.
   - If $\text{Alive} + \text{Dead} = 0$, displays *"Insufficient monitoring data."*

---

## 3. Architecture & Data Flow

```
+-------------------------------------------------------+
|          PostgreSQL / PostGIS Data Stores             |
+-------------------------------------------------------+
                           |
                           v
+-------------------------------------------------------+
| Analytics Service & Data Service                      |
| (analytics_service.py / data_service.py)             |
+-------------------------------------------------------+
                           |
                           v
+-------------------------------------------------------+
| Report Service (report_service.py)                    |
| Assembles report JSON & compiles PDF via ReportLab   |
+-------------------------------------------------------+
                           |
                           v
+-------------------------------------------------------+
| FastAPI Reports Router (/api/v1/reports)              |
| GET /conservation, /sdg, /conservation.pdf, /sdg.pdf  |
+-------------------------------------------------------+
                           |
                           v
+-------------------------------------------------------+
| Dashboard Download Center (Export & Reports Tab)      |
+-------------------------------------------------------+
```

---

## 4. Report Structure & Sections

1. **Title & Document Metadata Header:**
   - Title: *"Van Udyan Biodiversity & Conservation Decision-Support Report"*
   - Generation timestamp (IST), project site location (Plus Code `GQ9J+74Q`), organization (`RSWF`), and data sources.
2. **Executive Summary & Baseline KPIs:**
   - Total recorded observations (227), unique recorded taxa (88), active zones (3), plant survival rate (100.0%).
   - Scientific notice regarding dataset sampling frequency vs ecological abundance.
3. **Active Zone Breakdown & Coverage Analytics:**
   - Detailed breakdown for Zone A, Zone B, Zone C, and Outer Unmonitored Site Boundary (104 obs, ~11.04 ha).
4. **Areas Requiring Action (Rule-Based Priorities):**
   - Integrates Phase 13 transparent rule-based field action recommendations (`MONITORING_PRIORITY`, `SURVEY_PRIORITY`, `DATA_COLLECTION_PRIORITY`, `NO_IMMEDIATE_DATA_DRIVEN_PRIORITY`).
5. **Potential Plantation Assessment Areas:**
   - Identifies areas for potential plantation assessment based on dataset indicators (e.g. unmonitored sectors, plant desiccation, missing tags). Uses safe wording: *"Additional plantation may be considered after field verification of ecological suitability."*
6. **Data Gaps & Limitations:**
   - Transparently outlines unmonitored sectors, missing dates/taxonomy, and absence of NGO field uploads yet.
7. **Conservation Recommendations:**
   - Evidence-based recommendations containing `Evidence + Reason + Suggested Action`.
8. **Sustainable Development Goal (SDG) Alignment:**
   - Maps measurable database evidence to SDGs:
     - **SDG 15 (Life on Land):** 227 observations, 88 recorded taxa, 3 planted specimens.
     - **SDG 11 (Sustainable Cities):** 12.5 ha site boundary, 3 active working zones (1.46 ha).
     - **SDG 13 (Climate Action):** Healthy tree sapling tracking (`Ficus religiosa`, `Azadirachta indica`, `Santalum album`).
     - **SDG 17 (Partnerships):** RSWF NGO academic service-learning partnership & open PostGIS API.
     - **SDG 9 (Industry & Innovation):** REST API, EXIF GPS parser, Pl@ntNet AI integration.

---

## 5. API Endpoints

- **`GET /api/v1/reports/conservation`**: Returns JSON conservation decision-support payload.
- **`GET /api/v1/reports/sdg`**: Returns JSON SDG impact evaluation payload.
- **`GET /api/v1/reports/conservation.pdf`**: Generates and streams PDF conservation report (`application/pdf`).
- **`GET /api/v1/reports/sdg.pdf`**: Generates and streams PDF SDG impact report (`application/pdf`).

---

## 6. Testing & Validation Summary

- **Pytest Suite:** `backend/tests/test_reports.py` (`18/18 PASSED`).
- **Phase 14 Validation Script:** `scripts/validate_phase14.py` (`10/10 CHECKS SUCCESSFUL`).
- **Data Consistency Test:** `Dashboard == Report == Database` verified (`iNaturalist = 227`, `NGO = 0`, `Planted = 3`).
