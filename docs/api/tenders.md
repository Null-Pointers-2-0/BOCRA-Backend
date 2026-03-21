# Tenders API

> Base URL: `/api/v1/tenders/`  
> Swagger tags: **Tenders — Public** · **Tenders — Staff**

Manages procurement tender notices published by BOCRA. Staff create tenders, attach documents, publish addenda, and announce awards. The public can browse open tenders and download documents.

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
| `GET` | `/categories/` | List tender categories | Public |
| `GET` | `/` | List public tenders | Public |
| `GET` | `/{id}/` | Tender detail (inc. documents, addenda, award) | Public |
| `GET` | `/{id}/documents/{doc_id}/download/` | Download a tender document | Public |

### Staff

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/staff/` | Create new tender (draft) | Staff |
| `GET` | `/staff/list/` | List all tenders (inc. drafts) | Staff |
| `GET` | `/staff/{id}/` | Full tender detail (staff) | Staff |
| `PATCH` | `/staff/{id}/edit/` | Update tender fields | Staff |
| `PATCH` | `/staff/{id}/publish/` | Publish a draft (DRAFT → OPEN) | Staff |
| `PATCH` | `/staff/{id}/close/` | Close a tender (OPEN → CLOSED) | Staff |
| `POST` | `/staff/{id}/documents/` | Upload document to tender | Staff |
| `POST` | `/staff/{id}/addenda/` | Add clarification / addendum | Staff |
| `POST` | `/staff/{id}/award/` | Announce tender award | Staff |
| `DELETE` | `/staff/{id}/delete/` | Soft-delete a tender | Staff |

---

## Lifecycle

Tenders follow a defined state machine:

```
DRAFT → OPEN → CLOSING_SOON → CLOSED → AWARDED
  │              │                │
  └→ CANCELLED   └→ CLOSED       └→ CANCELLED
```

| From | Allowed To | Endpoint |
|---|---|---|
| `DRAFT` | `OPEN` | `PATCH /staff/{id}/publish/` |
| `OPEN` | `CLOSED` | `PATCH /staff/{id}/close/` |
| `CLOSING_SOON` | `CLOSED` | `PATCH /staff/{id}/close/` |
| `CLOSED` | `AWARDED` | `POST /staff/{id}/award/` |

### Status Visibility

| Status | Visible to Public |
|---|---|
| `DRAFT` | No |
| `OPEN` | Yes |
| `CLOSING_SOON` | Yes |
| `CLOSED` | Yes |
| `AWARDED` | Yes |
| `CANCELLED` | No |

### Key Rules

- **Publishing** requires a `closing_date` to be set
- **Opening date** is auto-set to "now" if not specified when publishing
- **Addenda** can only be added to `OPEN` or `CLOSING_SOON` tenders
- **Awards** can only be created for `CLOSED` tenders (one award per tender)
- `days_until_closing` is computed live on `OPEN` and `CLOSING_SOON` tenders
- `is_overdue` is `true` when closing date has passed but tender is still open

---

## Public — Browse & Download

### GET `/categories/`

Returns all available tender categories.

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Tender categories retrieved.",
  "data": [
    { "value": "IT_SERVICES", "label": "IT Services" },
    { "value": "CONSULTING", "label": "Consulting" },
    { "value": "CONSTRUCTION", "label": "Construction" },
    { "value": "EQUIPMENT", "label": "Equipment" },
    { "value": "PROFESSIONAL", "label": "Professional Services" },
    { "value": "MAINTENANCE", "label": "Maintenance" },
    { "value": "OTHER", "label": "Other" }
  ],
  "errors": null
}
```

---

### GET `/`

Browse public tenders. Only `OPEN`, `CLOSING_SOON`, `CLOSED`, and `AWARDED` tenders are shown.

**Query parameters**

| Param | Type | Description |
|---|---|---|
| `category` | string | Filter by category (e.g. `IT_SERVICES`) |
| `status` | string | Filter by status (e.g. `OPEN`) |
| `search` | string | Search title, reference number, and description |
| `ordering` | string | Sort by `closing_date`, `opening_date`, `title`, `created_at` (prefix `-` for descending) |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Tenders retrieved.",
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "ICT Infrastructure Upgrade",
      "slug": "ict-infrastructure-upgrade",
      "reference_number": "BOCRA/TENDER/2026/001",
      "category": "IT_SERVICES",
      "category_display": "IT Services",
      "status": "OPEN",
      "status_display": "Open",
      "opening_date": "2026-03-15T08:00:00Z",
      "closing_date": "2026-04-15T17:00:00Z",
      "days_until_closing": 25,
      "budget_range": "BWP 500,000 – 1,000,000"
    }
  ],
  "errors": null
}
```

---

### GET `/{id}/`

Full detail of a public tender, including documents, addenda, and award information.

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Tender retrieved.",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "ICT Infrastructure Upgrade",
    "slug": "ict-infrastructure-upgrade",
    "reference_number": "BOCRA/TENDER/2026/001",
    "description": "BOCRA invites proposals for upgrading its ICT infrastructure...",
    "category": "IT_SERVICES",
    "category_display": "IT Services",
    "status": "OPEN",
    "status_display": "Open",
    "opening_date": "2026-03-15T08:00:00Z",
    "closing_date": "2026-04-15T17:00:00Z",
    "days_until_closing": 25,
    "budget_range": "BWP 500,000 – 1,000,000",
    "contact_name": "Procurement Office",
    "contact_email": "procurement@bocra.org.bw",
    "contact_phone": "+26739100000",
    "documents": [
      {
        "id": "660e8400-e29b-41d4-a716-446655440001",
        "title": "Request for Proposal",
        "file": "/media/tenders/documents/BOCRA-TENDER-2026-001/rfp.pdf",
        "uploaded_by_name": "Kago Mosweu",
        "created_at": "2026-03-15T09:00:00Z"
      }
    ],
    "addenda": [
      {
        "id": "770e8400-e29b-41d4-a716-446655440002",
        "title": "Clarification on technical requirements",
        "content": "Section 4.2 of the RFP has been amended to clarify...",
        "author_name": "Kago Mosweu",
        "created_at": "2026-03-18T11:00:00Z"
      }
    ],
    "award": null,
    "created_at": "2026-03-14T08:00:00Z"
  },
  "errors": null
}
```

**Error `404`** — tender not found or not in a public status

---

### GET `/{id}/documents/{doc_id}/download/`

Stream a tender document file as a download.

**Response `200 OK`** — Binary file stream (`Content-Disposition: attachment`)

**Error `404`** — tender/document not found, tender not public, or no file attached

---

## Staff — Create & Manage

> All staff endpoints require a valid JWT token from a user with **Staff** role or above.

### POST `/staff/`

Create a new tender in `DRAFT` status.

**Request body**

```json
{
  "title": "ICT Infrastructure Upgrade",
  "reference_number": "BOCRA/TENDER/2026/001",
  "description": "BOCRA invites proposals for upgrading its ICT infrastructure...",
  "category": "IT_SERVICES",
  "opening_date": null,
  "closing_date": "2026-04-15T17:00:00Z",
  "budget_range": "BWP 500,000 – 1,000,000",
  "contact_name": "Procurement Office",
  "contact_email": "procurement@bocra.org.bw",
  "contact_phone": "+26739100000"
}
```

| Field | Required | Type | Notes |
|---|---|---|---|
| `title` | Yes | string | Max 300 characters |
| `reference_number` | Yes | string | Must be unique (e.g. `BOCRA/TENDER/2026/001`) |
| `description` | Yes | string | Full tender description / scope of work |
| `category` | Yes | string | One of the category enum values |
| `opening_date` | No | datetime | Auto-set on publish if omitted |
| `closing_date` | No | datetime | Required before publishing |
| `budget_range` | No | string | Indicative range (free text) |
| `contact_name` | No | string | Contact person's name |
| `contact_email` | No | email | Contact email address |
| `contact_phone` | No | string | Contact phone number |

**Response `201 Created`** — Returns full staff detail serializer

```json
{
  "success": true,
  "message": "Tender created successfully.",
  "data": {
    "id": "...",
    "title": "ICT Infrastructure Upgrade",
    "slug": "ict-infrastructure-upgrade",
    "reference_number": "BOCRA/TENDER/2026/001",
    "status": "DRAFT",
    "status_display": "Draft",
    "..."
  },
  "errors": null
}
```

---

### GET `/staff/list/`

List all tenders including drafts and cancelled. Supports filtering and search.

**Query parameters**

| Param | Type | Description |
|---|---|---|
| `category` | string | Filter by category |
| `status` | string | Filter by status |
| `search` | string | Search title, reference number, description |
| `ordering` | string | Sort by `closing_date`, `opening_date`, `title`, `created_at`, `status` |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Tenders retrieved.",
  "data": [
    {
      "id": "...",
      "title": "ICT Infrastructure Upgrade",
      "slug": "ict-infrastructure-upgrade",
      "reference_number": "BOCRA/TENDER/2026/001",
      "category": "IT_SERVICES",
      "category_display": "IT Services",
      "status": "DRAFT",
      "status_display": "Draft",
      "opening_date": null,
      "closing_date": "2026-04-15T17:00:00Z",
      "days_until_closing": null,
      "budget_range": "BWP 500,000 – 1,000,000",
      "created_at": "2026-03-20T14:00:00Z"
    }
  ],
  "errors": null
}
```

**Error `403`** — non-staff user

---

### GET `/staff/{id}/`

Full tender detail with audit metadata, documents, addenda, and award.

**Response `200 OK`** — Same as public detail plus `created_by_name`, `updated_at`, and access to all statuses

---

### PATCH `/staff/{id}/edit/`

Update tender fields. All fields are optional.

**Request body**

```json
{
  "title": "ICT Infrastructure Upgrade – Phase 2",
  "closing_date": "2026-04-30T17:00:00Z"
}
```

| Field | Required | Type |
|---|---|---|
| `title` | No | string |
| `reference_number` | No | string |
| `description` | No | string |
| `category` | No | string |
| `opening_date` | No | datetime |
| `closing_date` | No | datetime |
| `budget_range` | No | string |
| `contact_name` | No | string |
| `contact_email` | No | email |
| `contact_phone` | No | string |

**Response `200 OK`** — Returns updated staff detail

---

### PATCH `/staff/{id}/publish/`

Transition a draft tender to `OPEN`.

- Requires `closing_date` to be set
- Sets `opening_date` to now if not already set
- Only works from `DRAFT` status

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Tender published successfully.",
  "data": { "...": "full staff detail with status: OPEN" },
  "errors": null
}
```

**Error `400`** — not in DRAFT status, or missing closing date

---

### PATCH `/staff/{id}/close/`

Close an open tender. Accepts `OPEN` or `CLOSING_SOON` status.

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Tender closed successfully.",
  "data": { "...": "full staff detail with status: CLOSED" },
  "errors": null
}
```

**Error `400`** — not in OPEN or CLOSING_SOON status

---

### POST `/staff/{id}/documents/`

Upload a document to a tender. Uses `multipart/form-data`.

**Request body**

| Field | Required | Type | Notes |
|---|---|---|---|
| `title` | Yes | string | Document title (e.g. "Request for Proposal") |
| `file` | Yes | file | The document file |

**Response `201 Created`**

```json
{
  "success": true,
  "message": "Document uploaded successfully.",
  "data": {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "title": "Request for Proposal",
    "file": "/media/tenders/documents/BOCRA-TENDER-2026-001/rfp.pdf"
  },
  "errors": null
}
```

---

### POST `/staff/{id}/addenda/`

Publish a clarification or amendment to a tender. Only works for `OPEN` or `CLOSING_SOON` tenders.

**Request body**

```json
{
  "title": "Clarification on technical requirements",
  "content": "Section 4.2 of the RFP has been amended to clarify the minimum server specifications..."
}
```

| Field | Required | Type |
|---|---|---|
| `title` | Yes | string |
| `content` | Yes | string |

**Response `201 Created`**

```json
{
  "success": true,
  "message": "Addendum added successfully.",
  "data": {
    "id": "770e8400-e29b-41d4-a716-446655440002",
    "title": "Clarification on technical requirements",
    "content": "Section 4.2 of the RFP has been amended...",
    "author_name": "Kago Mosweu",
    "created_at": "2026-03-18T11:00:00Z"
  },
  "errors": null
}
```

**Error `400`** — tender is not open

---

### POST `/staff/{id}/award/`

Announce the tender award. Only works for `CLOSED` tenders. One award per tender.

**Request body**

```json
{
  "awardee_name": "TechBW Solutions (Pty) Ltd",
  "award_date": "2026-05-01",
  "award_amount": "BWP 750,000.00",
  "summary": "Selected based on best-value evaluation of technical and financial proposals."
}
```

| Field | Required | Type | Notes |
|---|---|---|---|
| `awardee_name` | Yes | string | Name of the winning bidder |
| `award_date` | Yes | date | Date of award |
| `award_amount` | No | string | Monetary value (free text) |
| `summary` | No | string | Brief justification or description |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Tender awarded successfully.",
  "data": { "...": "full staff detail with status: AWARDED, award object populated" },
  "errors": null
}
```

**Error `400`** — not in CLOSED status, or already awarded

---

### DELETE `/staff/{id}/delete/`

Soft-delete a tender. Removes from all listings but retains data in the database.

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Tender deleted successfully.",
  "data": null,
  "errors": null
}
```

---

## Enums & Reference

### Tender Categories

| Value | Label |
|---|---|
| `IT_SERVICES` | IT Services |
| `CONSULTING` | Consulting |
| `CONSTRUCTION` | Construction |
| `EQUIPMENT` | Equipment |
| `PROFESSIONAL` | Professional Services |
| `MAINTENANCE` | Maintenance |
| `OTHER` | Other |

### Tender Statuses

| Value | Label | Visible to Public |
|---|---|---|
| `DRAFT` | Draft | No |
| `OPEN` | Open | Yes |
| `CLOSING_SOON` | Closing Soon | Yes |
| `CLOSED` | Closed | Yes |
| `AWARDED` | Awarded | Yes |
| `CANCELLED` | Cancelled | No |
