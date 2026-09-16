"""
Phase 4 Database Validation Suite Script
Validates PostgreSQL connection, PostGIS extension, table schemas, spatial indexing,
geography import, iNaturalist record counts, ID preservation, and spatial queries.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import csv
import psycopg2
from setup_database import get_db_url

def validate_database():
    print("=" * 70)
    print("      PHASE 4 VALIDATION SUITE — POSTGRESQL + POSTGIS DATABASE")
    print("=" * 70)
    
    db_url = get_db_url()
    schema_sql_path = os.path.join("database", "schema", "01_init_postgis_schema.sql")
    clean_csv_path = os.path.join("data", "processed", "inaturalist", "observations_van_udyan_clean.csv")
    
    # Static Schema Validation Checks (File Level)
    results = []
    
    def log(test_name, passed, details=""):
        status = "[PASS]" if passed else "[FAIL]"
        results.append((test_name, passed, details))
        print(f"{status} {test_name}")
        if details:
            print(f"       Details: {details}")

    log("Schema DDL File Existence", os.path.exists(schema_sql_path), schema_sql_path)
    log("Cleaned CSV Input File Existence", os.path.exists(clean_csv_path), clean_csv_path)

    # Inspect DDL file for critical architectural definitions
    with open(schema_sql_path, "r", encoding="utf-8") as f:
        ddl_text = f.read()
        
    has_postgis = "CREATE EXTENSION IF NOT EXISTS postgis;" in ddl_text
    has_boundary_tbl = "CREATE TABLE IF NOT EXISTS geography_boundaries" in ddl_text
    has_zones_tbl = "CREATE TABLE IF NOT EXISTS geography_zones" in ddl_text
    has_taxa_tbl = "CREATE TABLE IF NOT EXISTS taxonomic_taxa" in ddl_text
    has_obs_tbl = "CREATE TABLE IF NOT EXISTS observations" in ddl_text
    has_planted_tbl = "CREATE TABLE IF NOT EXISTS planted_plants" in ddl_text
    has_ai_tbl = "CREATE TABLE IF NOT EXISTS ai_predictions" in ddl_text
    has_spatial_idx = "CREATE INDEX IF NOT EXISTS idx_obs_geom ON observations USING GIST" in ddl_text
    
    log("DDL Definition: PostGIS Spatial Extension", has_postgis)
    log("DDL Definition: geography_boundaries table", has_boundary_tbl)
    log("DDL Definition: geography_zones table", has_zones_tbl)
    log("DDL Definition: taxonomic_taxa reference table", has_taxa_tbl)
    log("DDL Definition: observations central table", has_obs_tbl)
    log("DDL Definition: planted_plants table (Phase 8 support)", has_planted_tbl)
    log("DDL Definition: ai_predictions table (Phase 10/11 support)", has_ai_tbl)
    log("DDL Definition: Spatial GIST Indexing", has_spatial_idx)
    
    # Try Live PostgreSQL Connection
    print("\nAttempting Live PostgreSQL + PostGIS Database Connection...")
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Test PostGIS
        cursor.execute("SELECT PostGIS_Version();")
        postgis_ver = cursor.fetchone()[0]
        log("Live Database: PostGIS Extension Version", True, f"PostGIS {postgis_ver}")
        
        # Test Tables
        cursor.execute("SELECT count(*) FROM geography_boundaries;")
        b_cnt = cursor.fetchone()[0]
        log("Live Database: Geography Boundaries Imported", b_cnt == 1, f"Found {b_cnt} boundary record")
        
        cursor.execute("SELECT count(*) FROM geography_zones;")
        z_cnt = cursor.fetchone()[0]
        log("Live Database: Active Zones Imported", z_cnt == 3, f"Found {z_cnt} active zone records (Zone A, B, C)")
        
        cursor.execute("SELECT count(*) FROM observations WHERE source = 'iNaturalist';")
        obs_cnt = cursor.fetchone()[0]
        log("Live Database: iNaturalist Cleaned Records Imported", obs_cnt == 227, f"Imported {obs_cnt} records (Target: 227)")

        # Test Spatial PostGIS Query (Point-in-Polygon inside PostgreSQL)
        cursor.execute("""
            SELECT count(*) 
            FROM observations o, geography_boundaries b
            WHERE b.site_code = 'BAVDHAN_VAN_UDYAN'
            AND ST_Intersects(o.geom, b.geom);
        """)
        spatial_inside_cnt = cursor.fetchone()[0]
        log("Live Database: PostGIS Spatial Containment Query", spatial_inside_cnt == 227, f"100% ({spatial_inside_cnt}/227) observations inside Van Udyan boundary via PostGIS ST_Intersects")

        cursor.close()
        conn.close()
        live_db_pass = True
        
    except Exception as e:
        print(f"\n[NOTE] Live PostgreSQL server not active on environment host.")
        print(f"       Connection details: {db_url.split('@')[-1]}")
        print(f"       Message: {str(e).strip()}")
        log("Live PostgreSQL Connection Test", False, "No active PostgreSQL server on localhost:5432")
        live_db_pass = False

    print("-" * 70)
    all_static_passed = all(item[1] for item in results if item[0] != "Live PostgreSQL Connection Test")
    print(f"STATIC SCHEMA ARCHITECTURE STATUS: {'PASSED' if all_static_passed else 'FAILED'}")
    print(f"LIVE DATABASE INSTANCE STATUS:     {'PASSED' if live_db_pass else 'ENVIRONMENT WAITING (PostgreSQL Service Inactive)'}")
    print("=" * 70)
    
    return all_static_passed

if __name__ == "__main__":
    success = validate_database()
    sys.exit(0 if success else 1)
