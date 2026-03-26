# Coverage Map API

> Base URL: `/api/v1/coverages/`
> Swagger tags: **Coverage Map** . **Coverage Map -- Staff**

Interactive network coverage map data for Botswana. Provides district boundaries
as GeoJSON, per-operator coverage records filterable by technology tier, national
and district-level summaries, side-by-side operator comparison, and admin upload
endpoints for ingesting new coverage data from operator submissions.

---

## Table of Contents

- [Endpoints Summary](#endpoints-summary)
- [Districts](#districts)
- [Coverage Areas](#coverage-areas)
- [Summaries](#summaries)
- [Comparison](#comparison)
- [Uploads (Staff/Admin)](#uploads-staffadmin)
- [Analytics (Staff)](#analytics-staff)
- [Models & Enums](#models--enums)
- [GeoJSON Format Reference](#geojson-format-reference)
- [Seed Data](#seed-data)

---

## Endpoints Summary

### Public (no auth required)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/districts/` | List all Botswana districts (lightweight, no boundaries) |
| `GET` | `/districts/geojson/` | All district boundaries as GeoJSON FeatureCollection |
| `GET` | `/districts/{id}/` | Single district detail with boundary + current coverage |
| `GET` | `/operators/` | Operators with coverage metadata (district count, technologies) |
| `GET` | `/areas/` | Coverage area records (paginated, filterable) |
| `GET` | `/areas/geojson/` | Coverage as GeoJSON FeatureCollection for Leaflet map overlay |
| `GET` | `/summary/` | National coverage summary (per-operator, white spots) |
| `GET` | `/summary/{district_id}/` | District-level coverage breakdown by operator and technology |
| `GET` | `/compare/` | Side-by-side operator coverage comparison across all districts |

### Staff / Admin (requires authentication + role)

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/upload/` | Admin | Upload coverage GeoJSON file from operator submission |
| `GET` | `/uploads/` | Staff | List upload history with processing status |
| `GET` | `/stats/` | Staff | Coverage analytics: trends, district ranking |

---

## Districts

### GET `/districts/`

List all active Botswana districts. Returns lightweight data without boundary
GeoJSON (use `/districts/geojson/` for map rendering).

**Query Parameters:** None

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Districts retrieved successfully.",
  "data": [
    {
      "id": "uuid",
      "name": "South-East (Gaborone)",
      "code": "SE",
      "region": "Southern",
      "population": 365000,
      "area_sq_km": "1878.00",
      "center_lat": "-24.654500",
      "center_lng": "25.908900",
      "is_active": true
    }
  ],
  "errors": null
}
```

---

### GET `/districts/geojson/`

All district boundaries as a GeoJSON FeatureCollection. Use this to render the
base Botswana district map on Leaflet. Each Feature includes the district
boundary as its geometry and district metadata in properties.

**Response `200 OK`**

```json
{
  "success": true,
  "message": "District boundaries retrieved.",
  "data": {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "geometry": {
          "type": "Polygon",
          "coordinates": [[[25.72, -24.50], [26.10, -24.50], ...]]
        },
        "properties": {
          "id": "uuid",
          "name": "South-East (Gaborone)",
          "code": "SE",
          "region": "Southern",
          "population": 365000,
          "area_sq_km": 1878.00,
          "center_lat": -24.6545,
          "center_lng": 25.9089
        }
      }
    ]
  },
  "errors": null
}
```

**Frontend usage:**

```javascript
const response = await fetch('/api/v1/coverages/districts/geojson/');
const { data } = await response.json();
L.geoJSON(data).addTo(map);
```

---

### GET `/districts/{id}/`

Full district detail including boundary GeoJSON and all coverage data for the
latest reporting period. Use this when a user clicks a district on the map.

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `id` | UUID | District primary key |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "District detail retrieved.",
  "data": {
    "id": "uuid",
    "name": "South-East (Gaborone)",
    "code": "SE",
    "region": "Southern",
    "population": 365000,
    "area_sq_km": "1878.00",
    "boundary_geojson": { "type": "Polygon", "coordinates": [...] },
    "center_lat": "-24.654500",
    "center_lng": "25.908900",
    "is_active": true,
    "coverage": [
      {
        "id": "uuid",
        "operator": "uuid",
        "operator_name": "Mascom",
        "operator_code": "MASCOM",
        "district": "uuid",
        "district_name": "South-East (Gaborone)",
        "district_code": "SE",
        "technology": "4G",
        "coverage_level": "FULL",
        "coverage_level_display": "Full (80-100%)",
        "coverage_percentage": "95.00",
        "population_covered": 346750,
        "signal_strength_avg": "-53.20",
        "period": "2026-03-01",
        "source": "BOCRA",
        "notes": ""
      }
    ],
    "coverage_period": "2026-03-01"
  },
  "errors": null
}
```

---

## Coverage Areas

### GET `/areas/`

Paginated list of coverage area records. Defaults to the latest reporting period.
Supports filtering by operator, technology, district, period, and coverage level.

**Query Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `operator` | string | No | Operator code: `MASCOM`, `ORANGE`, `BTCL` |
| `technology` | string | No | Technology tier: `2G`, `3G`, `4G` |
| `district` | UUID | No | District primary key |
| `period` | date | No | Reporting period (YYYY-MM-DD). Defaults to latest. |
| `coverage_level` | string | No | `FULL`, `PARTIAL`, `MINIMAL`, `NONE` |
| `ordering` | string | No | Sort field: `period`, `coverage_percentage`, `operator__name`, `district__name` |
| `search` | string | No | Search district or operator name |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Coverage areas retrieved.",
  "data": {
    "count": 48,
    "next": "http://localhost:8000/api/v1/coverages/areas/?page=2",
    "previous": null,
    "results": [
      {
        "id": "uuid",
        "operator": "uuid",
        "operator_name": "Mascom",
        "operator_code": "MASCOM",
        "district": "uuid",
        "district_name": "Central",
        "district_code": "CE",
        "technology": "4G",
        "coverage_level": "FULL",
        "coverage_level_display": "Full (80-100%)",
        "coverage_percentage": "88.00",
        "population_covered": 475200,
        "signal_strength_avg": "-54.96",
        "period": "2026-03-01",
        "source": "BOCRA",
        "notes": ""
      }
    ]
  },
  "errors": null
}
```

**Example requests:**

```
GET /api/v1/coverages/areas/?operator=MASCOM&technology=4G
GET /api/v1/coverages/areas/?district={uuid}&period=2025-10-01
GET /api/v1/coverages/areas/?coverage_level=NONE
GET /api/v1/coverages/areas/?ordering=-coverage_percentage
```

---

### GET `/areas/geojson/`

Coverage areas as a GeoJSON FeatureCollection, ready for Leaflet map overlay.
Each Feature has the coverage polygon as geometry and operator/technology/level
metadata in properties. Excludes NONE-coverage areas from the response.

**Query Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `operator` | string | No | Filter by operator code |
| `technology` | string | No | Filter by technology tier |
| `period` | date | No | Reporting period. Defaults to latest. |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Coverage GeoJSON retrieved.",
  "data": {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "geometry": {
          "type": "Polygon",
          "coordinates": [[[25.50, -20.80], [27.10, -20.80], ...]]
        },
        "properties": {
          "id": "uuid",
          "operator": "MASCOM",
          "operator_name": "Mascom",
          "technology": "4G",
          "coverage_level": "FULL",
          "coverage_percentage": 88.0,
          "district": "Central",
          "district_code": "CE",
          "period": "2026-03-01",
          "population_covered": 475200
        }
      }
    ]
  },
  "errors": null
}
```

**Frontend usage:**

```javascript
// Load Mascom 4G coverage overlay
const res = await fetch('/api/v1/coverages/areas/geojson/?operator=MASCOM&technology=4G');
const { data } = await res.json();

L.geoJSON(data, {
  style: feature => ({
    fillColor: getColorByCoverage(feature.properties.coverage_level),
    weight: 1,
    fillOpacity: 0.5
  }),
  onEachFeature: (feature, layer) => {
    layer.bindPopup(`${feature.properties.district}: ${feature.properties.coverage_percentage}%`);
  }
}).addTo(map);
```

---

## Operators

### GET `/operators/`

List operators that have coverage data, enriched with coverage metadata for
building filter controls on the frontend.

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Coverage operators retrieved.",
  "data": [
    {
      "id": "uuid",
      "name": "Mascom",
      "code": "MASCOM",
      "logo": null,
      "districts_covered": 16,
      "technologies": ["2G", "3G", "4G"]
    },
    {
      "id": "uuid",
      "name": "Orange",
      "code": "ORANGE",
      "logo": null,
      "districts_covered": 16,
      "technologies": ["2G", "3G", "4G"]
    },
    {
      "id": "uuid",
      "name": "Btcl",
      "code": "BTCL",
      "logo": null,
      "districts_covered": 13,
      "technologies": ["2G", "3G", "4G"]
    }
  ],
  "errors": null
}
```

---

## Summaries

### GET `/summary/`

National-level coverage summary. Returns overall average, per-operator
breakdown, and white spots (districts with no meaningful coverage).

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `technology` | string | No | `4G` | Technology to summarise |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Coverage summary retrieved.",
  "data": {
    "period": "2026-03-01",
    "technology": "4G",
    "national_avg_coverage": 57.25,
    "total_districts": 16,
    "by_operator": [
      {
        "operator": "MASCOM",
        "operator_name": "Mascom",
        "avg_coverage_percentage": 71.12,
        "districts_covered": 16,
        "total_districts": 16,
        "population_covered": 1661589
      },
      {
        "operator": "ORANGE",
        "operator_name": "Orange",
        "avg_coverage_percentage": 63.69,
        "districts_covered": 16,
        "total_districts": 16,
        "population_covered": 1574958
      },
      {
        "operator": "BTCL",
        "operator_name": "Btcl",
        "avg_coverage_percentage": 36.94,
        "districts_covered": 13,
        "total_districts": 16,
        "population_covered": 1038650
      }
    ],
    "white_spots": [],
    "white_spot_count": 0
  },
  "errors": null
}
```

---

### GET `/summary/{district_id}/`

Coverage breakdown for a single district: every operator, every technology,
coverage level, percentage, population covered, and signal strength.

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `district_id` | UUID | District primary key |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Coverage summary for Kgalagadi retrieved.",
  "data": {
    "district": {
      "id": "uuid",
      "name": "Kgalagadi",
      "code": "KD",
      "population": 50000
    },
    "period": "2026-03-01",
    "operators": [
      {
        "operator": "MASCOM",
        "operator_name": "Mascom",
        "technologies": {
          "2G": {
            "coverage_level": "PARTIAL",
            "coverage_percentage": 60.0,
            "population_covered": 30000,
            "signal_strength_avg": -72.19
          },
          "3G": {
            "coverage_level": "PARTIAL",
            "coverage_percentage": 55.0,
            "population_covered": 27500,
            "signal_strength_avg": -74.44
          },
          "4G": {
            "coverage_level": "PARTIAL",
            "coverage_percentage": 30.0,
            "population_covered": 15000,
            "signal_strength_avg": -93.26
          }
        }
      }
    ]
  },
  "errors": null
}
```

**Response `404 Not Found`**

```json
{
  "success": false,
  "message": "District not found.",
  "data": null,
  "errors": null
}
```

---

## Comparison

### GET `/compare/`

Side-by-side operator comparison across all districts for a given technology.
Returns a pivot table: rows are districts, columns are operators.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `technology` | string | No | `4G` | Technology to compare |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Coverage comparison retrieved.",
  "data": {
    "period": "2026-03-01",
    "technology": "4G",
    "operators": [
      { "code": "BTCL", "name": "Btcl" },
      { "code": "MASCOM", "name": "Mascom" },
      { "code": "ORANGE", "name": "Orange" }
    ],
    "comparison": [
      {
        "district": "Central",
        "district_code": "CE",
        "district_id": "uuid",
        "operators": {
          "BTCL":   { "coverage_level": "PARTIAL", "coverage_percentage": 55.0 },
          "MASCOM": { "coverage_level": "FULL",    "coverage_percentage": 88.0 },
          "ORANGE": { "coverage_level": "FULL",    "coverage_percentage": 85.0 }
        }
      },
      {
        "district": "Kgalagadi",
        "district_code": "KD",
        "district_id": "uuid",
        "operators": {
          "BTCL":   { "coverage_level": "NONE",    "coverage_percentage": 0.0 },
          "MASCOM": { "coverage_level": "PARTIAL", "coverage_percentage": 30.0 },
          "ORANGE": { "coverage_level": "MINIMAL", "coverage_percentage": 5.0 }
        }
      }
    ]
  },
  "errors": null
}
```

---

## Uploads (Staff/Admin)

### POST `/upload/`

Upload new coverage GeoJSON data from an operator submission. The file is stored
and queued for processing. A Celery task will parse the GeoJSON and create or
update CoverageArea records.

**Auth:** Admin role required

**Content-Type:** `multipart/form-data`

**Request body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `operator` | UUID | Yes | Operator ID |
| `technology` | string | Yes | `2G`, `3G`, or `4G` |
| `file` | file | Yes | GeoJSON file (.json or .geojson) |
| `period` | date | Yes | Reporting period this upload covers |

**Response `201 Created`**

```json
{
  "success": true,
  "message": "Coverage data uploaded. Processing will begin shortly.",
  "data": {
    "id": "uuid",
    "operator": "uuid",
    "operator_name": "Mascom",
    "operator_code": "MASCOM",
    "technology": "4G",
    "file": "/media/coverages/uploads/2026/03/mascom_4g_q1_2026.geojson",
    "file_name": "mascom_4g_q1_2026.geojson",
    "file_size": 45230,
    "period": "2026-01-01",
    "status": "PENDING",
    "status_display": "Pending",
    "records_created": 0,
    "error_message": "",
    "processed_at": null,
    "created_at": "2026-03-25T10:30:00Z",
    "created_by": "uuid"
  },
  "errors": null
}
```

---

### GET `/uploads/`

List all coverage upload history with processing status. Paginated.

**Auth:** Staff role required

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Upload history retrieved.",
  "data": {
    "count": 6,
    "next": null,
    "previous": null,
    "results": [
      {
        "id": "uuid",
        "operator": "uuid",
        "operator_name": "Mascom",
        "operator_code": "MASCOM",
        "technology": "4G",
        "file": "/media/coverages/uploads/...",
        "file_name": "mascom_4g_q1_2026.geojson",
        "file_size": 45230,
        "period": "2026-01-01",
        "status": "COMPLETED",
        "status_display": "Completed",
        "records_created": 16,
        "error_message": "",
        "processed_at": "2026-03-25T10:31:00Z",
        "created_at": "2026-03-25T10:30:00Z",
        "created_by": "uuid"
      }
    ]
  },
  "errors": null
}
```

---

## Analytics (Staff)

### GET `/stats/`

Coverage growth trends over time and district ranking for staff analytics.

**Auth:** Staff role required

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `technology` | string | No | `4G` | Technology to analyse |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Coverage statistics retrieved.",
  "data": {
    "technology": "4G",
    "trends": [
      {
        "period": "2023-01-01",
        "operators": { "MASCOM": 58.5, "ORANGE": 50.2, "BTCL": 22.1 }
      },
      {
        "period": "2026-03-01",
        "operators": { "MASCOM": 71.1, "ORANGE": 63.7, "BTCL": 36.9 }
      }
    ],
    "district_ranking": [
      { "district": "South-East (Gaborone)", "code": "SE", "avg_coverage": 90.67 },
      { "district": "Kgalagadi", "code": "KD", "avg_coverage": 11.67 }
    ],
    "total_records": 2016,
    "periods_available": ["2023-01-01", "2023-04-01", "...", "2026-03-01"]
  },
  "errors": null
}
```

---

## Models & Enums

### District

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Primary key |
| `name` | string | District name (e.g. "South-East (Gaborone)") |
| `code` | string | Unique short code (e.g. "SE") |
| `region` | string | Broader region: Southern, Northern, Central, Western |
| `population` | integer | Approximate population |
| `area_sq_km` | decimal | Area in square kilometres |
| `boundary_geojson` | object | GeoJSON Polygon or MultiPolygon |
| `center_lat` | decimal | Centre point latitude |
| `center_lng` | decimal | Centre point longitude |
| `is_active` | boolean | Whether visible on map |

### CoverageArea

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Primary key |
| `operator` | FK (NetworkOperator) | Which operator |
| `district` | FK (District) | Which district |
| `technology` | enum | `2G`, `3G`, `4G`, `5G` |
| `coverage_level` | enum | `FULL`, `PARTIAL`, `MINIMAL`, `NONE` |
| `coverage_percentage` | decimal | 0-100 numeric percentage |
| `population_covered` | integer | Estimated population with access |
| `geometry_geojson` | object | Optional coverage polygon override |
| `signal_strength_avg` | decimal | Average signal in dBm |
| `period` | date | Reporting period (first of quarter) |
| `source` | enum | `BOCRA`, `OPERATOR_SUBMISSION`, `ESTIMATED` |
| `notes` | text | Internal notes |

**Unique constraint:** `(operator, district, technology, period)`

### CoverageUpload

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Primary key |
| `operator` | FK (NetworkOperator) | Which operator submitted |
| `technology` | enum | `2G`, `3G`, `4G` |
| `file` | file | Uploaded GeoJSON/shapefile |
| `file_name` | string | Original filename |
| `file_size` | integer | File size in bytes |
| `period` | date | Reporting period |
| `status` | enum | `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED` |
| `records_created` | integer | Records created from upload |
| `error_message` | text | Error details if failed |
| `processed_at` | datetime | When processing completed |
| `created_by` | FK (User) | Admin who uploaded |

### Coverage Level Enum

| Value | Label | Range |
|---|---|---|
| `FULL` | Full (80-100%) | 80-100% area covered |
| `PARTIAL` | Partial (30-79%) | 30-79% area covered |
| `MINIMAL` | Minimal (1-29%) | 1-29% area covered |
| `NONE` | None (0%) | No coverage |

### Coverage Source Enum

| Value | Label |
|---|---|
| `BOCRA` | BOCRA Internal Data |
| `OPERATOR_SUBMISSION` | Operator Submission |
| `ESTIMATED` | Estimated / Extrapolated |

---

## GeoJSON Format Reference

All geometry data follows the [GeoJSON RFC 7946](https://datatracker.ietf.org/doc/html/rfc7946) specification.

**Coordinate order:** `[longitude, latitude]` (NOT lat/lng)

**FeatureCollection structure:**

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[lng, lat], [lng, lat], ...]]
      },
      "properties": { ... }
    }
  ]
}
```

Both `/districts/geojson/` and `/areas/geojson/` return FeatureCollections
wrapped inside the standard BOCRA API envelope (`data` field).

---

## Seed Data

Run the seed command to populate districts and coverage data:

```bash
python manage.py seed_coverages          # Create 16 districts + 2000+ coverage records
python manage.py seed_coverages --clear  # Clear existing data first
```

**Seeded data:**
- 16 Botswana districts (10 main + 6 sub-districts) with boundary GeoJSON
- 3 operators: Mascom, Orange, BTCL
- 3 technologies per district per operator: 2G, 3G, 4G
- 14 quarterly reporting periods (Q1 2023 -- Mar 2026)
- Historical progression: coverage improves over time
- Total: 2,016 CoverageArea records

Districts: South-East (Gaborone), North-East (Francistown), North-West (Maun),
Chobe, Central, Kgatleng, Kweneng, Southern, Kgalagadi, Ghanzi, Selebi-Phikwe,
Lobatse, Jwaneng, Sowa Town, Orapa, Letlhakane.
