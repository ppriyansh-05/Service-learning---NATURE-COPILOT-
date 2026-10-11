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

def create_test_jpeg_with_gps(lat: float, lng: float, filename="test_exif.jpg", img: Image.Image = None, quality: int = 75) -> bytes:
    """
    Helper creating an in-memory JPEG image with custom EXIF GPS metadata.
    Each call uses a new random image (unless one is passed) so separate tests never upload the same photo.
    """
    if img is None:
        img = Image.frombytes("RGB", (100, 100), os.urandom(100 * 100 * 3))
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
    img.save(buf, format="JPEG", exif=exif, quality=quality)
    return buf.getvalue()

def create_test_geotag_jpeg(text: str = "Lat 18.518511 Long 73.780200") -> bytes:
    """Helper creating a WhatsApp-style JPEG (no EXIF) with a visible GPS geotag overlay and a unique background."""
    from PIL import ImageDraw, ImageFont
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 32)
    img = Image.new("RGB", (800, 200), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    noise = os.urandom(40)
    for i, b in enumerate(noise):
        d.rectangle([i * 20, 160, i * 20 + 19, 199], fill=(b, 255 - b, b // 2))
    d.text((30, 60), text, font=font, fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
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
    # Offset ~3 m from test 1 so the new 1-metre same-plant guard treats this as a different plant.
    img_bytes = create_test_jpeg_with_gps(18.5184636, 73.7802123)
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
    # Different spot in Zone A so this isn't rejected as "same plant" as earlier tests.
    img_bytes = create_test_jpeg_with_gps(18.5184886, 73.7802123)
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
    geotag_bytes = create_test_geotag_jpeg()

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


# =====================================================================
# Duplicate Photo Upload Protection
# =====================================================================

def _ngo_store_count() -> int:
    import json
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    store_path = os.path.join(base_dir, "data", "processed", "ngo_observations_store.json")
    if not os.path.exists(store_path):
        return 0
    with open(store_path, "r", encoding="utf-8") as f:
        return len(json.load(f))

def _structured_test_image() -> Image.Image:
    """A photo-like image (gradient + shapes) whose perceptual hash survives JPEG recompression."""
    from PIL import ImageDraw
    img = Image.new("RGB", (400, 300))
    d = ImageDraw.Draw(img)
    for x in range(400):
        d.line([(x, 0), (x, 299)], fill=(x * 255 // 400, 120, 255 - x * 255 // 400))
    d.ellipse([60, 50, 200, 190], fill=(20, 160, 40))
    d.rectangle([250, 120, 360, 260], fill=(90, 60, 30))
    return img

# 14. Same photo uploaded twice -> second upload rejected, points to existing observation
def test_duplicate_exif_upload_rejected():
    # Offset to a fresh spot (3 m north of zone-B test) so this independent test owns its coords.
    img_bytes = create_test_jpeg_with_gps(18.5187971, 73.7800814)
    files = {"file": ("dup_plant.jpg", img_bytes, "image/jpeg")}
    first = client.post("/api/v1/observations/upload", files=files)
    assert first.status_code == 201
    first_id = first.json()["observation_id"]
    count_after_first = _ngo_store_count()

    files = {"file": ("dup_plant_again.jpg", img_bytes, "image/jpeg")}
    second = client.post("/api/v1/observations/upload", files=files)
    assert second.status_code == 409
    detail = second.json()["detail"]
    assert detail["duplicate"] is True
    assert detail["existing_observation_id"] == first_id
    assert detail["photo_url"] == first.json()["photo_url"]
    assert _ngo_store_count() == count_after_first

# 15. Same image re-compressed (e.g. forwarded again on WhatsApp) at the same spot -> rejected
def test_recompressed_duplicate_upload_rejected():
    # Offset so this test gets its own virgin spot.
    img = _structured_test_image()
    original = create_test_jpeg_with_gps(18.5190494, 73.7798533, img=img, quality=92)
    recompressed = create_test_jpeg_with_gps(18.5190494, 73.7798533, img=img, quality=55)
    assert original != recompressed

    first = client.post("/api/v1/observations/upload", files={"file": ("orig.jpg", original, "image/jpeg")})
    assert first.status_code == 201
    second = client.post("/api/v1/observations/upload", files={"file": ("fwd.jpg", recompressed, "image/jpeg")})
    assert second.status_code == 409
    assert second.json()["detail"]["existing_observation_id"] == first.json()["observation_id"]

# 16. Two different photos at the same spot are now treated as the same plant by default,
#     but the uploader can override with allow_nearby_duplicate=true.
def test_same_spot_treated_as_same_plant_but_overridable():
    # Fresh spot, outside the active zones.
    lat, lng = 18.5194321, 73.7791570
    first = client.post(
        "/api/v1/observations/upload",
        files={"file": ("a.jpg", create_test_jpeg_with_gps(lat, lng), "image/jpeg")},
    )
    assert first.status_code == 201
    first_id = first.json()["observation_id"]

    # Default behaviour: a second photo within 1 m is rejected as the same plant.
    second = client.post(
        "/api/v1/observations/upload",
        files={"file": ("b.jpg", create_test_jpeg_with_gps(lat, lng), "image/jpeg")},
    )
    assert second.status_code == 409
    detail = second.json()["detail"]
    assert detail["duplicate_kind"] == "nearby"
    assert detail["overridable"] is True
    assert detail["existing_observation_id"] == first_id

    # Override: pass allow_nearby_duplicate=true and the backend records it as a new plant.
    third = client.post(
        "/api/v1/observations/upload?allow_nearby_duplicate=true",
        files={"file": ("c.jpg", create_test_jpeg_with_gps(lat, lng), "image/jpeg")},
    )
    assert third.status_code == 201
    assert third.json()["observation_id"] != first_id

# 17. Geotag photo: re-upload after confirmation and double confirmation are both rejected
def test_duplicate_geotag_upload_and_confirm_rejected():
    # Fresh coord well away from other test spots so the 1-metre same-plant guard isn't triggered
    # by an earlier test having already recorded a plant here.
    geotag_bytes = create_test_geotag_jpeg("Lat 18.518850 Long 73.779950")
    res = client.post("/api/v1/observations/upload", files={"file": ("wa.jpg", geotag_bytes, "image/jpeg")})
    assert res.status_code == 200
    data = res.json()
    payload = {"photo_url": data["photo_url"], "latitude": data["latitude"], "longitude": data["longitude"]}

    confirmed = client.post("/api/v1/observations/confirm-location", json=payload)
    assert confirmed.status_code == 201
    obs_id = confirmed.json()["observation_id"]
    count_after_confirm = _ngo_store_count()

    # Double confirmation of the same staged photo
    again = client.post("/api/v1/observations/confirm-location", json=payload)
    assert again.status_code == 409
    assert again.json()["detail"]["existing_observation_id"] == obs_id

    # Uploading the same file again after it was saved
    re_upload = client.post("/api/v1/observations/upload", files={"file": ("wa_copy.jpg", geotag_bytes, "image/jpeg")})
    assert re_upload.status_code == 409
    assert re_upload.json()["detail"]["existing_observation_id"] == obs_id
    assert _ngo_store_count() == count_after_confirm

# 18. Re-uploading the same photo never writes a second copy to disk
def test_same_photo_stored_once_on_disk():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    uploads_dir = os.path.join(base_dir, "data", "uploads")
    img_bytes = create_test_jpeg_no_gps()
    before = set(os.listdir(uploads_dir)) if os.path.isdir(uploads_dir) else set()
    for _ in range(3):
        client.post("/api/v1/observations/upload", files={"file": ("nogps.jpg", img_bytes, "image/jpeg")})
    new_files = set(os.listdir(uploads_dir)) - before
    assert len(new_files) <= 1

# =====================================================================
# Placeholder EXIF GPS (GPS Map Camera without a fix) & Small Overlay Text
# =====================================================================

def create_gpsmap_camera_style_jpeg(overlay_text: str, size=(2448, 3264)) -> bytes:
    """
    Full-resolution photo like GPS Map Camera saves without a GPS fix: EXIF GPS tags present but empty
    ('\x00' refs, 0/0 rationals), with the real coordinates only printed in a small bottom overlay.
    """
    from PIL import ImageDraw, ImageFont
    from PIL.TiffImagePlugin import IFDRational
    img = Image.frombytes("RGB", (size[0] // 8, size[1] // 8), os.urandom((size[0] // 8) * (size[1] // 8) * 3)).resize(size)
    d = ImageDraw.Draw(img)
    d.rectangle([380, size[1] - 330, size[0] - 60, size[1] - 40], fill=(60, 50, 45))
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 44)
    d.text((410, size[1] - 300), "Pune, Maharashtra, India", font=font, fill=(255, 255, 255))
    d.text((410, size[1] - 200), overlay_text, font=font, fill=(255, 255, 255))
    exif = img.getexif()
    zero = IFDRational(0, 0)
    exif[34853] = {1: "\x00", 2: (zero, zero, zero), 3: "\x00", 4: (zero, zero, zero)}
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif, quality=90)
    return buf.getvalue()

# 19. Empty placeholder EXIF GPS is not read as (0, 0)
def test_placeholder_exif_gps_rejected():
    from app.services.exif_service import extract_exif_gps
    img_bytes = create_gpsmap_camera_style_jpeg("Lat 18.51871 Long 73.780211")
    temp_path = os.path.abspath("temp_placeholder_gps.jpg")
    with open(temp_path, "wb") as f:
        f.write(img_bytes)
    try:
        lat, lng, _, err = extract_exif_gps(temp_path)
    finally:
        os.remove(temp_path)
    assert lat is None and lng is None
    assert "placeholder" in err.lower()

# 20. Placeholder EXIF GPS falls back to the visible overlay, even when its text is small on a large photo
def test_placeholder_exif_gps_falls_back_to_overlay():
    img_bytes = create_gpsmap_camera_style_jpeg("Lat 18.51871 Long 73.780211")
    res = client.post("/api/v1/observations/upload", files={"file": ("20260628_94140AMByGPSMapCamera.jpg", img_bytes, "image/jpeg")})
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["gps_source"] == "IMAGE_GEOTAG"
    assert data["requires_confirmation"] is True
    assert data["latitude"] == 18.51871
    assert data["longitude"] == 73.780211
    assert data["zone"] == "ZONE A"

# 21. OCR voting: a single misread pass (5 read as 9) is outvoted by passes that agree
def test_geotag_ocr_majority_vote_rejects_misread(tmp_path):
    from unittest.mock import patch
    from app.services import exif_service
    path = tmp_path / "wa.jpg"
    Image.new("RGB", (600, 800), "green").save(path, "JPEG")
    readings = iter([
        "Lat 18.918685 Long 73.780256",   # misread
        "Lat 18.518685 Long 73.780256",
        "Lat 18.518685 Long 73.780256",
    ])
    with patch.object(exif_service, "_ocr_image", side_effect=lambda img: next(readings, "")):
        lat, lng, _ = exif_service.extract_visible_image_geotag(str(path))
    assert (lat, lng) == (18.518685, 73.780256)
