"""
Phase 2 — Reproducible iNaturalist Ingestion & Spatial Verification Pipeline
Fetches raw candidate observations from official iNaturalist API using Van Udyan bbox,
performs point-in-polygon spatial verification against the exact Van Udyan boundary,
assigns active working zones (ZONE A, B, C or OUTSIDE_ACTIVE_ZONES), and outputs clean processed CSV.
"""

import os
import json
import csv
from datetime import datetime
from shapely.geometry import shape, Point
from inaturalist_api import calculate_bbox, fetch_observations_bbox

def run_ingestion():
    print("=" * 70)
    print("      VAN UDYAN BIODIVERSITY PLATFORM — PHASE 2 INGESTION")
    print("=" * 70)
    
    raw_boundary_path = os.path.join("data", "raw", "van_udyan_boundary.geojson")
    raw_zones_path = os.path.join("data", "raw", "van_udyan_zones.geojson")
    
    if not (os.path.exists(raw_boundary_path) and os.path.exists(raw_zones_path)):
        raise FileNotFoundError("Phase 1 GeoJSON files missing in data/raw/")
        
    # 1. Load Geometries
    with open(raw_boundary_path, "r", encoding="utf-8") as f:
        boundary_geojson = json.load(f)
    boundary_shape = shape(boundary_geojson["features"][0]["geometry"])
    
    with open(raw_zones_path, "r", encoding="utf-8") as f:
        zones_geojson = json.load(f)
    zones_shapes = {
        feat["properties"]["name"]: shape(feat["geometry"])
        for feat in zones_geojson["features"]
    }
    
    print(f"Loaded Van Udyan Boundary geometry (Area: {boundary_shape.area:.8f} sq deg)")
    print(f"Loaded {len(zones_shapes)} Active Zones: {list(zones_shapes.keys())}")
    
    # 2. Calculate Bounding Box
    swlat, swlng, nelat, nelng = calculate_bbox(boundary_geojson, padding=0.003)
    print(f"Calculated Retrieval Bounding Box (Padded):")
    print(f"  SW: ({swlat:.6f}, {swlng:.6f}) | NE: ({nelat:.6f}, {nelng:.6f})")
    
    # 3. Call iNaturalist Public API (Read-only, no credentials)
    print("\nFetching public candidate observations from official iNaturalist API...")
    raw_results, meta = fetch_observations_bbox(swlat, swlng, nelat, nelng, per_page=200)
    
    print(f"API Response: {meta['total_retrieved']} total candidate observations retrieved.")
    
    # 4. Store Raw API Data & Metadata
    raw_dir = os.path.join("data", "raw", "inaturalist")
    os.makedirs(raw_dir, exist_ok=True)
    
    raw_obs_file = os.path.join(raw_dir, "observations_raw.json")
    meta_obs_file = os.path.join(raw_dir, "ingestion_metadata.json")
    
    with open(raw_obs_file, "w", encoding="utf-8") as f:
        json.dump(raw_results, f, indent=2)
        
    full_metadata = {
        "ingestion_timestamp_utc": datetime.utcnow().isoformat() + "Z",
        "phase": 2,
        "source_platform": "iNaturalist",
        "api_metadata": meta,
        "boundary_source_file": raw_boundary_path,
        "zones_source_file": raw_zones_path
    }
    
    with open(meta_obs_file, "w", encoding="utf-8") as f:
        json.dump(full_metadata, f, indent=2)
        
    print(f"Saved raw dataset: {raw_obs_file}")
    print(f"Saved ingestion metadata: {meta_obs_file}")
    
    # 5. Spatial Verification & Field Processing
    processed_dir = os.path.join("data", "processed", "inaturalist")
    os.makedirs(processed_dir, exist_ok=True)
    
    proc_csv_path = os.path.join(processed_dir, "observations_van_udyan.csv")
    
    usable_coords_cnt = 0
    missing_coords_cnt = 0
    inside_van_udyan_cnt = 0
    outside_van_udyan_cnt = 0
    
    zone_counts = {
        "ZONE A": 0,
        "ZONE B": 0,
        "ZONE C": 0,
        "OUTSIDE_ACTIVE_ZONES": 0
    }
    
    processed_records = []
    seen_ids = set()
    
    for obs in raw_results:
        obs_id = obs.get("id")
        if not obs_id or obs_id in seen_ids:
            continue
        seen_ids.add(obs_id)
        
        loc_str = obs.get("location")
        if not loc_str:
            missing_coords_cnt += 1
            continue
            
        try:
            lat_str, lng_str = loc_str.split(",")
            lat = float(lat_str.strip())
            lng = float(lng_str.strip())
        except Exception:
            missing_coords_cnt += 1
            continue
            
        # Validate WGS84 range near Pune
        if not (-90 <= lat <= 90 and -180 <= lng <= 180 and 18.0 <= lat <= 19.0 and 73.0 <= lng <= 74.5):
            missing_coords_cnt += 1
            continue
            
        usable_coords_cnt += 1
        
        # Spatial Point-in-Polygon check against exact Van Udyan boundary (Point(longitude, latitude))
        pt = Point(lng, lat)
        
        is_inside = boundary_shape.intersects(pt) or boundary_shape.contains(pt)
        
        if not is_inside:
            outside_van_udyan_cnt += 1
            continue
            
        inside_van_udyan_cnt += 1
        
        # Assign Zone
        assigned_zone = None
        for z_name, z_shape in zones_shapes.items():
            if z_shape.intersects(pt) or z_shape.contains(pt):
                assigned_zone = z_name
                break
                
        if assigned_zone:
            zone = assigned_zone
            zone_status = "ACTIVE_ZONE"
            zone_counts[assigned_zone] += 1
        else:
            zone = ""
            zone_status = "OUTSIDE_ACTIVE_ZONES"
            zone_counts["OUTSIDE_ACTIVE_ZONES"] += 1
            
        # Taxonomic fields
        taxon = obs.get("taxon") or {}
        taxon_id = taxon.get("id", "")
        scientific_name = taxon.get("name", "")
        common_name = taxon.get("preferred_common_name", "") or scientific_name
        species_name = taxon.get("name", "")
        taxon_rank = taxon.get("rank", "")
        
        # Photo URL extraction
        photo_url = ""
        default_photo = obs.get("default_photo") or {}
        if default_photo.get("medium_url"):
            photo_url = default_photo["medium_url"]
        elif default_photo.get("square_url"):
            photo_url = default_photo["square_url"]
        elif obs.get("photos") and len(obs["photos"]) > 0:
            photo_url = obs["photos"][0].get("url", "")
            
        user = obs.get("user") or {}
        observer = user.get("login", "") or user.get("name", "")
        
        obs_url = obs.get("uri") or f"https://www.inaturalist.org/observations/{obs_id}"
        
        record = {
            "observation_id": obs_id,
            "taxon_id": taxon_id,
            "species_name": species_name,
            "scientific_name": scientific_name,
            "common_name": common_name,
            "taxon_rank": taxon_rank,
            "latitude": lat,
            "longitude": lng,
            "observed_on": obs.get("observed_on") or obs.get("time_observed_at", ""),
            "quality_grade": obs.get("quality_grade", ""),
            "observer": observer,
            "observation_url": obs_url,
            "photo_url": photo_url,
            "created_at": obs.get("created_at", ""),
            "updated_at": obs.get("updated_at", ""),
            "source": "iNaturalist",
            "zone": zone,
            "zone_status": zone_status
        }
        
        processed_records.append(record)

    # 6. Write Processed CSV
    fieldnames = [
        "observation_id", "taxon_id", "species_name", "scientific_name", "common_name",
        "taxon_rank", "latitude", "longitude", "observed_on", "quality_grade",
        "observer", "observation_url", "photo_url", "created_at", "updated_at",
        "source", "zone", "zone_status"
    ]
    
    with open(proc_csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(processed_records)
        
    print(f"\nSuccessfully written spatially verified dataset to {proc_csv_path}")
    print(f"Summary Metrics:")
    print(f"  - Total Candidates Retrieved: {meta['total_retrieved']}")
    print(f"  - Observations with Usable Coords: {usable_coords_cnt}")
    print(f"  - Observations without Usable Coords: {missing_coords_cnt}")
    print(f"  - Spatially Verified Inside Van Udyan: {inside_van_udyan_cnt}")
    print(f"  - Excluded Outside Van Udyan: {outside_van_udyan_cnt}")
    print(f"  - Zone Distribution:")
    print(f"      * Zone A: {zone_counts['ZONE A']}")
    print(f"      * Zone B: {zone_counts['ZONE B']}")
    print(f"      * Zone C: {zone_counts['ZONE C']}")
    print(f"      * Outside Active Zones (Retained): {zone_counts['OUTSIDE_ACTIVE_ZONES']}")
    
    unique_species = len(set(r["scientific_name"] for r in processed_records if r["scientific_name"]))
    print(f"  - Unique Recorded Species / Taxa: {unique_species}")
    
    return {
        "status": "SUCCESS",
        "total_retrieved": meta["total_retrieved"],
        "usable_coords": usable_coords_cnt,
        "missing_coords": missing_coords_cnt,
        "inside_van_udyan": inside_van_udyan_cnt,
        "outside_van_udyan": outside_van_udyan_cnt,
        "zone_counts": zone_counts,
        "unique_species": unique_species,
        "processed_csv": proc_csv_path
    }

if __name__ == "__main__":
    run_ingestion()
