# QoE Reporter API

> Base URL: `/api/v1/qoe/`
> Swagger tags: **QoE Reporter** . **QoE Reporter -- Staff**

Crowdsourced citizen network experience reporting. Citizens rate their operator,
optionally run an in-browser speed test, and BOCRA gets ground-truth QoE data.
Anonymous submission supported -- no login required. Includes aggregation
endpoints for heatmaps, trends, speed distributions, and staff analytics.

---

## Table of Contents

- [Endpoints Summary](#endpoints-summary)
- [Report Submission](#report-submission)
- [Speed Test](#speed-test)
- [Public Aggregation](#public-aggregation)
- [Staff Endpoints](#staff-endpoints)
- [Models & Enums](#models--enums)
- [Rate Limiting](#rate-limiting)
- [Location Privacy](#location-privacy)
- [Seed Data](#seed-data)

---

## Endpoints Summary

### Public (no auth required)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/reports/` | Submit a QoE report |
| `GET` | `/speedtest-file/` | Download 1MB blob for speed measurement |
| `POST` | `/speedtest-upload/` | Upload blob for upload speed measurement |
| `GET` | `/ping/` | Latency ping (minimal JSON response) |
| `GET` | `/heatmap/` | Aggregated QoE data by district for heatmap |
| `GET` | `/summary/` | QoE summary stats per operator |
| `GET` | `/trends/` | Monthly QoE score trends |
| `GET` | `/speeds/` | Speed test distribution per operator |
| `GET` | `/districts/` | Districts with QoE report data |

### Staff / Admin (requires authentication + role)

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/reports/list/` | Staff | List all reports (paginated, filtered) |
| `GET` | `/reports/{id}/` | Staff | Single report detail |
| `GET` | `/analytics/` | Staff | Full QoE analytics dashboard data |
| `GET` | `/compare/` | Staff | QoS (operator-reported) vs QoE (citizen-reported) |

---

## Report Submission

### POST `/reports/`

Submit a citizen QoE report. No authentication required. If the user is logged
in (JWT token provided), the report is automatically linked to their account.

Rate limited to **5 reports per IP per hour**.

**Request body (JSON):**

| Field | Type | Required | Description |
|---|---|---|---|
| `operator` | UUID | Yes | Operator UUID (get from `/coverages/operators/`) |
| `service_type` | string | No | `DATA` (default), `VOICE`, `SMS`, `FIXED` |
| `connection_type` | string | Yes | `2G`, `3G`, `4G`, `5G` |
| `rating` | integer | Yes | 1-5 star rating (1=Very Poor, 5=Excellent) |
| `download_speed` | decimal | No | Download speed in Mbps (from speed test) |
| `upload_speed` | decimal | No | Upload speed in Mbps (from speed test) |
| `latency_ms` | integer | No | Latency in milliseconds (from ping test) |
| `latitude` | decimal | No | GPS latitude (auto-rounded to 3dp for privacy) |
| `longitude` | decimal | No | GPS longitude (auto-rounded to 3dp) |
| `district` | UUID | No | District UUID (auto-resolved from coords if omitted) |
| `description` | string | No | Free text, max 1000 characters |

**Example request:**

```json
{
  "operator": "uuid-of-mascom",
  "service_type": "DATA",
  "connection_type": "4G",
  "rating": 4,
  "download_speed": "22.50",
  "upload_speed": "5.10",
  "latency_ms": 28,
  "latitude": "-24.655",
  "longitude": "25.909",
  "description": "Good coverage in Gaborone CBD."
}
```

**Response `201 Created`**

```json
{
  "success": true,
  "message": "QoE report submitted successfully. Thank you!",
  "data": {
    "id": "uuid",
    "operator": "uuid",
    "operator_name": "Mascom",
    "operator_code": "MASCOM",
    "service_type": "DATA",
    "connection_type": "4G",
    "rating": 4,
    "download_speed": "22.50",
    "upload_speed": "5.10",
    "latency_ms": 28,
    "latitude": "-24.655",
    "longitude": "25.909",
    "district": "uuid",
    "district_name": "South-East (Gaborone)",
    "district_code": "SE",
    "description": "Good coverage in Gaborone CBD.",
    "submitted_at": "2026-03-25T12:30:00Z"
  },
  "errors": null
}
```

**Response `429 Too Many Requests`**

```json
{
  "success": false,
  "message": "Rate limit exceeded. Maximum 5 reports per hour.",
  "data": null,
  "errors": {"rate_limit": "5/5 used"}
}
```

---

## Speed Test

The speed test runs entirely in the browser against the BOCRA server. No external
APIs, no Ookla, no API keys required.

### GET `/speedtest-file/`

Returns a **1MB binary blob** for client-side download speed measurement.

**Headers:**
- `Content-Type: application/octet-stream`
- `Content-Length: 1048576`
- `Cache-Control: no-store, no-cache, must-revalidate`

**Frontend usage:**

```javascript
const start = performance.now();
const response = await fetch('/api/v1/qoe/speedtest-file/');
const blob = await response.blob();
const elapsed = (performance.now() - start) / 1000; // seconds
const bits = blob.size * 8;
const speedMbps = (bits / elapsed) / 1_000_000;
```

### POST `/speedtest-upload/`

Client POSTs a binary blob (recommended 512KB). Server returns elapsed time.

**Request:** Raw binary body (`Content-Type: application/octet-stream`)

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Upload speed test completed.",
  "data": {
    "size_bytes": 524288,
    "elapsed_ms": 0.31
  },
  "errors": null
}
```

**Frontend usage:**

```javascript
const blob = new Uint8Array(512 * 1024); // 512KB
const start = performance.now();
const response = await fetch('/api/v1/qoe/speedtest-upload/', {
  method: 'POST',
  body: blob,
  headers: { 'Content-Type': 'application/octet-stream' }
});
const elapsed = (performance.now() - start) / 1000;
const bits = blob.length * 8;
const speedMbps = (bits / elapsed) / 1_000_000;
```

### GET `/ping/`

Minimal JSON response for round-trip latency measurement.

**Response `200 OK`**

```json
{"pong": true, "ts": 1774461491238}
```

**Frontend usage:**

```javascript
const pings = [];
for (let i = 0; i < 5; i++) {
  const start = performance.now();
  await fetch('/api/v1/qoe/ping/');
  pings.push(performance.now() - start);
}
const avgLatency = pings.reduce((a, b) => a + b) / pings.length;
```

---

## Public Aggregation

### GET `/heatmap/`

Aggregated QoE data per district for heatmap rendering on the map.

**Query Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `operator` | string | all | Filter by operator code (e.g. `MASCOM`) |
| `connection_type` | string | all | Filter by connection type (`3G`, `4G`, `5G`) |
| `days` | integer | 30 | Lookback window in days |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "QoE heatmap data retrieved.",
  "data": {
    "days": 30,
    "districts": [
      {
        "district_id": "uuid",
        "district_name": "South-East (Gaborone)",
        "district_code": "SE",
        "center_lat": -24.6545,
        "center_lng": 25.9089,
        "report_count": 320,
        "avg_rating": 3.42,
        "avg_download_mbps": 15.8,
        "avg_upload_mbps": 3.9,
        "avg_latency_ms": 48.2
      }
    ]
  },
  "errors": null
}
```

---

### GET `/summary/`

Overall QoE summary with per-operator breakdown and rating distribution.

**Query Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `operator` | string | all | Filter by operator code |
| `days` | integer | 30 | Lookback window in days |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "QoE summary retrieved.",
  "data": {
    "days": 30,
    "total_reports": 862,
    "avg_rating": 3.4,
    "avg_download_mbps": 14.5,
    "avg_upload_mbps": 3.4,
    "avg_latency_ms": 62.3,
    "rating_distribution": {
      "1": 25,
      "2": 102,
      "3": 280,
      "4": 345,
      "5": 110
    },
    "by_operator": [
      {
        "operator": "MASCOM",
        "operator_name": "Mascom",
        "report_count": 353,
        "avg_rating": 3.62,
        "avg_download_mbps": 16.93,
        "avg_upload_mbps": 4.21,
        "avg_latency_ms": 60.9
      },
      {
        "operator": "ORANGE",
        "operator_name": "Orange",
        "report_count": 382,
        "avg_rating": 3.45,
        "avg_download_mbps": 13.15,
        "avg_upload_mbps": 3.12,
        "avg_latency_ms": 67.2
      },
      {
        "operator": "BTCL",
        "operator_name": "Btcl",
        "report_count": 127,
        "avg_rating": 2.65,
        "avg_download_mbps": 9.48,
        "avg_upload_mbps": 1.88,
        "avg_latency_ms": 84.6
      }
    ]
  },
  "errors": null
}
```

---

### GET `/trends/`

Monthly QoE score trends per operator.

**Query Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `months` | integer | 6 | Lookback in months |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "QoE trends retrieved.",
  "data": {
    "months": 6,
    "trends": [
      {
        "month": "2025-10",
        "operators": {
          "MASCOM": {
            "operator_name": "Mascom",
            "avg_rating": 3.55,
            "avg_download_mbps": 16.8,
            "report_count": 340
          },
          "ORANGE": { "..." : "..." },
          "BTCL": { "..." : "..." }
        }
      },
      {
        "month": "2026-03",
        "operators": { "..." : "..." }
      }
    ]
  },
  "errors": null
}
```

---

### GET `/speeds/`

Speed test distribution per operator with min/max/avg breakdown per connection type.

**Query Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `connection_type` | string | all | Filter: `2G`, `3G`, `4G`, `5G` |
| `days` | integer | 30 | Lookback window in days |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Speed distribution retrieved.",
  "data": {
    "days": 30,
    "operators": [
      {
        "operator": "MASCOM",
        "operator_name": "Mascom",
        "sample_count": 1200,
        "download": {
          "avg_mbps": 17.03,
          "min_mbps": 0.12,
          "max_mbps": 42.5
        },
        "upload": {
          "avg_mbps": 4.21,
          "min_mbps": 0.03,
          "max_mbps": 12.8
        },
        "latency": {
          "avg_ms": 60.9,
          "min_ms": 8,
          "max_ms": 380
        },
        "by_connection_type": [
          {
            "connection_type": "4G",
            "sample_count": 780,
            "avg_download_mbps": 17.98,
            "avg_upload_mbps": 4.5,
            "avg_latency_ms": 35.1
          },
          {
            "connection_type": "3G",
            "sample_count": 320,
            "avg_download_mbps": 6.45,
            "avg_upload_mbps": 1.6,
            "avg_latency_ms": 84.9
          }
        ]
      }
    ]
  },
  "errors": null
}
```

---

### GET `/districts/`

Districts that have QoE report data, ranked by report count.

**Response `200 OK`**

```json
{
  "success": true,
  "message": "QoE districts retrieved.",
  "data": [
    {
      "district_id": "uuid",
      "district_name": "South-East (Gaborone)",
      "district_code": "SE",
      "center_lat": -24.6545,
      "center_lng": 25.9089,
      "report_count": 1969,
      "avg_rating": 3.39
    }
  ],
  "errors": null
}
```

---

## Staff Endpoints

### GET `/reports/list/`

Paginated list of all QoE reports with full detail. Auth: Staff role required.

**Query Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `operator` | string | Filter by operator code (e.g. `MASCOM`) |
| `district` | UUID | Filter by district UUID |
| `connection_type` | string | `2G`, `3G`, `4G`, `5G` |
| `service_type` | string | `DATA`, `VOICE`, `SMS`, `FIXED` |
| `rating` | integer | Filter by exact rating (1-5) |
| `is_flagged` | boolean | Filter flagged reports |
| `date_from` | date | Reports from this date |
| `date_to` | date | Reports up to this date |
| `search` | string | Search description, operator, district name |
| `ordering` | string | Sort: `submitted_at`, `rating`, `download_speed` |
| `page` | integer | Page number |
| `page_size` | integer | Items per page (max 200, default 50) |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "QoE reports retrieved.",
  "data": {
    "count": 5001,
    "next": "http://localhost:8000/api/v1/qoe/reports/list/?page=2",
    "previous": null,
    "results": [
      {
        "id": "uuid",
        "operator": "uuid",
        "operator_name": "Mascom",
        "operator_code": "MASCOM",
        "service_type": "DATA",
        "service_type_display": "Mobile Data / Internet",
        "connection_type": "4G",
        "connection_type_display": "4G",
        "rating": 4,
        "download_speed": "22.50",
        "upload_speed": "5.10",
        "latency_ms": 28,
        "latitude": "-24.655",
        "longitude": "25.909",
        "district": "uuid",
        "district_name": "South-East (Gaborone)",
        "district_code": "SE",
        "description": "Good coverage in Gaborone CBD.",
        "submitted_by": "uuid",
        "submitted_by_email": "citizen@example.com",
        "submitted_at": "2026-03-25T12:30:00Z",
        "ip_hash": "a1b2c3...",
        "is_verified": false,
        "is_flagged": false,
        "created_at": "2026-03-25T12:30:00Z"
      }
    ]
  },
  "errors": null
}
```

---

### GET `/reports/{id}/`

Single report detail. Auth: Staff role required.

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `id` | UUID | Report primary key |

Returns the same structure as a single item from `/reports/list/`.

---

### GET `/analytics/`

Comprehensive QoE analytics for BOCRA staff dashboards.

**Query Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `days` | integer | 30 | Lookback window in days |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "QoE analytics retrieved.",
  "data": {
    "days": 30,
    "total_reports": 862,
    "flagged_reports": 8,
    "verified_reports": 0,
    "reports_with_speed_test": 510,
    "reports_with_location": 690,
    "overall": {
      "avg_rating": 3.4,
      "avg_download_mbps": 14.5,
      "avg_upload_mbps": 3.4,
      "avg_latency_ms": 62.3
    },
    "by_operator": [
      {
        "operator__code": "MASCOM",
        "operator__name": "Mascom",
        "report_count": 353,
        "avg_rating": 3.62,
        "avg_download": 16.93,
        "avg_upload": 4.21,
        "avg_latency": 60.9
      }
    ],
    "by_service_type": [
      {"service_type": "DATA", "count": 470, "avg_rating": 3.35},
      {"service_type": "VOICE", "count": 220, "avg_rating": 3.55}
    ],
    "by_connection_type": [
      {"connection_type": "4G", "count": 480, "avg_rating": 3.5, "avg_download": 16.2},
      {"connection_type": "3G", "count": 260, "avg_rating": 3.1, "avg_download": 5.5}
    ],
    "top_districts": [
      {"district__name": "South-East (Gaborone)", "district__code": "SE", "report_count": 320, "avg_rating": 3.42}
    ]
  },
  "errors": null
}
```

---

### GET `/compare/`

QoS (operator-reported from `analytics.QoSRecord`) vs QoE (citizen-reported)
side-by-side comparison. Useful for BOCRA to identify discrepancies between
what operators report and what citizens experience.

**Response `200 OK`**

```json
{
  "success": true,
  "message": "QoS vs QoE comparison retrieved.",
  "data": {
    "qoe_window_days": 30,
    "qos_period": "2026-01-01",
    "comparison": [
      {
        "operator": "MASCOM",
        "operator_name": "Mascom",
        "citizen_qoe": {
          "report_count": 353,
          "avg_rating": 3.62,
          "avg_download_mbps": 16.93,
          "avg_upload_mbps": 4.21,
          "avg_latency_ms": 60.9
        },
        "operator_qos": {
          "period": "2026-01-01",
          "metrics": {
            "CALL_SUCCESS": {"value": 98.5, "unit": "%", "benchmark": 95.0},
            "DATA_SPEED": {"value": 25.0, "unit": "Mbps", "benchmark": 10.0},
            "LATENCY": {"value": 30.0, "unit": "ms", "benchmark": 50.0},
            "DROP_RATE": {"value": 1.2, "unit": "%", "benchmark": 2.0}
          }
        }
      }
    ]
  },
  "errors": null
}
```

---

## Models & Enums

### QoEReport

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Primary key |
| `operator` | FK (NetworkOperator) | Which operator is being rated |
| `service_type` | enum | `DATA`, `VOICE`, `SMS`, `FIXED` |
| `connection_type` | enum | `2G`, `3G`, `4G`, `5G` |
| `rating` | integer 1-5 | Star rating (1=Very Poor, 5=Excellent) |
| `download_speed` | decimal | Mbps (nullable, from speed test) |
| `upload_speed` | decimal | Mbps (nullable, from speed test) |
| `latency_ms` | integer | Milliseconds (nullable, from ping test) |
| `latitude` | decimal | GPS latitude, rounded to 3dp |
| `longitude` | decimal | GPS longitude, rounded to 3dp |
| `district` | FK (District) | Auto-resolved from coords or manual selection |
| `description` | text | Free text, max 1000 chars |
| `submitted_by` | FK (User) | Null if anonymous, set if authenticated |
| `submitted_at` | datetime | Server timestamp |
| `ip_hash` | string | SHA-256 of client IP (never stores raw IP) |
| `is_verified` | boolean | Staff-verified report |
| `is_flagged` | boolean | Suspicious / spam flagged |

### ServiceType Enum

| Value | Label |
|---|---|
| `DATA` | Mobile Data / Internet |
| `VOICE` | Voice Calls |
| `SMS` | Text Messaging |
| `FIXED` | Fixed Broadband |

### ConnectionType Enum

| Value | Label |
|---|---|
| `2G` | 2G |
| `3G` | 3G |
| `4G` | 4G |
| `5G` | 5G |

---

## Rate Limiting

- **5 reports per IP per hour** (configurable)
- IP addresses are **never stored** -- only SHA-256 hashes
- Rate limit check happens server-side before report creation
- Returns `429 Too Many Requests` when exceeded

---

## Location Privacy

- Browser Geolocation API used with user permission
- Fallback: manual district selection from dropdown
- Coordinates **rounded to 3 decimal places** (~100m precision) before storage
- District auto-resolved from coordinates using bounding-box lookup
- Raw IP addresses **never stored** -- only SHA-256 hashes for rate limiting

---

## Seed Data

```bash
python manage.py seed_qoe           # Create 5000 QoE reports
python manage.py seed_qoe --clear   # Clear existing data first
python manage.py seed_qoe --count 1000  # Custom count
```

**Seeded data:**
- 5,000 QoE reports across Oct 2025 -- Mar 2026
- Operator split: Mascom ~42%, Orange ~43%, BTCL ~15% (matching market share)
- 60% include speed test results, 40% rating-only
- 80% have GPS coordinates, 20% manual district selection only
- Distribution weighted by district population (most from Gaborone)
- Realistic operator-specific speed profiles (Mascom fastest, BTCL slowest)
- Connection type distribution varies by district urbanization
- 1% auto-flagged as suspicious
