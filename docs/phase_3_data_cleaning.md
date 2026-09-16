# 🧹 Phase 3 — Data Cleaning & Standardization Report

---

## 📌 1. Phase 3 Objective
The objective of Phase 3 is to clean, standardize, and format the Phase 2 iNaturalist dataset into a production-grade, reproducible dataset suitable for future database insertion (PostgreSQL/PostGIS), web mapping, and AI classification.

---

## 📊 2. Input / Output Dataset Accounting

| Dataset Stage | File Location | Record Count |
| :--- | :--- | :---: |
| **Raw API Source (Untouched)** | [`data/raw/inaturalist/observations_raw.json`](file:///c:/Users/ppriy/OneDrive/Desktop/semester%205/Service%20Learning%20NGO/data/raw/inaturalist/observations_raw.json) | **331** |
| **Phase 2 Processed Dataset** | [`data/processed/inaturalist/observations_van_udyan.csv`](file:///c:/Users/ppriy/OneDrive/Desktop/semester%205/Service%20Learning%20NGO/data/processed/inaturalist/observations_van_udyan.csv) | **227** |
| **Phase 3 Cleaned Dataset** | [`data/processed/inaturalist/observations_van_udyan_clean.csv`](file:///c:/Users/ppriy/OneDrive/Desktop/semester%205/Service%20Learning%20NGO/data/processed/inaturalist/observations_van_udyan_clean.csv) | **227** |

### Accounting Summary
- **Input Records:** `227`
- **Duplicate Observation IDs:** `0`
- **Records Removed:** `0`
- **Output Records:** `227`
- **Data Preservation Rate:** **100%** (No valid source observations destroyed or discarded)

---

## 🔍 3. Missing-Value Analysis (Before vs. After Cleaning)

| Column Field | Data Type | Missing Count (Before) | Missing Count (After) | Representation Strategy |
| :--- | :--- | :---: | :---: | :--- |
| `observation_id` | `String` / `Int` | 0 | 0 | Unique iNaturalist Primary Key |
| `taxon_id` | `String` / `Int` | 4 | 4 | Empty String `""` (Preserved missing) |
| `species_name` | `String` | 4 | 4 | Empty String `""` (Unidentified observations) |
| `scientific_name` | `String` | 4 | 4 | Empty String `""` (Unidentified observations) |
| `common_name` | `String` | 4 | 4 | Empty String `""` (No common name available) |
| `taxon_rank` | `String` | 4 | 4 | Empty String `""` (Unclassified rank) |
| `latitude` | `Float` | 0 | 0 | WGS84 Decimal Degrees |
| `longitude` | `Float` | 0 | 0 | WGS84 Decimal Degrees |
| `observed_on` | `Date String` | 1 | 1 | Standardized ISO `YYYY-MM-DD` |
| `quality_grade` | `String` | 0 | 0 | `research` / `needs_id` / `casual` |
| `observer` | `String` | 0 | 0 | iNaturalist handle |
| `photo_url` | `String` | 3 | 3 | Empty String `""` (No photo attached) |
| `zone` | `String` | 104 | 104 | Empty String `""` for `OUTSIDE_ACTIVE_ZONES` |
| `zone_status` | `String` | 0 | 0 | `ACTIVE_ZONE` vs `OUTSIDE_ACTIVE_ZONES` |

*(Note: Missing values are represented cleanly as empty strings `""` rather than fabricated placeholder text such as `"Unknown"` or `"None"`).*

---

## 🛠️ 4. Transformations & Standardization Applied

1. **Header & Schema Standardization:** Standardized all CSV column headers to strict, consistent `snake_case` naming.
2. **Numeric ID Cleanup:** Formatted `observation_id` and `taxon_id` as clean integer strings, stripping float notation (e.g. `47122` instead of `47122.0`).
3. **Taxonomic Preservation:** Preserved original taxonomic names without guessing or forced reclassification.
4. **ISO Date Formatting:** Formatted `observed_on` into standard `YYYY-MM-DD` strings.
5. **Coordinate Validation:** Verified `latitude` and `longitude` numeric types, valid WGS84 bounds, and rounded floating point precision to 8 decimal places.
6. **Spatial Boundary Re-Verification:** Confirmed via Shapely point-in-polygon checks that **100% of cleaned records (227/227)** fall within the exact `van_udyan_boundary.geojson` polygon.
7. **Zone Consistency:** Enforced consistent zone values (`ZONE A`, `ZONE B`, `ZONE C`, or `""`) and status tags (`ACTIVE_ZONE` or `OUTSIDE_ACTIVE_ZONES`).
8. **Lineage Enforcment:** Retained original `observation_id` and `source = "iNaturalist"` tags.

---

## 📁 5. Created Datasets & Artifacts

- **Cleaned Dataset:** [`data/processed/inaturalist/observations_van_udyan_clean.csv`](file:///c:/Users/ppriy/OneDrive/Desktop/semester%205/Service%20Learning%20NGO/data/processed/inaturalist/observations_van_udyan_clean.csv)
- **Cleaning Metadata:** [`data/processed/inaturalist/cleaning_metadata.json`](file:///c:/Users/ppriy/OneDrive/Desktop/semester%205/Service%20Learning%20NGO/data/processed/inaturalist/cleaning_metadata.json)
- **Cleaning Script:** [`scripts/clean_inaturalist_data.py`](file:///c:/Users/ppriy/OneDrive/Desktop/semester%205/Service%20Learning%20NGO/scripts/clean_inaturalist_data.py)
- **Validation Script:** [`scripts/validate_phase3.py`](file:///c:/Users/ppriy/OneDrive/Desktop/semester%205/Service%20Learning%20NGO/scripts/validate_phase3.py)

---

## 🔄 6. Reproduction Instructions

To re-run the Phase 3 cleaning and validation pipeline at any time:

```bash
# Execute Phase 3 cleaning script
python scripts/clean_inaturalist_data.py

# Execute Phase 3 automated validation suite
python scripts/validate_phase3.py
```
