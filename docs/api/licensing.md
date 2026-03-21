# Licensing API

> Base URL: `/api/v1/licensing/`  
> Swagger tags: **Licensing — Public** · **Licensing — Applications** · **Licensing — Licences** · **Licensing — Staff**

Manages the full licence lifecycle: type catalogue, application submission, document upload, status review workflow, issued licences, renewal, and PDF certificate download.

---

## Table of Contents

- [Endpoints Summary](#endpoints-summary)
- [Application Status Values](#application-status-values)
- [Licence Status Values](#licence-status-values)
- [Public — Licence Types & Verification](#public--licence-types--verification)
- [Applications — Applicant](#applications--applicant)
- [Licences — Applicant](#licences--applicant)
- [Staff — Review Queue](#staff--review-queue)

---

## Endpoints Summary

### Public

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/types/` | List all active licence types | Public |
| `GET` | `/types/{id}/` | Licence type detail with full requirements | Public |
| `GET` | `/verify/?licence_no=` | Verify a licence by number or company name | Public |

### Applications (Applicant)

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/applications/` | List my applications | Registered |
| `POST` | `/applications/` | Submit a new application | Registered |
| `GET` | `/applications/{id}/` | Application detail + status timeline | Owner / Staff |
| `PATCH` | `/applications/{id}/cancel/` | Cancel a draft or submitted application | Owner |
| `POST` | `/applications/{id}/documents/` | Upload a supporting document | Owner / Staff |

### Licences (Applicant)

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/licences/` | List my licences | Registered |
| `GET` | `/licences/{id}/` | Licence detail | Owner / Staff |
| `POST` | `/licences/{id}/renew/` | Submit a renewal application | Owner |
| `GET` | `/licences/{id}/certificate/` | Download PDF certificate | Owner / Staff |

### Staff

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `PATCH` | `/applications/{id}/status/` | Update application status (state machine) | Staff |
| `GET` | `/staff/applications/` | All applications across all users | Staff |
| `GET` | `/staff/applications/{id}/` | Application detail with internal staff notes | Staff |

---

## Application Status Values

Applications move through a defined state machine. Not all transitions are valid — see the transition table.

| Value | Display | Description |
|---|---|---|
| `DRAFT` | Draft | Saved but not submitted |
| `SUBMITTED` | Submitted | Submitted; awaiting staff review |
| `UNDER_REVIEW` | Under Review | Assigned to a staff reviewer |
| `INFO_REQUESTED` | Information Requested | Staff requested more info from applicant |
| `APPROVED` | Approved | Application approved; licence being prepared |
| `REJECTED` | Rejected | Application rejected |
| `CANCELLED` | Cancelled | Cancelled by applicant |
| `LICENCE_ISSUED` | Licence Issued | Licence record created and active |

### Valid Transitions

| From | Allowed Next States |
|---|---|
| `DRAFT` | `SUBMITTED`, `CANCELLED` |
| `SUBMITTED` | `UNDER_REVIEW`, `CANCELLED` |
| `UNDER_REVIEW` | `INFO_REQUESTED`, `APPROVED`, `REJECTED` |
| `INFO_REQUESTED` | `UNDER_REVIEW`, `CANCELLED` |
| `APPROVED` | `LICENCE_ISSUED` |

---

## Licence Status Values

| Value | Display |
|---|---|
| `ACTIVE` | Active |
| `EXPIRED` | Expired |
| `SUSPENDED` | Suspended |
| `REVOKED` | Revoked |
| `PENDING_RENEWAL` | Pending Renewal |

---

## Public — Licence Types & Verification

### GET `/types/`

List all active licence types available for application.

**Auth**: None required

**Query parameters**

| Param | Description |
|---|---|
| `search` | Search by name or code |
| `ordering` | Sort by `name`, `fee_amount`, `-fee_amount` |
| `page` / `page_size` | Pagination |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Licence types retrieved.",
  "data": {
    "count": 8,
    "next": null,
    "previous": null,
    "results": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "Type A — Public Mobile Network",
        "code": "TYPE_A",
        "description": "Licence for public mobile network operators.",
        "fee_amount": "50000.00",
        "fee_currency": "BWP",
        "validity_period_months": 12,
        "is_active": true
      }
    ]
  },
  "errors": null
}
```

---

### GET `/types/{id}/`

Full licence type detail including the requirements text for applicants.

**Auth**: None required

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Licence type retrieved.",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Type A — Public Mobile Network",
    "code": "TYPE_A",
    "description": "Licence for public mobile network operators.",
    "requirements": "1. Proof of incorporation...\n2. Technical capability statement...",
    "fee_amount": "50000.00",
    "fee_currency": "BWP",
    "validity_period_months": 12,
    "is_active": true,
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z"
  },
  "errors": null
}
```

**Error `404`** — licence type not found or inactive

---

### GET `/verify/`

Public licence verification. Looks up an issued licence by licence number or company name. Returns safe public fields only (no holder personal data).

**Auth**: None required

**Query parameters** (at least one required)

| Param | Description |
|---|---|
| `licence_no` | Exact licence number (e.g. `LIC-2025-00042`) |
| `company` | Company/organisation name (partial match) |

**Example requests**

```
GET /api/v1/licensing/verify/?licence_no=LIC-2025-00042
GET /api/v1/licensing/verify/?company=Mascom
```

**Response `200 OK`** — licence found

```json
{
  "success": true,
  "message": "1 licence(s) found.",
  "data": [
    {
      "licence_number": "LIC-2025-00042",
      "licence_type_name": "Type A — Public Mobile Network",
      "licence_type_code": "TYPE_A",
      "organisation_name": "Mascom Wireless",
      "issued_date": "2025-03-01",
      "expiry_date": "2026-03-01",
      "status": "ACTIVE",
      "status_display": "Active",
      "is_expired": false
    }
  ],
  "errors": null
}
```

**Response `200 OK`** — no match

```json
{
  "success": true,
  "message": "No licences found matching the provided criteria.",
  "data": [],
  "errors": null
}
```

**Error `400`** — neither `licence_no` nor `company` provided

---

## Applications — Applicant

### GET `/applications/`

List all applications belonging to the authenticated user.

**Auth**: `Authorization: Bearer <access_token>`

**Query parameters**

| Param | Description |
|---|---|
| `status` | Filter by status value (e.g. `SUBMITTED`, `UNDER_REVIEW`) |
| `ordering` | Sort by `created_at`, `submitted_at`, `-created_at` |
| `page` / `page_size` | Pagination |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Applications retrieved.",
  "data": {
    "count": 3,
    "next": null,
    "previous": null,
    "results": [
      {
        "id": "660e8400-e29b-41d4-a716-446655440001",
        "reference_number": "APP-2026-00001",
        "licence_type_name": "Type A — Public Mobile Network",
        "licence_type_code": "TYPE_A",
        "organisation_name": "ACME Corp",
        "status": "SUBMITTED",
        "status_display": "Submitted",
        "submitted_at": "2026-03-10T08:00:00Z",
        "decision_date": null,
        "has_licence": false,
        "created_at": "2026-03-09T14:00:00Z",
        "updated_at": "2026-03-10T08:00:00Z"
      }
    ]
  },
  "errors": null
}
```

---

### POST `/applications/`

Submit a new licence application. Set `"submit": true` to submit immediately; omit or set `false` to save as a draft.

**Auth**: `Authorization: Bearer <access_token>`

**Request body**

```json
{
  "licence_type": "550e8400-e29b-41d4-a716-446655440000",
  "organisation_name": "ACME Corp",
  "organisation_registration": "BW-2020-12345",
  "contact_person": "Jane Doe",
  "contact_email": "jane@acme.bw",
  "contact_phone": "+26771234567",
  "description": "Application for Type A licence to operate a public mobile network.",
  "submit": true
}
```

| Field | Required | Notes |
|---|---|---|
| `licence_type` | Yes | UUID of an active licence type |
| `organisation_name` | Yes | |
| `organisation_registration` | No | Company registration number |
| `contact_person` | Yes | Primary contact name |
| `contact_email` | Yes | |
| `contact_phone` | No | Botswana phone number |
| `description` | No | Free-text description of the application |
| `submit` | No | `true` = submit immediately; `false` (default) = save as draft |

**Response `201 Created`**

```json
{
  "success": true,
  "message": "Application submitted successfully.",
  "data": {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "reference_number": "APP-2026-00001",
    "licence_type": "550e8400-e29b-41d4-a716-446655440000",
    "organisation_name": "ACME Corp",
    "status": "SUBMITTED",
    "submitted_at": "2026-03-10T08:00:00Z"
  },
  "errors": null
}
```

**Error `400`** — validation failure (e.g. inactive licence type)

---

### GET `/applications/{id}/`

Full application detail including embedded licence type info, uploaded documents, and complete status change timeline.

**Auth**: Owner or Staff

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Application retrieved.",
  "data": {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "reference_number": "APP-2026-00001",
    "licence_type": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Type A — Public Mobile Network",
      "code": "TYPE_A",
      "fee_amount": "50000.00",
      "fee_currency": "BWP",
      "validity_period_months": 12,
      "is_active": true
    },
    "organisation_name": "ACME Corp",
    "organisation_registration": "BW-2020-12345",
    "contact_person": "Jane Doe",
    "contact_email": "jane@acme.bw",
    "contact_phone": "+26771234567",
    "description": "Application for Type A licence.",
    "status": "UNDER_REVIEW",
    "status_display": "Under Review",
    "submitted_at": "2026-03-10T08:00:00Z",
    "decision_date": null,
    "decision_reason": null,
    "info_request_message": null,
    "can_cancel": false,
    "has_licence": false,
    "licence_id": null,
    "documents": [
      {
        "id": "770e8400-e29b-41d4-a716-446655440002",
        "name": "Certificate of Incorporation",
        "file": "/media/documents/cert_of_inc.pdf",
        "file_type": "application/pdf",
        "file_size": 512000,
        "uploaded_by_name": "Jane Doe",
        "created_at": "2026-03-09T15:00:00Z"
      }
    ],
    "status_timeline": [
      {
        "id": "880e8400-e29b-41d4-a716-446655440003",
        "from_status": null,
        "from_status_display": null,
        "to_status": "DRAFT",
        "to_status_display": "Draft",
        "changed_by_name": "Jane Doe",
        "reason": "",
        "changed_at": "2026-03-09T14:00:00Z"
      },
      {
        "id": "880e8400-e29b-41d4-a716-446655440004",
        "from_status": "DRAFT",
        "from_status_display": "Draft",
        "to_status": "SUBMITTED",
        "to_status_display": "Submitted",
        "changed_by_name": "Jane Doe",
        "reason": "Application submitted by applicant.",
        "changed_at": "2026-03-10T08:00:00Z"
      }
    ],
    "created_at": "2026-03-09T14:00:00Z",
    "updated_at": "2026-03-12T11:00:00Z"
  },
  "errors": null
}
```

**Error `403`** — not the owner and not staff  
**Error `404`** — application not found

---

### PATCH `/applications/{id}/cancel/`

Cancel a draft or submitted application. Only valid while the application is in `DRAFT` or `SUBMITTED` status.

**Auth**: Owner only

**Request body** (optional)

```json
{ "reason": "No longer required." }
```

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Application cancelled successfully.",
  "data": null,
  "errors": null
}
```

**Error `400`** — application is not in a cancellable status  
**Error `404`** — application not found

---

### POST `/applications/{id}/documents/`

Upload a supporting document to an application. Accepted while status is `DRAFT`, `SUBMITTED`, `UNDER_REVIEW`, or `INFO_REQUESTED`.

**Auth**: Owner or Staff  
**Content-Type**: `multipart/form-data`

**Form fields**

| Field | Required | Notes |
|---|---|---|
| `name` | Yes | Descriptive label, e.g. "Certificate of Incorporation" |
| `file` | Yes | PDF, DOC, DOCX, JPG, or PNG; max 50 MB |

**Response `201 Created`**

```json
{
  "success": true,
  "message": "Document uploaded successfully.",
  "data": {
    "id": "770e8400-e29b-41d4-a716-446655440002",
    "name": "Certificate of Incorporation"
  },
  "errors": null
}
```

**Error `400`** — unsupported file type, file too large, or application in wrong status  
**Error `403`** — not the owner and not staff  
**Error `404`** — application not found

---

## Licences — Applicant

### GET `/licences/`

List all licences held by the authenticated user.

**Auth**: `Authorization: Bearer <access_token>`

**Query parameters**

| Param | Description |
|---|---|
| `status` | Filter by licence status (`ACTIVE`, `EXPIRED`, etc.) |
| `ordering` | Sort by `expiry_date`, `-expiry_date`, `issued_date` |
| `page` / `page_size` | Pagination |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Licences retrieved.",
  "data": {
    "count": 1,
    "next": null,
    "previous": null,
    "results": [
      {
        "id": "990e8400-e29b-41d4-a716-446655440005",
        "licence_number": "LIC-2026-00001",
        "licence_type_name": "Type A — Public Mobile Network",
        "licence_type_code": "TYPE_A",
        "organisation_name": "ACME Corp",
        "issued_date": "2026-03-15",
        "expiry_date": "2027-03-15",
        "status": "ACTIVE",
        "status_display": "Active",
        "is_expired": false,
        "days_until_expiry": 360
      }
    ]
  },
  "errors": null
}
```

---

### GET `/licences/{id}/`

Full licence detail including embedded licence type and source application reference.

**Auth**: Owner or Staff

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Licence retrieved.",
  "data": {
    "id": "990e8400-e29b-41d4-a716-446655440005",
    "licence_number": "LIC-2026-00001",
    "licence_type": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Type A — Public Mobile Network",
      "code": "TYPE_A",
      "fee_amount": "50000.00",
      "fee_currency": "BWP",
      "validity_period_months": 12,
      "is_active": true
    },
    "organisation_name": "ACME Corp",
    "holder": "550e8400-e29b-41d4-a716-446655440099",
    "issued_date": "2026-03-15",
    "expiry_date": "2027-03-15",
    "status": "ACTIVE",
    "status_display": "Active",
    "conditions": "Licence conditions and obligations as per Schedule A.",
    "is_expired": false,
    "days_until_expiry": 360,
    "has_certificate": true,
    "application_reference": "APP-2026-00001",
    "created_at": "2026-03-15T09:00:00Z",
    "updated_at": "2026-03-15T09:00:00Z"
  },
  "errors": null
}
```

**Error `403`** — not the holder and not staff  
**Error `404`** — licence not found

---

### POST `/licences/{id}/renew/`

Submit a renewal application for an active or soon-to-expire licence. Creates a new `Application` record linked to the current licence.

**Auth**: Licence holder

**Request body**: No body required. The renewal application inherits all details from the existing licence.

**Response `201 Created`**

```json
{
  "success": true,
  "message": "Renewal application APP-2026-00002 submitted successfully.",
  "data": {
    "application_id": "aa0e8400-e29b-41d4-a716-446655440006",
    "reference_number": "APP-2026-00002"
  },
  "errors": null
}
```

**Error `400`** — licence is not in a renewable status  
**Error `403`** — not the licence holder  
**Error `404`** — licence not found

---

### GET `/licences/{id}/certificate/`

Download the PDF licence certificate. If a stored certificate exists, it is served directly. If not, one is generated on-the-fly and cached for subsequent requests.

**Auth**: Owner or Staff

**Response `200 OK`**

```
Content-Type: application/pdf
Content-Disposition: attachment; filename="BOCRA_Licence_LIC-2026-00001.pdf"

<binary PDF data>
```

**Error `400`** — licence is not `ACTIVE`  
**Error `404`** — licence not found  
**Error `500`** — certificate generation failed

---

## Staff — Review Queue

> All endpoints in this section require `Staff`, `Admin`, or `SuperAdmin` role.

### PATCH `/applications/{id}/status/`

Drive the application state machine. Validates that the requested transition is legal before applying it. Automatically creates a status log entry.

**Auth**: Staff

**Request body**

```json
{
  "status": "UNDER_REVIEW",
  "reason": "",
  "info_request_message": "",
  "internal_notes": "Assigned to John Banda for review."
}
```

| Field | Required | Notes |
|---|---|---|
| `status` | Yes | Target status value — must be a valid next state |
| `reason` | Conditional | Required when `status` is `REJECTED` |
| `info_request_message` | Conditional | Required when `status` is `INFO_REQUESTED` |
| `internal_notes` | No | Not visible to the applicant |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Application status updated to 'Under Review'.",
  "data": {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "reference_number": "APP-2026-00001",
    "status": "UNDER_REVIEW",
    "status_display": "Under Review"
  },
  "errors": null
}
```

**Error `400`** — invalid transition, missing required `reason` or `info_request_message`  
**Error `403`** — caller is not staff  
**Error `404`** — application not found

---

### GET `/staff/applications/`

List all applications across all users. Includes applicant name and email fields not visible in the applicant-facing list.

**Auth**: Staff

**Query parameters**

| Param | Description |
|---|---|
| `status` | Filter by status |
| `licence_type` | Filter by licence type UUID |
| `search` | Search by reference number, organisation name, or applicant email |
| `ordering` | Sort by `submitted_at`, `-submitted_at`, `created_at` |
| `page` / `page_size` | Pagination |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Applications retrieved.",
  "data": {
    "count": 15,
    "next": null,
    "previous": null,
    "results": [
      {
        "id": "660e8400-e29b-41d4-a716-446655440001",
        "reference_number": "APP-2026-00001",
        "licence_type_name": "Type A — Public Mobile Network",
        "licence_type_code": "TYPE_A",
        "organisation_name": "ACME Corp",
        "status": "SUBMITTED",
        "status_display": "Submitted",
        "submitted_at": "2026-03-10T08:00:00Z",
        "decision_date": null,
        "has_licence": false,
        "applicant_name": "Jane Doe",
        "applicant_email": "jane@acme.bw",
        "created_at": "2026-03-09T14:00:00Z",
        "updated_at": "2026-03-10T08:00:00Z"
      }
    ]
  },
  "errors": null
}
```

---

### GET `/staff/applications/{id}/`

Full application detail with additional staff-only fields: internal notes and reviewed-by name.

**Auth**: Staff

**Response `200 OK`** — same shape as `GET /applications/{id}/` plus:

```json
{
  "notes": "Reviewed by John Banda. Outstanding document — certificate of incorporation.",
  "reviewed_by_name": "John Banda"
}
```

**Error `404`** — application not found

---

*BOCRA Digital Platform — Licensing API — v1.0*
