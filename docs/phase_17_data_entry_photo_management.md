# Phase 17 — Complete NGO Data Entry, Photo Management & Field UX

## 1. Executive Summary

Phase 17 enhances the field data entry workflow, photo attachment pipeline, and user interface for the **Van Udyan Biodiversity Intelligence Platform**.

Key improvements include:
1. **Complete Planted Plant Form:** Full UI field exposure (`plant_code`, `scientific_name`, `common_name`, `planted_on`, `status`, `latitude`, `longitude`, `zone_code`, `notes`, and photo upload attachment).
2. **NGO Field Sighting Form & Educational Field Guidance:** Added explicit field guidance text to distinguish wild/spontaneous species observations from RSWF planted trees, with photo attachment support.
3. **Unified Photo Storage Pipeline:** Reused the central safe photo upload pipeline (`process_photo_upload`, `exif_service.py`, `/data/uploads/`) for Planted Plants, NGO Field Sightings, and geotagged uploads.
4. **Post-Upload EXIF GPS & Pl@ntNet AI Field UX:** Integrated image preview thumbnail, extracted lat/lng coordinates, boundary geofence check result, assigned zone, captured date, Pl@ntNet AI predicted species, confidence score, rank 1–3 list, and human verification/correction controls.
5. **Security & Data Integrity Preservation:** Maintained Phase 15 password authorization (`X-NGO-Admin-Password`), public open access, permanent read-only protection for original iNaturalist records (`HTTP 403 Forbidden`), and strict database baseline integrity (227 iNaturalist, 0 NGO test observations, 3 planted plants, 3 active zones).

---

## 2. Technical Architecture & Field Workflows

### A. Planted Plant Management (`#plant-modal`)
- **Fields Exposed:** `plant_code` (unique ID), `scientific_name`, `common_name`, `planted_on` (ISO date), `status` (`Alive`, `Dead`, `Unknown`), `latitude` & `longitude` (WGS84 EPSG:4326), `zone_code` (auto-computed from PostGIS boundary polygon), `notes`, and optional photo file upload (`photo_url`).
- **Photo Upload:** When a photo file is selected in `#form-plant-photo-file`, the frontend uploads it via the central upload endpoint and attaches `photo_url` (`/uploads/upload_...jpg`) to the plant record.

### B. NGO Field Sighting Form (`#ngo-obs-modal`)
- **Educational Guidance:** Prominently informs field team members:
  > *"Field Guidance: An NGO Field Sighting represents a wild or naturally occurring plant/species observed in Van Udyan by the field team (distinct from RSWF planted trees)."*
- **Fields Exposed:** `scientific_name`, `common_name`, `observed_on`, `observer` (default *"RSWF NGO Team"*), `latitude`, `longitude`, auto-assigned zone, `notes`, and optional photo file upload (`photo_url`).

### C. Unified Photo Storage & Validation Pipeline
- **Validation Rules:** File extension check (`.jpg`, `.jpeg`, `.png`, `.webp`), MIME type verification, file size cap (max 10MB), collision-safe filename generation (`upload_YYYYMMDD_HHMMSS_uuid.ext`).
- **EXIF GPS Metadata:** Automatically parses EXIF GPS tags when present and verifies location against the Van Udyan PostGIS boundary geofence polygon. Does not fabricate GPS when absent.

### D. Post-Upload EXIF GPS & Pl@ntNet AI Field UX (`#upload-photo-modal`)
- **Upload Details Summary Card:** Displays image thumbnail, WGS84 coordinates, geofence boundary containment, active zone assignment (Zone A, B, C or Outside Active Zones), and captured timestamp.
- **Pl@ntNet AI Predictions:** Displays top prediction scientific name, common name, confidence score, and confidence level badge (High, Medium, Low).
- **Human Verification Controls:**
  - **Confirm Prediction:** Confirms AI suggestion and updates observation quality grade to `research`.
  - **Manual Species Correction Form:** Allows expert correction of species name while preserving original AI suggestion in database audit log.
  - **Flag Needs Review:** Flags observation for expert review.

---

## 3. Access Control & iNaturalist Protection

- **Public Access (No Password Required):** Dashboard KPI overview, GIS maps, species catalog, observation search, EXIF GPS photo upload, Pl@ntNet AI identification, dataset CSV/GeoJSON/ZIP downloads, and PDF conservation reports.
- **Password Protection (Requires `X-NGO-Admin-Password`):** Planted plant creation/editing/deletion, condition monitoring visits, AI species verification/correction, and NGO observation deletion.
- **iNaturalist Reference Records:** Permanently read-only reference data (`HTTP 403 Forbidden` on any edit or delete attempt, even with a valid password).

---

## 4. Verification & Validation Results

- **Pytest Suite:** `124/124 PASSED` (100% backend test pass rate across all 10 test modules).
- **Phase 17 Validation Suite (`scripts/validate_phase17.py`):** `10/10 CHECKS SUCCESSFUL`.
- **Complete Validation Pipeline (`validate_phase5.py` to `validate_phase17.py` + `cleanup_test_ngo_data.py`):** `ALL 13 VALIDATION PIPELINE SCRIPTS PASSED 100%`.

---

## 5. Baseline Real Data Integrity Audit

- **iNaturalist Observations:** `227` (Spatially verified reference records intact)
- **NGO / New Upload Observations:** `0` (Test data completely purged after validation)
- **RSWF Planted Plants:** `3` (`PL-001`, `PL-002`, `PL-003` baseline intact)
- **Active Working Zones:** `3` (`ZONE A`, `ZONE B`, `ZONE C`)
