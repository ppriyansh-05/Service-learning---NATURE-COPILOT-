# 🛠️ Phase 7 — Data Management & CRUD Documentation

---

## 📌 1. Executive Summary & Architecture

Phase 7 implements full **Data Management & CRUD (Create, Read, Update, Delete)** capability for the **Van Udyan Biodiversity Intelligence Platform**.

It enables RSWF NGO administrators and field teams to manage **Planted Plants** (`source = "Planted Plants"`) and **NGO Field Sightings** (`source = "NGO / New Upload"`) while strictly protecting original **iNaturalist** reference data from modification or deletion.

```
┌─────────────────────────────────────────────────────────────┐
│                 DASHBOARD DATA MANAGEMENT UI                │
│    [+ Add Planted Plant Modal]    [+ Add NGO Sighting Modal] │
│     [View]         [Edit]         [Confirm Delete Modal]    │
└──────────────────────────────┬──────────────────────────────┘
                               │ REST JSON API (v1)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│            FASTAPI BACKEND API LAYER (api/v1/)              │
│   POST /planted-plants          GET /planted-plants         │
│   PUT  /planted-plants/{id}     DELETE /planted-plants/{id} │
│   POST /observations/ngo        DELETE /observations/{id}   │
└──────────────────────────────┬──────────────────────────────┘
                               │ Provenance & Geofence Checks
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                POSTGRESQL + POSTGIS DATABASE                │
│  - iNaturalist (Protected Reference Data)                   │
│  - Planted Plants (RSWF Managed Plantation Dataset)         │
│  - NGO / New Upload (Field Volunteer Observations)          │
└──────────────────────────────┴──────────────────────────────┘
```

---

## 🌐 2. Planted Plants & NGO Observation Endpoints

| Endpoint Route | HTTP Method | Scope | Description |
| :--- | :---: | :--- | :--- |
| `/api/v1/planted-plants` | `POST` | Planted Plants | Create new RSWF Planted Plant record (requires `plant_code`, lat/lng) |
| `/api/v1/planted-plants` | `GET` | Planted Plants | List paginated Planted Plants with `status`, `zone`, `species` filters |
| `/api/v1/planted-plants/{id}` | `GET` | Planted Plants | Retrieve single Planted Plant detail by ID |
| `/api/v1/planted-plants/{id}` | `PUT` / `PATCH` | Planted Plants | Update Planted Plant record details, health condition status, or location |
| `/api/v1/planted-plants/{id}` | `DELETE` | Planted Plants | Delete Planted Plant record with confirmation |
| `/api/v1/observations/ngo` | `POST` | NGO Sightings | Create new NGO field observation record (`source = "NGO / New Upload"`) |
| `/api/v1/observations/{id}` | `DELETE` | Protection | Deletion protection check (returns HTTP 403 Forbidden for iNaturalist records) |

---

## 🔒 3. Data Provenance & Security Rules

1. **Source Provenance Preservation:** Every database record retains its exact origin stream (`iNaturalist`, `Planted Plants`, `NGO / New Upload`). Editing a record never overwrites its source provenance.
2. **iNaturalist Protection:** Original iNaturalist observations are read-only reference data. Attempted modification or deletion of iNaturalist records through CRUD endpoints is rejected with HTTP `403 Forbidden`.
3. **Health Condition Validation:** Plant status values are strictly constrained server-side to `Alive`, `Dead`, or `Unknown`. Arbitrary status values are rejected with HTTP `422 Unprocessable Entity` or `400 Bad Request`.
4. **Location Geofence Verification:** All incoming coordinates are checked against the WGS84 Van Udyan boundary polygon. Coordinates outside the project site are rejected with HTTP `400 Bad Request`. Active zones (`ZONE A`, `ZONE B`, `ZONE C`) are automatically assigned based on PostGIS spatial containment.

---

## 🖥️ 4. Dashboard UI Integration

The Phase 6 frontend dashboard is extended with a new **Data Management** tab (`#tab-management`):
- **`[ + Add Planted Plant ]` Button & Modal:** Interactive form for registering new plantation records with plant code, species, planting date, condition status, and location coordinates.
- **`[ + Add NGO Sighting ]` Button & Modal:** Interactive form for field volunteers to register new sightings.
- **Planted Plants Table:** Displays plant code, species name, common name, planting date, active zone, status badge (`Alive`, `Dead`, `Unknown`), and Action buttons (`[Edit]`, `[Delete]`).
- **Confirmation Dialog:** Confirms before executing destructive deletion operations.

---

## 🧪 5. Testing & Automated Validation

Execute the Pytest test suite and Phase 7 validation script:

```bash
# Run all backend Pytest test suites (21/21 passed)
python -m pytest backend/tests/

# Run Phase 7 automated validation suite
python scripts/validate_phase7.py
```
