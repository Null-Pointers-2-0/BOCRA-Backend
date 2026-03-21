# Analytics & Dashboard API

> Base URL: `/api/v1/analytics/`  
> Swagger tags: **Analytics — Dashboard** · **Analytics — Telecoms** · **Analytics — QoS** · **Analytics — Summaries**

Provides public and staff dashboards, telecoms statistics, quality-of-service data, and aggregated summaries across complaints and licensing.

---

## Table of Contents

- [Endpoints Summary](#endpoints-summary)
- [Dashboard](#dashboard)
- [Telecoms](#telecoms)
- [Quality of Service (QoS)](#quality-of-service-qos)
- [Summaries](#summaries)

---

## Endpoints Summary

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/dashboard/public/` | Public dashboard overview | Public |
| `GET` | `/dashboard/staff/` | Staff operational dashboard | Staff |
| `GET` | `/telecoms/overview/` | Telecoms market overview | Public |
| `GET` | `/telecoms/operators/` | List network operators | Public |
| `GET` | `/qos/` | Quality of Service records | Public |
| `GET` | `/qos/by-operator/` | QoS averages grouped by operator | Staff |
| `GET` | `/complaints/summary/` | Complaints analytics summary | Staff |
| `GET` | `/licensing/summary/` | Licensing analytics summary | Staff |

---

## Dashboard

### GET `/dashboard/public/`

Combined overview for the public-facing dashboard. Aggregates key metrics from licensing, complaints, and telecoms.

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Public dashboard data retrieved.",
  "data": {
    "licensing": {
      "active_licences": 42
    },
    "complaints": {
      "total": 156,
      "resolved": 89
    },
    "telecoms": {
      "total_subscribers": 2450000,
      "active_operators": 3
    }
  },
  "errors": null
}
```

---

### GET `/dashboard/staff/`

Full operational dashboard for BOCRA staff. Includes detailed breakdowns across all modules.

**Auth**: `Authorization: Bearer <access_token>` (Staff role)

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Staff dashboard data retrieved.",
  "data": {
    "licensing": {
      "active": 42,
      "expired": 5,
      "suspended": 1,
      "pending_applications": 8
    },
    "complaints": {
      "total": 156,
      "by_status": {
        "SUBMITTED": 12,
        "ASSIGNED": 5,
        "INVESTIGATING": 18,
        "AWAITING_RESPONSE": 7,
        "RESOLVED": 89,
        "CLOSED": 20,
        "REOPENED": 5
      },
      "by_category": {
        "SERVICE_QUALITY": 45,
        "BILLING": 30,
        "COVERAGE": 25
      },
      "overdue": 3,
      "unassigned": 12
    },
    "telecoms": {
      "total_subscribers": 2450000,
      "active_operators": 3
    }
  },
  "errors": null
}
```

---

## Telecoms

### GET `/telecoms/overview/`

Telecoms market overview with subscriber counts and market share, aggregated by operator and technology. Supports date-range filtering.

**Query parameters** (optional)

| Param | Description | Example |
|---|---|---|
| `start_date` | Filter from date (inclusive) | `2026-01-01` |
| `end_date` | Filter to date (inclusive) | `2026-03-31` |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Telecoms overview retrieved.",
  "data": {
    "summary": {
      "total_subscribers": 2450000,
      "total_revenue": 1250000000.00,
      "active_operators": 3
    },
    "by_operator": [
      {
        "operator__name": "Mascom Wireless",
        "total_subscribers": 1200000,
        "avg_market_share": 48.98
      },
      {
        "operator__name": "Orange Botswana",
        "total_subscribers": 800000,
        "avg_market_share": 32.65
      },
      {
        "operator__name": "beMobile",
        "total_subscribers": 450000,
        "avg_market_share": 18.37
      }
    ],
    "by_technology": [
      {
        "technology": "4G",
        "total_subscribers": 1500000,
        "avg_market_share": 61.22
      },
      {
        "technology": "3G",
        "total_subscribers": 700000,
        "avg_market_share": 28.57
      },
      {
        "technology": "2G",
        "total_subscribers": 250000,
        "avg_market_share": 10.21
      }
    ]
  },
  "errors": null
}
```

---

### GET `/telecoms/operators/`

List all registered network operators.

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Operators retrieved.",
  "data": [
    {
      "id": "...",
      "name": "Mascom Wireless",
      "code": "MASCOM",
      "logo": "/media/analytics/logos/mascom.png",
      "is_active": true,
      "created_at": "2026-01-01T00:00:00Z"
    },
    {
      "id": "...",
      "name": "Orange Botswana",
      "code": "ORANGE",
      "logo": "/media/analytics/logos/orange.png",
      "is_active": true,
      "created_at": "2026-01-01T00:00:00Z"
    }
  ],
  "errors": null
}
```

---

## Quality of Service (QoS)

### GET `/qos/`

List QoS records. Defaults to the latest reporting period if no date filter is provided.

**Query parameters** (optional)

| Param | Description | Example |
|---|---|---|
| `operator` | Filter by operator UUID | `550e8400-...` |
| `metric_type` | Filter by metric type | `CALL_SUCCESS` |
| `region` | Filter by region name | `Gaborone` |
| `start_date` | Filter from period (inclusive) | `2026-01-01` |
| `end_date` | Filter to period (inclusive) | `2026-03-31` |
| `ordering` | Sort by field | `period`, `value`, `metric_type` |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "QoS records retrieved.",
  "data": [
    {
      "id": "...",
      "operator": {
        "id": "...",
        "name": "Mascom Wireless",
        "code": "MASCOM"
      },
      "period": "2026-03-01",
      "metric_type": "CALL_SUCCESS",
      "metric_type_display": "Call Success Rate",
      "value": 97.50,
      "unit": "%",
      "region": "Gaborone",
      "benchmark": 95.00,
      "meets_benchmark": true,
      "created_at": "2026-03-15T00:00:00Z"
    },
    {
      "id": "...",
      "operator": {
        "id": "...",
        "name": "Mascom Wireless",
        "code": "MASCOM"
      },
      "period": "2026-03-01",
      "metric_type": "DROP_RATE",
      "metric_type_display": "Call Drop Rate",
      "value": 1.20,
      "unit": "%",
      "region": "Gaborone",
      "benchmark": 2.00,
      "meets_benchmark": true,
      "created_at": "2026-03-15T00:00:00Z"
    }
  ],
  "errors": null
}
```

> **Note**: For `DROP_RATE` and `LATENCY` metrics, lower values are better — `meets_benchmark` is `true` when the value is ≤ the benchmark.

---

### GET `/qos/by-operator/`

QoS averages grouped by operator and metric type. Useful for comparative analysis across operators.

**Auth**: `Authorization: Bearer <access_token>` (Staff role)

**Query parameters** (optional)

| Param | Description |
|---|---|
| `start_date` | Filter from period |
| `end_date` | Filter to period |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "QoS data by operator retrieved.",
  "data": [
    {
      "operator__name": "Mascom Wireless",
      "metric_type": "CALL_SUCCESS",
      "avg_value": 97.25,
      "min_value": 95.10,
      "max_value": 99.10,
      "record_count": 12
    },
    {
      "operator__name": "Mascom Wireless",
      "metric_type": "DATA_SPEED",
      "avg_value": 25.50,
      "min_value": 18.00,
      "max_value": 45.00,
      "record_count": 12
    },
    {
      "operator__name": "Orange Botswana",
      "metric_type": "CALL_SUCCESS",
      "avg_value": 96.80,
      "min_value": 94.50,
      "max_value": 98.90,
      "record_count": 12
    }
  ],
  "errors": null
}
```

---

## Summaries

### GET `/complaints/summary/`

Aggregated complaints analytics for management reporting.

**Auth**: `Authorization: Bearer <access_token>` (Staff role)

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Complaints summary retrieved.",
  "data": {
    "total": 156,
    "resolved": 89,
    "resolution_rate": 57.05,
    "avg_resolution_days": 8.3,
    "overdue": 3,
    "sla_compliance_rate": 92.13,
    "by_status": {
      "SUBMITTED": 12,
      "ASSIGNED": 5,
      "INVESTIGATING": 18,
      "AWAITING_RESPONSE": 7,
      "RESOLVED": 89,
      "CLOSED": 20,
      "REOPENED": 5
    },
    "by_category": {
      "SERVICE_QUALITY": 45,
      "BILLING": 30,
      "COVERAGE": 25,
      "INTERNET": 20,
      "CONDUCT": 15,
      "BROADCASTING": 10,
      "POSTAL": 6,
      "OTHER": 5
    },
    "by_priority": {
      "URGENT": 5,
      "HIGH": 20,
      "MEDIUM": 90,
      "LOW": 41
    }
  },
  "errors": null
}
```

---

### GET `/licensing/summary/`

Aggregated licensing analytics including renewal projections.

**Auth**: `Authorization: Bearer <access_token>` (Staff role)

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Licensing summary retrieved.",
  "data": {
    "total_active": 42,
    "total_expired": 5,
    "total_suspended": 1,
    "by_type": {
      "TELECOM": 12,
      "BROADCASTING": 8,
      "POSTAL": 5,
      "ISP": 10,
      "VANS": 7
    },
    "renewals_due_30_days": 3,
    "renewals_due_60_days": 7,
    "renewals_due_90_days": 12,
    "application_pipeline": {
      "SUBMITTED": 4,
      "UNDER_REVIEW": 2,
      "APPROVED": 1,
      "REJECTED": 1
    }
  },
  "errors": null
}
```

---

## Enums & Reference

### Technology Types

| Value | Label |
|---|---|
| `2G` | 2G |
| `3G` | 3G |
| `4G` | 4G |
| `5G` | 5G |

### QoS Metric Types

| Value | Label | Lower is Better? |
|---|---|---|
| `CALL_SUCCESS` | Call Success Rate | No |
| `DATA_SPEED` | Data Speed | No |
| `LATENCY` | Latency | Yes |
| `DROP_RATE` | Call Drop Rate | Yes |
