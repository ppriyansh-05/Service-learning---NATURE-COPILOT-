"""
Pl@ntNet AI Plant Identification Service Module
Provides integration with Pl@ntNet REST API for plant species identification from field photos,
normalizes Top 3 predictions, calculates confidence thresholds, and handles API errors securely.
"""

import os
import json
import urllib.parse
from typing import Dict, Any, List, Optional
import requests
from app.core.config import settings

class PlantNetService:
    PLANTNET_API_URL = "https://my-api.plantnet.org/v2/identify/all"

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
    def identify_plant(image_path: str, organ: str = "auto") -> Dict[str, Any]:
        """
        Sends an image file to the Pl@ntNet API for AI plant species identification.
        Returns normalized prediction results with Top 3 suggestions.
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

        # Build URL with api-key query parameter
        encoded_key = urllib.parse.quote(api_key)
        url = f"{PlantNetService.PLANTNET_API_URL}?api-key={encoded_key}&lang=en"

        try:
            with open(image_path, "rb") as img_f:
                files = [("images", (os.path.basename(image_path), img_f, "image/jpeg"))]
                data = [("organs", organ_param)] if organ_param != "auto" else []
                
                response = requests.post(url, files=files, data=data, timeout=15)

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
