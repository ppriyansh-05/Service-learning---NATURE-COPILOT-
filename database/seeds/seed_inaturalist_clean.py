"""
Database Seed Module — iNaturalist Cleaned Data Importer
Imports Phase 3 cleaned dataset into PostgreSQL/PostGIS.
"""

import os
import csv
import json
import psycopg2

def seed_inaturalist_data(db_url):
    print("Seeding Phase 3 Cleaned iNaturalist dataset into PostgreSQL/PostGIS...")
    
    clean_csv_path = os.path.join("data", "processed", "inaturalist", "observations_van_udyan_clean.csv")
    if not os.path.exists(clean_csv_path):
        raise FileNotFoundError(f"Cleaned CSV dataset missing: {clean_csv_path}")
        
    with open(clean_csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        records = list(reader)
        
    print(f"Loaded {len(records)} cleaned records from {clean_csv_path}")
    
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    # 1. Populate Taxonomic Reference Table
    taxa_map = {}
    
    for r in records:
        sc_name = r.get("scientific_name", "").strip()
        if not sc_name:
            continue
            
        t_id = r.get("taxon_id", "").strip() or None
        sp_name = r.get("species_name", "").strip() or None
        cm_name = r.get("common_name", "").strip() or None
        t_rank = r.get("taxon_rank", "").strip() or None
        
        cursor.execute("""
            INSERT INTO taxonomic_taxa (taxon_id, scientific_name, species_name, common_name, taxon_rank)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (scientific_name) DO UPDATE
            SET common_name = COALESCE(EXCLUDED.common_name, taxonomic_taxa.common_name),
                species_name = COALESCE(EXCLUDED.species_name, taxonomic_taxa.species_name)
            RETURNING id;
        """, (t_id, sc_name, sp_name, cm_name, t_rank))
        
        db_id = cursor.fetchone()[0]
        taxa_map[sc_name] = db_id
        
    # Build zone mapping
    cursor.execute("SELECT id, zone_code FROM geography_zones;")
    zone_db_map = {row[1]: row[0] for row in cursor.fetchall()}
    
    # 2. Populate Central Observations Table
    inserted_cnt = 0
    for r in records:
        obs_id_str = str(r["observation_id"]).strip()
        sc_name = r.get("scientific_name", "").strip() or None
        cm_name = r.get("common_name", "").strip() or None
        db_taxon_id = taxa_map.get(sc_name) if sc_name else None
        
        obs_date = r.get("observed_on", "").strip() or None
        q_grade = r.get("quality_grade", "").strip() or None
        observer = r.get("observer", "").strip() or None
        obs_url = r.get("observation_url", "").strip() or None
        photo_url = r.get("photo_url", "").strip() or None
        
        lat = float(r["latitude"])
        lng = float(r["longitude"])
        
        z_code = r.get("zone", "").strip() or None
        z_status = r.get("zone_status", "OUTSIDE_ACTIVE_ZONES").strip()
        db_zone_id = zone_db_map.get(z_code) if z_code else None
        
        cursor.execute("""
            INSERT INTO observations (
                source, source_id, taxon_id, scientific_name, common_name,
                observed_on, quality_grade, observer, observation_url, photo_url,
                latitude, longitude, geom, zone_id, zone_code, zone_status
            ) VALUES (
                'iNaturalist', %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s, %s
            )
            ON CONFLICT (source, source_id) DO UPDATE
            SET taxon_id = EXCLUDED.taxon_id,
                scientific_name = EXCLUDED.scientific_name,
                common_name = EXCLUDED.common_name,
                observed_on = EXCLUDED.observed_on,
                latitude = EXCLUDED.latitude,
                longitude = EXCLUDED.longitude,
                geom = EXCLUDED.geom,
                zone_id = EXCLUDED.zone_id,
                zone_code = EXCLUDED.zone_code,
                zone_status = EXCLUDED.zone_status,
                updated_at = CURRENT_TIMESTAMP;
        """, (
            obs_id_str, db_taxon_id, sc_name, cm_name,
            obs_date, q_grade, observer, obs_url, photo_url,
            lat, lng, lng, lat, db_zone_id, z_code, z_status
        ))
        inserted_cnt += 1
        
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"Imported {inserted_cnt} records into PostgreSQL/PostGIS observations table.")

if __name__ == "__main__":
    db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/van_udyan_db")
    seed_inaturalist_data(db_url)
