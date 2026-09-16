# Phase 12 — Plant Status & Survival Monitoring Architecture

## 1. Executive Summary

The **Van Udyan Biodiversity Intelligence Platform** extends the RSWF Planted Plants management system to support long-term condition monitoring visits and plant survival analytics across Bavdhan Van Udyan intervention zones.

### Key Capabilities:
1. **Chronological Monitoring Visits:** Multiple inspection visit records per planted plant are saved sequentially over time without overwriting previous visit history.
2. **Standardized Condition Statuses:** Supports three standardized condition states:
   - `Alive` (Healthy / Growing)
   - `Dead` (Withered / Dry)
   - `Unknown` (Unverified / Tag Missing)
3. **Dynamic Survival Analytics:** Survival rates are calculated dynamically from database records as `Alive / (Alive + Dead) * 100`, handling zero-denominator edge cases safely. `Unknown` statuses are excluded from numerator and denominator calculations.
4. **Zone-Wise Mortality Insights:** Calculates plant counts, mortality rates, and empirical conservation insights across `ZONE A`, `ZONE B`, and `ZONE C`.

---

## 2. Monitoring Workflow Architecture

```
                  +-------------------------------+
                  | Planted Plant (planted_plants)|
                  +-------------------------------+
                                  |
                                  v
                  +-------------------------------+
                  | Field Inspection Visit        |
                  | (status, date, notes, observer)|
                  +-------------------------------+
                                  |
                                  v
                  +-------------------------------+
                  | plant_monitoring DDL Table    |
                  | & Database Repository         |
                  +-------------------------------+
                                  |
                                  v
                  +-------------------------------+
                  | Plant Current Status Updated  |
                  | & Survival Rate Analytics     |
                  +-------------------------------+
```

---

## 3. Database Design & ORM Model

The `plant_monitoring` relational table tracks chronological inspection visits:

```sql
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
```

---

## 4. Plant Monitoring REST API Endpoints

### 1. Log Monitoring Visit
- **Endpoint:** `POST /api/v1/planted-plants/{id}/monitoring`
- **Request Body (`PlantMonitoringCreate`):**
  ```json
  {
    "status": "Alive",
    "monitoring_date": "2026-07-15",
    "notes": "Sapling height 1.2m, foliage healthy",
    "observer": "RSWF Field Team"
  }
  ```
- **Validations:** Rejects invalid plant IDs (`404`), invalid status strings (`400`), and invalid ISO dates (`400`).

### 2. Retrieve Monitoring Visit History
- **Endpoint:** `GET /api/v1/planted-plants/{id}/monitoring`
- **Response:** Chronological array of visit history records for `planted_plant_id`.

### 3. Retrieve Survival & Zone Analytics
- **Endpoint:** `GET /api/v1/planted-plants/monitoring/statistics`
- **Response Payload:**
  ```json
  {
    "total_planted": 3,
    "alive_count": 3,
    "dead_count": 0,
    "unknown_count": 0,
    "survival_rate": "100.0%",
    "zone_breakdown": {
      "ZONE A": { "total_planted": 1, "alive": 1, "dead": 0, "unknown": 0, "survival_rate": "100.0%" },
      "ZONE B": { "total_planted": 1, "alive": 1, "dead": 0, "unknown": 0, "survival_rate": "100.0%" },
      "ZONE C": { "total_planted": 1, "alive": 1, "dead": 0, "unknown": 0, "survival_rate": "100.0%" }
    },
    "insights": [
      "Overall plant survival rate across Van Udyan active zones stands at 100.0%."
    ]
  }
  ```

---

## 5. Testing & Validation

### Pytest Unit Tests (`backend/tests/test_monitoring.py` — 15/15 Passed):
- Create monitoring records (`Alive`, `Dead`, `Unknown`)
- Rejection of invalid status values (`400 Bad Request`)
- Rejection of nonexistent plant IDs (`404 Not Found`)
- Rejection of invalid ISO date formats (`400 Bad Request`)
- Chronological history preservation across multiple visit logs
- Auto-updating of latest condition status on plant record
- Survival rate calculation and zero-denominator handling
- Zone-wise breakdown analytics
- Data provenance and dataset isolation

---

## 6. Known Limitations & Future Work

- **Separation of Taxonomy:** Plant identity and condition status remain strictly decoupled. AI species predictions never overwrite plant condition status.
- **Photo Attachments:** Monitoring records support optional photo reference paths pointing to Phase 9 geotagged photo uploads.
