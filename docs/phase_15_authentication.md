# Phase 15 — Password-Protected Editing & Read-Only iNaturalist Data

## 1. Executive Summary

Phase 15 implements a lightweight, non-intrusive backend authorization mechanism for the **Van Udyan Biodiversity Intelligence Platform** to protect NGO data mutation operations while preserving completely open public access for viewing, searching, uploading, exporting, and report downloads.

To align with the project requirements of the **Reform Social Welfare Foundation (RSWF)**:
- **No mandatory user accounts or login** are required for normal public usage.
- **Public endpoints** (dashboard, GIS map, species catalog, observation list, EXIF GPS photo upload, dataset exports, and conservation PDF reports) remain 100% open without password prompts.
- **Data mutation endpoints** (creating/updating/deleting planted plants, logging condition monitoring visits, updating species verification, deleting NGO observations) require authorization via the HTTP `X-NGO-Admin-Password` header.
- **iNaturalist reference observations** remain strictly and permanently **READ-ONLY** (HTTP `403 Forbidden` on any edit or delete attempt, even if a valid password is provided).

---

## 2. Access Policy Matrix

| Action / Feature | Access Level | Endpoint / Method | Authorization Requirement |
| :--- | :--- | :--- | :--- |
| **View Dashboard & Maps** | Public / Open | `GET /api/v1/observations`, `/map/observations`, `/zones`, `/geography` | None |
| **Search Species Catalog** | Public / Open | `GET /api/v1/species` | None |
| **Upload Geotagged Photo** | Public / Open | `POST /api/v1/observations/upload` | None |
| **Submit Field Sighting** | Public / Open | `POST /api/v1/observations/ngo` | None |
| **Download Datasets & Package** | Public / Open | `GET /api/v1/export/*` | None |
| **Download PDF Reports** | Public / Open | `GET /api/v1/reports/*` | None |
| **Add Planted Plant Record** | Protected | `POST /api/v1/planted-plants` | Header `X-NGO-Admin-Password` |
| **Edit Planted Plant Record** | Protected | `PUT/PATCH /api/v1/planted-plants/{id}` | Header `X-NGO-Admin-Password` |
| **Delete Planted Plant Record** | Protected | `DELETE /api/v1/planted-plants/{id}` | Header `X-NGO-Admin-Password` |
| **Log Condition Monitoring Visit** | Protected | `POST /api/v1/planted-plants/{id}/monitoring` | Header `X-NGO-Admin-Password` |
| **Human AI Species Verification** | Protected | `POST /api/v1/observations/{id}/verify` | Header `X-NGO-Admin-Password` |
| **Delete NGO Sighting Record** | Protected | `DELETE /api/v1/observations/{id}` | Header `X-NGO-Admin-Password` |
| **Edit / Delete iNaturalist Record** | **FORBIDDEN** | `PUT/PATCH/DELETE /api/v1/observations/{id}` | **Permanently Blocked (HTTP 403)** |

---

## 3. Password Security & Backend Architecture

### Environment Configuration
- The administrative password is stored server-side via the environment variable `NGO_ADMIN_PASSWORD`.
- Default development fallback in `backend/app/core/config.py`: `rswf-admin-pass`.
- `.env.example` updated with `NGO_ADMIN_PASSWORD=rswf-admin-pass` (never commit production secrets).

### Security Implementation (`backend/app/core/security.py`)
```python
def verify_ngo_admin_password(
    x_ngo_admin_password: str = Header(None, alias="X-NGO-Admin-Password")
) -> str:
    if not x_ngo_admin_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="NGO administrative password is required for editing or deleting records."
        )
    if x_ngo_admin_password != settings.NGO_ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid NGO administrative password."
        )
    return x_ngo_admin_password
```

### Password Protection Best Practices
- **No Plaintext Storage in Frontend:** The password is NOT hard-coded into JavaScript or HTML.
- **No Password Exposure in APIs:** Endpoints never return or log the password.
- **Session Cache Handling:** Frontend caches the password in memory (`sessionStorage`) upon user authorization, attaching `X-NGO-Admin-Password` to protected API requests. Invalid passwords clear the cached session.

---

## 4. Frontend User Experience

- **Public View Mode:** Users can browse maps, search species, view observations, upload photos, and download reports without seeing any authentication dialogs.
- **Protected Actions Modal (`#ngo-auth-modal`):** When an RSWF user clicks a protected action (e.g., `+ Add Planted Plant`, `Edit`, `Delete`, `+ Visit`, or `Confirm AI Species`), the system prompts for the **RSWF NGO Administrative Password** if not already cached for the current session.
- **Header Status Badge:** Top header displays `🔓 Public View Mode` or `🔒 RSWF Admin Active (Click to Lock)` with a one-click session lock option.

---

## 5. Verification & Test Results

- **Pytest Authentication Suite (`backend/tests/test_authentication.py`):** `11/11 PASSED`.
- **Full Pytest Suite:** `113/113 PASSED` across all 9 test modules.
- **Phase 15 Validation Script (`scripts/validate_phase15.py`):** `10/10 CHECKS SUCCESSFUL`.
- **Full Regression Pipeline (`validate_phase5.py` to `validate_phase15.py`):** `ALL 11 VALIDATION SUITES PASSED`.

---

## 6. Baseline Real Data Integrity Audit

- **iNaturalist Observations:** `227` (Spatially verified reference dataset intact)
- **NGO / New Upload Observations:** `0` (Synthetic test records purged)
- **RSWF Planted Plants:** `3` (`PL-001`, `PL-002`, `PL-003`)
- **Active Working Zones:** `3` (`ZONE A`, `ZONE B`, `ZONE C`)
