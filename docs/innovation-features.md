# Innovation Features — Backend Specification

> BOCRA Digital Platform — 4 Innovation Features (Backend Implementation Detail)
>
> Companion document to the main SRS. Covers models, endpoints, seed data, and
> integration points for the four innovation features that elevate this platform
> beyond a standard website rebuild.

## Table of Contents

- [Overview](#overview)
- [Feature 1 — Interactive Network Coverage Map](#feature-1--interactive-network-coverage-map)
- [Feature 2 — Citizen QoE Reporter](#feature-2--citizen-qoe-reporter)
- [Feature 3 — Live Operator Scorecard](#feature-3--live-operator-scorecard)
- [Feature 4 — Proactive Alert Subscriptions](#feature-4--proactive-alert-subscriptions)
- [Cross-Feature Dependencies](#cross-feature-dependencies)
- [Seed Data Summary](#seed-data-summary)

---

## Overview

| Feature | Django App | Priority | Depends On |
|---|---|---|---|
| Interactive Network Coverage Map | `coverages` | Critical | `analytics.NetworkOperator` |
| Citizen QoE Reporter | `qoe` | Critical | `analytics.NetworkOperator`, `coverages.District` |
| Live Operator Scorecard | `scorecard` | High | `analytics.NetworkOperator`, `qoe`, `complaints`, `coverages` |
| Proactive Alert Subscriptions | `alerts` | Medium | `notifications`, `publications`, `tenders`, `licensing`, `complaints` |

All four apps follow BOCRA backend conventions:

- Models inherit from `core.BaseModel` or `core.AuditableModel`
- UUID primary keys everywhere
- Soft deletes via `is_deleted` / `deleted_at`
- Standard response envelope: `{success, message, data, errors}`
- `api_success()` / `api_error()` helpers from `core.utils`
- drf-spectacular schema decorators on every view

---

## Feature 1 — Interactive Network Coverage Map

**App name:** `coverages`

### Purpose

Expose network coverage data per operator (Mascom, Orange, BTCL) and technology
tier (2G, 3G, 4G) as GeoJSON via API. Frontends render this on a Leaflet.js map.
Citizens filter by operator and technology. Clicking a district reveals coverage
details. Admin staff can upload updated coverage GeoJSON from operator submissions.

### Models

#### District

Botswana administrative district — stores boundary polygon as GeoJSON.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK | Inherited from BaseModel |
| `name` | CharField(200) | required | District name (e.g. "South-East") |
| `code` | CharField(20) | unique, indexed | Short code (e.g. "SE", "NE") |
| `region` | CharField(100) | optional | Broader region grouping |
| `population` | PositiveIntegerField | optional | Latest census population |
| `area_sq_km` | DecimalField(10,2) | optional | Area in square kilometres |
| `boundary_geojson` | JSONField | required | GeoJSON Polygon/MultiPolygon of district boundary |
| `center_lat` | DecimalField(9,6) | optional | Centre latitude for map positioning |
| `center_lng` | DecimalField(9,6) | optional | Centre longitude for map positioning |
| `is_active` | BooleanField | default True | Whether to show on map |
| `created_at` | DateTime | auto | Inherited |
| `updated_at` | DateTime | auto | Inherited |
| `is_deleted` | Boolean | default False | Inherited |

#### CoverageLevel (enum)

```
FULL    = "FULL"     -- 80-100% area covered
PARTIAL = "PARTIAL"  -- 30-79% area covered
MINIMAL = "MINIMAL"  -- 1-29% area covered
NONE    = "NONE"     -- No coverage
```

#### CoverageArea

Network coverage record linking an operator to a district at a specific technology.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK | Inherited from BaseModel |
| `operator` | FK -> NetworkOperator | required, indexed | Which operator (from analytics app) |
| `district` | FK -> District | required, indexed | Which district |
| `technology` | CharField(5) | choices: 2G/3G/4G | Network technology tier |
| `coverage_level` | CharField(10) | choices: CoverageLevel | Qualitative coverage level |
| `coverage_percentage` | DecimalField(5,2) | 0-100 | Numeric coverage percentage |
| `population_covered` | PositiveIntegerField | optional | Estimated population with access |
| `geometry_geojson` | JSONField | optional | Coverage polygon (if different from full district boundary) |
| `signal_strength_avg` | DecimalField(5,2) | optional | Average signal strength in dBm |
| `period` | DateField | indexed | Reporting period (first of quarter/month) |
| `source` | CharField(50) | default "BOCRA" | Data source: "BOCRA", "OPERATOR_SUBMISSION", "ESTIMATED" |
| `notes` | TextField | optional | Internal notes about this record |
| `created_at` | DateTime | auto | Inherited |
| `updated_at` | DateTime | auto | Inherited |
| `is_deleted` | Boolean | default False | Inherited |

**unique_together:** `(operator, district, technology, period)`

#### CoverageUpload

Tracks admin uploads of coverage data from operator submissions.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK | Inherited from AuditableModel |
| `operator` | FK -> NetworkOperator | required | Which operator submitted |
| `technology` | CharField(5) | choices: 2G/3G/4G | Technology tier |
| `file` | FileField | required | Uploaded GeoJSON/shapefile |
| `file_name` | CharField(255) | auto | Original filename |
| `file_size` | PositiveIntegerField | auto | File size in bytes |
| `period` | DateField | required | Reporting period this upload covers |
| `status` | CharField(20) | PENDING/PROCESSING/COMPLETED/FAILED | Processing status |
| `records_created` | PositiveIntegerField | default 0 | Number of CoverageArea records created |
| `error_message` | TextField | optional | Error details if processing failed |
| `processed_at` | DateTime | nullable | When processing completed |
| `created_by` | FK -> User | auto | Inherited from AuditableModel |
| `modified_by` | FK -> User | auto | Inherited from AuditableModel |

### API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/coverages/districts/` | Public | All districts as GeoJSON FeatureCollection |
| GET | `/api/v1/coverages/districts/{id}/` | Public | Single district detail with boundary |
| GET | `/api/v1/coverages/operators/` | Public | Operators with coverage metadata |
| GET | `/api/v1/coverages/areas/` | Public | Coverage areas filtered by `?operator=&technology=&district=&period=` |
| GET | `/api/v1/coverages/areas/geojson/` | Public | Coverage areas as GeoJSON FeatureCollection (map-ready) |
| GET | `/api/v1/coverages/summary/` | Public | National coverage summary stats |
| GET | `/api/v1/coverages/summary/{district_id}/` | Public | Coverage summary for a specific district |
| GET | `/api/v1/coverages/compare/` | Public | Side-by-side operator coverage comparison |
| POST | `/api/v1/coverages/upload/` | Admin | Upload new coverage GeoJSON from operator |
| GET | `/api/v1/coverages/uploads/` | Staff | List upload history |
| GET | `/api/v1/coverages/stats/` | Staff | Coverage analytics (white spots, growth trends) |

### Seed Data

- **10 districts** with real Botswana boundary GeoJSON (simplified polygons from GADM)
- **3 operators** (reuse existing NetworkOperator: Mascom, Orange, BTCL)
- **Coverage records:** 3 operators x 10 districts x 3 techs (2G/3G/4G) x 8 quarterly periods (Q1 2024 - Q4 2025) = **720 CoverageArea records**
- Additional sub-district granularity for major districts to reach **2,000+ records**
- Coverage levels based on real BOCRA data: capitals get FULL, remote areas get MINIMAL/NONE
- Historical progression shows network expansion over time

### Key Business Rules

1. Coverage data is versioned by `period` — each quarter is a new snapshot
2. A district with no CoverageArea record for an operator+tech = NONE coverage
3. National summary aggregates across all districts weighted by population
4. White spots = districts where all operators have NONE or MINIMAL for a given tech
5. Admin uploads are processed asynchronously (Celery task) — file is validated, parsed, and CoverageArea records created
6. GeoJSON endpoint returns data in Leaflet-compatible format (FeatureCollection with properties)

---

## Feature 2 — Citizen QoE Reporter

**App name:** `qoe`

### Purpose

Crowdsourced quality of experience data from citizens. A citizen reports their
network experience (operator, service type, rating, optional speed test). BOCRA
gets ground-truth data about actual network performance as experienced by users,
not just operator-reported QoS metrics.

### Models

#### ServiceType (enum)

```
DATA   = "DATA"    -- Mobile data / internet
VOICE  = "VOICE"   -- Voice calls
SMS    = "SMS"     -- Text messaging
FIXED  = "FIXED"   -- Fixed broadband
```

#### QoEReport

A single citizen network experience report.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK | Inherited from BaseModel |
| `operator` | CharField(20) | choices: MASCOM/ORANGE/BTCL/OTHER | Operator being rated |
| `service_type` | CharField(10) | choices: ServiceType | Service type rated |
| `rating` | PositiveSmallIntegerField | 1-5, validators | 1=Very Poor, 5=Excellent |
| `download_speed` | DecimalField(8,2) | nullable | Mbps from browser speed test |
| `upload_speed` | DecimalField(8,2) | nullable | Mbps from browser speed test |
| `latency_ms` | PositiveIntegerField | nullable | Milliseconds from ping test |
| `latitude` | DecimalField(9,6) | nullable | Rounded to 3dp for privacy |
| `longitude` | DecimalField(9,6) | nullable | Rounded to 3dp for privacy |
| `district` | FK -> District | nullable | Resolved from coords or manual selection |
| `description` | TextField | optional, max 1000 chars | Issue description |
| `submitted_at` | DateTimeField | auto_now_add | Server timestamp |
| `ip_hash` | CharField(64) | indexed | SHA-256 hashed IP for rate limiting |
| `is_verified` | BooleanField | default False | Staff-verified report |
| `is_flagged` | BooleanField | default False | Flagged as suspicious |

**Indexes:** `operator`, `district`, `submitted_at`, `rating`

### Speed Test Mechanism (In-House, No External API)

The speed test runs entirely in the browser against our own Django server:

1. **Download test:** Frontend requests `/api/v1/qoe/speedtest-file/` (1MB binary blob).
   JavaScript measures elapsed time via `performance.now()`.
   Speed = `(file_size_bits) / (elapsed_seconds)` converted to Mbps.

2. **Upload test:** Frontend POSTs a 512KB blob to `/api/v1/qoe/speedtest-upload/`.
   Server measures receipt time and returns duration.
   Speed = `(blob_size_bits) / (elapsed_seconds)` converted to Mbps.

3. **Latency test:** Frontend hits `/api/v1/qoe/ping/` (tiny JSON response).
   Round-trip time measured client-side.

No Ookla. No Speedtest.net. No external dependencies. No API keys.

### Location Privacy

- Browser Geolocation API (`navigator.geolocation`) used with user permission
- Fallback: manual district selection from dropdown
- Coordinates rounded to 3 decimal places (~100m precision) before storage
- Raw IP addresses never stored — only SHA-256 hash for rate limiting

### API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/qoe/reports/` | Public | Submit a QoE report |
| GET | `/api/v1/qoe/reports/` | Staff | List all reports (filtered, paginated) |
| GET | `/api/v1/qoe/speedtest-file/` | Public | Download 1MB test blob for speed measurement |
| POST | `/api/v1/qoe/speedtest-upload/` | Public | Upload blob for upload speed measurement |
| GET | `/api/v1/qoe/ping/` | Public | Latency ping endpoint (minimal JSON) |
| GET | `/api/v1/qoe/heatmap/` | Public | Aggregated QoE data for heatmap by district |
| GET | `/api/v1/qoe/summary/` | Public | QoE summary stats, filterable by `?operator=` |
| GET | `/api/v1/qoe/trends/` | Public | QoE score trends over time per operator |
| GET | `/api/v1/qoe/speeds/` | Public | Speed test distribution per operator |
| GET | `/api/v1/qoe/analytics/` | Staff | Full QoE analytics for BOCRA staff |
| GET | `/api/v1/qoe/compare/` | Staff | QoS (operator-reported) vs QoE (citizen-reported) comparison |
| GET | `/api/v1/qoe/districts/` | Public | Districts with available QoE data |
| GET | `/api/v1/qoe/top-issues/` | Staff | Top complaint areas and common descriptions |

### Seed Data

- **5,000 QoE reports** spread across 6 months (Oct 2025 - Mar 2026)
- Distribution weighted by district population (more reports from Gaborone, fewer from Kgalagadi)
- Operator distribution roughly matching market share (Mascom 42%, Orange 43%, BTCL 15%)
- Ratings follow realistic bell curves per operator per district
- Speed test data: 60% of reports include speed test results
- Download speeds: 5-35 Mbps range with operator-specific averages
- Location data: 80% with GPS coords, 20% manual district selection only

### Key Business Rules

1. Rate limiting: max 5 reports per IP hash per hour (prevents spam)
2. Coordinates rounded to 3 decimal places before storage
3. District auto-resolved from coordinates using bounding-box lookup against District boundaries
4. Reports with suspicious patterns (same IP, identical ratings, rapid submission) auto-flagged
5. Heatmap aggregation is per-district, per-operator — weighted by recency (last 30 days by default)
6. QoS vs QoE comparison links citizen-reported speeds/ratings against operator-reported QoSRecord data

---

## Feature 3 — Live Operator Scorecard

**App name:** `scorecard`

### Purpose

Public-facing operator comparison dashboard. Three operator cards showing how
Mascom, Orange, and BTCL compare across key performance indicators. The scorecard
is computed from live data (QoE reports, complaints, coverage records) and stored
as periodic snapshots.

### Models

#### ScorecardMetric (enum)

```
COVERAGE        = "COVERAGE"         -- 4G population coverage %
DOWNLOAD_SPEED  = "DOWNLOAD_SPEED"   -- Average download speed
QOE_RATING      = "QOE_RATING"       -- Citizen QoE rating (1-5)
RESOLUTION_RATE = "RESOLUTION_RATE"  -- Complaint resolution rate %
CALL_SUCCESS    = "CALL_SUCCESS"     -- Call success rate %
COMPLAINT_VOL   = "COMPLAINT_VOL"    -- Complaint volume (inverse)
```

#### ScorecardWeightConfig

Admin-configurable weights for the overall score calculation.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK | Inherited from AuditableModel |
| `metric` | CharField(20) | unique, choices: ScorecardMetric | Which metric |
| `weight` | DecimalField(5,2) | 0-100 | Weight percentage |
| `direction` | CharField(10) | HIGHER_BETTER / LOWER_BETTER | Score direction |
| `benchmark_min` | DecimalField(10,4) | optional | Minimum value for 0 score |
| `benchmark_max` | DecimalField(10,4) | optional | Maximum value for 100 score |
| `is_active` | BooleanField | default True | Whether included in scoring |

Default weights:
- QoE Rating: 30%
- 4G Coverage: 20%
- Download Speed: 20%
- Complaint Resolution Rate: 15%
- Call Success Rate: 10%
- Complaint Volume: 5% (inverse — fewer = higher score)

#### OperatorScore

Computed scorecard snapshot for one operator for one period.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK | Inherited from BaseModel |
| `operator` | FK -> NetworkOperator | required, indexed | Which operator |
| `period` | DateField | indexed | Snapshot date (first of month) |
| `overall_score` | DecimalField(5,2) | 0-100 | Weighted composite score |
| `coverage_score` | DecimalField(5,2) | 0-100 | 4G coverage normalised |
| `coverage_value` | DecimalField(5,2) | | Raw 4G coverage percentage |
| `speed_score` | DecimalField(5,2) | 0-100 | Download speed normalised |
| `speed_value` | DecimalField(8,2) | | Raw average speed in Mbps |
| `qoe_score` | DecimalField(5,2) | 0-100 | QoE rating normalised |
| `qoe_value` | DecimalField(3,2) | | Raw average QoE rating (1-5) |
| `resolution_score` | DecimalField(5,2) | 0-100 | Resolution rate normalised |
| `resolution_value` | DecimalField(5,2) | | Raw resolution rate % |
| `call_success_score` | DecimalField(5,2) | 0-100 | Call success normalised |
| `call_success_value` | DecimalField(5,2) | | Raw call success rate % |
| `complaint_score` | DecimalField(5,2) | 0-100 | Complaint vol normalised (inverse) |
| `complaint_value` | PositiveIntegerField | | Raw complaint count (30 days) |
| `market_share` | DecimalField(5,2) | optional | Market share % for context |
| `total_subscribers` | PositiveIntegerField | optional | Subscriber count for context |
| `computed_at` | DateTimeField | auto | When this score was calculated |

**unique_together:** `(operator, period)`

#### ManualMetricEntry

Staff-entered metrics not available from automated sources (e.g. price competitiveness).

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK | Inherited from AuditableModel |
| `operator` | FK -> NetworkOperator | required | Which operator |
| `metric_name` | CharField(100) | required | Metric label |
| `value` | DecimalField(10,4) | required | Metric value |
| `unit` | CharField(20) | optional | Display unit (%, Mbps, etc.) |
| `period` | DateField | required | Period this applies to |
| `notes` | TextField | optional | Justification or source |

### Scoring Algorithm

For each metric, the raw value is normalised to 0-100:

```
For HIGHER_BETTER metrics:
    score = ((value - benchmark_min) / (benchmark_max - benchmark_min)) * 100
    score = clamp(score, 0, 100)

For LOWER_BETTER metrics (complaint volume):
    score = ((benchmark_max - value) / (benchmark_max - benchmark_min)) * 100
    score = clamp(score, 0, 100)

Overall = sum(metric_score * weight / 100) for all active metrics
```

### API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/scorecard/` | Public | All operators current scores |
| GET | `/api/v1/scorecard/{operator_code}/` | Public | Single operator detailed scorecard |
| GET | `/api/v1/scorecard/{operator_code}/history/` | Public | Historical scores for trend chart |
| GET | `/api/v1/scorecard/compare/` | Public | Side-by-side comparison data |
| GET | `/api/v1/scorecard/weights/` | Staff | Current weight configuration |
| PATCH | `/api/v1/scorecard/weights/{metric}/` | Admin | Update weight for a metric |
| POST | `/api/v1/scorecard/compute/` | Staff | Trigger scorecard recomputation |
| POST | `/api/v1/scorecard/manual/` | Staff | Submit manual metric entry |
| GET | `/api/v1/scorecard/manual/` | Staff | List manual entries |

### Seed Data

- **36 OperatorScore records:** 3 operators x 12 monthly periods (Apr 2025 - Mar 2026)
- Scores show realistic progression with seasonal variation
- Default ScorecardWeightConfig: 6 metrics with standard weights
- **10 ManualMetricEntry records:** price competitiveness per operator per quarter
- Mascom: overall ~72, Orange: ~69, BTCL: ~58 (reflecting real market position)

### Key Business Rules

1. Scorecard is computed via management command or Celery periodic task (daily)
2. Computation pulls live data from: CoverageArea (latest period), QoEReport (last 30 days), Complaint (last 30 days), QoSRecord (latest period)
3. If a metric has no data for an operator, that metric is excluded and weights re-normalised
4. Historical scores are immutable once computed — they represent point-in-time snapshots
5. Manual entries supplement automated data, not replace it
6. Colour coding thresholds: green > 80, amber 50-80, red < 50

---

## Feature 4 — Proactive Alert Subscriptions

**App name:** `alerts`

### Purpose

Push regulatory information to citizens and businesses via email. Subscribers
choose categories they care about. When relevant events happen (new publication,
tender, licence expiry, complaint status change), subscribers are notified
automatically via email.

### Models

#### AlertCategory

Categories of alerts citizens can subscribe to.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK | Inherited from BaseModel |
| `name` | CharField(200) | required | Display name |
| `code` | CharField(50) | unique, indexed | Machine code (e.g. "NEW_REGULATION") |
| `description` | TextField | optional | What this category covers |
| `icon` | CharField(50) | optional | Icon identifier for frontend |
| `is_public` | BooleanField | default True | Visible to anonymous subscribers |
| `is_active` | BooleanField | default True | Whether category accepts subscriptions |
| `sort_order` | PositiveIntegerField | default 0 | Display ordering |

Default categories:
1. `NEW_REGULATION` — New regulation or policy published
2. `NEW_TENDER` — New tender published
3. `LICENCE_EXPIRY` — Licence expiry reminders (90/60/30 days)
4. `CYBERSECURITY` — Cybersecurity advisories
5. `CONSUMER_RIGHTS` — Consumer rights updates
6. `COMPLAINT_STATUS` — Complaint status changes (auto-enrolled)
7. `APPLICATION_STATUS` — Application status changes (auto-enrolled)
8. `SPECTRUM_NOTICE` — Spectrum and frequency notices

#### AlertSubscription

A subscriber's subscription to one or more alert categories.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK | Inherited from BaseModel |
| `email` | EmailField | indexed | Subscriber email |
| `user` | FK -> User | nullable | Linked user account (if registered) |
| `categories` | M2M -> AlertCategory | | Subscribed categories |
| `is_confirmed` | BooleanField | default False | Email confirmation status |
| `confirm_token` | CharField(64) | unique | Token for email confirmation link |
| `unsubscribe_token` | CharField(64) | unique | Token for one-click unsubscribe |
| `confirmed_at` | DateTimeField | nullable | When email was confirmed |
| `operator_filter` | CharField(20) | nullable | Optional operator filter (MASCOM/ORANGE/BTCL) |
| `is_active` | BooleanField | default True | Master on/off switch |

**unique_together:** `(email,)` — one subscription record per email, categories via M2M

#### AlertLog

Audit trail of sent alerts.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK | Inherited from BaseModel |
| `subscription` | FK -> AlertSubscription | required | Who was notified |
| `category` | FK -> AlertCategory | required | Alert category |
| `subject` | CharField(300) | required | Email subject line |
| `body_preview` | TextField | max 500 | First 500 chars of email body |
| `related_object_type` | CharField(50) | optional | e.g. "publication", "tender", "complaint" |
| `related_object_id` | UUIDField | optional | ID of the triggering object |
| `status` | CharField(20) | PENDING/SENT/FAILED | Delivery status |
| `sent_at` | DateTimeField | nullable | When email was sent |
| `error_message` | TextField | optional | Error details if failed |

### Email Delivery

- Celery tasks triggered on relevant events (publication created, tender opened, status change)
- HTML email templates per category — BOCRA branded
- Batch sending: large lists sent in batches of 100 via Celery
- Double opt-in: confirmation email with token link before any alerts are sent
- Every email includes one-click unsubscribe link
- Django's built-in email backend + SMTP configuration

### API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/alerts/subscribe/` | Public | Subscribe email to alert categories |
| GET | `/api/v1/alerts/confirm/{token}/` | Public | Confirm subscription via email link |
| GET | `/api/v1/alerts/unsubscribe/{token}/` | Public | One-click unsubscribe |
| GET | `/api/v1/alerts/categories/` | Public | List all public alert categories |
| GET | `/api/v1/alerts/subscriptions/` | Auth | List my subscriptions |
| PATCH | `/api/v1/alerts/subscriptions/` | Auth | Update my subscription categories |
| DELETE | `/api/v1/alerts/subscriptions/` | Auth | Delete my subscription |
| GET | `/api/v1/alerts/logs/` | Staff | Alert sending audit log |
| GET | `/api/v1/alerts/stats/` | Staff | Subscription analytics |

### Seed Data

- **8 AlertCategory** records (all default categories listed above)
- **200 AlertSubscription** records (mix of confirmed/unconfirmed, with/without user accounts)
- **500 AlertLog** records spread across categories and time periods
- Realistic distribution: more subscriptions for NEW_TENDER and LICENCE_EXPIRY

### Key Business Rules

1. Double opt-in required — subscription is not active until email confirmed
2. Confirmation tokens expire after 72 hours
3. Unsubscribe is one-click, no login required, instant
4. Registered users filing complaints are auto-enrolled in COMPLAINT_STATUS
5. Licence applicants are auto-enrolled in APPLICATION_STATUS and LICENCE_EXPIRY
6. Rate limit subscription creation: 3 per email per hour
7. Batch sending respects SMTP rate limits (configurable, default 100/batch)
8. Failed sends are retried up to 3 times with exponential backoff

---

## Cross-Feature Dependencies

```
analytics.NetworkOperator
    |
    +-- coverages.CoverageArea (FK: operator)
    +-- qoe.QoEReport (uses operator code)
    +-- scorecard.OperatorScore (FK: operator)

coverages.District
    |
    +-- coverages.CoverageArea (FK: district)
    +-- qoe.QoEReport (FK: district)

scorecard reads from (no FK, computed):
    +-- coverages.CoverageArea (latest coverage %)
    +-- qoe.QoEReport (avg rating, avg speed, last 30 days)
    +-- complaints.Complaint (volume, resolution rate, last 30 days)
    +-- analytics.QoSRecord (call success rate, latest period)

alerts triggers from (signal/hook, no FK):
    +-- publications.Publication (on create -> NEW_REGULATION)
    +-- tenders.Tender (on create -> NEW_TENDER)
    +-- complaints.Complaint (on status change -> COMPLAINT_STATUS)
    +-- licensing.Application (on status change -> APPLICATION_STATUS)
    +-- licensing.Licence (on expiry approach -> LICENCE_EXPIRY)
```

---

## Seed Data Summary

| App | Model | Record Count | Source / Logic |
|---|---|---|---|
| coverages | District | 16 | 10 main districts + 6 sub-districts |
| coverages | CoverageArea | 2,000+ | 3 ops x 16 districts x 3 techs x ~14 periods |
| coverages | CoverageUpload | 6 | Sample upload history |
| qoe | QoEReport | 5,000 | 6 months, weighted by district population |
| scorecard | ScorecardWeightConfig | 6 | Default weight configuration |
| scorecard | OperatorScore | 36 | 3 operators x 12 monthly periods |
| scorecard | ManualMetricEntry | 12 | Price competitiveness quarterly |
| alerts | AlertCategory | 8 | All default categories |
| alerts | AlertSubscription | 200 | Mix of confirmed/unconfirmed |
| alerts | AlertLog | 500 | Spread across 6 months |
| **Total** | | **~7,768+** | |

All seed data commands follow the pattern: `python manage.py seed_{app_name} [--clear]`

- `python manage.py seed_coverages [--clear]`
- `python manage.py seed_qoe [--clear]`
- `python manage.py seed_scorecard [--clear]`
- `python manage.py seed_alerts [--clear]`
