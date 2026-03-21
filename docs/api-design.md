# API Design

> BOCRA Digital Platform — API Standards & Endpoint Reference

## Table of Contents

- [API Conventions](#api-conventions)
- [Response Format](#response-format)
- [Authentication](#authentication)
- [Pagination](#pagination)
- [Filtering & Search](#filtering--search)
- [Error Handling](#error-handling)
- [Endpoints by Module](#endpoints-by-module)

---

## API Conventions

### Base URL

```
/api/v1/{module}/{resource}/
```

### HTTP Methods

| Method | Usage |
|---|---|
| `GET` | Retrieve resource(s) — never modify state |
| `POST` | Create new resource |
| `PUT` | Full update of existing resource |
| `PATCH` | Partial update of existing resource |
| `DELETE` | Remove resource (soft delete where applicable) |

### Versioning

- Current version: `/api/v1/`
- Future breaking changes go to `/api/v2/`
- Non-breaking additions (new fields, new endpoints) stay in v1

### Content Type

- All requests and responses: `application/json`
- File uploads: `multipart/form-data`

---

## Response Format

All API responses use a consistent JSON envelope:

### Success Response

```json
{
  "success": true,
  "message": "Applications retrieved successfully",
  "data": {
    "results": [...],
    "count": 42,
    "next": "/api/v1/licensing/applications/?page=2",
    "previous": null
  },
  "errors": null
}
```

### Error Response

```json
{
  "success": false,
  "message": "Validation failed",
  "data": null,
  "errors": {
    "email": ["This field is required."],
    "licence_type": ["Invalid licence type."]
  }
}
```

### HTTP Status Codes

| Code | Meaning | When Used |
|---|---|---|
| `200` | OK | Successful GET, PUT, PATCH |
| `201` | Created | Successful POST |
| `204` | No Content | Successful DELETE |
| `400` | Bad Request | Validation errors |
| `401` | Unauthorized | Missing or invalid JWT |
| `403` | Forbidden | Valid JWT but insufficient permissions |
| `404` | Not Found | Resource doesn't exist |
| `429` | Too Many Requests | Rate limited |
| `500` | Internal Server Error | Unexpected server error |

---

## Authentication

### JWT Token Flow

```
POST /api/v1/accounts/login/
Body: { "email": "user@example.com", "password": "..." }

Response: {
  "access": "eyJ...",    // 15-minute expiry
  "refresh": "eyJ..."    // 7-day expiry
}
```

### Using Tokens

Include the access token in the `Authorization` header:

```
Authorization: Bearer eyJ...
```

### Token Refresh

```
POST /api/v1/accounts/token/refresh/
Body: { "refresh": "eyJ..." }

Response: { "access": "new_eyJ..." }
```

### Public vs Protected Endpoints

| Access Level | Description | Auth Required |
|---|---|---|
| Public | Anyone can access | No |
| Registered User | Must have valid JWT | Yes |
| Owner | Must own the resource | Yes + ownership check |
| Staff | BOCRA staff only | Yes + staff role |
| Admin | BOCRA admin only | Yes + admin role |

---

## Pagination

All list endpoints are paginated:

```
GET /api/v1/licensing/applications/?page=1&page_size=20
```

### Parameters

| Param | Default | Max | Description |
|---|---|---|---|
| `page` | 1 | — | Page number |
| `page_size` | 20 | 100 | Results per page |

### Response

```json
{
  "count": 142,
  "next": "/api/v1/licensing/applications/?page=2&page_size=20",
  "previous": null,
  "results": [...]
}
```

---

## Filtering & Search

### Query Parameter Filtering

```
GET /api/v1/complaints/?status=SUBMITTED&category=BILLING
GET /api/v1/publications/?category=regulations&year=2025
GET /api/v1/tenders/?status=OPEN&ordering=-deadline
```

### Ordering

```
GET /api/v1/news/?ordering=-published_at       # newest first
GET /api/v1/licensing/types/?ordering=name      # alphabetical
```

### Search

```
GET /api/v1/publications/?search=spectrum+policy
GET /api/v1/news/?search=broadband
```

### Date Range Filtering

```
GET /api/v1/analytics/qos/?date_from=2026-01-01&date_to=2026-03-31
```

---

## Error Handling

### Validation Errors (400)

```json
{
  "success": false,
  "message": "Validation failed",
  "data": null,
  "errors": {
    "email": ["Enter a valid email address."],
    "password": ["This field may not be blank."],
    "licence_type": ["Object with pk=999 does not exist."]
  }
}
```

### Authentication Error (401)

```json
{
  "success": false,
  "message": "Authentication credentials were not provided.",
  "data": null,
  "errors": null
}
```

### Permission Error (403)

```json
{
  "success": false,
  "message": "You do not have permission to perform this action.",
  "data": null,
  "errors": null
}
```

### Not Found (404)

```json
{
  "success": false,
  "message": "Not found.",
  "data": null,
  "errors": null
}
```

---

## Endpoints by Module

### Accounts (`/api/v1/accounts/`)

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/register/` | Register new user | Public |
| `GET` | `/verify-email/` | Verify email via token | Public |
| `POST` | `/login/` | Login — returns JWT pair | Public |
| `POST` | `/token/refresh/` | Refresh access token | Public |
| `POST` | `/password-reset/` | Request password reset email | Public |
| `POST` | `/password-reset/confirm/` | Set new password with token | Public |
| `GET` | `/profile/` | Get current user profile | Registered |
| `PATCH` | `/profile/` | Update profile | Registered |
| `GET` | `/users/` | List all users | Admin |
| `GET` | `/users/{id}/` | User detail | Admin |
| `PATCH` | `/users/{id}/` | Update user (role, active status) | Admin |

---

### Licensing (`/api/v1/licensing/`)

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/types/` | List all licence types | Public |
| `GET` | `/types/{id}/` | Licence type detail + requirements | Public |
| `GET` | `/verify/` | Public licence verification (`?licence_no=` or `?company=`) | Public |
| `GET` | `/applications/` | List my applications | Registered |
| `POST` | `/applications/` | Submit new application | Registered |
| `GET` | `/applications/{id}/` | Application detail + status timeline | Owner / Staff |
| `PATCH` | `/applications/{id}/status/` | Update application status | Staff |
| `POST` | `/applications/{id}/documents/` | Upload supporting documents | Owner / Staff |
| `GET` | `/licences/` | List my active licences | Registered |
| `GET` | `/licences/{id}/` | Licence detail | Owner / Staff |
| `POST` | `/licences/{id}/renew/` | Initiate licence renewal | Licensee |
| `GET` | `/licences/{id}/certificate/` | Download PDF certificate | Owner / Staff |
| `GET` | `/staff/applications/` | Staff queue — all applications | Staff |
| `GET` | `/staff/applications/{id}/` | Staff view of application | Staff |

---

### Complaints (`/api/v1/complaints/`)

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/` | Submit a complaint | Public (or Registered) |
| `GET` | `/track/` | Track complaint by reference (`?ref=CMP-2026-001234`) | Public |
| `GET` | `/` | List my complaints | Registered |
| `GET` | `/{id}/` | Complaint detail + case notes timeline | Owner / Staff |
| `PATCH` | `/{id}/status/` | Update case status | Staff |
| `PATCH` | `/{id}/assign/` | Assign case handler | Staff |
| `POST` | `/{id}/notes/` | Add internal case note | Staff |
| `POST` | `/{id}/resolve/` | Send resolution to citizen | Staff |
| `GET` | `/analytics/` | Aggregate complaint stats | Staff / Admin |
| `GET` | `/categories/` | List complaint categories | Public |

---

### Publications (`/api/v1/publications/`)

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/` | List publications (filterable) | Public |
| `GET` | `/{id}/` | Publication detail | Public |
| `GET` | `/{id}/download/` | Download document file | Public |
| `GET` | `/categories/` | List publication categories | Public |
| `POST` | `/` | Create publication | Admin |
| `PUT` | `/{id}/` | Update publication | Admin |
| `DELETE` | `/{id}/` | Remove publication | Admin |

---

### Tenders (`/api/v1/tenders/`)

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/` | List tenders (filterable by status) | Public |
| `GET` | `/{id}/` | Tender detail | Public |
| `GET` | `/{id}/documents/` | List tender documents for download | Public |
| `POST` | `/` | Create tender listing | Admin |
| `PUT` | `/{id}/` | Update tender | Admin |
| `DELETE` | `/{id}/` | Remove tender | Admin |

---

### News (`/api/v1/news/`)

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/` | List articles (filterable) | Public |
| `GET` | `/{id}/` | Article detail | Public |
| `GET` | `/categories/` | List news categories | Public |
| `POST` | `/` | Create article | Admin |
| `PUT` | `/{id}/` | Update article | Admin |
| `PATCH` | `/{id}/publish/` | Publish/unpublish article | Admin |
| `DELETE` | `/{id}/` | Remove article | Admin |

---

### Analytics (`/api/v1/analytics/`)

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/telecoms/overview/` | Market overview — subscribers by operator/tech | Public (subset) |
| `GET` | `/telecoms/operators/` | List operators | Public |
| `GET` | `/qos/` | QoS metrics — call rates, speeds, latency | Public (subset) |
| `GET` | `/qos/by-operator/` | QoS broken down by operator | Staff |
| `GET` | `/complaints/summary/` | Complaint volume, categories, resolution rates | Staff |
| `GET` | `/licensing/summary/` | Licence stats, renewals due, pipeline | Staff |
| `GET` | `/dashboard/public/` | Aggregated public dashboard data | Public |
| `GET` | `/dashboard/staff/` | Full operational dashboard data | Staff |
| `GET` | `/export/` | Data export as CSV/Excel (`?format=csv`) | Staff |

---

### Site / Core (`/api/v1/core/`)

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/homepage/` | Homepage data — hero, quick links, stats, featured | Public |
| `GET` | `/search/` | Global search (`?q=spectrum`) | Public |
| `GET` | `/settings/` | Public site settings | Public |
| `GET` | `/audit-log/` | System audit log | Admin |

---

## API Documentation (Auto-Generated)

The following endpoints are auto-generated by `drf-spectacular`:

| URL | Purpose |
|---|---|
| `/api/docs/` | Swagger UI — interactive API explorer |
| `/api/schema/` | Raw OpenAPI 3.0 schema (JSON) |
| `/api/schema/?format=yaml` | Raw OpenAPI 3.0 schema (YAML) |

All viewsets, serializers, and parameters are automatically documented. Use `@extend_schema` decorator for additional customisation where needed.

---

*BOCRA Digital Platform API Design — v1.0 — March 2026*
