"""
Pl@ntNet AI Plant Identification Service Module
Provides integration with Pl@ntNet REST API for plant species identification from field photos,
normalizes Top 3 predictions, calculates confidence thresholds, and handles API errors securely.
"""

import os
import io
import json
import urllib.parse
from typing import Dict, Any, List, Optional
import requests
from PIL import Image, ImageOps
from app.core.config import settings

# Fraction of the photo height covered by a GPS Map Camera style overlay box at the bottom
GEOTAG_OVERLAY_FRACTION = 0.22
# Longest side of the image sent to Pl@ntNet (keeps uploads fast; well above its recommended minimum)
MAX_UPLOAD_DIMENSION = 1600

class PlantNetService:
    PLANTNET_API_BASE = "https://my-api.plantnet.org/v2/identify"
    # Fallback flora when the regional flora has no match
    FALLBACK_PROJECT = "all"

    @staticmethod
    def prepare_image(image_path: str, crop_geotag_overlay: bool = False) -> bytes:
        """
        Prepares a field photo for identification:
        - applies EXIF orientation,
        - removes the bottom geotag overlay (address text + map thumbnail), which otherwise gets
          analysed as if it were part of the plant,
        - downsizes to MAX_UPLOAD_DIMENSION and re-encodes as JPEG.
        """
        img = ImageOps.exif_transpose(Image.open(image_path)).convert("RGB")
        if crop_geotag_overlay:
            w, h = img.size
            img = img.crop((0, 0, w, int(h * (1 - GEOTAG_OVERLAY_FRACTION))))
        img.thumbnail((MAX_UPLOAD_DIMENSION, MAX_UPLOAD_DIMENSION), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        return buf.getvalue()

    @staticmethod
    def classify_confidence(score: float) -> str:
        """Classifies confidence score into application thresholds."""
        if score >= 0.90:
            return "HIGH CONFIDENCE"
        elif score >= 0.60:
            return "MEDIUM CONFIDENCE"
        else:
            return "LOW CONFIDENCE"

    @staticmethod
    def identify_plant(image_path: str, organ: str = "auto", crop_geotag_overlay: bool = False) -> Dict[str, Any]:
        """
        Sends an image file to the Pl@ntNet API for AI plant species identification.
        Queries the regional flora (settings.PLANTNET_PROJECT, default Indian Subcontinent) so
        species from other continents are not suggested, falling back to the world flora when the
        regional flora has no match. Returns normalized prediction results with Top 3 suggestions.
        """
        api_key = settings.PLANTNET_API_KEY
        if not api_key:
            return {
                "success": False,
                "error_code": "MISSING_API_KEY",
                "message": "PLANTNET_API_KEY environment variable is not configured. AI identification requires a valid Pl@ntNet API key.",
                "predictions": []
            }

        if not os.path.exists(image_path):
            return {
                "success": False,
                "error_code": "FILE_NOT_FOUND",
                "message": f"Image file '{image_path}' not found on server.",
                "predictions": []
            }

        # Validate plant organ parameter
        valid_organs = {"auto", "leaf", "flower", "fruit", "bark", "habit"}
        organ_param = organ.lower() if organ and organ.lower() in valid_organs else "auto"

        encoded_key = urllib.parse.quote(api_key)
        project = settings.PLANTNET_PROJECT

        try:
            try:
                image_bytes = PlantNetService.prepare_image(image_path, crop_geotag_overlay)
            except Exception:
                with open(image_path, "rb") as img_f:
                    image_bytes = img_f.read()

            def post(project_id: str):
                url = f"{PlantNetService.PLANTNET_API_BASE}/{urllib.parse.quote(project_id)}?api-key={encoded_key}&lang=en"
                files = [("images", ("photo.jpg", image_bytes, "image/jpeg"))]
                data = [("organs", organ_param)]
                return requests.post(url, files=files, data=data, timeout=30)

            response = post(project)
            # Pl@ntNet answers 404 "Species not found" when the regional flora has no match
            if response.status_code == 404 and project != PlantNetService.FALLBACK_PROJECT:
                project = PlantNetService.FALLBACK_PROJECT
                response = post(project)

            if response.status_code in [401, 403]:
                return {
                    "success": False,
                    "error_code": "INVALID_API_KEY",
                    "message": "Pl@ntNet API rejected credentials (Invalid or expired API key).",
                    "predictions": []
                }
            elif response.status_code == 429:
                return {
                    "success": False,
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "message": "Pl@ntNet API rate limit exceeded. Please try again later.",
                    "predictions": []
                }
            elif response.status_code == 404:
                return {
                    "success": False,
                    "error_code": "NO_MATCH",
                    "message": "Pl@ntNet could not match this photo to any species. Try a close-up photo where a single leaf, flower or fruit fills most of the frame.",
                    "predictions": []
                }
            elif response.status_code != 200:
                return {
                    "success": False,
                    "error_code": f"HTTP_{response.status_code}",
                    "message": f"Pl@ntNet API error HTTP {response.status_code}.",
                    "predictions": []
                }

            res_json = response.json()
            raw_results = res_json.get("results", [])

            predictions = []
            for idx, item in enumerate(raw_results[:3]):
                score = float(item.get("score", 0.0))
                species_info = item.get("species", {})
                sci_name = species_info.get("scientificNameWithoutAuthor") or species_info.get("scientificName") or "Unknown Species"
                
                common_names = species_info.get("commonNames", [])
                common_name = common_names[0] if common_names else None
                
                family = species_info.get("family", {}).get("scientificNameWithoutAuthor")
                genus = species_info.get("genus", {}).get("scientificNameWithoutAuthor")

                conf_level = PlantNetService.classify_confidence(score)

                predictions.append({
                    "rank": idx + 1,
                    "scientific_name": sci_name,
                    "common_name": common_name,
                    "family": family,
                    "genus": genus,
                    "confidence": round(score, 4),
                    "confidence_percentage": f"{round(score * 100, 1)}%",
                    "confidence_level": conf_level
                })

            return {
                "success": True,
                "provider": "Pl@ntNet",
                "organ_used": organ_param,
                "flora_project": project,
                "geotag_overlay_removed": crop_geotag_overlay,
                "total_predictions": len(predictions),
                "top_prediction": predictions[0] if predictions else None,
                "predictions": predictions
            }

        except Exception as e:
            return {
                "success": False,
                "error_code": "REQUEST_FAILED",
                "message": f"Pl@ntNet connection error: {str(e)}",
                "predictions": []
            }
