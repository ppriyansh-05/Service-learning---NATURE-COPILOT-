"""
Validation Suite for Robust GPS / Geotag Photo Workflow.
Verifies all 14 required cases:
1. Photo with valid EXIF GPS -> EXIF GPS used
2. Photo with EXIF GPS -> Image geotag detection is not unnecessarily used
3. Photo with no EXIF but valid visible GPS overlay -> Image geotag detected
4. Image geotag detected -> Coordinates shown to user
5. Image geotag detected -> User confirmation required
6. Photo with neither EXIF nor visible geotag -> "Location not available"
7. No GPS -> No fabricated coordinates
8. No GPS -> No automatic zone assignment
9. Valid GPS inside Van Udyan -> Boundary validation succeeds
10. Valid GPS inside Zone A/B/C -> Correct zone assigned
11. Valid GPS outside Van Udyan -> Rejected as outside project boundary
12. Valid location -> Pl@ntNet workflow continues
13. iNaturalist records remain untouched
14. Existing authentication tests continue passing
"""

import sys
import os
import io
import json
from PIL import Image, ImageDraw, ImageFont
from fractions import Fraction

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.services.exif_service import extract_photo_location, parse_gps_from_text
from app.services.data_service import save_ngo_observations_store

client = TestClient(app)
VALID_HEADER = {"X-NGO-Admin-Password": "rswf-admin-pass"}

def create_exif_jpeg(lat: float, lng: float) -> bytes:
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

    gps_ifd = {
        1: lat_ref,
        2: dec_to_dms(lat),
        3: lng_ref,
        4: dec_to_dms(lng)
    }
    exif[34853] = gps_ifd

    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    return buf.getvalue()

def create_visible_geotag_jpeg(text: str) -> bytes:
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 32)
    img = Image.new("RGB", (800, 200), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((30, 60), text, font=font, fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

def create_blank_jpeg() -> bytes:
    img = Image.new("RGB", (100, 100), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

def run_gps_workflow_validation():
    print("=" * 75)
    print("       ROBUST GPS / GEOTAG PHOTO WORKFLOW VALIDATION SUITE")
    print("=" * 75)

    passed_checks = 0
    total_checks = 14

    # Save initial state
    save_ngo_observations_store([])

    # 1. Photo with valid EXIF GPS -> EXIF GPS used
    exif_bytes = create_exif_jpeg(18.5184386, 73.7802123)
    res1 = client.post("/api/v1/observations/upload", files={"file": ("exif_test.jpg", exif_bytes, "image/jpeg")})
    d1 = res1.json()
    if res1.status_code == 201 and d1.get("gps_source") == "EXIF":
        print("[PASS] Check 1: Photo with valid EXIF GPS uses EXIF GPS directly")
        passed_checks += 1
    else:
        print(f"[FAIL] Check 1: {res1.status_code}, {d1}")

    # 2. Photo with EXIF GPS -> Image geotag detection is not unnecessarily used (OCR bypassed)
    temp_exif_path = os.path.abspath("temp_val_exif.jpg")
    with open(temp_exif_path, "wb") as f:
        f.write(exif_bytes)
    loc_exif = extract_photo_location(temp_exif_path)
    if os.path.exists(temp_exif_path):
        os.remove(temp_exif_path)
    if loc_exif["gps_source"] == "EXIF" and loc_exif["ocr_used"] is False:
        print("[PASS] Check 2: Image geotag detection (OCR) is bypassed when EXIF GPS is present")
        passed_checks += 1
    else:
        print(f"[FAIL] Check 2: OCR was not bypassed: {loc_exif}")

    # 3. Photo with no EXIF but valid visible GPS overlay -> Image geotag detected
    geotag_bytes = create_visible_geotag_jpeg("Lat 18.518511 Long 73.780200")
    res3 = client.post("/api/v1/observations/upload", files={"file": ("geotag_cam.jpg", geotag_bytes, "image/jpeg")})
    d3 = res3.json()
    if res3.status_code == 200 and d3.get("gps_source") == "IMAGE_GEOTAG":
        print("[PASS] Check 3: Photo with no EXIF but visible GPS overlay detected as IMAGE_GEOTAG")
        passed_checks += 1
    else:
        print(f"[FAIL] Check 3: {res3.status_code}, {d3}")

    # 4. Image geotag detected -> Coordinates shown to user
    if d3.get("latitude") is not None and d3.get("longitude") is not None:
        print(f"[PASS] Check 4: Detected coordinates returned ({d3['latitude']}, {d3['longitude']})")
        passed_checks += 1
    else:
        print(f"[FAIL] Check 4: Coordinates not in response: {d3}")

    # 5. Image geotag detected -> User confirmation required
    if d3.get("requires_confirmation") is True and d3.get("observation_id") is None:
        print("[PASS] Check 5: Image geotag coordinates require user confirmation (not silently trusted)")
        passed_checks += 1
    else:
        print(f"[FAIL] Check 5: Confirmation flag missing or observation saved prematurely: {d3}")

    # 6. Photo with neither EXIF nor visible geotag -> "Location not available"
    blank_bytes = create_blank_jpeg()
    res6 = client.post("/api/v1/observations/upload", files={"file": ("blank.jpg", blank_bytes, "image/jpeg")})
    d6 = res6.json()
    if res6.status_code == 400 and "location not available" in d6.get("detail", "").lower():
        print("[PASS] Check 6: Photo with neither EXIF nor visible geotag returns 'Location not available'")
        passed_checks += 1
    else:
        print(f"[FAIL] Check 6: {res6.status_code}, {d6}")

    # 7. No GPS -> No fabricated coordinates
    temp_blank_path = os.path.abspath("temp_val_blank.jpg")
    with open(temp_blank_path, "wb") as f:
        f.write(blank_bytes)
    loc_blank = extract_photo_location(temp_blank_path)
    if os.path.exists(temp_blank_path):
        os.remove(temp_blank_path)
    if loc_blank["gps_available"] is False and loc_blank["latitude"] is None and loc_blank["longitude"] is None:
        print("[PASS] Check 7: No GPS produces latitude=None, longitude=None (zero fabrication)")
        passed_checks += 1
    else:
        print(f"[FAIL] Check 7: Coordinates fabricated: {loc_blank}")

    # 8. No GPS -> No automatic zone assignment
    res_insp = client.post("/api/v1/observations/inspect-photo", files={"file": ("blank.jpg", blank_bytes, "image/jpeg")})
    d_insp = res_insp.json()
    if d_insp.get("gps_available") is False and d_insp.get("zone") is None:
        print("[PASS] Check 8: No GPS does not assign any active zone")
        passed_checks += 1
    else:
        print(f"[FAIL] Check 8: Zone assigned without GPS: {d_insp}")

    # 9. Valid GPS inside Van Udyan -> Boundary validation succeeds
    # Confirm location for geotag photo from check 3
    res9 = client.post("/api/v1/observations/confirm-location", json={
        "photo_url": d3["photo_url"],
        "latitude": d3["latitude"],
        "longitude": d3["longitude"]
    })
    d9 = res9.json()
    if res9.status_code == 201 and d9.get("status") == "spatially_verified":
        print("[PASS] Check 9: Valid GPS inside Van Udyan boundary validation succeeds")
        passed_checks += 1
    else:
        print(f"[FAIL] Check 9: {res9.status_code}, {d9}")

    # 10. Valid GPS inside Zone A/B/C -> Correct zone assigned
    if d9.get("zone") == "ZONE A":
        print("[PASS] Check 10: Valid coordinates inside Zone A assign 'ZONE A'")
        passed_checks += 1
    else:
        print(f"[FAIL] Check 10: Incorrect zone assigned: {d9.get('zone')}")

    # 11. Valid GPS outside Van Udyan -> Rejected as outside project boundary
    mumbai_exif = create_exif_jpeg(19.0760, 72.8777)
    res11 = client.post("/api/v1/observations/upload", files={"file": ("mumbai.jpg", mumbai_exif, "image/jpeg")})
    if res11.status_code == 400 and "outside" in res11.json().get("detail", "").lower():
        print("[PASS] Check 11: Valid GPS outside Van Udyan rejected as outside project boundary")
        passed_checks += 1
    else:
        print(f"[FAIL] Check 11: Outside GPS not rejected: {res11.status_code}")

    # 12. Valid location -> Pl@ntNet workflow continues
    obs_id = d9.get("observation_id")
    if obs_id:
        res12 = client.post(f"/api/v1/observations/{obs_id}/identify?organ=leaf")
        if res12.status_code == 200:
            print("[PASS] Check 12: Valid location allows Pl@ntNet AI workflow to continue")
            passed_checks += 1
        else:
            print(f"[FAIL] Check 12: Pl@ntNet workflow failed: {res12.status_code}")
    else:
        print("[FAIL] Check 12: Missing observation_id for Pl@ntNet test")

    # 13. iNaturalist records remain untouched
    res_del_inat = client.delete("/api/v1/observations/1", headers=VALID_HEADER)
    if res_del_inat.status_code == 403 and "read-only" in res_del_inat.json().get("detail", "").lower():
        print("[PASS] Check 13: iNaturalist reference records remain untouched & read-only (HTTP 403)")
        passed_checks += 1
    else:
        print(f"[FAIL] Check 13: iNaturalist read-only check failed: {res_del_inat.status_code}")

    # 14. Existing authentication tests continue passing
    res_no_auth = client.post("/api/v1/planted-plants", json={
        "plant_code": "PL-VAL", "status": "Alive", "latitude": 18.5195, "longitude": 73.7800
    })
    if res_no_auth.status_code == 401:
        print("[PASS] Check 14: Mutation password authentication remains enforced (HTTP 401)")
        passed_checks += 1
    else:
        print(f"[FAIL] Check 14: Auth check failed: {res_no_auth.status_code}")

    # Clean up test observations created during validation
    save_ngo_observations_store([])

    print("-" * 75)
    print(f"GPS / GEOTAG WORKFLOW AUDIT: {'PASSED — ' + str(passed_checks) + '/' + str(total_checks) + ' CHECKS SUCCESSFUL' if passed_checks == total_checks else 'FAILED'}")
    print("=" * 75)
    return passed_checks == total_checks

if __name__ == "__main__":
    success = run_gps_workflow_validation()
    sys.exit(0 if success else 1)
