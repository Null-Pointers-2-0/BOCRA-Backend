# Analytics & Dashboard API

> Base URL: `/api/v1/analytics/`  
> Swagger tags: **Analytics — Dashboard** · **Analytics — Public** · **Analytics — Staff**

Provides a comprehensive centralized dashboard with 15 endpoints covering public dashboards, telecoms statistics, quality-of-service data, and deep analytics across users, licensing, complaints, publications, tenders, news, and notifications.

---

## Table of Contents

- [Endpoints Summary](#endpoints-summary)
- [Dashboard](#dashboard)
- [Telecoms](#telecoms)
- [Quality of Service (QoS)](#quality-of-service-qos)
- [Users Analytics](#users-analytics)
- [Licensing & Applications](#licensing--applications)
- [Complaints Analytics](#complaints-analytics)
- [Publications Analytics](#publications-analytics)
- [Tenders Analytics](#tenders-analytics)
- [News Analytics](#news-analytics)
- [Content Overview](#content-overview)
- [Enums & Reference](#enums--reference)

---

## Endpoints Summary

### Public (no auth required)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/dashboard/public/` | Public dashboard overview |
| `GET` | `/telecoms/overview/` | Telecoms market overview |
| `GET` | `/telecoms/operators/` | List network operators |
| `GET` | `/qos/` | Quality of Service records |

### Staff (requires Staff role)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/dashboard/staff/` | Staff operational dashboard (all modules) |
| `GET` | `/qos/by-operator/` | QoS averages grouped by operator |
| `GET` | `/users/summary/` | User registration & account analytics |
| `GET` | `/licensing/summary/` | Licensing analytics summary |
| `GET` | `/applications/trend/` | Application volume trend & processing times |
| `GET` | `/complaints/summary/` | Complaints analytics summary |
| `GET` | `/complaints/trend/` | Complaint trends, top operators, staff workload |
| `GET` | `/publications/summary/` | Publications analytics |
| `GET` | `/tenders/summary/` | Tenders analytics |
| `GET` | `/news/summary/` | News articles analytics |
| `GET` | `/content/overview/` | Combined content metrics (publications + tenders + news) |

---

## Dashboard

### GET `/dashboard/public/`

Combined overview for the public-facing dashboard. Aggregates key metrics from licensing, complaints, telecoms, publications, tenders, and news.

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Public dashboard stats retrieved.",
  "data": {
    "active_licences": 42,
    "total_complaints": 156,
    "resolved_complaints": 89,
    "total_subscribers": 2450000,
    "active_operators": 3,
    "telecoms_period": "2026-03-01",
    "published_publications": 28,
    "open_tenders": 5,
    "published_articles": 18
  },
  "errors": null
}
```

| Field | Description |
|---|---|
| `active_licences` | Number of licences with `ACTIVE` status |
| `total_complaints` | Total non-deleted complaints |
| `resolved_complaints` | Complaints with `RESOLVED` or `CLOSED` status |
| `total_subscribers` | Total telecoms subscribers from the latest reporting period |
| `active_operators` | Number of active network operators |
| `telecoms_period` | Latest telecoms data reporting period |
| `published_publications` | Publications with `PUBLISHED` status |
| `open_tenders` | Tenders with `OPEN` or `CLOSING_SOON` status |
| `published_articles` | News articles with `PUBLISHED` status |

---

### GET `/dashboard/staff/`

Full operational dashboard for BOCRA staff. Returns 7 sections covering all platform modules in a single call.

**Auth**: `Authorization: Bearer <access_token>` (Staff role)

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Staff dashboard retrieved.",
  "data": {
    "users": {
      "total": 450,
      "new_this_month": 23,
      "by_role": {
        "CITIZEN": 380,
        "OPERATOR": 45,
        "STAFF": 20,
        "ADMIN": 5
      }
    },
    "licensing": {
      "active": 42,
      "expired": 5,
      "suspended": 1,
      "renewals_due_30d": 3
    },
    "applications": {
      "pending_review": 4,
      "under_review": 2,
      "info_requested": 1,
      "approved_total": 38,
      "rejected_total": 6
    },
    "complaints": {
      "open": 42,
      "resolved": 109,
      "overdue": 3,
      "unassigned": 12,
      "by_category": {
        "SERVICE_QUALITY": 15,
        "BILLING": 10,
        "COVERAGE": 8
      }
    },
    "telecoms": {
      "total_subscribers": 2450000,
      "active_operators": 3,
      "latest_period": "2026-03-01"
    },
    "content": {
      "publications": {
        "total": 35,
        "published": 28,
        "draft": 7
      },
      "tenders": {
        "total": 20,
        "open": 5,
        "awarded": 10
      },
      "news": {
        "total": 25,
        "published": 18,
        "draft": 7
      }
    },
    "notifications": {
      "total_sent": 1200,
      "unread": 45
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
    "total_subscribers": 2450000,
    "by_operator": [
      {
        "operator__name": "Mascom Wireless",
        "operator__code": "MASCOM",
        "total_subscribers": 1200000,
        "avg_market_share": 48.98
      },
      {
        "operator__name": "Orange Botswana",
        "operator__code": "ORANGE",
        "total_subscribers": 800000,
        "avg_market_share": 32.65
      }
    ],
    "by_technology": [
      {
        "technology": "4G",
        "total_subscribers": 1500000
      },
      {
        "technology": "3G",
        "total_subscribers": 700000
      }
    ],
    "period": "2026-03-01"
  },
  "errors": null
}
```

---

### GET `/telecoms/operators/`

List all active network operators.

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Operators retrieved successfully.",
  "data": [
    {
      "id": "...",
      "name": "Mascom Wireless",
      "code": "MASCOM",
      "logo": "/media/analytics/logos/mascom.png",
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
  "message": "QoS by operator retrieved.",
  "data": [
    {
      "operator__name": "Mascom Wireless",
      "operator__code": "MASCOM",
      "metric_type": "CALL_SUCCESS",
      "avg_value": 97.25,
      "record_count": 12
    }
  ],
  "errors": null
}
```

---

## Users Analytics

### GET `/users/summary/`

User registration and account analytics — totals, breakdown by role, email verification stats, locked accounts, and 12-month registration trend.

**Auth**: `Authorization: Bearer <access_token>` (Staff role)

**Response `200 OK`**

```json
{
  "success": true,
  "message": "User analytics retrieved.",
  "data": {
    "total": 450,
    "by_role": {
      "CITIZEN": 380,
      "OPERATOR": 45,
      "STAFF": 20,
      "ADMIN": 5
    },
    "email_verified": 410,
    "verification_rate_percent": 91.1,
    "locked_accounts": 2,
    "new_last_7_days": 8,
    "new_last_30_days": 23,
    "registration_trend": [
      { "month": "2025-04", "count": 15 },
      { "month": "2025-05", "count": 22 },
      { "month": "2025-06", "count": 18 },
      { "month": "2026-03", "count": 23 }
    ]
  },
  "errors": null
}
```

| Field | Description |
|---|---|
| `total` | Total non-deleted users |
| `by_role` | User count per role (`CITIZEN`, `OPERATOR`, `STAFF`, `ADMIN`) |
| `email_verified` | Users who have verified their email |
| `verification_rate_percent` | Percentage of verified users |
| `locked_accounts` | Users currently locked out (failed login attempts) |
| `new_last_7_days` | Registrations in the last 7 days |
| `new_last_30_days` | Registrations in the last 30 days |
| `registration_trend` | Monthly registration counts for the last 12 months |

---

## Licensing & Applications

### GET `/licensing/summary/`

Aggregated licensing analytics including licence breakdown, renewal projections, and application pipeline.

**Auth**: `Authorization: Bearer <access_token>` (Staff role)

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Licensing summary retrieved.",
  "data": {
    "licences": {
      "total": 48,
      "active": 42,
      "expired": 5,
      "suspended": 1,
      "by_type": {
        "Telecommunications": 12,
        "Broadcasting": 8,
        "Postal": 5,
        "ISP": 10,
        "VANS": 7
      }
    },
    "renewals_due": {
      "30_days": 3,
      "60_days": 7,
      "90_days": 12
    },
    "applications": {
      "total": 52,
      "by_status": {
        "SUBMITTED": 4,
        "UNDER_REVIEW": 2,
        "INFO_REQUESTED": 1,
        "APPROVED": 38,
        "REJECTED": 6,
        "WITHDRAWN": 1
      }
    }
  },
  "errors": null
}
```

---

### GET `/applications/trend/`

Application submission volume by month, approval/rejection rates, and average processing time.

**Auth**: `Authorization: Bearer <access_token>` (Staff role)

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Applications trend retrieved.",
  "data": {
    "total": 52,
    "by_licence_type": {
      "Telecommunications": 15,
      "Broadcasting": 10,
      "ISP": 12,
      "Postal": 8,
      "VANS": 7
    },
    "approved": 38,
    "rejected": 6,
    "approval_rate_percent": 86.4,
    "avg_processing_days": 12.5,
    "volume_trend": [
      { "month": "2025-04", "count": 3 },
      { "month": "2025-05", "count": 5 },
      { "month": "2026-03", "count": 4 }
    ]
  },
  "errors": null
}
```

| Field | Description |
|---|---|
| `total` | Total non-deleted applications |
| `by_licence_type` | Application count per licence type name |
| `approved` / `rejected` | Total approved / rejected applications |
| `approval_rate_percent` | `approved / (approved + rejected) * 100` |
| `avg_processing_days` | Average days from `submitted_at` to `decision_date` for decided applications. `null` if no decided applications exist. |
| `volume_trend` | Monthly application submission counts for the last 12 months |

---

## Complaints Analytics

### GET `/complaints/summary/`

Aggregated complaints analytics for management reporting — totals, resolution stats, SLA compliance, breakdowns by status, category, and priority.

**Auth**: `Authorization: Bearer <access_token>` (Staff role)

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Complaints summary retrieved.",
  "data": {
    "total": 156,
    "open": 42,
    "resolved": 109,
    "resolution_rate_percent": 69.9,
    "avg_resolution_days": 8.3,
    "overdue": 3,
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

### GET `/complaints/trend/`

Monthly complaint volumes, resolution trends, most-targeted operators, and staff workload.

**Auth**: `Authorization: Bearer <access_token>` (Staff role)

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Complaints trend retrieved.",
  "data": {
    "volume_trend": [
      { "month": "2025-04", "count": 12 },
      { "month": "2025-05", "count": 18 },
      { "month": "2026-03", "count": 15 }
    ],
    "resolution_trend": [
      { "month": "2025-04", "count": 10 },
      { "month": "2025-05", "count": 14 }
    ],
    "top_targeted_operators": [
      { "against_operator_name": "Mascom Wireless", "count": 45 },
      { "against_operator_name": "Orange Botswana", "count": 32 },
      { "against_operator_name": "beMobile", "count": 18 }
    ],
    "staff_workload": [
      {
        "assigned_to__email": "officer@bocra.org.bw",
        "assigned_to__first_name": "Keabetswe",
        "assigned_to__last_name": "Mosweu",
        "assigned": 25,
        "resolved": 20
      },
      {
        "assigned_to__email": "analyst@bocra.org.bw",
        "assigned_to__first_name": "Thato",
        "assigned_to__last_name": "Kgosi",
        "assigned": 18,
        "resolved": 15
      }
    ]
  },
  "errors": null
}
```

| Field | Description |
|---|---|
| `volume_trend` | Monthly complaint submission counts (last 12 months) |
| `resolution_trend` | Monthly resolved complaint counts (last 12 months) |
| `top_targeted_operators` | Top 10 operators by complaint count |
| `staff_workload` | Top 10 staff by assigned complaints, with resolved count |

---

## Publications Analytics

### GET `/publications/summary/`

Total publications, breakdowns by status and category, download stats, and publishing trend.

**Auth**: `Authorization: Bearer <access_token>` (Staff role)

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Publications analytics retrieved.",
  "data": {
    "total": 35,
    "by_status": {
      "DRAFT": 7,
      "PUBLISHED": 28,
      "ARCHIVED": 0
    },
    "by_category": {
      "REGULATION": 10,
      "REPORT": 8,
      "POLICY": 6,
      "GUIDELINE": 5,
      "ANNUAL_REPORT": 3,
      "OTHER": 3
    },
    "total_downloads": 1250,
    "top_downloaded": [
      {
        "id": "...",
        "title": "ICT Policy Framework 2025",
        "category": "POLICY",
        "download_count": 340
      },
      {
        "id": "...",
        "title": "Annual Report 2025",
        "category": "ANNUAL_REPORT",
        "download_count": 280
      }
    ],
    "publishing_trend": [
      { "month": "2025-06", "count": 3 },
      { "month": "2025-09", "count": 5 },
      { "month": "2026-01", "count": 4 }
    ]
  },
  "errors": null
}
```

| Field | Description |
|---|---|
| `total` | Total non-deleted publications |
| `by_status` | Count per publication status (`DRAFT`, `PUBLISHED`, `ARCHIVED`) |
| `by_category` | Count per publication category |
| `total_downloads` | Sum of `download_count` across all publications |
| `top_downloaded` | Top 5 publications by download count |
| `publishing_trend` | Monthly publication count for the last 12 months (published items only) |

---

## Tenders Analytics

### GET `/tenders/summary/`

Tender stats by status and category, award totals, and volume trend.

**Auth**: `Authorization: Bearer <access_token>` (Staff role)

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Tenders analytics retrieved.",
  "data": {
    "total": 20,
    "by_status": {
      "DRAFT": 2,
      "OPEN": 4,
      "CLOSING_SOON": 1,
      "CLOSED": 3,
      "EVALUATION": 2,
      "AWARDED": 6,
      "CANCELLED": 2
    },
    "by_category": {
      "GOODS": 8,
      "SERVICES": 7,
      "WORKS": 3,
      "CONSULTANCY": 2
    },
    "awards": {
      "total_awarded": 6,
      "total_amount": 4500000.00,
      "avg_amount": 750000.00
    },
    "volume_trend": [
      { "month": "2025-06", "count": 2 },
      { "month": "2025-09", "count": 3 },
      { "month": "2026-01", "count": 4 }
    ]
  },
  "errors": null
}
```

| Field | Description |
|---|---|
| `total` | Total non-deleted tenders |
| `by_status` | Count per tender status |
| `by_category` | Count per tender category |
| `awards.total_awarded` | Number of `TenderAward` records |
| `awards.total_amount` | Sum of all award amounts |
| `awards.avg_amount` | Average award amount |
| `volume_trend` | Monthly tender creation count for the last 12 months |

---

## News Analytics

### GET `/news/summary/`

Article stats by category and status, view counts, and publishing trend.

**Auth**: `Authorization: Bearer <access_token>` (Staff role)

**Response `200 OK`**

```json
{
  "success": true,
  "message": "News analytics retrieved.",
  "data": {
    "total": 25,
    "by_status": {
      "DRAFT": 7,
      "PUBLISHED": 18,
      "ARCHIVED": 0
    },
    "by_category": {
      "PRESS_RELEASE": 8,
      "ANNOUNCEMENT": 6,
      "REGULATORY_UPDATE": 5,
      "EVENT": 4,
      "OTHER": 2
    },
    "total_views": 3200,
    "top_viewed": [
      {
        "id": "...",
        "title": "BOCRA Launches New Consumer Portal",
        "category": "ANNOUNCEMENT",
        "view_count": 540
      },
      {
        "id": "...",
        "title": "5G Spectrum Allocation Update",
        "category": "REGULATORY_UPDATE",
        "view_count": 420
      }
    ],
    "publishing_trend": [
      { "month": "2025-06", "count": 2 },
      { "month": "2025-09", "count": 4 },
      { "month": "2026-01", "count": 3 }
    ]
  },
  "errors": null
}
```

| Field | Description |
|---|---|
| `total` | Total non-deleted articles |
| `by_status` | Count per article status (`DRAFT`, `PUBLISHED`, `ARCHIVED`) |
| `by_category` | Count per article category |
| `total_views` | Sum of `view_count` across all articles |
| `top_viewed` | Top 5 articles by view count |
| `publishing_trend` | Monthly article count for the last 12 months (published items only) |

---

## Content Overview

### GET `/content/overview/`

Single-call summary combining publications, tenders, and news — designed for dashboard header cards. Returns status breakdowns and aggregate metrics for each content type.

**Auth**: `Authorization: Bearer <access_token>` (Staff role)

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Content overview retrieved.",
  "data": {
    "publications": {
      "total": 35,
      "published": 28,
      "draft": 7,
      "archived": 0,
      "total_downloads": 1250
    },
    "tenders": {
      "total": 20,
      "open": 5,
      "closed": 3,
      "awarded": 6,
      "draft": 2
    },
    "news": {
      "total": 25,
      "published": 18,
      "draft": 7,
      "archived": 0,
      "total_views": 3200
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

### Error Responses

All endpoints return errors in the standard BOCRA envelope:

**`401 Unauthorized`** — Missing or invalid JWT token

```json
{
  "success": false,
  "message": "Authentication credentials were not provided.",
  "data": null,
  "errors": null
}
```

**`403 Forbidden`** — Authenticated but lacks Staff role

```json
{
  "success": false,
  "message": "You do not have permission to perform this action.",
  "data": null,
  "errors": null
}
```
