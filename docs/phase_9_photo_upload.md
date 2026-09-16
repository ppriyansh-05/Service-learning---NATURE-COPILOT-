# 📷 Phase 9 — Photo Upload & EXIF GPS Extraction Documentation

---

## 📌 1. Executive Summary & Architecture

Phase 9 implements an end-to-end **Geotagged Photo Upload & EXIF GPS Extraction Pipeline** for field observation collection in the **Van Udyan Biodiversity Intelligence Platform**.

Field volunteers and NGO workers can upload plant photographs directly via the dashboard. The system validates file safety, extracts WGS84 decimal coordinates from EXIF metadata, verifies spatial containment against the authoritative Van Udyan boundary polygon, assigns active monitoring zones (`ZONE A`, `ZONE B`, `ZONE C`, or `OUTSIDE_ACTIVE_ZONES`), and stores the record with source provenance (`NGO / New Upload`).

```
┌─────────────────────────────────────────────────────────────┐
│                 DASHBOARD PHOTO UPLOAD MODAL                │
│    [Select Photo (.jpg, .png, .webp)]  ->  [Upload Button]  │
└──────────────────────────────┬──────────────────────────────┘
                               │ Multipart Form-Data Request
                               ▼
┌─────────────────────────────────────────────────────────────┐
│             FASTAPI PHOTO UPLOAD ROUTER MODULE              │
│               POST /api/v1/observations/upload              │
└──────────────────────────────┬──────────────────────────────┘
                               │ 1. Validate Extension, MIME & Max 10MB
                               │ 2. Save file as upload_<uuid>.<ext>
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 EXIF METADATA SERVICE                       │
│  - Extract GPSLatitude, GPSLongitude, captured_at           │
│  - Convert N/S/E/W degrees/minutes/seconds -> decimal       │
└──────────────────────────────┬──────────────────────────────┘
                               │ 3. Check EXIF GPS Availability
                               ▼
┌─────────────────────────────────────────────────────────────┐
│             WGS84 GEOFENCE & ZONE SERVICE                   │
│  - Validate Point inside FULL Van Udyan Boundary Polygon    │
│  - Assign Zone A / Zone B / Zone C / Outside Active Zones   │
└──────────────────────────────┬──────────────────────────────┘
                               │ 4. Save Record (source = "NGO / New Upload")
                               ▼
┌─────────────────────────────────────────────────────────────┐
│               CENTRAL POSTGRESQL / POSTGIS STORE            │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔒 2. Security & Storage Rules

- **Allowed Formats:** JPG/JPEG (`image/jpeg`), PNG (`image/png`), WEBP (`image/webp`).
- **File Size Limit:** Maximum 10 MB (`10 * 1024 * 1024` bytes). Oversized files return HTTP 413 Payload Too Large.
- **Path Traversal Protection:** Input filenames are stripped of directories; files are saved using generated safe UUID filenames: `upload_<uuid4_hex>.<ext>`.
- **Storage Location:** Saved locally in project `data/uploads/` directory, exposed safely over static endpoint `/uploads/<filename>`.

---

## 🌐 3. API Endpoint Specification

### `POST /api/v1/observations/upload`

**Request:** `multipart/form-data`
- `file: UploadFile` (Required plant photograph)

**Successful Response (`HTTP 201 Created`):**
```json
{
  "success": true,
  "gps_available": true,
  "observation_id": 228,
  "source": "NGO / New Upload",
  "latitude": 18.5184386,
  "longitude": 73.7802123,
  "zone": "ZONE A",
  "zone_status": "ACTIVE_ZONE",
  "photo_url": "/uploads/upload_a1b2c3d4.jpg",
  "captured_at": "2026-08-30",
  "status": "spatially_verified",
  "message": "Photo observation successfully uploaded and spatially verified inside Zone A."
}
```

**Missing EXIF GPS Response (`HTTP 400 Bad Request`):**
```json
{
  "detail": "Uploaded photo does not contain EXIF GPS metadata. EXIF GPS is required for automatic spatial verification."
}
```

**Location Outside Boundary (`HTTP 400 Bad Request`):**
```json
{
  "detail": "Uploaded photo location (19.076, 72.8777) is outside the Van Udyan project boundary."
}
```

---

## 🧪 4. Testing & Validation

Run all Pytest unit test suites and validation scripts:

```bash
# Run upload unit test suite (11 passed)
python -m pytest backend/tests/test_upload.py

# Run all project Pytest test suites (40 passed)
python -m pytest backend/tests/

# Run Phase 9 automated validation script
python scripts/validate_phase9.py
```
