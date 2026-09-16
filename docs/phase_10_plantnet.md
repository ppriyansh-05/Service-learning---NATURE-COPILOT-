# Phase 10 — Pl@ntNet AI Plant Identification Architecture

## 1. Executive Summary & AI Strategy Decision

The **Van Udyan Biodiversity Intelligence Platform** integrates the official **Pl@ntNet REST API** as its primary AI plant species identification engine for field photographs uploaded by Reform Social Welfare Foundation (RSWF) volunteers.

### AI Strategy Decision:
- **Primary AI Engine:** Pl@ntNet REST API (`https://myapi.plantnet.org/v2/identify/all`).
- **Deferred Feature:** Custom **EfficientNet-B0** transfer learning model training is **DEFERRED**.
- **Rationale:**
  1. RSWF NGO field teams require an immediate, accurate plant identification tool.
  2. Local image training data from Bavdhan Van Udyan is currently insufficient for training a high-accuracy custom vision model.
  3. Verified observations collected via Pl@ntNet + human verification will systematically build the dataset required for future custom model training on Google Colab.

---

## 2. API Architecture & Security Boundary

To protect API credentials and enforce security boundaries, the frontend Single Page Application (SPA) **NEVER** communicates directly with Pl@ntNet. All AI identification requests are proxied through our FastAPI backend.

```
+-------------------+             +-----------------------+             +----------------------+
| NGO Dashboard UI  |  =========> | FastAPI Backend API   |  =========> | Pl@ntNet REST API    |
| (HTML5 / JS SPA)  |  <========= | (app/services/...)    |  <========= | (myapi.plantnet.org) |
+-------------------+             +-----------------------+             +----------------------+
                                             |
                                             v
                                  +--------------------+
                                  | PostgreSQL / DB    |
                                  | ai_predictions     |
                                  +--------------------+
```

### Database Persistence Architecture (Phase 10.1 Cleanup):
- **Central Source of Truth:** AI predictions are persisted in the PostgreSQL/PostGIS `ai_predictions` database table (and `AIPrediction` ORM repository model).
- **No JSON File Storage:** The application no longer relies on `ai_predictions_store.json` for normal prediction storage or retrieval.
- **Traceability:** Multiple prediction attempts for an observation are saved as distinct rows in the database, ensuring full auditability of AI identification attempts over time.
- **Human Verification Isolation:** User confirmations/corrections update `user_confirmed = True` and observation taxonomy while preserving original AI prediction rows intact.

### Security Principles:
- `PLANTNET_API_KEY` is loaded exclusively on the server from environment variables (`.env`).
- The API key is **never** sent to the browser, rendered in HTML, logged in console outputs, or exposed in error tracebacks.
- `.env` is listed in `.gitignore` to prevent accidental credential commits.
- Template configuration is documented in `.env.example`.

---

## 3. Plant Organ & Prediction Normalization

Pl@ntNet API allows optional specifying of plant organ context for higher identification precision:
- `auto` (Default — auto-detection)
- `leaf` (Foliage & leaf structural patterns)
- `flower` (Floral blossoms & inflorescence)
- `fruit` (Fruit, seeds, seed pods)
- `bark` (Trunk texture & bark surface)
- `habit` (Whole plant habit & growth form)

### Prediction Normalization (Top 3):
Each identification response is parsed and normalized into the Top 3 structured predictions:

```json
{
  "observation_id": 229,
  "identification_status": "ai_suggested",
  "provider": "Pl@ntNet",
  "organ_used": "leaf",
  "top_prediction": {
    "rank": 1,
    "scientific_name": "Azadirachta indica",
    "common_name": "Neem",
    "family": "Meliaceae",
    "confidence": 0.9452,
    "confidence_percentage": "94.5%",
    "confidence_level": "HIGH CONFIDENCE"
  },
  "predictions": [ ... Top 3 Items ... ]
}
```

---

## 4. Confidence Level Classification

Predictions are classified into standardized application confidence thresholds:

| Score Range | Confidence Level Badge | Dashboard Representation |
| :---: | :---: | :--- |
| **>= 90.0%** | `HIGH CONFIDENCE` (🟢 Emerald) | Strong AI match — AI suggestion pending verification |
| **60.0% – 89.9%** | `MEDIUM CONFIDENCE` (🟡 Amber) | Moderate AI match — Review top 3 candidates |
| **< 60.0%** | `LOW CONFIDENCE` (🔴 Red) | Weak match — Human inspection recommended |

> [!IMPORTANT]
> **Data Quality Directive:** AI predictions are labeled as *"AI Suggestions — Not Yet Verified"*. They do **NOT** automatically increment official biodiversity species counts until confirmed or corrected by human verifiers.

---

## 5. API Endpoints & Failure Resilience

### REST API Endpoints:
1. `POST /api/v1/observations/{id}/identify?organ=leaf`
   - Triggers Pl@ntNet identification for an uploaded photo observation.
   - Saves prediction records in `ai_predictions` store.
2. `GET /api/v1/observations/{id}/predictions`
   - Retrieves stored Pl@ntNet predictions for an observation.
3. `POST /api/v1/observations/{id}/verify`
   - Accepts human verification (`scientific_name`, `common_name`, `verification_status`).
   - Updates observation status to `"verified"` or `"corrected"`.
   - **Preserves original AI predictions intact without overwriting.**

### Outage & Failure Resilience:
- A Pl@ntNet API outage, rate limit, timeout, or missing API key **NEVER** deletes or invalidates a spatially verified photo observation.
- If AI identification fails, the observation remains safely stored with status `"identification_failed"`, allowing manual verification or retry later.

---

## 6. Testing & Automated Mocking Strategy

All automated unit tests in [`backend/tests/test_plantnet.py`](file:///c:/Users/ppriy/OneDrive/Desktop/semester%205/Service%20Learning%20NGO/backend/tests/test_plantnet.py) mock the external Pl@ntNet HTTP provider completely. Zero real API calls are executed during test runs.

### Test Coverage (9/9 Passed):
- Confidence level classification thresholds
- Missing API key error handling (`MISSING_API_KEY`)
- Invalid API key error handling (`INVALID_API_KEY`)
- Rate limit handling (`RATE_LIMIT_EXCEEDED`)
- Network timeout handling (`REQUEST_FAILED`)
- Response parsing & Top 3 normalization
- Endpoint integration `POST /api/v1/observations/{id}/identify`
- Human verification flow `POST /api/v1/observations/{id}/verify`
- Original iNaturalist reference dataset protection (227 records intact)

---

## 7. Future EfficientNet-B0 Roadmap

When field volunteers collect sufficient verified images across Bavdhan Van Udyan plant species, Phase 10's deferred custom vision pipeline will be activated:
1. Export verified image dataset categorized by species.
2. Train EfficientNet-B0 transfer learning classifier via PyTorch on Google Colab GPU instances.
3. Evaluate F1-score & accuracy metrics against Pl@ntNet baseline.
4. Deploy custom ONNX runtime model container for offline/local inference.
