# Phase 11 — Human Verification & AI Feedback Loop Architecture

## 1. Executive Summary

The **Van Udyan Biodiversity Intelligence Platform** implements a formal human verification workflow and AI feedback loop for plant species identification. 

While **Pl@ntNet REST API** generates initial Top-3 predictions and confidence scores for uploaded plant photographs, field volunteers from Reform Social Welfare Foundation (RSWF) retain full authority over species verification. 

### Key Principles:
1. **AI Suggestion vs Human Verification:** AI predictions are labeled as *"AI Suggestions — Pending Human Verification"*. They do **NOT** count as official verified species occurrences until confirmed or corrected by human verifiers.
2. **Preservation of Original AI Predictions:** AI suggestions (predicted scientific name, common name, rank, confidence score, raw top 3 candidates) are stored permanently in the database repository and are **NEVER** overwritten or deleted.
3. **Separate Storage of Human Decisions:** Human choices (`confirm`, `correct`, `needs_review`, verifier species taxonomy, verification timestamp, and correction notes) are saved separately for ML performance evaluation and data quality control.
4. **Training Data Pipeline:** Verified observations form high-quality labeled training samples for the **FUTURE** transfer learning of a custom EfficientNet-B0 model on Google Colab.

---

## 2. Human Verification Workflow Architecture

```
                                 +-----------------------+
                                 | Geotagged Photo Upload|
                                 +-----------------------+
                                             |
                                             v
                                 +-----------------------+
                                 | Pl@ntNet AI Engine    |
                                 | (Top 3 Predictions)   |
                                 +-----------------------+
                                             |
                                             v
                                 +-----------------------+
                                 | Human Volunteer Review|
                                 +-----------------------+
                                             |
                   +-------------------------+-------------------------+
                   |                         |                         |
                   v                         v                         v
          [CONFIRM PREDICTION]     [MANUAL CORRECTION]      [NEEDS EXPERT REVIEW]
                   |                         |                         |
                   v                         v                         v
        status = 'verified'       status = 'corrected'     status = 'needs_review'
        quality = 'research'      quality = 'needs_id'     quality = 'needs_id'
                   |                         |                         |
                   +-------------------------+-------------------------+
                                             |
                                             v
                                 +-----------------------+
                                 | PostgreSQL / PostGIS  |
                                 | Audit & AI Feedback   |
                                 +-----------------------+
```

---

## 3. Database Design & ORM Model

The `ai_predictions` database schema tracks both the AI prediction and separate human verification decision:

```sql
CREATE TABLE IF NOT EXISTS ai_predictions (
    id BIGSERIAL PRIMARY KEY,
    observation_id BIGINT REFERENCES observations(id) ON DELETE CASCADE,
    provider VARCHAR(50) DEFAULT 'Pl@ntNet',
    organ_used VARCHAR(50) DEFAULT 'auto',
    predicted_scientific_name VARCHAR(255),
    predicted_common_name VARCHAR(255),
    confidence_score NUMERIC(5, 4),
    confidence_level VARCHAR(50),
    prediction_rank INTEGER DEFAULT 1,
    model_version VARCHAR(50) DEFAULT 'Pl@ntNet-v2',
    top_3_predictions JSONB,
    
    -- Separate Human Decision Storage --
    user_confirmed BOOLEAN DEFAULT FALSE,
    human_decision VARCHAR(50), -- 'confirm', 'correct', 'needs_review'
    verified_scientific_name VARCHAR(255),
    verified_common_name VARCHAR(255),
    verification_notes TEXT,
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

---

## 4. Verification API & Decision Options

### Endpoint:
`POST /api/v1/observations/{id}/verify`

### Request Body Schema (`ObservationVerificationRequest`):
```json
{
  "decision": "confirm",
  "selected_prediction_rank": 1,
  "scientific_name": "Azadirachta indica",
  "common_name": "Neem Tree",
  "notes": "Verified leaf structure pattern"
}
```

### Verification Decision Actions:

| Action | Decision String | Resulting `identification_status` | Resulting `quality_grade` | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Confirm AI Prediction** | `confirm` | `verified` | `research` | Verifier accepts Top 1, Top 2, or Top 3 AI suggestion. Observation taxonomy updated to selected prediction. |
| **Manual Correction** | `correct` | `corrected` | `needs_id` | Verifier overrides AI with manually entered scientific & common names. |
| **Needs Review** | `needs_review` | `needs_review` | `needs_id` | Verifier flags observation as ambiguous for expert botanist review. |

---

## 5. AI Feedback Loop Performance Metrics API

### Endpoint:
`GET /api/v1/observations/ai-feedback`

### Response Payload:
```json
{
  "total_ai_predictions_reviewed": 0,
  "total_confirmed": 0,
  "total_corrected": 0,
  "total_needs_review": 0,
  "confirmation_rate_percentage": "0.0%",
  "correction_rate_percentage": "0.0%",
  "evaluation_note": "No verified NGO AI evaluation data yet."
}
```

---

## 6. Testing & Regression Coverage

### Automated Unit Tests (`backend/tests/test_verification.py` — 13/13 Passed):
1. Confirm Top 1 Prediction
2. Confirm Top 2 Prediction
3. Confirm Top 3 Prediction
4. Manual Species Correction Flow
5. Needs Expert Review Flow
6. Server-Side Invalid Decision Rejection (HTTP 400)
7. Invalid Observation ID Handling (HTTP 404)
8. Protection of Read-Only iNaturalist Observations (HTTP 403)
9. Original AI Prediction Preservation (Fields intact)
10. Separate Human Decision Storage
11. Idempotent Repeated Verification Safety
12. AI Feedback Metrics Endpoint (`GET /observations/ai-feedback`)
13. iNaturalist Dataset Count Integrity (227 records unchanged)

---

## 7. Deferred Work & EfficientNet Roadmap

- **Custom Vision Training Status:** **DEFERRED (FUTURE GOAL)**
- **Reason:** Insufficient verified image data from Bavdhan Van Udyan currently.
- **Future Trigger:** As RSWF volunteers confirm and correct field observations, labeled image samples will be aggregated into an export package for transfer learning of an EfficientNet-B0 classifier on Google Colab GPU instances.
