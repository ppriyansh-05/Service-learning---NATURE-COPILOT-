# 🌿 Phase 2 — iNaturalist Data Collection & Spatial Verification Report

---

## 📌 1. Phase 2 Objective
The primary goal of Phase 2 is to collect publicly available biodiversity observations from the official iNaturalist API for the Bavdhan Van Udyan site, validate their coordinates, and perform exact **point-in-polygon spatial verification** against the WGS84 Van Udyan boundary geometry ([`data/raw/van_udyan_boundary.geojson`](file:///c:/Users/ppriy/OneDrive/Desktop/semester%205/Service%20Learning%20NGO/data/raw/van_udyan_boundary.geojson)) and active NGO working zones ([`data/raw/van_udyan_zones.geojson`](file:///c:/Users/ppriy/OneDrive/Desktop/semester%205/Service%20Learning%20NGO/data/raw/van_udyan_zones.geojson)).

---

## 🌐 2. API Source & Access Specifications

- **Official API Endpoint:** `https://api.inaturalist.org/v1/observations`
- **API Documentation:** [https://api.inaturalist.org/v1/docs/](https://api.inaturalist.org/v1/docs/)
- **Authentication Status:** **NO AUTHENTICATION REQUIRED**. The public read-only endpoint was queried without API keys, tokens, or credentials.
- **Access Protocol:** Polite HTTP GET requests with custom User-Agent headers (`VanUdyanBiodiversityIntelligencePlatform/1.0`).
- **Retrieval Bounding Box (Padded):**
  - **Southwest Corner (SW):** `Latitude 18.514915° N, Longitude 73.775825° E`
  - **Northeast Corner (NE):** `Latitude 18.523114° N, Longitude 73.784342° E`
  *(Note: The bounding box is used purely as a broad API retrieval mechanism; the exact Van Udyan polygon is the sole spatial authority).*

---

## 📊 3. Ingestion & Spatial Verification Summary Metrics

| Metric Category | Metric Name | Value / Count |
| :--- | :--- | :---: |
| **Raw Ingestion** | Total Candidates Retrieved from API | **331** |
| **Coordinate Check** | Observations with Usable Coordinates | **331** |
| **Coordinate Check** | Observations without Usable Coordinates | **0** |
| **Spatial Filtering** | **Spatially Verified INSIDE Van Udyan** | **227** |
| **Spatial Filtering** | Excluded OUTSIDE Van Udyan (Candidates outside polygon) | **104** |
| **Zone Allocation** | Active Working Zone — **ZONE A** | **60** |
| **Zone Allocation** | Active Working Zone — **ZONE B** | **37** |
| **Zone Allocation** | Active Working Zone — **ZONE C** | **26** |
| **Zone Allocation** | **Inside Van Udyan but Outside Active Zones** (`OUTSIDE_ACTIVE_ZONES`) | **104** |
| **Taxonomic Metrics** | Unique Recorded Species / Taxa | **88** |
| **Quality & Safety** | Duplicate Records Found | **0** |
| **Quality & Safety** | API Errors / Warnings | **0** |

---

## 🗺️ 4. Spatial Interpretation & Zone Breakdown

### 📢 Core Spatial Concept
- **`VAN UDHYAN` Polygon:** Enforces the complete project area boundary.
- **`ZONE A`, `ZONE B`, `ZONE C` Polygons:** Represent current active RSWF NGO intervention/monitoring areas.
- **Outside Active Zone Handling:** Observations located inside the Van Udyan outer boundary but outside Zone A, B, and C (104 records) are tagged as `zone = ""` and `zone_status = "OUTSIDE_ACTIVE_ZONES"`. **These observations are retained in the dataset** as valid project data for future zone expansion.

```
       TOTAL API CANDIDATES RETRIEVED (331)
                        │
       ┌────────────────┴────────────────┐
       ▼                                 ▼
INSIDE VAN UDYAN (227)          OUTSIDE VAN UDYAN (104)
       │                        (Excluded from dataset)
 ┌─────┼─────┬────────────┐
 ▼     ▼     ▼            ▼
ZONE A ZONE B ZONE C  OUTSIDE ACTIVE ZONES
 (60)   (37)   (26)       (104 Retained)
```

---

## 📂 5. Output Datasets & Structure

- **Raw API JSON Dataset:** [`data/raw/inaturalist/observations_raw.json`](file:///c:/Users/ppriy/OneDrive/Desktop/semester%205/Service%20Learning%20NGO/data/raw/inaturalist/observations_raw.json)
- **Ingestion Metadata:** [`data/raw/inaturalist/ingestion_metadata.json`](file:///c:/Users/ppriy/OneDrive/Desktop/semester%205/Service%20Learning%20NGO/data/raw/inaturalist/ingestion_metadata.json)
- **Spatially Verified Processed Dataset:** [`data/processed/inaturalist/observations_van_udyan.csv`](file:///c:/Users/ppriy/OneDrive/Desktop/semester%205/Service%20Learning%20NGO/data/processed/inaturalist/observations_van_udyan.csv)

### CSV Schema Fields (`observations_van_udyan.csv`)
1. `observation_id` (Unique iNaturalist ID)
2. `taxon_id` (Taxon ID)
3. `species_name` (Species name)
4. `scientific_name` (Scientific binomial name)
5. `common_name` (Vernacular common name)
6. `taxon_rank` (Taxonomic rank e.g. species, genus)
7. `latitude` (WGS84 Latitude decimal degrees)
8. `longitude` (WGS84 Longitude decimal degrees)
9. `observed_on` (Date of field observation)
10. `quality_grade` (iNaturalist quality grade: research, needs_id, casual)
11. `observer` (iNaturalist observer handle)
12. `observation_url` (Direct iNaturalist web URL)
13. `photo_url` (Photo URL reference)
14. `created_at` (Record creation timestamp)
15. `updated_at` (Record update timestamp)
16. `source` (`"iNaturalist"`)
17. `zone` (`"ZONE A"`, `"ZONE B"`, `"ZONE C"`, or `""`)
18. `zone_status` (`"ACTIVE_ZONE"` or `"OUTSIDE_ACTIVE_ZONES"`)

---

## ⚠️ 6. Important Limitations & Biodiversity Interpretation Rule

> **CRITICAL RULE:** A low observation count in a specific zone or unzoned area does **NOT** indicate "low biodiversity." iNaturalist observation counts represent **recorded public observations**, not an exhaustive ecological survey.

---

## 🔄 7. Reproduction Instructions

To re-run the entire Phase 2 ingestion and verification pipeline at any time:

```bash
# Run reproducible iNaturalist ingestion pipeline
python scripts/run_inaturalist_ingestion.py

# Run Phase 2 automated validation suite
python scripts/validate_phase2.py
```
