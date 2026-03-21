# Publications API

> Base URL: `/api/v1/publications/`  
> Swagger tags: **Publications — Public** · **Publications — Staff**

Manages regulatory documents, policy papers, reports, and other publications. Staff create and manage publications through a draft → publish → archive lifecycle. The public can browse published documents and download files.

---

## Table of Contents

- [Endpoints Summary](#endpoints-summary)
- [Lifecycle](#lifecycle)
- [Public — Browse & Download](#public--browse--download)
- [Staff — Create & Manage](#staff--create--manage)
- [Enums & Reference](#enums--reference)

---

## Endpoints Summary

### Public

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/categories/` | List publication categories | Public |
| `GET` | `/` | List published publications | Public |
| `GET` | `/{id}/` | Publication detail | Public |
| `GET` | `/{id}/download/` | Download publication file | Public |

### Staff

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/staff/` | Create new publication (draft) | Staff |
| `GET` | `/staff/list/` | List all publications (inc. drafts) | Staff |
| `GET` | `/staff/{id}/` | Full publication detail (staff) | Staff |
| `PATCH` | `/staff/{id}/edit/` | Update publication fields | Staff |
| `PATCH` | `/staff/{id}/publish/` | Publish a draft | Staff |
| `PATCH` | `/staff/{id}/archive/` | Archive a publication | Staff |
| `DELETE` | `/staff/{id}/delete/` | Soft-delete a publication | Staff |

---

## Lifecycle

Publications follow a simple state model:

```
DRAFT → PUBLISHED → ARCHIVED
  └───────────────→ ARCHIVED
```

| From | Allowed To | Endpoint |
|---|---|---|
| `DRAFT` | `PUBLISHED` | `PATCH /staff/{id}/publish/` |
| `DRAFT` | `ARCHIVED` | `PATCH /staff/{id}/archive/` |
| `PUBLISHED` | `ARCHIVED` | `PATCH /staff/{id}/archive/` |

- **DRAFT**: Default state on creation. Not visible to the public.
- **PUBLISHED**: Visible in public listings and available for download.
- **ARCHIVED**: Removed from public view. Cannot be re-published directly.

---

## Public — Browse & Download

### GET `/categories/`

Returns all available publication categories.

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Publication categories retrieved.",
  "data": [
    { "value": "REGULATION", "label": "Regulation" },
    { "value": "POLICY", "label": "Policy" },
    { "value": "REPORT", "label": "Report" },
    { "value": "GUIDELINE", "label": "Guideline" },
    { "value": "CONSULTATION", "label": "Consultation Paper" },
    { "value": "ANNUAL_REPORT", "label": "Annual Report" },
    { "value": "STRATEGY", "label": "Strategy Document" },
    { "value": "OTHER", "label": "Other" }
  ],
  "errors": null
}
```

---

### GET `/`

Browse published publications. Only `PUBLISHED` status items are returned.

**Query parameters**

| Param | Type | Description |
|---|---|---|
| `category` | string | Filter by category (e.g. `POLICY`) |
| `year` | integer | Filter by publication year |
| `is_featured` | boolean | Filter featured publications |
| `search` | string | Search title and summary |
| `ordering` | string | Sort by `published_date`, `title`, `download_count`, `created_at` (prefix `-` for descending) |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Publications retrieved.",
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Spectrum Management Policy 2026",
      "slug": "spectrum-management-policy-2026",
      "summary": "Framework for radio frequency spectrum allocation...",
      "category": "POLICY",
      "category_display": "Policy",
      "published_date": "2026-03-15",
      "year": 2026,
      "version": "1.0",
      "is_featured": true,
      "download_count": 142
    }
  ],
  "errors": null
}
```

---

### GET `/{id}/`

Full detail of a published publication, including attachments.

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Publication retrieved.",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "Spectrum Management Policy 2026",
    "slug": "spectrum-management-policy-2026",
    "summary": "Framework for radio frequency spectrum allocation...",
    "category": "POLICY",
    "category_display": "Policy",
    "file": "/media/publications/files/2026/spectrum-policy.pdf",
    "published_date": "2026-03-15",
    "year": 2026,
    "version": "1.0",
    "is_featured": true,
    "download_count": 142,
    "attachments": [
      {
        "id": "660e8400-e29b-41d4-a716-446655440001",
        "title": "Appendix A – Frequency Table",
        "file": "/media/publications/attachments/appendix-a.xlsx",
        "uploaded_by_name": "Kago Mosweu",
        "created_at": "2026-03-15T10:30:00Z"
      }
    ],
    "created_at": "2026-03-14T08:00:00Z"
  },
  "errors": null
}
```

**Error `404`** — publication not found or not in `PUBLISHED` status

---

### GET `/{id}/download/`

Stream the primary file as an attachment. Increments the download counter atomically.

**Response `200 OK`** — Binary file stream (`Content-Disposition: attachment`)

**Error `404`** — publication not found, not published, or no file attached

---

## Staff — Create & Manage

> All staff endpoints require a valid JWT token from a user with **Staff** role or above.

### POST `/staff/`

Create a new publication in `DRAFT` status.

**Request body** (`multipart/form-data` or JSON)

```json
{
  "title": "Annual Report 2025",
  "summary": "BOCRA annual regulatory report for the 2025 fiscal year.",
  "category": "ANNUAL_REPORT",
  "file": "<binary>",
  "published_date": "2026-03-20",
  "version": "1.0",
  "is_featured": false
}
```

| Field | Required | Type | Notes |
|---|---|---|---|
| `title` | Yes | string | Max 300 characters |
| `summary` | No | string | Shown in listing views |
| `category` | Yes | string | One of the category enum values |
| `file` | Yes | file | PDF, DOCX, XLSX, etc. |
| `published_date` | No | date | Auto-set on first publish if omitted |
| `version` | No | string | Default: `"1.0"` |
| `is_featured` | No | boolean | Default: `false` |

**Response `201 Created`** — Returns full staff detail serializer

```json
{
  "success": true,
  "message": "Publication created successfully.",
  "data": {
    "id": "...",
    "title": "Annual Report 2025",
    "slug": "annual-report-2025",
    "status": "DRAFT",
    "status_display": "Draft",
    "..."
  },
  "errors": null
}
```

---

### GET `/staff/list/`

List all publications including drafts and archived. Supports filtering and search.

**Query parameters**

| Param | Type | Description |
|---|---|---|
| `category` | string | Filter by category |
| `status` | string | Filter by status (`DRAFT`, `PUBLISHED`, `ARCHIVED`) |
| `year` | integer | Filter by publication year |
| `is_featured` | boolean | Filter featured |
| `search` | string | Search title and summary |
| `ordering` | string | Sort by `published_date`, `title`, `created_at`, `status` |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Publications retrieved.",
  "data": [
    {
      "id": "...",
      "title": "Annual Report 2025",
      "slug": "annual-report-2025",
      "category": "ANNUAL_REPORT",
      "category_display": "Annual Report",
      "status": "DRAFT",
      "status_display": "Draft",
      "published_date": null,
      "year": null,
      "is_featured": false,
      "download_count": 0,
      "created_at": "2026-03-20T14:00:00Z"
    }
  ],
  "errors": null
}
```

**Error `403`** — non-staff user

---

### GET `/staff/{id}/`

Full publication detail with audit metadata.

**Response `200 OK`** — Same as public detail plus `status`, `status_display`, `created_by_name`, `updated_at`

---

### PATCH `/staff/{id}/edit/`

Update publication fields. All fields are optional.

**Request body**

```json
{
  "title": "Annual Report 2025 – Final",
  "is_featured": true
}
```

| Field | Required | Type |
|---|---|---|
| `title` | No | string |
| `summary` | No | string |
| `category` | No | string |
| `file` | No | file |
| `published_date` | No | date |
| `version` | No | string |
| `is_featured` | No | boolean |

**Response `200 OK`** — Returns updated staff detail

---

### PATCH `/staff/{id}/publish/`

Transition a draft publication to `PUBLISHED`.

- Sets `published_date` to today if not already set
- Sets `year` from `published_date`
- Fails if already published or archived

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Publication published successfully.",
  "data": { "...": "full staff detail with status: PUBLISHED" },
  "errors": null
}
```

**Error `400`** — already published, or publication is archived

---

### PATCH `/staff/{id}/archive/`

Archive a publication (removes from public view).

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Publication archived successfully.",
  "data": { "...": "full staff detail with status: ARCHIVED" },
  "errors": null
}
```

**Error `400`** — already archived

---

### DELETE `/staff/{id}/delete/`

Soft-delete a publication. Removes from all listings but retains data in the database.

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Publication deleted successfully.",
  "data": null,
  "errors": null
}
```

---

## Enums & Reference

### Publication Categories

| Value | Label |
|---|---|
| `REGULATION` | Regulation |
| `POLICY` | Policy |
| `REPORT` | Report |
| `GUIDELINE` | Guideline |
| `CONSULTATION` | Consultation Paper |
| `ANNUAL_REPORT` | Annual Report |
| `STRATEGY` | Strategy Document |
| `OTHER` | Other |

### Publication Statuses

| Value | Label | Visible to Public |
|---|---|---|
| `DRAFT` | Draft | No |
| `PUBLISHED` | Published | Yes |
| `ARCHIVED` | Archived | No |
