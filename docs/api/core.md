# Core API

> Base URL: `/api/v1/`  
> Swagger tag: **Core**

Service discovery and health monitoring. All endpoints are public — no authentication required.

---

## Endpoints

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/api/v1/` | API root — module index and documentation links | Public |
| `GET` | `/api/v1/health/` | Health check — returns 200 if service is running | Public |

---

## GET `/api/v1/`

Returns the full API index: all module base URLs, documentation links, and platform metadata. Useful for service discovery and client bootstrapping.

**Response `200 OK`**

```json
{
  "success": true,
  "message": "BOCRA Digital Platform API",
  "data": {
    "version": "v1",
    "documentation": {
      "swagger": "http://localhost:8000/api/swagger/",
      "redoc":   "http://localhost:8000/api/redoc/",
      "schema":  "http://localhost:8000/api/schema/"
    },
    "modules": {
      "accounts":      "http://localhost:8000/api/v1/accounts/",
      "licensing":     "http://localhost:8000/api/v1/licensing/",
      "complaints":    "http://localhost:8000/api/v1/complaints/",
      "publications":  "http://localhost:8000/api/v1/publications/",
      "tenders":       "http://localhost:8000/api/v1/tenders/",
      "news":          "http://localhost:8000/api/v1/news/",
      "analytics":     "http://localhost:8000/api/v1/analytics/",
      "notifications": "http://localhost:8000/api/v1/notifications/"
    },
    "platform":   "BOCRA Digital Platform",
    "authority":  "Botswana Communications Regulatory Authority"
  },
  "errors": null
}
```

---

## GET `/api/v1/health/`

Minimal liveness probe. Returns `200` if the process is running. Used by load balancers, Docker health checks, and uptime monitors.

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Service is running.",
  "data": { "status": "ok" },
  "errors": null
}
```

---

## API Documentation URLs

| URL | Description |
|---|---|
| `/api/swagger/` | Swagger UI — interactive browser for testing all endpoints |
| `/api/redoc/` | ReDoc — clean, read-only API reference |
| `/api/schema/` | Raw OpenAPI 3.0 schema (JSON) |
| `/api/schema/?format=yaml` | Raw OpenAPI 3.0 schema (YAML) |

---

*BOCRA Digital Platform — Core API — v1.0*
