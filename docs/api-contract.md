# E-State — API Contract

> HTTP contract between `apps/web` and `services/api`. OpenAPI is the source of truth and is generated from the FastAPI app; TypeScript types are regenerated into `apps/web/src/lib/api/types.ts` on every schema change. Extends [data-model.md](data-model.md).

## 1. Conventions

- **Base URL:** `${NEXT_PUBLIC_API_URL}` (e.g. `https://api.e-state.example`).
- **Auth:** Bearer JWT for staff and inspectors; no auth on citizen endpoints (rate-limited + CAPTCHA).
- **Content type:** `application/json` for all endpoints except `/upload` (multipart).
- **Timezone:** All timestamps UTC, ISO-8601 with trailing `Z`.
- **Envelope:** Every non-error response uses:

  ```ts
  interface ApiResponse<T> {
    success: true
    data: T
    meta?: { total: number; page: number; limit: number }
  }
  ```

  Every error response:

  ```ts
  interface ApiError {
    success: false
    error: { code: string; message: string; field?: string }
  }
  ```

  `code` values come from a stable enum (`VALIDATION_ERROR`, `NOT_FOUND`, `CONFLICT`, `RATE_LIMITED`, `INTERNAL`, `UNAUTHORIZED`, `FORBIDDEN`, `PII_PROTECTED`).
- **Pagination:** `?page=1&limit=50`; `limit` capped at 200.
- **IDs:** all UUIDs are strings in JSON.

## 2. Endpoints

### 2.1 `POST /upload` — ingest a pair of registries

Request: `multipart/form-data`

| Field | Required | Notes |
|---|---|---|
| `zem` | yes | `.xlsx` or `.csv` for ДЗК |
| `ner` | yes | `.xlsx` or `.csv` for ДРРП |
| `label` | no | Human label for the dataset |

Response `201`:

```json
{
  "success": true,
  "data": {
    "dataset_id": "3c1b...",
    "label": "Сокаль 2026-04-18",
    "zem_rows": 21656,
    "ner_rows": 20382,
    "status": "ingesting"
  }
}
```

Errors: `VALIDATION_ERROR` (missing file, wrong headers), `CONFLICT` (same files re-uploaded within 60 s).

### 2.2 `POST /matcher/run`

Runs the full pipeline for a `dataset_id`. Idempotent — safe to call multiple times.

Request:

```json
{ "dataset_id": "3c1b..." }
```

Response `200`:

```json
{
  "success": true,
  "data": {
    "dataset_id": "3c1b...",
    "took_ms": 7420,
    "stats": {
      "critical": 38,
      "warning": 1204,
      "info": 5080,
      "by_type": {
        "LAND_NO_REAL_ESTATE": 612,
        "AREA_PORTFOLIO_DELTA": 38,
        "TERMINATED_BUT_ACTIVE": 5080,
        "OWNER_NAME_MISMATCH": 0,
        "MISSING_OWNER": 0,
        "DUPLICATE_REGISTRATION": 0,
        "USE_VS_OBJECT_MISMATCH": 0,
        "REAL_ESTATE_NO_LAND": 0
      }
    }
  }
}
```

### 2.3 `GET /findings`

Paginated list for the back-office table.

Query parameters:

| Name | Type | Notes |
|---|---|---|
| `dataset_id` | uuid | required |
| `severity` | `critical|warning|info` | repeatable |
| `status` | `open|in_review|resolved|dismissed` | repeatable, defaults to `open,in_review` |
| `finding_type` | enum | repeatable |
| `q` | string | fuzzy search over person name |
| `koatuu` | string | |
| `page`, `limit` | int | |

Response:

```json
{
  "success": true,
  "data": [
    {
      "id": "f1...",
      "dataset_id": "3c1b...",
      "person": {
        "tax_id_masked": "***4477",
        "full_name": "Малетич Тетяна Василівна"
      },
      "finding_type": "LAND_NO_REAL_ESTATE",
      "severity": "warning",
      "status": "open",
      "computed_metrics": { "residential_parcels": 1, "total_residential_m2": 1250 },
      "detected_at": "2026-04-18T10:22:19Z",
      "last_visit_id": null
    }
  ],
  "meta": { "total": 612, "page": 1, "limit": 50 }
}
```

Masking note: `tax_id_masked` for list views; full `tax_id` only on the detail endpoint for authenticated staff, and always after writing `audit_log`.

### 2.4 `GET /findings/{id}`

Detail view used by the back-office side-by-side and by the inspector on mobile. Returns the finding plus denormalized `land_parcels`, `real_estate`, and `evidence` blobs for the involved person.

```json
{
  "success": true,
  "data": {
    "finding": { /* as above, with full tax_id */ },
    "person": { "tax_id": "3580294477", "full_name": "Малетич Тетяна Василівна" },
    "land_parcels": [ /* LandParcel DTOs */ ],
    "real_estate":  [ /* RealEstate DTOs */ ],
    "visits":       [ /* FieldVisit DTOs, newest first */ ]
  }
}
```

### 2.5 `POST /inspector/visits`

Inspector submits a field-visit that resolves a finding.

Request:

```json
{
  "finding_id": "f1...",
  "photo_refs": [
    { "blob_key": "visits/2026-04-18/abc.jpg", "sha256": "...", "width": 3024, "height": 4032 }
  ],
  "actual_object_type": "ресторан",
  "actual_area_m2": 210.5,
  "actual_use": "Громадське харчування",
  "notes": "На ділянці діючий ресторан, вивіска 'Калина'.",
  "gps": { "lat": 50.4756, "lng": 24.2812, "acc_m": 8 }
}
```

Response `201`: returns the created `FieldVisit` and the updated `Finding` with `status: "resolved"`.

Errors: `FORBIDDEN` (inspector not assigned), `VALIDATION_ERROR` (missing photo refs when required by policy).

### 2.6 `POST /inspector/photos/presign`

Returns a short-lived presigned upload URL so the mobile client can PUT photos directly to object storage without passing them through the API.

```json
{ "content_type": "image/jpeg", "sha256": "...", "size_bytes": 2348923 }
```

Response:

```json
{
  "success": true,
  "data": {
    "upload_url": "https://...",
    "blob_key": "visits/2026-04-18/abc.jpg",
    "expires_at": "2026-04-18T10:45:00Z"
  }
}
```

### 2.7 `POST /citizen/lookup` — public, unauthenticated

Citizens enter their РНОКПП (tax ID) and see the status of their own records only. Tax ID is in the **request body**, never in the URL or query string (see [legal-compliance.md](legal-compliance.md)).

Request:

```json
{ "tax_id": "2247237363", "captcha_token": "..." }
```

Response `200`:

```json
{
  "success": true,
  "data": {
    "tax_id_masked": "***7363",
    "full_name": "Тодирюк Василь Тодорович",
    "summary": { "land_parcels": 1, "real_estate": 1 },
    "status": "synchronized",
    "findings_public": []
  }
}
```

`findings_public` is a **redacted** subset; it includes severity and finding_type labels translated into citizen-friendly language, but never cites specific neighbors' data.

Rate limit: 5 requests / 15 min / IP + CAPTCHA required.

### 2.8 `GET /reports/budget-impact`

Staff-only summary for the Голова ОТГ slide in the demo.

Query: `?dataset_id=...`

Response:

```json
{
  "success": true,
  "data": {
    "expected_tax_uplift_uah": 4820000,
    "by_finding_type": {
      "AREA_PORTFOLIO_DELTA": 1720000,
      "LAND_NO_REAL_ESTATE":  2640000,
      "TERMINATED_BUT_ACTIVE": 460000
    },
    "caveats": [
      "Rates from matcher/config.py; tune per ОТГ before publishing."
    ]
  }
}
```

## 3. DTO catalog

All DTOs live in `services/api/app/api/dto/` and are Pydantic v2 models. The corresponding TS types are emitted by:

```bash
pnpm --filter web run generate:api
```

which runs `openapi-typescript` against `http://localhost:8000/openapi.json` and writes `apps/web/src/lib/api/types.ts`. This is enforced by the `e-state-api-contracts` rule.

## 4. Error model (complete)

| `code` | HTTP | When |
|---|---|---|
| `VALIDATION_ERROR` | 400 | Zod/Pydantic validation failed |
| `UNAUTHORIZED` | 401 | Missing/invalid JWT for staff/inspector routes |
| `FORBIDDEN` | 403 | Role/ownership check failed |
| `NOT_FOUND` | 404 | Resource or dataset unknown |
| `CONFLICT` | 409 | Idempotency violation, duplicate upload |
| `RATE_LIMITED` | 429 | Citizen portal throttled |
| `PII_PROTECTED` | 422 | Citizen attempted lookup of another person |
| `INTERNAL` | 500 | Caught exception, logged with correlation id; never leaks stack |

## 5. Observability

- Every response carries `X-Request-ID`. The web client logs it with errors.
- FastAPI middleware writes a JSON log line per request with `duration_ms`, `route`, `status`, `actor_role`, `dataset_id` (when applicable). Tax IDs are masked to `***NNNN`.
