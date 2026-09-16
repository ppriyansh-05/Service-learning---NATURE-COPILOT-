"""
Phase 4 Database Setup Pipeline Script
Executes PostgreSQL + PostGIS schema creation, imports Phase 1 geography polygons,
and seeds Phase 3 cleaned iNaturalist observations into PostgreSQL/PostGIS.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import psycopg2
import importlib.util

def load_seed_module(mod_name, file_rel_path):
    abs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", file_rel_path))
    spec = importlib.util.spec_from_file_location(mod_name, abs_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

geo_mod = load_seed_module("seed_geography", os.path.join("database", "seeds", "seed_geography.py"))
seed_geography = geo_mod.seed_geography

inat_mod = load_seed_module("seed_inaturalist_data", os.path.join("database", "seeds", "seed_inaturalist_clean.py"))
seed_inaturalist_data = inat_mod.seed_inaturalist_data

def get_db_url():
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
        
    host = os.environ.get("PGHOST", "localhost")
    port = os.environ.get("PGPORT", "5432")
    user = os.environ.get("PGUSER", "postgres")
    password = os.environ.get("PGPASSWORD", "postgres")
    dbname = os.environ.get("PGDATABASE", "van_udyan_db")
    
    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"

def setup_database():
    print("=" * 70)
    print("      VAN UDYAN BIODIVERSITY PLATFORM — PHASE 4 DATABASE SETUP")
    print("=" * 70)
    
    db_url = get_db_url()
    schema_sql_path = os.path.join("database", "schema", "01_init_postgis_schema.sql")
    
    if not os.path.exists(schema_sql_path):
        raise FileNotFoundError(f"Schema DDL file missing: {schema_sql_path}")
        
    print(f"Connecting to PostgreSQL database: {db_url.split('@')[-1]}...")
    
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # 1. Execute PostGIS Schema DDL
        print(f"Executing DDL Schema: {schema_sql_path}...")
        with open(schema_sql_path, "r", encoding="utf-8") as f:
            sql_script = f.read()
            
        cursor.execute(sql_script)
        conn.commit()
        cursor.close()
        conn.close()
        print("Schema and PostGIS extensions initialized successfully.")
        
        # 2. Seed Geography
        seed_geography(db_url)
        
        # 3. Seed iNaturalist Cleaned Data
        seed_inaturalist_data(db_url)
        
        print("\nDatabase setup completed successfully.")
        return True
        
    except psycopg2.OperationalError as e:
        print("\n" + "!" * 70)
        print("DATABASE CONNECTION ERROR:")
        print(f"Could not connect to PostgreSQL server at {db_url.split('@')[-1]}")
        print("Details:", str(e).strip())
        print("\nINSTRUCTIONS TO RUN THE SETUP:")
        print("1. Start a local PostgreSQL server with PostGIS extension enabled.")
        print("2. Set environment variable DATABASE_URL (or PGHOST, PGUSER, PGPASSWORD, PGDATABASE).")
        print("3. Execute: python scripts/setup_database.py")
        print("!" * 70 + "\n")
        return False

if __name__ == "__main__":
    success = setup_database()
    sys.exit(0 if success else 1)
