-- =====================================================================
-- Phase 4 — PostgreSQL + PostGIS Schema Definition
-- Van Udyan Biodiversity Intelligence Platform
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS postgis;

-- 1. Geography Boundaries Table (Van Udyan Complete Boundary Polygon)
CREATE TABLE IF NOT EXISTS geography_boundaries (
    id SERIAL PRIMARY KEY,
    site_code VARCHAR(50) UNIQUE NOT NULL DEFAULT 'BAVDHAN_VAN_UDYAN',
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL DEFAULT 'complete_boundary',
    plus_code VARCHAR(50) DEFAULT 'GQ9J+74Q',
    address TEXT DEFAULT 'Lantana Gardens, Bavdhan, Pune, Maharashtra 411021',
    geom GEOMETRY(Polygon, 4326) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 2. Geography Active Zones Table (Zone A, Zone B, Zone C Polygons)
CREATE TABLE IF NOT EXISTS geography_zones (
    id SERIAL PRIMARY KEY,
    zone_code VARCHAR(50) UNIQUE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE_ZONE',
    description TEXT,
    geom GEOMETRY(Polygon, 4326) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 3. Taxonomic Taxa Reference Table
CREATE TABLE IF NOT EXISTS taxonomic_taxa (
    id SERIAL PRIMARY KEY,
    taxon_id VARCHAR(50) UNIQUE,
    scientific_name VARCHAR(255) NOT NULL,
    species_name VARCHAR(255),
    common_name VARCHAR(255),
    taxon_rank VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 4. Central Observations Table (iNaturalist + New User Uploads)
CREATE TABLE IF NOT EXISTS observations (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL DEFAULT 'iNaturalist',
    source_id VARCHAR(100),
    taxon_id INTEGER REFERENCES taxonomic_taxa(id) ON DELETE SET NULL,
    scientific_name VARCHAR(255),
    common_name VARCHAR(255),
    observed_on DATE,
    quality_grade VARCHAR(50),
    observer VARCHAR(100),
    observation_url TEXT,
    photo_url TEXT,
    latitude NUMERIC(10, 8) NOT NULL,
    longitude NUMERIC(11, 8) NOT NULL,
    geom GEOMETRY(Point, 4326) NOT NULL,
    zone_id INTEGER REFERENCES geography_zones(id) ON DELETE SET NULL,
    zone_code VARCHAR(50),
    zone_status VARCHAR(50) NOT NULL DEFAULT 'OUTSIDE_ACTIVE_ZONES',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_source_record UNIQUE (source, source_id)
);

-- 5. Planted Plants Table (RSWF Plantation Dataset — Ready for Phase 8)
CREATE TABLE IF NOT EXISTS planted_plants (
    id BIGSERIAL PRIMARY KEY,
    plant_code VARCHAR(100) UNIQUE NOT NULL,
    source VARCHAR(50) NOT NULL DEFAULT 'Planted',
    taxon_id INTEGER REFERENCES taxonomic_taxa(id) ON DELETE SET NULL,
    scientific_name VARCHAR(255),
    common_name VARCHAR(255),
    planted_on DATE,
    status VARCHAR(50) NOT NULL DEFAULT 'Alive',
    latitude NUMERIC(10, 8) NOT NULL,
    longitude NUMERIC(11, 8) NOT NULL,
    geom GEOMETRY(Point, 4326) NOT NULL,
    zone_id INTEGER REFERENCES geography_zones(id) ON DELETE SET NULL,
    zone_code VARCHAR(50),
    photo_url TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_plant_status CHECK (status IN ('Alive', 'Dead', 'Unknown'))
);

-- 6. AI Plant Predictions Table (Ready for Phase 10 & Phase 11 ML Workflow)
CREATE TABLE IF NOT EXISTS ai_predictions (
    id BIGSERIAL PRIMARY KEY,
    observation_id BIGINT REFERENCES observations(id) ON DELETE CASCADE,
    predicted_taxon_id INTEGER REFERENCES taxonomic_taxa(id) ON DELETE SET NULL,
    predicted_scientific_name VARCHAR(255),
    confidence_score NUMERIC(5, 4) CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    model_version VARCHAR(50) DEFAULT 'EfficientNet-B0-v1',
    top_3_predictions JSONB,
    user_confirmed BOOLEAN,
    final_accepted_taxon_id INTEGER REFERENCES taxonomic_taxa(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 7. Plant Monitoring History Table (Phase 12 Survival Monitoring)
CREATE TABLE IF NOT EXISTS plant_monitoring (
    id BIGSERIAL PRIMARY KEY,
    planted_plant_id BIGINT REFERENCES planted_plants(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL DEFAULT 'Alive',
    monitoring_date DATE NOT NULL,
    notes TEXT,
    photo_url TEXT,
    observer VARCHAR(255) DEFAULT 'RSWF Field Team',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_monitoring_status CHECK (status IN ('Alive', 'Dead', 'Unknown'))
);

-- Spatial & Performance Indexing
CREATE INDEX IF NOT EXISTS idx_obs_geom ON observations USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_planted_geom ON planted_plants USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_boundary_geom ON geography_boundaries USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_zones_geom ON geography_zones USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_obs_source ON observations (source);
CREATE INDEX IF NOT EXISTS idx_obs_zone ON observations (zone_code);
CREATE INDEX IF NOT EXISTS idx_obs_taxon ON observations (taxon_id);
CREATE INDEX IF NOT EXISTS idx_obs_date ON observations (observed_on);
