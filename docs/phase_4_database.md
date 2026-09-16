# 🗄️ Phase 4 — Database Architecture & Data Integration Report

---

## 📌 1. Executive Summary & Architectural Vision

Phase 4 establishes the central relational and spatial database foundation for the **Van Udyan Biodiversity Intelligence Platform**.

Rather than designing a single-purpose "iNaturalist database," the architecture is engineered as a **multi-source, production-ready spatial database** using **PostgreSQL** with the **PostGIS** geospatial extension.

---

## 📐 2. Data Source Model & Entity-Relationship Architecture

```
   DATA SOURCES                      POSTGRESQL + POSTGIS SCHEMA
┌────────────────┐          ┌─────────────────────────────────────────┐
│  iNaturalist   │───────┐  │           geography_boundaries          │
└────────────────┘       │  │ (Van Udyan WGS84 Boundary Polygon)     │
┌────────────────┐       │  └────────────────────┬────────────────────┘
│ Planted Plants │───────┼───────────────────────┤
└────────────────┘       │                       ▼
┌────────────────┐       │          ┌─────────────────────────┐
│  User Uploads  │───────┘          │     geography_zones     │
└────────────────┘                  │ (Zone A, B, C Polygons) │
                                    └────────────┬────────────┘
                                                 │
                                                 ▼
┌────────────────────────┐          ┌─────────────────────────┐
│     taxonomic_taxa     │◄─────────│       observations      │
│ (Ref Taxonomy Table)   │          │ (Central Point Table)   │
└───────────┬────────────┘          └────────────┬────────────┘
            │                                    │
            │                       ┌────────────┴────────────┐
            ▼                       ▼                         ▼
┌────────────────────────┐ ┌───────────────────┐ ┌───────────────────┐
│     planted_plants     │ │   ai_predictions  │ │    future_users   │
│ (RSWF Plantation Data) │ │ (ML Predictions)  │ │ (Upload Metadata) │
└────────────────────────┘ └───────────────────┘ └───────────────────┘
```

### 📢 Core Conceptual Distinction
1. **Observation (`observations` table):** Represents a recorded occurrence/photograph of an organism observed in the field (e.g. iNaturalist records or field volunteer uploads).
2. **Planted Plant (`planted_plants` table):** Represents an actual plant planted and managed by RSWF/team (with Plant ID `PL001`, planting date, and condition status `Alive`/`Dead`/`Unknown`).

---

## 🛠️ 3. Relational Schema & Entity Specifications

### Table 1: `geography_boundaries`
Stores the complete outer boundary polygon of Bavdhan Van Udyan.
- `id` (SERIAL PRIMARY KEY)
- `site_code` (VARCHAR UNIQUE DEFAULT 'BAVDHAN_VAN_UDYAN')
- `name` (VARCHAR)
- `geom` (`GEOMETRY(Polygon, 4326)` NOT NULL)

### Table 2: `geography_zones`
Stores active working polygons (Zone A, Zone B, Zone C).
- `id` (SERIAL PRIMARY KEY)
- `zone_code` (VARCHAR UNIQUE NOT NULL)
- `status` (VARCHAR NOT NULL DEFAULT 'ACTIVE_ZONE')
- `geom` (`GEOMETRY(Polygon, 4326)` NOT NULL)

### Table 3: `taxonomic_taxa`
Reference table for plant taxonomy avoiding duplicate species names.
- `id` (SERIAL PRIMARY KEY)
- `taxon_id` (VARCHAR UNIQUE)
- `scientific_name` (VARCHAR UNIQUE NOT NULL)
- `common_name` (VARCHAR)
- `taxon_rank` (VARCHAR)

### Table 4: `observations` (Central Table)
Primary table for all observed plant occurrences.
- `id` (BIGSERIAL PRIMARY KEY) — Internal system ID!
- `source` (VARCHAR NOT NULL DEFAULT 'iNaturalist') — Source stream (`iNaturalist`, `New Upload`)
- `source_id` (VARCHAR) — External record ID
- `taxon_id` (INTEGER REFERENCES `taxonomic_taxa(id)`)
- `latitude` (NUMERIC(10, 8) NOT NULL)
- `longitude` (NUMERIC(11, 8) NOT NULL)
- `geom` (`GEOMETRY(Point, 4326)` NOT NULL) — PostGIS spatial point
- `zone_id` (INTEGER REFERENCES `geography_zones(id)`)
- `zone_code` (VARCHAR)
- `zone_status` (VARCHAR NOT NULL DEFAULT 'OUTSIDE_ACTIVE_ZONES')
- **Constraint:** `CONSTRAINT unique_source_record UNIQUE (source, source_id)`

### Table 5: `planted_plants` (Phase 8 Preparation)
Stores RSWF verified plantation records.
- `id` (BIGSERIAL PRIMARY KEY)
- `plant_code` (VARCHAR UNIQUE NOT NULL e.g. "PL001")
- `status` (VARCHAR NOT NULL DEFAULT 'Alive')
- `geom` (`GEOMETRY(Point, 4326)` NOT NULL)
- **Constraint:** `CONSTRAINT valid_plant_status CHECK (status IN ('Alive', 'Dead', 'Unknown'))`

### Table 6: `ai_predictions` (Phase 10/11 Preparation)
Stores ML plant identification inferences and human verification.
- `id` (BIGSERIAL PRIMARY KEY)
- `observation_id` (BIGINT REFERENCES `observations(id)`)
- `confidence_score` (NUMERIC(5, 4))
- `model_version` (VARCHAR DEFAULT 'EfficientNet-B0-v1')
- `top_3_predictions` (JSONB)
- `user_confirmed` (BOOLEAN)
- `final_accepted_taxon_id` (INTEGER REFERENCES `taxonomic_taxa(id)`)

---

## ⚡ 4. Spatial Indexing & Constraints

```sql
CREATE INDEX idx_obs_geom ON observations USING GIST (geom);
CREATE INDEX idx_planted_geom ON planted_plants USING GIST (geom);
CREATE INDEX idx_boundary_geom ON geography_boundaries USING GIST (geom);
CREATE INDEX idx_zones_geom ON geography_zones USING GIST (geom);
CREATE INDEX idx_obs_source ON observations (source);
CREATE INDEX idx_obs_zone ON observations (zone_code);
CREATE INDEX idx_obs_taxon ON observations (taxon_id);
```

---

## 📁 5. Created Files & Modules

- **DDL Schema Script:** [`database/schema/01_init_postgis_schema.sql`](file:///c:/Users/ppriy/OneDrive/Desktop/semester%205/Service%20Learning%20NGO/database/schema/01_init_postgis_schema.sql)
- **Geography Seeder:** [`database/seeds/seed_geography.py`](file:///c:/Users/ppriy/OneDrive/Desktop/semester%205/Service%20Learning%20NGO/database/seeds/seed_geography.py)
- **iNaturalist Data Seeder:** [`database/seeds/seed_inaturalist_clean.py`](file:///c:/Users/ppriy/OneDrive/Desktop/semester%205/Service%20Learning%20NGO/database/seeds/seed_inaturalist_clean.py)
- **Setup Script:** [`scripts/setup_database.py`](file:///c:/Users/ppriy/OneDrive/Desktop/semester%205/Service%20Learning%20NGO/scripts/setup_database.py)
- **Validation Script:** [`scripts/validate_database.py`](file:///c:/Users/ppriy/OneDrive/Desktop/semester%205/Service%20Learning%20NGO/scripts/validate_database.py)

---

## 🚀 6. Setup & Execution Instructions

To execute database schema creation, geography seeding, and Phase 3 iNaturalist data import:

```bash
# 1. Ensure PostgreSQL with PostGIS extension is running on target host
# 2. Configure connection string via environment variable:
export DATABASE_URL="postgresql://username:password@localhost:5432/van_udyan_db"

# 3. Run database setup pipeline
python scripts/setup_database.py

# 4. Run database validation suite
python scripts/validate_database.py
```
