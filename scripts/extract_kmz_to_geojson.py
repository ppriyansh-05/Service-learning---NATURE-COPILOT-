import os
import zipfile
import xml.etree.ElementTree as ET
import json

def extract_kmz_to_geojson():
    kmz_path = os.path.join('scripts', 'Bavdhan van udyan.kmz')
    if not os.path.exists(kmz_path):
        kmz_path = 'Bavdhan van udyan.kmz'
    
    with zipfile.ZipFile(kmz_path, 'r') as z:
        kml_bytes = z.read('doc.kml')
    
    tree = ET.fromstring(kml_bytes)
    ns = {'kml': 'http://www.opengis.net/kml/2.2'}
    
    boundary_feature = None
    zones_features = []
    
    for pm in tree.findall('.//kml:Placemark', ns):
        name_node = pm.find('kml:name', ns)
        name = name_node.text.strip() if name_node is not None and name_node.text else 'Unnamed'
        
        poly = pm.find('.//kml:Polygon', ns)
        if poly is None:
            continue
            
        coords_node = poly.find('.//kml:coordinates', ns)
        if coords_node is None or not coords_node.text:
            continue
            
        raw_coords = coords_node.text.strip().split()
        coordinates_ring = []
        for pt in raw_coords:
            parts = pt.split(',')
            lon = float(parts[0])
            lat = float(parts[1])
            coordinates_ring.append([lon, lat])
            
        # Ensure polygon ring is closed
        if coordinates_ring[0] != coordinates_ring[-1]:
            coordinates_ring.append(coordinates_ring[0])
            
        feature = {
            "type": "Feature",
            "properties": {
                "name": name,
                "site_name": "Bavdhan Van Udyan",
                "plus_code": "GQ9J+74Q",
                "address": "Lantana Gardens, Bavdhan, Pune, Maharashtra 411021",
                "crs": "EPSG:4326"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [coordinates_ring]
            }
        }
        
        if name.upper() in ["VAN UDHYAN", "VAN UDYAN", "BAVDHAN VAN UDYAN"]:
            feature["properties"]["type"] = "complete_boundary"
            feature["properties"]["description"] = "Complete geographical boundary of Bavdhan Van Udyan project area"
            boundary_feature = feature
        else:
            feature["properties"]["type"] = "active_monitoring_zone"
            feature["properties"]["status"] = "active"
            feature["properties"]["description"] = f"Current RSWF active intervention/monitoring work zone {name}"
            zones_features.append(feature)
            
    # Sort zones by name (ZONE A, ZONE B, ZONE C)
    zones_features.sort(key=lambda f: f["properties"]["name"])
    
    boundary_geojson = {
        "type": "FeatureCollection",
        "name": "Bavdhan_Van_Udyan_Boundary",
        "crs": {
            "type": "name",
            "properties": {
                "name": "urn:ogc:def:crs:OGC:1.3:CRS84"
            }
        },
        "features": [boundary_feature] if boundary_feature else []
    }
    
    zones_geojson = {
        "type": "FeatureCollection",
        "name": "Bavdhan_Van_Udyan_Active_Zones",
        "crs": {
            "type": "name",
            "properties": {
                "name": "urn:ogc:def:crs:OGC:1.3:CRS84"
            }
        },
        "features": zones_features
    }
    
    master_geojson = {
        "type": "FeatureCollection",
        "name": "Bavdhan_Van_Udyan_Master_Geography",
        "crs": {
            "type": "name",
            "properties": {
                "name": "urn:ogc:def:crs:OGC:1.3:CRS84"
            }
        },
        "features": ([boundary_feature] if boundary_feature else []) + zones_features
    }
    
    # Save raw files
    os.makedirs(os.path.join('data', 'raw'), exist_ok=True)
    os.makedirs(os.path.join('data', 'processed'), exist_ok=True)
    
    raw_boundary_path = os.path.join('data', 'raw', 'van_udyan_boundary.geojson')
    raw_zones_path = os.path.join('data', 'raw', 'van_udyan_zones.geojson')
    
    with open(raw_boundary_path, 'w', encoding='utf-8') as f:
        json.dump(boundary_geojson, f, indent=2)
        
    with open(raw_zones_path, 'w', encoding='utf-8') as f:
        json.dump(zones_geojson, f, indent=2)
        
    # Save processed copies
    proc_boundary_path = os.path.join('data', 'processed', 'van_udyan_boundary.geojson')
    proc_zones_path = os.path.join('data', 'processed', 'van_udyan_zones.geojson')
    proc_master_path = os.path.join('data', 'processed', 'van_udyan_master_geography.geojson')
    
    with open(proc_boundary_path, 'w', encoding='utf-8') as f:
        json.dump(boundary_geojson, f, indent=2)
        
    with open(proc_zones_path, 'w', encoding='utf-8') as f:
        json.dump(zones_geojson, f, indent=2)
        
    with open(proc_master_path, 'w', encoding='utf-8') as f:
        json.dump(master_geojson, f, indent=2)
        
    print("Extract script executed successfully.")
    print(f"Created {raw_boundary_path} ({len(boundary_geojson['features'])} feature)")
    print(f"Created {raw_zones_path} ({len(zones_geojson['features'])} features)")
    print(f"Created processed copies in data/processed/")

if __name__ == "__main__":
    extract_kmz_to_geojson()
