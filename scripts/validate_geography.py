"""
Validate Geography Script for Bavdhan Van Udyan
Validates GeoJSON files, geometry validity, WGS84 CRS, containment within boundary, and zone non-overlap.
"""

import os
import json
import sys
from shapely.geometry import shape, Polygon

def validate():
    print("=" * 70)
    print("      VAN UDYAN GEOGRAPHY VALIDATION REPORT (PHASE 1)")
    print("=" * 70)
    
    raw_boundary_path = os.path.join('data', 'raw', 'van_udyan_boundary.geojson')
    raw_zones_path = os.path.join('data', 'raw', 'van_udyan_zones.geojson')
    
    results = []
    
    def log_result(test_name, passed, details=""):
        status = "[PASS]" if passed else "[FAIL]"
        results.append((test_name, passed, details))
        print(f"{status} {test_name}")
        if details:
            print(f"       Details: {details}")
            
    # Check 1: File existence
    boundary_exists = os.path.exists(raw_boundary_path)
    zones_exists = os.path.exists(raw_zones_path)
    log_result("File Existence: Boundary GeoJSON", boundary_exists, raw_boundary_path)
    log_result("File Existence: Zones GeoJSON", zones_exists, raw_zones_path)
    
    if not (boundary_exists and zones_exists):
        print("\nERROR: Required GeoJSON files missing. Run extract_kmz_to_geojson.py first.")
        sys.exit(1)
        
    # Check 2: GeoJSON Syntax & Loading
    try:
        with open(raw_boundary_path, 'r', encoding='utf-8') as f:
            b_json = json.load(f)
        log_result("GeoJSON Syntax: van_udyan_boundary.geojson", True)
    except Exception as e:
        log_result("GeoJSON Syntax: van_udyan_boundary.geojson", False, str(e))
        b_json = None

    try:
        with open(raw_zones_path, 'r', encoding='utf-8') as f:
            z_json = json.load(f)
        log_result("GeoJSON Syntax: van_udyan_zones.geojson", True)
    except Exception as e:
        log_result("GeoJSON Syntax: van_udyan_zones.geojson", False, str(e))
        z_json = None
        
    if not (b_json and z_json):
        sys.exit(1)

    # Check 3: Geometry Types (Polygon / MultiPolygon)
    b_features = b_json.get("features", [])
    z_features = z_json.get("features", [])
    
    b_geom_type = b_features[0]["geometry"]["type"] if b_features else "None"
    valid_b_type = b_geom_type in ["Polygon", "MultiPolygon"]
    log_result("Geometry Type: Boundary", valid_b_type, f"Type: {b_geom_type}")

    zones_geom_valid = True
    zone_geom_types = []
    for f in z_features:
        gtype = f["geometry"]["type"]
        zone_geom_types.append(f"{f['properties'].get('name')}: {gtype}")
        if gtype not in ["Polygon", "MultiPolygon"]:
            zones_geom_valid = False
    log_result("Geometry Type: Active Zones", zones_geom_valid, ", ".join(zone_geom_types))

    # Check 4: WGS84 Coordinate Ranges
    def check_coords_range(coordinates):
        # Flattens nested list of coordinates
        def extract_pts(coords):
            pts = []
            if isinstance(coords[0], (int, float)):
                return [coords]
            for item in coords:
                pts.extend(extract_pts(item))
            return pts
        
        pts = extract_pts(coordinates)
        valid = True
        for lon, lat in pts:
            if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
                valid = False
            # Also check near Pune expectation (~73.7-73.8 Lon, ~18.5 Lat)
            if not (73.0 <= lon <= 74.5 and 18.0 <= lat <= 19.0):
                valid = False
        return valid, len(pts)

    b_coord_ok, b_pts_cnt = check_coords_range(b_features[0]["geometry"]["coordinates"])
    log_result("Coordinate Range (WGS84 / Pune Region): Boundary", b_coord_ok, f"Inspected {b_pts_cnt} points")

    z_coords_ok = True
    total_z_pts = 0
    for f in z_features:
        ok, cnt = check_coords_range(f["geometry"]["coordinates"])
        total_z_pts += cnt
        if not ok:
            z_coords_ok = False
    log_result("Coordinate Range (WGS84 / Pune Region): Active Zones", z_coords_ok, f"Inspected {total_z_pts} total points across {len(z_features)} zones")

    # Check 5: Closed Polygon Rings
    def is_ring_closed(coordinates):
        # Ring is outer ring of polygon
        ring = coordinates[0]
        return ring[0] == ring[-1]

    b_ring_closed = is_ring_closed(b_features[0]["geometry"]["coordinates"])
    log_result("Closed Polygon Ring: Boundary", b_ring_closed)

    z_rings_closed = True
    for f in z_features:
        if not is_ring_closed(f["geometry"]["coordinates"]):
            z_rings_closed = False
    log_result("Closed Polygon Rings: Active Zones", z_rings_closed)

    # Check 6: Shapely Geometry Validity
    boundary_geom = shape(b_features[0]["geometry"])
    log_result("Topology & Geometry Validity: Boundary", boundary_geom.is_valid, f"Area: {boundary_geom.area:.8f} sq deg")

    zones_dict = {}
    zones_valid = True
    for f in z_features:
        name = f["properties"]["name"]
        g = shape(f["geometry"])
        zones_dict[name] = g
        if not g.is_valid:
            zones_valid = False
    log_result("Topology & Geometry Validity: Active Zones", zones_valid, f"Validated zones: {list(zones_dict.keys())}")

    # Check 7: Containment — Active Zones inside Van Udyan Boundary
    containment_pass = True
    containment_details = []
    for name, g in zones_dict.items():
        is_inside = g.within(boundary_geom)
        if not is_inside:
            # Check if slight numerical precision boundary issue, else flag error
            outside_area = g.difference(boundary_geom).area
            if outside_area > 1e-12:
                containment_pass = False
                containment_details.append(f"{name} NOT fully inside (outside area: {outside_area})")
            else:
                containment_details.append(f"{name} inside boundary (precision clean)")
        else:
            containment_details.append(f"{name} inside boundary")
            
    log_result("Spatial Containment: Active Zones inside Van Udyan", containment_pass, "; ".join(containment_details))

    # Check 8: Non-Overlap between Active Zones (Zone A, Zone B, Zone C)
    overlap_pass = True
    overlap_details = []
    zone_names = list(zones_dict.keys())
    for i in range(len(zone_names)):
        for j in range(i + 1, len(zone_names)):
            n1, n2 = zone_names[i], zone_names[j]
            g1, g2 = zones_dict[n1], zones_dict[n2]
            intersection_area = g1.intersection(g2).area
            if intersection_area > 1e-12:
                overlap_pass = False
                overlap_details.append(f"{n1} overlaps {n2} (intersection: {intersection_area})")
            else:
                overlap_details.append(f"{n1} & {n2} disjoint")
                
    log_result("Spatial Non-Overlap: Zone A / Zone B / Zone C", overlap_pass, "; ".join(overlap_details))

    print("-" * 70)
    all_passed = all(item[1] for item in results)
    overall_status = "PASSED — ALL CHECKS SUCCESSFUL" if all_passed else "FAILED — ACTION REQUIRED"
    print(f"OVERALL STATUS: {overall_status}")
    print("=" * 70)
    
    return all_passed

if __name__ == "__main__":
    success = validate()
    sys.exit(0 if success else 1)
