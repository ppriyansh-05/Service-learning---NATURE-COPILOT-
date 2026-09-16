"""
Phase 9 Photo Upload & EXIF GPS Pytest Suite
Tests photo upload validation, EXIF GPS extraction, coordinate conversion, WGS84 boundary geofencing,
zone assignment, missing GPS error handling, file size limits, MIME type validation, safe filename generation,
and provenance preservation.
"""

import sys
import os
import io
import pytest
from PIL import Image
from fractions import Fraction

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.services.exif_service import generate_safe_filename, dms_to_decimal

client = TestClient(app)

@pytest.fixture(autouse=True, scope="module")
def cleanup_after_upload_tests():
    yield
    import json, glob
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    store_path = os.path.join(base_dir, "data", "processed", "ngo_observations_store.json")
    uploads_dir = os.path.join(base_dir, "data", "uploads")

    if os.path.exists(store_path):
        with open(store_path, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)

    if os.path.exists(uploads_dir):
        for file_path in glob.glob(os.path.join(uploads_dir, "upload_*")):
            try:
                os.remove(file_path)
            except Exception:
                pass

def create_test_jpeg_with_gps(lat: float, lng: float, filename="test_exif.jpg") -> bytes:
    """Helper creating an in-memory JPEG image with custom EXIF GPS metadata."""
    img = Image.new("RGB", (100, 100), color="green")
    exif = img.getexif()

    def dec_to_dms(deg_float):
        deg = int(abs(deg_float))
        rem = (abs(deg_float) - deg) * 60.0
        minute = int(rem)
        sec = round((rem - minute) * 60.0, 4)
        return (Fraction(deg, 1), Fraction(minute, 1), Fraction(int(sec * 1000), 1000))

    lat_ref = "N" if lat >= 0 else "S"
    lng_ref = "E" if lng >= 0 else "W"

    lat_dms = dec_to_dms(lat)
    lng_dms = dec_to_dms(lng)

    gps_ifd = {
        1: lat_ref,
        2: lat_dms,
        3: lng_ref,
        4: lng_dms
    }
    exif[34853] = gps_ifd

    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    return buf.getvalue()

def create_test_jpeg_no_gps() -> bytes:
    """Helper creating an in-memory JPEG image without EXIF metadata."""
    img = Image.new("RGB", (100, 100), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

# 1. Valid image with GPS inside Van Udyan
def test_upload_valid_gps_inside_van_udyan():
    img_bytes = create_test_jpeg_with_gps(18.5184386, 73.7802123)
    files = {"file": ("plant.jpg", img_bytes, "image/jpeg")}
    response = client.post("/api/v1/observations/upload", files=files)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["gps_available"] is True
    assert data["source"] == "NGO / New Upload"
    assert "observation_id" in data

# 2. Valid image with GPS inside Zone A
def test_upload_gps_inside_zone_a():
    img_bytes = create_test_jpeg_with_gps(18.5184386, 73.7802123)
    files = {"file": ("zone_a_plant.jpg", img_bytes, "image/jpeg")}
    response = client.post("/api/v1/observations/upload", files=files)
    assert response.status_code == 201
    data = response.json()
    assert data["zone"] == "ZONE A"

# 3. Valid image with GPS inside Zone B
def test_upload_gps_inside_zone_b():
    img_bytes = create_test_jpeg_with_gps(18.5187710, 73.7800814)
    files = {"file": ("zone_b_plant.jpg", img_bytes, "image/jpeg")}
    response = client.post("/api/v1/observations/upload", files=files)
    assert response.status_code == 201
    data = response.json()
    assert data["zone"] == "ZONE B"

# 4. Valid image with GPS inside Zone C
def test_upload_gps_inside_zone_c():
    img_bytes = create_test_jpeg_with_gps(18.5190233, 73.7798533)
    files = {"file": ("zone_c_plant.jpg", img_bytes, "image/jpeg")}
    response = client.post("/api/v1/observations/upload", files=files)
    assert response.status_code == 201
    data = response.json()
    assert data["zone"] == "ZONE C"

# 5. Valid image inside Van Udyan but outside active zones
def test_upload_gps_outside_active_zones():
    img_bytes = create_test_jpeg_with_gps(18.5194060, 73.7791570)
    files = {"file": ("outside_zone.jpg", img_bytes, "image/jpeg")}
    response = client.post("/api/v1/observations/upload", files=files)
    assert response.status_code == 201
    data = response.json()
    assert data["zone_status"] == "OUTSIDE_ACTIVE_ZONES"

# 6. Image with no GPS
def test_upload_image_no_gps():
    img_bytes = create_test_jpeg_no_gps()
    files = {"file": ("no_gps.jpg", img_bytes, "image/jpeg")}
    response = client.post("/api/v1/observations/upload", files=files)
    assert response.status_code == 400
    assert "exif" in response.json()["detail"].lower()

# 7. GPS outside Van Udyan (Mumbai coordinates)
def test_upload_gps_outside_van_udyan():
    img_bytes = create_test_jpeg_with_gps(19.0760, 72.8777) # Mumbai coordinates!
    files = {"file": ("mumbai_plant.jpg", img_bytes, "image/jpeg")}
    response = client.post("/api/v1/observations/upload", files=files)
    assert response.status_code == 400
    assert "outside" in response.json()["detail"].lower()

# 8. Unsupported file type
def test_upload_unsupported_file_type():
    files = {"file": ("document.pdf", b"%PDF-1.4 test document content", "application/pdf")}
    response = client.post("/api/v1/observations/upload", files=files)
    assert response.status_code == 415

# 9. Oversized file (>10MB)
def test_upload_oversized_file():
    big_bytes = b"0" * (11 * 1024 * 1024)
    files = {"file": ("large.jpg", big_bytes, "image/jpeg")}
    response = client.post("/api/v1/observations/upload", files=files)
    assert response.status_code == 413

# 10. Safe filename generation & path traversal prevention
def test_safe_filename_generation():
    unsafe = "../../../etc/passwd.jpg"
    safe = generate_safe_filename(unsafe)
    assert ".." not in safe
    assert "/" not in safe
    assert "\\" not in safe
    assert safe.startswith("upload_")
    assert safe.endswith(".jpg")

# 11. Provenance preservation check
def test_upload_provenance():
    img_bytes = create_test_jpeg_with_gps(18.5184386, 73.7802123)
    files = {"file": ("provenance_test.jpg", img_bytes, "image/jpeg")}
    response = client.post("/api/v1/observations/upload", files=files)
    assert response.status_code == 201
    data = response.json()
    assert data["source"] == "NGO / New Upload"

    # Verify original iNaturalist observations remain intact
    obs1 = client.get("/api/v1/observations/1").json()
    assert obs1["source"] == "iNaturalist"

# 12. Visible Image Geotag Detection & Confirmation Workflow
def test_upload_visible_image_geotag_workflow():
    from PIL import ImageDraw, ImageFont
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 32)
    img = Image.new("RGB", (800, 200), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((30, 60), "Lat 18.518511 Long 73.780200", font=font, fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    geotag_bytes = buf.getvalue()

    # Step 1: Upload photo without confirmation -> returns 200, requires_confirmation=True
    files = {"file": ("whatsapp_photo.jpg", geotag_bytes, "image/jpeg")}
    res = client.post("/api/v1/observations/upload", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["gps_source"] == "IMAGE_GEOTAG"
    assert data["requires_confirmation"] is True
    assert data["observation_id"] is None
    assert data["latitude"] == 18.518511
    assert data["longitude"] == 73.7802

    # Step 2: User confirms location -> returns 201, creates observation
    c_res = client.post("/api/v1/observations/confirm-location", json={
        "photo_url": data["photo_url"],
        "latitude": data["latitude"],
        "longitude": data["longitude"]
    })
    assert c_res.status_code == 201
    c_data = c_res.json()
    assert c_data["observation_id"] is not None
    assert c_data["status"] == "spatially_verified"
    assert c_data["zone"] == "ZONE A"

# 13. EXIF GPS priority over visible geotag
def test_exif_gps_bypasses_image_geotag():
    from app.services.exif_service import extract_photo_location
    img_bytes = create_test_jpeg_with_gps(18.5184386, 73.7802123)
    temp_path = os.path.abspath("temp_exif_prio.jpg")
    with open(temp_path, "wb") as f:
        f.write(img_bytes)
    loc = extract_photo_location(temp_path)
    if os.path.exists(temp_path):
        os.remove(temp_path)
    assert loc["gps_source"] == "EXIF"
    assert loc["ocr_used"] is False
    assert loc["requires_confirmation"] is False

