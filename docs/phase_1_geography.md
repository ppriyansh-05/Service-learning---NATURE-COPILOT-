# 🗺️ Phase 1 — Van Udyan Geographical Foundation & Spatial Documentation

---

## 📌 1. Project Location & Site Details

- **Site Name:** Bavdhan Van Udyan
- **Plus Code:** `GQ9J+74Q`
- **Address:** Lantana Gardens, Bavdhan, Pune, Maharashtra 411021
- **Geographic Source File:** `scripts/Bavdhan van udyan.kmz` (Extracted from Google My Maps manually created KMZ)
- **Coordinate Reference System (CRS):** `WGS84` / `EPSG:4326` (Latitude / Longitude decimal degrees)

---

## 📐 2. Spatial Hierarchy & Zone Semantics

```
                       BAVDHAN VAN UDYAN
                   (Complete Project Boundary)
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
     ZONE A                  ZONE B                  ZONE C
 (Active RSWF            (Active RSWF            (Active RSWF
Intervention Area)      Intervention Area)      Intervention Area)
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                ▼
                       OTHER / UNZONED AREAS
               (Retained as part of overall site;
               Eligible for future active expansion)
```

### 📢 Key Spatial Interpretation Rule
> **"Van Udyan represents the complete geographical project area. Zone A, Zone B and Zone C represent the current RSWF intervention/monitoring areas within Van Udyan. Areas outside these active zones remain part of the overall Van Udyan project area and may be incorporated into future monitoring zones."**

- **Complete Boundary (`VAN UDHYAN`):** Represents the entire geographic extent of the Van Udyan conservation project area.
- **Active Working Zones (`ZONE A`, `ZONE B`, `ZONE C`):** Represent specific sub-regions where RSWF currently has active manpower and monitoring operations. They do not cover the whole site.
- **Data Filtering Behavior:** Observations inside Van Udyan are valid biodiversity data regardless of whether they fall within Zone A/B/C or in the unzoned portion of Van Udyan.

---

## 📊 3. Polygons & Geometry Summary

| Polygon Name | Type | Vertices Count | Bounding Box (Lon Min, Lat Min, Lon Max, Lat Max) | Spatial Relation |
| :--- | :--- | :---: | :--- | :--- |
| **VAN UDHYAN** | Complete Boundary | 12 | (73.778825, 18.517915, 73.813422, 18.520114) | Encloses all active zones |
| **ZONE A** | Active Work Zone | 7 | (73.780051, 18.518285, 73.780645, 18.518829) | Completely inside Boundary; Disjoint |
| **ZONE B** | Active Work Zone | 8 | (73.779886, 18.518648, 73.780399, 18.519053) | Completely inside Boundary; Disjoint |
| **ZONE C** | Active Work Zone | 13 | (73.779760, 18.518820, 73.780260, 18.519596) | Completely inside Boundary; Disjoint |

---

## 📁 4. Created Datasets & Files

- **`scripts/Bavdhan van udyan.kmz`**: Source KMZ archive containing `doc.kml`.
- **`scripts/extract_kmz_to_geojson.py`**: Automated extraction script converting KMZ polygons to GeoJSON.
- **`scripts/validate_geography.py`**: Automated spatial validation suite.
- **`data/raw/van_udyan_boundary.geojson`**: WGS84 GeoJSON containing the full Van Udyan boundary polygon.
- **`data/raw/van_udyan_zones.geojson`**: WGS84 GeoJSON containing Active Zones A, B, and C.
- **`data/processed/van_udyan_boundary.geojson`**: Processed boundary copy for backend & map rendering.
- **`data/processed/van_udyan_zones.geojson`**: Processed active zones copy.
- **`data/processed/van_udyan_master_geography.geojson`**: Combined FeatureCollection of all site geometries.

---

## ✅ 5. Validation Results Summary

The spatial validation script (`scripts/validate_geography.py`) executed with **100% PASS** on all criteria:

1. **File Existence & GeoJSON Syntax:** `PASS`
2. **Geometry Type (Polygon/MultiPolygon):** `PASS`
3. **Coordinate Ranges (WGS84 EPSG:4326):** `PASS`
4. **Closed Polygon Rings:** `PASS`
5. **Topology & Validity (Shapely):** `PASS`
6. **Active Zones Containment within Van Udyan:** `PASS` (Zone A, B, and C are 100% inside boundary)
7. **Active Zones Non-Overlap:** `PASS` (Zone A, B, and C are strictly disjoint with 0.0 intersection area)

---

## 🔮 6. Future Expansion Concept

As RSWF expands its volunteer capacity and project scope:
- Additional working zones (e.g., Zone D, Zone E) can be added to `data/raw/van_udyan_zones.geojson` without altering the `VAN UDHYAN` outer boundary.
- Observations collected prior to zone creation will automatically re-index to newly added zones.
