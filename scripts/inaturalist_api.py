"""
iNaturalist API Client Module
Provides reusable functions to fetch public observation data from the official iNaturalist API v1.
"""

import requests
import time
import json
from typing import Dict, Any, List, Tuple

BASE_URL = "https://api.inaturalist.org/v1/observations"

def calculate_bbox(boundary_geojson: Dict[str, Any], padding: float = 0.002) -> Tuple[float, float, float, float]:
    """
    Calculate bounding box with optional padding from a boundary GeoJSON feature collection or geometry.
    Returns (swlat, swlng, nelat, nelng).
    """
    features = boundary_geojson.get("features", [])
    if not features:
        raise ValueError("GeoJSON feature collection is empty")
        
    geom = features[0]["geometry"]
    coords_ring = geom["coordinates"][0]
    
    lons = [pt[0] for pt in coords_ring]
    lats = [pt[1] for pt in coords_ring]
    
    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)
    
    swlat = min_lat - padding
    swlng = min_lon - padding
    nelat = max_lat + padding
    nelng = max_lon + padding
    
    return swlat, swlng, nelat, nelng

def fetch_observations_bbox(
    swlat: float, 
    swlng: float, 
    nelat: float, 
    nelng: float,
    iconic_taxa: str = None,
    per_page: int = 200,
    max_pages: int = 50
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Fetch all public observations within a bounding box from official iNaturalist API (Read-only, no auth).
    Returns (results_list, metadata_dict).
    """
    headers = {
        "User-Agent": "VanUdyanBiodiversityIntelligencePlatform/1.0 (Service Learning NGO Project)"
    }
    
    all_results = []
    page = 1
    total_results = 0
    errors = []
    
    start_time = time.time()
    
    while page <= max_pages:
        params = {
            "swlat": swlat,
            "swlng": swlng,
            "nelat": nelat,
            "nelng": nelng,
            "per_page": per_page,
            "page": page,
            "order": "desc",
            "order_by": "created_at"
        }
        if iconic_taxa:
            params["iconic_taxa"] = iconic_taxa
            
        try:
            response = requests.get(BASE_URL, params=params, headers=headers, timeout=15)
            if response.status_code != 200:
                err_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                errors.append(err_msg)
                print(f"API Request Warning: {err_msg}")
                break
                
            data = response.json()
            total_results = data.get("total_results", 0)
            results = data.get("results", [])
            
            if not results:
                break
                
            all_results.extend(results)
            
            if len(all_results) >= total_results:
                break
                
            page += 1
            time.sleep(0.2) # Polite request delay
            
        except Exception as e:
            err_msg = f"Request Exception on page {page}: {str(e)}"
            errors.append(err_msg)
            print(f"API Error: {err_msg}")
            break
            
    execution_time = round(time.time() - start_time, 2)
    
    metadata = {
        "api_endpoint": BASE_URL,
        "authentication_required": False,
        "bbox": {
            "swlat": swlat,
            "swlng": swlng,
            "nelat": nelat,
            "nelng": nelng
        },
        "pages_requested": page,
        "total_results_reported": total_results,
        "total_retrieved": len(all_results),
        "execution_time_seconds": execution_time,
        "errors_or_warnings": errors
    }
    
    return all_results, metadata
