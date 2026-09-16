"""
Automated Phase 9 Validation Suite Script
Verifies Photo Upload & EXIF GPS extraction pipeline, WGS84 Van Udyan boundary geofencing,
active zone allocation, error handling (missing EXIF, outside boundary, oversized files),
data provenance protection, and dashboard UI controls.
"""

import os
import sys
import io
import json
from PIL import Image
from fractions import Fraction

# Ensure backend root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app

def create_test_jpeg(lat=None, lng=None) -> bytes:
    img = Image.new("RGB", (100, 100), color="green")
    exif = img.getexif()

    if lat is not None and lng is not None:
        def dec_to_dms(deg_float):
            deg = int(abs(deg_float))
            rem = (abs(deg_float) - deg) * 60.0
            minute = int(rem)
            sec = round((rem - minute) * 60.0, 4)
            return (Fraction(deg, 1), Fraction(minute, 1), Fraction(int(sec * 1000), 1000))

        gps_ifd = {
            1: "N" if lat >= 0 else "S",
            2: dec_to_dms(lat),
            3: "E" if lng >= 0 else "W",
            4: dec_to_dms(lng)
        }
        exif[34853] = gps_ifd

    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    return buf.getvalue()

def validate_phase9():
    print("=" * 70)
    print("    PHASE 9 VALIDATION SUITE — PHOTO UPLOAD & EXIF GPS EXTRACTION")
    print("=" * 70)

    results = []

    def log(test_name, passed, details=""):
        status = "[PASS]" if passed else "[FAIL]"
        results.append((test_name, passed, details))
        print(f"{status} {test_name}")
        if details:
            print(f"       Details: {details}")

    # 1. Core Structure & Files Check
    files_to_check = [
        os.path.join("backend", "app", "services", "exif_service.py"),
        os.path.join("backend", "tests", "test_upload.py"),
        os.path.join("docs", "phase_9_photo_upload.md"),
        os.path.join("data", "uploads"),
        os.path.join("frontend", "index.html"),
        os.path.join("frontend", "js", "api.js"),
        os.path.join("frontend", "js", "app.js")
    ]
    files_ok = all(os.path.exists(f) for f in files_to_check)
    log("Phase 9 Core Architecture & Storage Structure", files_ok, ", ".join(files_to_check))

    client = TestClient(app)

    # 2. Valid Photo Upload with EXIF GPS inside Van Udyan
    valid_bytes = create_test_jpeg(18.5184386, 73.7802123)
    r_valid = client.post("/api/v1/observations/upload", files={"file": ("test_plant.jpg", valid_bytes, "image/jpeg")})
    upload_ok = (
        r_valid.status_code == 201 and
        r_valid.json().get("success") is True and
        r_valid.json().get("source") == "NGO / New Upload" and
        r_valid.json().get("zone") == "ZONE A"
    )
    log("POST /api/v1/observations/upload (Valid Photo with EXIF GPS)", upload_ok, f"Returned Observation ID: #{r_valid.json().get('observation_id')}")

    # 3. Missing EXIF GPS Handling
    no_gps_bytes = create_test_jpeg(None, None)
    r_nogps = client.post("/api/v1/observations/upload", files={"file": ("no_gps.jpg", no_gps_bytes, "image/jpeg")})
    nogps_ok = r_nogps.status_code == 400 and "exif" in r_nogps.json().get("detail", "").lower()
    log("EXIF GPS Missing Error Handling (HTTP 400)", nogps_ok, f"Detail: {r_nogps.json().get('detail')}")

    # 4. GPS Outside Van Udyan Boundary Handling
    outside_bytes = create_test_jpeg(19.0760, 72.8777)
    r_outside = client.post("/api/v1/observations/upload", files={"file": ("mumbai.jpg", outside_bytes, "image/jpeg")})
    outside_ok = r_outside.status_code == 400 and "outside" in r_outside.json().get("detail", "").lower()
    log("Geofence Location Validation Outside Boundary (HTTP 400)", outside_ok, f"Detail: {r_outside.json().get('detail')}")

    # 5. Unsupported Media Type Rejection
    r_unsupported = client.post("/api/v1/observations/upload", files={"file": ("test.pdf", b"%PDF content", "application/pdf")})
    unsupported_ok = r_unsupported.status_code == 415
    log("Unsupported File Type Rejection (HTTP 415)", unsupported_ok)

    # 6. Oversized File Rejection
    big_bytes = b"0" * (11 * 1024 * 1024)
    r_big = client.post("/api/v1/observations/upload", files={"file": ("big.jpg", big_bytes, "image/jpeg")})
    big_ok = r_big.status_code == 413
    log("Oversized File Rejection (>10MB HTTP 413)", big_ok)

    # 7. Data Provenance & iNaturalist Preservation
    r_obs1 = client.get("/api/v1/observations/1")
    prov_ok = r_obs1.status_code == 200 and r_obs1.json().get("source") == "iNaturalist"
    log("Data Provenance Protection (Original iNaturalist Records Unchanged)", prov_ok)

    # 8. Dashboard UI Controls Check
    with open(os.path.join("frontend", "index.html"), "r", encoding="utf-8") as f:
        html_text = f.read()
    ui_ok = "upload-photo-modal" in html_text and "upload-photo-file" in html_text and "openUploadPhotoModal" in html_text
    log("Dashboard Photo Upload UI Controls Defined", ui_ok)

    print("-" * 70)
    all_passed = all(item[1] for item in results)
    status_str = "PASSED — ALL PHASE 9 CHECKS SUCCESSFUL" if all_passed else "FAILED — ACTION REQUIRED"
    print(f"OVERALL STATUS: {status_str}")
    print("=" * 70)

    return all_passed

if __name__ == "__main__":
    success = validate_phase9()
    sys.exit(0 if success else 1)
