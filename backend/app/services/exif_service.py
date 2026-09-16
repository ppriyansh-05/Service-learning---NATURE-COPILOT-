"""
EXIF Metadata Extraction Service Module
Provides EXIF GPS extraction, coordinate conversion to WGS84 decimal degrees,
timestamp parsing, and file upload safety validation for plant biodiversity photographs.
"""

import os
import uuid
import re
from typing import Tuple, Optional, Dict, Any
from PIL import Image, ExifTags

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB limit

def validate_upload_file(filename: str, content_type: str, file_size: int):
    """Validates file extension, MIME type, and maximum file size."""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS or content_type.lower() not in ALLOWED_MIME_TYPES:
        raise ValueError(
            f"Unsupported file type '{ext}' ({content_type}). Allowed formats: JPG, JPEG, PNG, WEBP."
        )

    if file_size > MAX_FILE_SIZE:
        raise ValueError(
            f"File size ({file_size / (1024*1024):.2f} MB) exceeds maximum allowed limit of 10 MB."
        )

def generate_safe_filename(original_filename: str) -> str:
    """Generates a unique, path-traversal safe filename."""
    ext = os.path.splitext(original_filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        ext = ".jpg"
    safe_name = f"upload_{uuid.uuid4().hex}{ext}"
    return safe_name

def dms_to_decimal(dms_tuple, ref_str: str) -> float:
    """Converts degrees/minutes/seconds tuple or rationals to decimal degrees."""
    def to_float(v):
        if isinstance(v, (int, float)):
            return float(v)
        if hasattr(v, "numerator") and hasattr(v, "denominator"):
            return float(v.numerator) / float(v.denominator) if v.denominator != 0 else 0.0
        if isinstance(v, (list, tuple)) and len(v) == 2:
            return float(v[0]) / float(v[1]) if v[1] != 0 else 0.0
        return float(v)

    deg = to_float(dms_tuple[0])
    minute = to_float(dms_tuple[1])
    sec = to_float(dms_tuple[2])

    decimal = deg + (minute / 60.0) + (sec / 3600.0)
    if ref_str and ref_str.upper() in ["S", "W"]:
        decimal = -decimal
    return decimal

def extract_exif_gps(file_path: str) -> Tuple[Optional[float], Optional[float], Optional[str], Optional[str]]:
    """
    Extracts WGS84 decimal latitude, longitude, and captured timestamp from an image's EXIF metadata.
    Returns (latitude, longitude, captured_at, error_message).
    If EXIF GPS metadata is missing, returns (None, None, captured_at, error_explanation).
    """
    try:
        img = Image.open(file_path)
        exif = img._getexif() if hasattr(img, "_getexif") else None
        if not exif:
            return None, None, None, "Uploaded photo does not contain EXIF metadata."

        gps_info = {}
        captured_at = None

        for tag_id, val in exif.items():
            tag_name = ExifTags.TAGS.get(tag_id, tag_id)
            if tag_name == "GPSInfo":
                if isinstance(val, dict):
                    for gps_tag_id, gps_val in val.items():
                        sub_tag_name = ExifTags.GPSTAGS.get(gps_tag_id, gps_tag_id)
                        gps_info[sub_tag_name] = gps_val
                        gps_info[gps_tag_id] = gps_val
            elif tag_name in ["DateTimeOriginal", "DateTimeDigitized", "DateTime"] and not captured_at:
                c_str = str(val).strip()
                if " " in c_str:
                    parts = c_str.split(" ")
                    date_part = parts[0].replace(":", "-")
                    captured_at = f"{date_part}"

        # Check for lat/lng tags in gps_info
        lat_val = gps_info.get("GPSLatitude") or gps_info.get(2)
        lat_ref = gps_info.get("GPSLatitudeRef") or gps_info.get(1)
        lng_val = gps_info.get("GPSLongitude") or gps_info.get(4)
        lng_ref = gps_info.get("GPSLongitudeRef") or gps_info.get(3)

        if not lat_val or not lat_ref or not lng_val or not lng_ref:
            return None, None, captured_at, "Uploaded photo does not contain EXIF GPS metadata."

        lat = dms_to_decimal(lat_val, str(lat_ref))
        lng = dms_to_decimal(lng_val, str(lng_ref))

        if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lng <= 180.0):
            return None, None, captured_at, f"Extracted EXIF GPS coordinates ({lat}, {lng}) are invalid."

        return round(lat, 6), round(lng, 6), captured_at, None

    except Exception as e:
        return None, None, None, f"Error parsing image EXIF metadata: {str(e)}"

def parse_gps_from_text(text: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Parses WGS84 decimal latitude and longitude from raw OCR text extracted from
    camera geotag overlays (e.g. GPS Map Camera, timestamp cameras, WhatsApp shared images).
    
    Supports formats:
    - Lat 18.518511° Long 73.7802° / Lat: 18.518511, Long: 73.7802
    - Latitude 18.518511 Longitude 73.7802
    - 18.518511° N, 73.7802° E
    - 18.518511, 73.7802
    - Lat 18.5185110 Long 73.78020
    """
    if not text:
        return None, None

    text_clean = text.replace("°", " ").replace("\n", " ").replace("\r", " ")

    # Pattern 1: Explicit Latitude ... Longitude labels
    # e.g., Lat 18.518511 Long 73.7802, Latitude: 18.518511, Longitude: 73.7802
    m1 = re.search(
        r'(?:lat|latitude)\s*[:=]?\s*([+-]?\d{1,2}(?:\.\d{2,8})?)\s*([NSns])?[^\d\n\r]*(?:lon|long|longitude)\s*[:=]?\s*([+-]?\d{1,3}(?:\.\d{2,8})?)\s*([EWew])?',
        text_clean,
        re.IGNORECASE
    )
    if m1:
        try:
            lat = float(m1.group(1))
            if m1.group(2) and m1.group(2).upper() == "S":
                lat = -lat
            lng = float(m1.group(3))
            if m1.group(4) and m1.group(4).upper() == "W":
                lng = -lng
            if -90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0:
                return round(lat, 6), round(lng, 6)
        except (ValueError, TypeError):
            pass

    # Pattern 2: Coordinates with Cardinal Directions: 18.518511 N, 73.7802 E
    m2 = re.search(
        r'([+-]?\d{1,2}\.\d{3,8})\s*([NSns])\s*[,/;\s]+\s*([+-]?\d{1,3}\.\d{3,8})\s*([EWew])',
        text_clean,
        re.IGNORECASE
    )
    if m2:
        try:
            lat = float(m2.group(1))
            if m2.group(2).upper() == "S":
                lat = -lat
            lng = float(m2.group(3))
            if m2.group(4).upper() == "W":
                lng = -lng
            if -90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0:
                return round(lat, 6), round(lng, 6)
        except (ValueError, TypeError):
            pass

    # Pattern 3: Comma-separated decimal pair: 18.518511, 73.7802
    m3 = re.search(
        r'(?<!\d)([+-]?\d{1,2}\.\d{4,8})\s*,\s*([+-]?\d{1,3}\.\d{4,8})(?!\d)',
        text_clean
    )
    if m3:
        try:
            lat = float(m3.group(1))
            lng = float(m3.group(2))
            if -90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0:
                return round(lat, 6), round(lng, 6)
        except (ValueError, TypeError):
            pass

    return None, None

def extract_visible_image_geotag(file_path: str) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    """
    Inspects an image for a visible GPS/geotag overlay using OCR.
    Used when EXIF metadata has been stripped (e.g. through WhatsApp sharing).
    Returns (latitude, longitude, recognized_raw_text).
    """
    abs_path = os.path.abspath(file_path)
    recognized_text = ""

    # Primary OCR Engine: Native Windows Media OCR (via winsdk)
    try:
        import asyncio
        import concurrent.futures
        from winsdk.windows.media.ocr import OcrEngine
        from winsdk.windows.graphics.imaging import BitmapDecoder
        from winsdk.windows.storage import StorageFile

        async def _run_windows_ocr(p: str) -> str:
            engine = OcrEngine.try_create_from_user_profile_languages()
            if not engine:
                return ""
            f = await StorageFile.get_file_from_path_async(p)
            stream = await f.open_async(0)
            decoder = await BitmapDecoder.create_async(stream)
            bitmap = await decoder.get_software_bitmap_async()
            res = await engine.recognize_async(bitmap)
            return res.text if res else ""

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(lambda: asyncio.run(_run_windows_ocr(abs_path)))
            recognized_text = future.result(timeout=10.0)

    except Exception:
        recognized_text = ""

    # Secondary OCR Fallback: pytesseract if installed
    if not recognized_text:
        try:
            import pytesseract
            img = Image.open(file_path)
            recognized_text = pytesseract.image_to_string(img)
        except Exception:
            pass

    if not recognized_text:
        return None, None, None

    lat, lng = parse_gps_from_text(recognized_text)
    return lat, lng, recognized_text

def extract_photo_location(file_path: str) -> Dict[str, Any]:
    """
    Extracts GPS location following the strict NGO workflow priority:
    
    STEP 1 — CHECK EXIF GPS
    If valid EXIF GPS exists:
        → Use EXIF GPS.
        → GPS source = 'EXIF'
        → Do NOT use OCR/geotag detection.
        
    STEP 2 — CHECK VISIBLE GEOTAG
    If EXIF GPS is absent, inspect image for visible geotag overlay via OCR.
    If reliable GPS coordinates detected:
        → GPS source = 'IMAGE_GEOTAG'
        → Requires user confirmation.
        
    STEP 3 — NO LOCATION AVAILABLE
    If neither EXIF nor visible geotag is found:
        → Location not available.
        → No coordinates fabricated.
    """
    # 1. First Check EXIF GPS
    exif_lat, exif_lng, captured_at, exif_err = extract_exif_gps(file_path)
    if exif_lat is not None and exif_lng is not None:
        return {
            "gps_available": True,
            "gps_source": "EXIF",
            "gps_description": "GPS detected from photo metadata",
            "latitude": round(exif_lat, 6),
            "longitude": round(exif_lng, 6),
            "captured_at": captured_at,
            "requires_confirmation": False,
            "ocr_used": False,
            "error": None
        }

    # 2. Check Visible Image Geotag (Only if EXIF is absent)
    geotag_lat, geotag_lng, ocr_text = extract_visible_image_geotag(file_path)
    if geotag_lat is not None and geotag_lng is not None:
        return {
            "gps_available": True,
            "gps_source": "IMAGE_GEOTAG",
            "gps_description": "GPS detected from visible geotag on image",
            "latitude": round(geotag_lat, 6),
            "longitude": round(geotag_lng, 6),
            "captured_at": captured_at,
            "requires_confirmation": True,
            "ocr_used": True,
            "ocr_text_sample": ocr_text[:120] if ocr_text else None,
            "error": None
        }

    # 3. Location Not Available
    return {
        "gps_available": False,
        "gps_source": None,
        "gps_description": "Location not available",
        "latitude": None,
        "longitude": None,
        "captured_at": captured_at,
        "requires_confirmation": False,
        "ocr_used": True,
        "message": "GPS information could not be found in the photo metadata or visible image geotag.",
        "error": "Location not available"
    }

