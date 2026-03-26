# Scorecard API

> Base URL: `/api/v1/scorecard/`
> Swagger tags: **Scorecard** . **Scorecard -- Admin** . **Scorecard -- Staff**

Live operator scorecard that aggregates data from coverage, QoE, complaints,
and QoS records into a composite score per operator per month. Includes
configurable scoring weights and a leaderboard with trend tracking.

---

## Table of Contents

- [Endpoints Summary](#endpoints-summary)
- [Weights](#weights)
- [Scores](#scores)
- [Rankings](#rankings)
- [Manual Metrics](#manual-metrics)
- [Score Computation](#score-computation)
- [Models & Enums](#models--enums)
- [Seed Data](#seed-data)

---

## Endpoints Summary

### Public (no auth required)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/weights/` | Current scoring weight configuration |
| `GET` | `/scores/` | Latest scorecard for all operators |
| `GET` | `/scores/history/` | Monthly score history |
| `GET` | `/scores/{operator_code}/` | Single operator scorecard detail |
| `GET` | `/rankings/` | Operator leaderboard with trends |

### Staff / Admin

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `PUT` | `/weights/{dimension}/` | Admin | Update a scoring weight |
| `POST` | `/scores/compute/` | Admin | Trigger score recomputation |
| `GET` | `/manual-metrics/` | Staff | List manual metric entries |
| `POST` | `/manual-metrics/create/` | Staff | Add a manual metric entry |

---

## Weights

### GET `/weights/`

Returns the current weight configuration for all four scoring dimensions.

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Scorecard weights retrieved.",
  "data": [
    {
      "id": "uuid",
      "dimension": "COVERAGE",
      "dimension_display": "Network Coverage",
      "weight": "0.30",
      "description": "Average network coverage percentage across all districts and technologies.",
      "updated_at": "2026-03-25T12:00:00Z"
    },
    {
      "id": "uuid",
      "dimension": "QOE",
      "dimension_display": "Quality of Experience",
      "weight": "0.30",
      "description": "...",
      "updated_at": "..."
    },
    {
      "id": "uuid",
      "dimension": "COMPLAINTS",
      "dimension_display": "Complaint Handling",
      "weight": "0.20",
      "description": "...",
      "updated_at": "..."
    },
    {
      "id": "uuid",
      "dimension": "QOS",
      "dimension_display": "QoS Compliance",
      "weight": "0.20",
      "description": "...",
      "updated_at": "..."
    }
  ],
  "errors": null
}
```

---

### PUT `/weights/{dimension}/`

Update the weight for a specific dimension. Admin only.

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `dimension` | string | `COVERAGE`, `QOE`, `COMPLAINTS`, `QOS` |

**Request body (JSON):**

| Field | Type | Required | Description |
|---|---|---|---|
| `weight` | decimal | No | New weight (0-1) |
| `description` | string | No | Updated description |

**Example request:**

```json
{
  "weight": "0.35",
  "description": "Increased weight for coverage dimension."
}
```

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Weight for COVERAGE updated.",
  "data": {
    "id": "uuid",
    "dimension": "COVERAGE",
    "dimension_display": "Network Coverage",
    "weight": "0.35",
    "description": "Increased weight for coverage dimension.",
    "updated_at": "2026-03-25T14:00:00Z"
  },
  "errors": null
}
```

---

## Scores

### GET `/scores/`

Returns the latest scorecard (most recent period) for all operators.

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Current operator scores retrieved.",
  "data": {
    "period": "2026-03-01",
    "scores": [
      {
        "id": "uuid",
        "operator": "uuid",
        "operator_name": "Mascom",
        "operator_code": "MASCOM",
        "period": "2026-03-01",
        "coverage_score": "82.56",
        "qoe_score": "69.16",
        "complaints_score": "82.87",
        "qos_score": "84.69",
        "composite_score": "79.03",
        "rank": 1,
        "created_at": "2026-03-25T12:00:00Z"
      },
      {
        "..." : "Orange (rank 2), BTCL (rank 3)"
      }
    ]
  },
  "errors": null
}
```

---

### GET `/scores/history/`

Monthly scorecard history grouped by period.

**Query Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `operator` | string | all | Filter by operator code |
| `months` | integer | 6 | Look back months |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Score history retrieved.",
  "data": {
    "months": 6,
    "periods": [
      {
        "period": "2025-10-01",
        "scores": [
          {
            "operator_code": "MASCOM",
            "composite_score": "77.02",
            "rank": 1,
            "..." : "..."
          }
        ]
      },
      {
        "period": "2026-03-01",
        "scores": ["..."]
      }
    ]
  },
  "errors": null
}
```

---

### GET `/scores/{operator_code}/`

Detailed scorecard for a single operator: latest score with full metadata and
recent history.

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `operator_code` | string | Operator code (e.g. `MASCOM`, `ORANGE`, `BTCL`) |

**Query Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `months` | integer | 6 | History months |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Scorecard for Mascom retrieved.",
  "data": {
    "operator": "uuid",
    "operator_name": "Mascom",
    "operator_code": "MASCOM",
    "latest": {
      "id": "uuid",
      "period": "2026-03-01",
      "coverage_score": "82.56",
      "qoe_score": "69.16",
      "complaints_score": "82.87",
      "qos_score": "84.69",
      "composite_score": "79.03",
      "rank": 1,
      "metadata": {
        "weights": {"coverage": 0.3, "qoe": 0.3, "complaints": 0.2, "qos": 0.2},
        "coverage": {"area_count": 48, "avg_coverage_pct": 82.56},
        "qoe": {"report_count": 353, "avg_rating": 3.62},
        "complaints": {"complaint_count": 5, "resolved_count": 3, "resolution_rate_pct": 60.0},
        "qos": {"metric_count": 4, "metrics": ["..."]}
      }
    },
    "history": [
      {"period": "2025-10-01", "composite_score": "77.02", "rank": 1, "...": "..."},
      {"...": "5 more months"}
    ]
  },
  "errors": null
}
```

---

## Rankings

### GET `/rankings/`

Operator leaderboard for the latest period, with trend data compared to the
previous period.

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Operator rankings retrieved.",
  "data": {
    "period": "2026-03-01",
    "rankings": [
      {
        "operator_code": "MASCOM",
        "operator_name": "Mascom",
        "composite_score": "79.03",
        "rank": 1,
        "coverage_score": "82.56",
        "qoe_score": "69.16",
        "complaints_score": "82.87",
        "qos_score": "84.69",
        "trend": {
          "score_change": 0.05,
          "rank_change": 0,
          "previous_rank": 1,
          "previous_composite": 78.98
        }
      },
      {
        "operator_code": "ORANGE",
        "composite_score": "73.25",
        "rank": 2,
        "trend": {
          "score_change": 0.72,
          "rank_change": 0,
          "previous_rank": 2,
          "previous_composite": 72.53
        }
      },
      {
        "operator_code": "BTCL",
        "composite_score": "60.67",
        "rank": 3,
        "trend": {
          "score_change": 3.71,
          "rank_change": 0,
          "previous_rank": 3,
          "previous_composite": 56.96
        }
      }
    ]
  },
  "errors": null
}
```

---

## Manual Metrics

### GET `/manual-metrics/`

Paginated list of staff-entered manual metrics. Staff only.

**Query Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `operator` | string | Filter by operator code |
| `period` | date | Filter by period |
| `page` | integer | Page number |
| `page_size` | integer | Items per page (max 200) |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Manual metrics retrieved.",
  "data": {
    "count": 12,
    "next": null,
    "previous": null,
    "results": [
      {
        "id": "uuid",
        "operator": "uuid",
        "operator_name": "Mascom",
        "operator_code": "MASCOM",
        "period": "2026-01-01",
        "metric_name": "Customer Satisfaction Index",
        "value": "82.45",
        "unit": "%",
        "entered_by": "uuid",
        "entered_by_email": "admin@bocra.org.bw",
        "created_at": "2026-03-25T12:00:00Z"
      }
    ]
  },
  "errors": null
}
```

---

### POST `/manual-metrics/create/`

Add a manual metric entry. Staff only. The `entered_by` field is auto-set.

**Request body (JSON):**

| Field | Type | Required | Description |
|---|---|---|---|
| `operator` | UUID | Yes | Operator UUID |
| `period` | date | Yes | Period (YYYY-MM-DD, first of month) |
| `metric_name` | string | Yes | Metric name |
| `value` | decimal | Yes | Metric value |
| `unit` | string | Yes | Unit of measurement |

**Example request:**

```json
{
  "operator": "uuid-of-mascom",
  "period": "2026-03-01",
  "metric_name": "Customer Satisfaction Index",
  "value": "85.20",
  "unit": "%"
}
```

**Response `201 Created`** -- same structure as list item.

---

## Score Computation

### POST `/scores/compute/`

Trigger score recomputation for a given period. Admin only.

**Query/Body Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `period` | date | current month | Period as YYYY-MM-DD |

Each dimension is computed from real data:

| Dimension | Source | Formula |
|---|---|---|
| **Coverage** | `coverages.CoverageArea` | avg `coverage_percentage` across all districts/techs |
| **QoE** | `qoe.QoEReport` | `(avg_rating - 1) / 4 * 100` |
| **Complaints** | `complaints.Complaint` | `max(0, 100 - count*2) + resolution_bonus` |
| **QoS** | `analytics.QoSRecord` | avg benchmark compliance per metric |

Composite = weighted sum using `ScorecardWeightConfig`.

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Scores computed for 2026-03-01. 3 operator(s) scored.",
  "data": {
    "period": "2026-03-01",
    "scores": [
      {
        "operator_code": "MASCOM",
        "composite_score": "79.03",
        "rank": 1,
        "...": "..."
      }
    ]
  },
  "errors": null
}
```

---

## Models & Enums

### ScoringDimension Enum

| Value | Label |
|---|---|
| `COVERAGE` | Network Coverage |
| `QOE` | Quality of Experience |
| `COMPLAINTS` | Complaint Handling |
| `QOS` | QoS Compliance |

### ScorecardWeightConfig

| Field | Type | Description |
|---|---|---|
| `dimension` | enum (unique) | Scoring dimension |
| `weight` | decimal 0-1 | Weight in composite calculation |
| `description` | text | What this dimension measures |
| `updated_by` | FK (User) | Last admin to update |

### OperatorScore

| Field | Type | Description |
|---|---|---|
| `operator` | FK (NetworkOperator) | Operator being scored |
| `period` | date | Reporting period (first of month) |
| `coverage_score` | decimal 0-100 | Coverage dimension score |
| `qoe_score` | decimal 0-100 | QoE dimension score |
| `complaints_score` | decimal 0-100 | Complaints dimension score |
| `qos_score` | decimal 0-100 | QoS compliance score |
| `composite_score` | decimal 0-100 | Weighted composite |
| `rank` | integer | Rank among operators (1=best) |
| `metadata` | JSON | Calculation details and raw values |

### ManualMetricEntry

| Field | Type | Description |
|---|---|---|
| `operator` | FK (NetworkOperator) | Operator |
| `period` | date | Reporting period |
| `metric_name` | string | Metric name |
| `value` | decimal | Metric value |
| `unit` | string | Unit of measurement |
| `entered_by` | FK (User) | Staff who entered |

---

## Seed Data

```bash
python manage.py seed_scorecard           # Seed all scorecard data
python manage.py seed_scorecard --clear   # Clear existing data first
```

**Seeded data:**
- 4 weight configs (coverage=0.30, qoe=0.30, complaints=0.20, qos=0.20)
- 18 operator scores (3 operators x 6 months: Oct 2025 -- Mar 2026)
- 12 manual metric entries (3 operators x 2 quarters x 2 metrics)
- Mascom consistently ranked #1, Orange #2, BTCL #3
- Slight upward trend over time for all operators
