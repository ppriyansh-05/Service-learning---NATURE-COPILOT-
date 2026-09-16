"""
Database Seed Module — Geography Importer
Imports Phase 1 WGS84 GeoJSON polygons into PostgreSQL/PostGIS.
"""

import os
import json
import psycopg2

def seed_geography(db_url):
    print("Seeding Phase 1 Geography into PostgreSQL/PostGIS...")
    
    boundary_path = os.path.join("data", "raw", "van_udyan_boundary.geojson")
    zones_path = os.path.join("data", "raw", "van_udyan_zones.geojson")
    
    with open(boundary_path, "r", encoding="utf-8") as f:
        boundary_json = json.load(f)
        
    with open(zones_path, "r", encoding="utf-8") as f:
        zones_json = json.load(f)
        
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    # 1. Seed Boundary
    b_feat = boundary_json["features"][0]
    b_geom_json = json.dumps(b_feat["geometry"])
    b_name = b_feat["properties"].get("name", "Bavdhan Van Udyan")
    b_plus = b_feat["properties"].get("plus_code", "GQ9J+74Q")
    b_addr = b_feat["properties"].get("address", "Lantana Gardens, Bavdhan, Pune, Maharashtra 411021")
    
    cursor.execute("""
        INSERT INTO geography_boundaries (site_code, name, type, plus_code, address, geom)
        VALUES ('BAVDHAN_VAN_UDYAN', %s, 'complete_boundary', %s, %s, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))
        ON CONFLICT (site_code) DO UPDATE
        SET geom = ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326),
            name = %s,
            plus_code = %s,
            address = %s;
    """, (b_name, b_plus, b_addr, b_geom_json, b_geom_json, b_name, b_plus, b_addr))
    
    # 2. Seed Active Zones
    for z_feat in zones_json["features"]:
        z_name = z_feat["properties"]["name"]
        z_status = z_feat["properties"].get("status", "ACTIVE_ZONE")
        z_desc = z_feat["properties"].get("description", f"RSWF Active Zone {z_name}")
        z_geom_json = json.dumps(z_feat["geometry"])
        
        cursor.execute("""
            INSERT INTO geography_zones (zone_code, status, description, geom)
            VALUES (%s, %s, %s, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))
            ON CONFLICT (zone_code) DO UPDATE
            SET geom = ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326),
                status = %s,
                description = %s;
        """, (z_name, z_status, z_desc, z_geom_json, z_geom_json, z_status, z_desc))
        
    conn.commit()
    cursor.close()
    conn.close()
    print("Geography seeding complete.")

if __name__ == "__main__":
    db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/van_udyan_db")
    seed_geography(db_url)
