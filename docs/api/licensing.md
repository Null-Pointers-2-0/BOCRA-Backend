# Licensing API

> Base URL: `/api/v1/licensing/`  
> Swagger tags: **Licensing — Public** · **Licensing — Applications** · **Licensing — Licences** · **Licensing — Staff**

Manages the full licence lifecycle: sector catalogue, type catalogue, application submission, document upload, status review workflow, issued licences, renewal, and PDF certificate download.

---

## Table of Contents

- [Endpoints Summary](#endpoints-summary)
- [Application Status Values](#application-status-values)
- [Licence Status Values](#licence-status-values)
- [Public — Sectors](#public--sectors)
- [Public — Licence Types & Verification](#public--licence-types--verification)
- [Applications — Applicant](#applications--applicant)
- [Licences — Applicant](#licences--applicant)
- [Staff — Review Queue](#staff--review-queue)
- [Staff — Licences](#staff--licences)
- [Staff — Sectors CRUD](#staff--sectors-crud)
- [Staff — Licence Types CRUD](#staff--licence-types-crud)

---

## Endpoints Summary

### Public

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/sectors/` | List all active licence sectors | Public |
| `GET` | `/sectors/{id}/` | Sector detail with nested licence types | Public |
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

### Staff — Applications

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `PATCH` | `/applications/{id}/status/` | Update application status (state machine) | Staff |
| `GET` | `/staff/applications/` | All applications across all users | Staff |
| `GET` | `/staff/applications/{id}/` | Application detail with internal staff notes | Staff |

### Staff — Licences

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/staff/licences/` | All issued licences across all holders | Staff |

### Staff — Sectors CRUD

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/staff/sectors/` | List all sectors (including inactive) | Staff |
| `POST` | `/staff/sectors/create/` | Create a new sector | Staff |
| `PATCH` | `/staff/sectors/{id}/` | Update a sector | Staff |
| `DELETE` | `/staff/sectors/{id}/delete/` | Soft-delete a sector | Staff |

### Staff — Licence Types CRUD

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/staff/types/` | List all licence types (including inactive) | Staff |
| `POST` | `/staff/types/create/` | Create a new licence type | Staff |
| `GET` | `/staff/types/{id}/` | Licence type detail (staff) | Staff |
| `PATCH` | `/staff/types/{id}/update/` | Update a licence type | Staff |
| `DELETE` | `/staff/types/{id}/delete/` | Soft-delete a licence type | Staff |

---

## Application Status Values

Applications move through a defined state machine. Not all transitions are valid — see the transition table.

| Value | Display | Description |
|---|---|---|
| `DRAFT` | Draft | Saved but not submitted |
| `SUBMITTED` | Submitted | Submitted; awaiting staff review |
| `UNDER_REVIEW` | Under Review | Assigned to a staff reviewer |
| `INFO_REQUESTED` | Information Requested | Staff requested more info from applicant |
| `APPROVED` | Approved | Application approved; licence auto-issued |
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

> **Note:** When an application is approved via `PATCH /applications/{id}/status/`, a `Licence` record is **automatically created** with an `ACTIVE` status and a PDF certificate is generated. The applicant's role is upgraded to `LICENSEE`.

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

## Public — Sectors

### GET `/sectors/`

List all active regulatory sectors.

**Auth**: None required

**Query parameters**

| Param | Description |
|---|---|
| `search` | Search by name, code, or description |
| `ordering` | Sort by `name`, `sort_order` |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Licence sectors retrieved successfully.",
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Telecommunications",
      "code": "TELECOM",
      "description": "Telecommunications licences for network operators and service providers.",
      "icon": "radio-tower",
      "sort_order": 1,
      "is_active": true,
      "type_count": 4
    }
  ],
  "errors": null
}
```

---

### GET `/sectors/{id}/`

Full detail for a single sector including its licence types.

**Auth**: None required

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Licence sector retrieved successfully.",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Telecommunications",
    "code": "TELECOM",
    "description": "Telecommunications licences for network operators and service providers.",
    "icon": "radio-tower",
    "sort_order": 1,
    "is_active": true,
    "licence_types": [
      {
        "id": "660e8400-e29b-41d4-a716-446655440001",
        "name": "Type A — Public Mobile Network",
        "code": "TYPE_A",
        "sector": "550e8400-e29b-41d4-a716-446655440000",
        "sector_name": "Telecommunications",
        "sector_code": "TELECOM",
        "description": "Licence for public mobile network operators.",
        "fee_amount": "50000.00",
        "annual_fee": "25000.00",
        "renewal_fee": "30000.00",
        "fee_currency": "BWP",
        "validity_period_months": 12,
        "is_domain_applicable": false,
        "sort_order": 1,
        "is_active": true
      }
    ],
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z"
  },
  "errors": null
}
```

**Error `404`** — sector not found

---

## Public — Licence Types & Verification

### GET `/types/`

List all active licence types available for application.

**Auth**: None required

**Query parameters**

| Param | Description |
|---|---|
| `search` | Search by name, code, or description |
| `ordering` | Sort by `name`, `code`, `fee_amount` |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Licence types retrieved successfully.",
  "data": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "name": "Type A — Public Mobile Network",
      "code": "TYPE_A",
      "sector": "550e8400-e29b-41d4-a716-446655440000",
      "sector_name": "Telecommunications",
      "sector_code": "TELECOM",
      "description": "Licence for public mobile network operators.",
      "fee_amount": "50000.00",
      "annual_fee": "25000.00",
      "renewal_fee": "30000.00",
      "fee_currency": "BWP",
      "validity_period_months": 12,
      "is_domain_applicable": false,
      "sort_order": 1,
      "is_active": true
    }
  ],
  "errors": null
}
```

---

### GET `/types/{id}/`

Full licence type detail including requirements, eligibility criteria, and required documents.

**Auth**: None required

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Licence type retrieved successfully.",
  "data": {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "name": "Type A — Public Mobile Network",
    "code": "TYPE_A",
    "sector": "550e8400-e29b-41d4-a716-446655440000",
    "sector_name": "Telecommunications",
    "sector_code": "TELECOM",
    "description": "Licence for public mobile network operators.",
    "requirements": "1. Proof of incorporation...\n2. Technical capability statement...",
    "eligibility_criteria": "Must be a registered Botswana company.",
    "required_documents": "Certificate of Incorporation, Tax Clearance, Technical Plan",
    "fee_amount": "50000.00",
    "annual_fee": "25000.00",
    "renewal_fee": "30000.00",
    "fee_currency": "BWP",
    "validity_period_months": 12,
    "is_domain_applicable": false,
    "sort_order": 1,
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
| `licence_no` | Exact licence number (e.g. `LIC-ISP-2026-000001`) |
| `company` | Company/organisation name (partial match) |

**Example requests**

```
GET /api/v1/licensing/verify/?licence_no=LIC-ISP-2026-000001
GET /api/v1/licensing/verify/?company=Mascom
```

**Response `200 OK`** — licence found

```json
{
  "success": true,
  "message": "1 licence(s) found.",
  "data": [
    {
      "licence_number": "LIC-ISP-2026-000001",
      "licence_type_name": "Internet Service Provider",
      "licence_type_code": "ISP",
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

**Error `400`** — neither `licence_no` nor `company` provided  
**Error `404`** — no licence found matching the provided details

---

## Applications — Applicant

### GET `/applications/`

List all applications belonging to the authenticated user.

**Auth**: `Authorization: Bearer <access_token>`

**Query parameters**

| Param | Description |
|---|---|
| `status` | Filter by status value (e.g. `SUBMITTED`, `UNDER_REVIEW`) |
| `licence_type` | Filter by licence type UUID |
| `ordering` | Sort by `created_at`, `submitted_at`, `status` |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Applications retrieved successfully.",
  "data": [
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
  ],
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
  "message": "Application retrieved successfully.",
  "data": {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "reference_number": "APP-2026-00001",
    "licence_type": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Type A — Public Mobile Network",
      "code": "TYPE_A",
      "sector": "...",
      "sector_name": "Telecommunications",
      "sector_code": "TELECOM",
      "description": "Licence for public mobile network operators.",
      "fee_amount": "50000.00",
      "annual_fee": "25000.00",
      "renewal_fee": "30000.00",
      "fee_currency": "BWP",
      "validity_period_months": 12,
      "is_domain_applicable": false,
      "sort_order": 1,
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
| `licence_type` | Filter by licence type UUID |
| `ordering` | Sort by `issued_date`, `expiry_date`, `status` |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Licences retrieved successfully.",
  "data": [
    {
      "id": "990e8400-e29b-41d4-a716-446655440005",
      "licence_number": "LIC-ISP-2026-000001",
      "licence_type_name": "Internet Service Provider",
      "licence_type_code": "ISP",
      "organisation_name": "ACME Corp",
      "issued_date": "2026-03-15",
      "expiry_date": "2027-03-15",
      "status": "ACTIVE",
      "status_display": "Active",
      "is_expired": false,
      "days_until_expiry": 360
    }
  ],
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
  "message": "Licence retrieved successfully.",
  "data": {
    "id": "990e8400-e29b-41d4-a716-446655440005",
    "licence_number": "LIC-ISP-2026-000001",
    "licence_type": {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "name": "Internet Service Provider",
      "code": "ISP",
      "sector": "...",
      "sector_name": "Telecommunications",
      "sector_code": "TELECOM",
      "description": "...",
      "fee_amount": "15000.00",
      "annual_fee": "10000.00",
      "renewal_fee": "12000.00",
      "fee_currency": "BWP",
      "validity_period_months": 12,
      "is_domain_applicable": true,
      "sort_order": 2,
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

**Error `400`** — licence is revoked or renewal already in progress  
**Error `404`** — licence not found

---

### GET `/licences/{id}/certificate/`

Download the PDF licence certificate. If a stored certificate exists, it is served directly. If not, one is generated on-the-fly and cached for subsequent requests.

**Auth**: Owner or Staff

**Response `200 OK`**

```
Content-Type: application/pdf
Content-Disposition: attachment; filename="BOCRA_Licence_LIC-ISP-2026-000001.pdf"

<binary PDF data>
```

**Error `400`** — licence is not `ACTIVE`  
**Error `404`** — licence not found  
**Error `500`** — certificate generation failed

---

## Staff — Review Queue

> All endpoints in this section require `Staff`, `Admin`, or `SuperAdmin` role.

### PATCH `/applications/{id}/status/`

Drive the application state machine. Validates that the requested transition is legal before applying it. Automatically creates a status log entry. **On `APPROVED`, automatically creates a `Licence` record, generates a PDF certificate, and upgrades the applicant's role to `LICENSEE`.**

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

**Response `200 OK`** — standard status change

```json
{
  "success": true,
  "message": "Application status updated to 'Under Review'.",
  "data": {
    "status": "UNDER_REVIEW",
    "licence_number": null
  },
  "errors": null
}
```

**Response `200 OK`** — approval (licence auto-created)

```json
{
  "success": true,
  "message": "Application status updated to 'Approved'. Licence LIC-ISP-2026-000001 issued.",
  "data": {
    "status": "APPROVED",
    "licence_number": "LIC-ISP-2026-000001"
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
| `ordering` | Sort by `submitted_at`, `created_at`, `status`, `organisation_name` |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Applications retrieved successfully.",
  "data": [
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
  ],
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

## Staff — Licences

### GET `/staff/licences/`

List all issued licences across all licence holders. Supports search by licence number, organisation name, or holder email/name.

**Auth**: Staff

**Query parameters**

| Param | Description |
|---|---|
| `status` | Filter by licence status (`ACTIVE`, `EXPIRED`, etc.) |
| `licence_type` | Filter by licence type UUID |
| `search` | Search by licence number, organisation name, holder email, first name, or last name |
| `ordering` | Sort by `issued_date`, `expiry_date`, `status`, `licence_number` |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Licences retrieved successfully.",
  "data": [
    {
      "id": "990e8400-e29b-41d4-a716-446655440005",
      "licence_number": "LIC-ISP-2026-000001",
      "licence_type_name": "Internet Service Provider",
      "licence_type_code": "ISP",
      "organisation_name": "ACME Corp",
      "issued_date": "2026-03-15",
      "expiry_date": "2027-03-15",
      "status": "ACTIVE",
      "status_display": "Active",
      "is_expired": false,
      "days_until_expiry": 360
    }
  ],
  "errors": null
}
```

---

## Staff — Sectors CRUD

> All endpoints in this section require `Staff`, `Admin`, or `SuperAdmin` role.

### GET `/staff/sectors/`

List all sectors including inactive ones (unlike the public endpoint which only returns active sectors).

**Auth**: Staff

**Query parameters**

| Param | Description |
|---|---|
| `search` | Search by name or code |
| `ordering` | Sort by `sort_order`, `name` |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Sectors retrieved successfully.",
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Telecommunications",
      "code": "TELECOM",
      "description": "Telecommunications licences for network operators and service providers.",
      "icon": "radio-tower",
      "sort_order": 1,
      "is_active": true,
      "type_count": 4
    }
  ],
  "errors": null
}
```

---

### POST `/staff/sectors/create/`

Create a new regulatory sector.

**Auth**: Staff

**Request body**

```json
{
  "name": "Postal Services",
  "code": "POSTAL",
  "description": "Licences for postal and courier service operators.",
  "icon": "mail",
  "sort_order": 5,
  "is_active": true
}
```

| Field | Required | Notes |
|---|---|---|
| `name` | Yes | Sector name |
| `code` | Yes | Unique uppercase code |
| `description` | No | Human-readable description |
| `icon` | No | Icon identifier |
| `sort_order` | No | Display ordering (default: 0) |
| `is_active` | No | Default: `true` |

**Response `201 Created`**

```json
{
  "success": true,
  "message": "Sector created successfully.",
  "data": {
    "id": "...",
    "name": "Postal Services",
    "code": "POSTAL",
    "description": "Licences for postal and courier service operators.",
    "icon": "mail",
    "sort_order": 5,
    "is_active": true,
    "type_count": 0
  },
  "errors": null
}
```

**Error `400`** — validation failure (e.g. duplicate code)

---

### PATCH `/staff/sectors/{id}/`

Update an existing sector. Supports partial updates.

**Auth**: Staff

**Request body** (partial)

```json
{
  "description": "Updated description.",
  "is_active": false
}
```

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Sector updated successfully.",
  "data": { "..." },
  "errors": null
}
```

**Error `400`** — validation failure  
**Error `404`** — sector not found

---

### DELETE `/staff/sectors/{id}/delete/`

Soft-delete a sector. Will fail if the sector still has active licence types.

**Auth**: Staff

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Sector deleted successfully.",
  "data": null,
  "errors": null
}
```

**Error `400`** — sector has active licence types  
**Error `404`** — sector not found

---

## Staff — Licence Types CRUD

> All endpoints in this section require `Staff`, `Admin`, or `SuperAdmin` role.

### GET `/staff/types/`

List all licence types including inactive ones. Supports filtering by sector, active status, and domain applicability.

**Auth**: Staff

**Query parameters**

| Param | Description |
|---|---|
| `is_active` | Filter by active status (`true` / `false`) |
| `sector` | Filter by sector UUID |
| `is_domain_applicable` | Filter by domain applicability |
| `search` | Search by name, code, or description |
| `ordering` | Sort by `name`, `code`, `sort_order`, `fee_amount` |

**Response `200 OK`** — same shape as `GET /types/`

---

### POST `/staff/types/create/`

Create a new licence type.

**Auth**: Staff

**Request body**

```json
{
  "name": "Internet Service Provider",
  "code": "ISP",
  "sector": "550e8400-e29b-41d4-a716-446655440000",
  "description": "Licence for Internet service providers.",
  "requirements": "1. Network infrastructure plan...",
  "eligibility_criteria": "Must be a registered Botswana company.",
  "required_documents": "Certificate of Incorporation, BOCRA Application Form",
  "fee_amount": "15000.00",
  "annual_fee": "10000.00",
  "renewal_fee": "12000.00",
  "fee_currency": "BWP",
  "validity_period_months": 12,
  "is_domain_applicable": true,
  "sort_order": 2,
  "is_active": true
}
```

| Field | Required | Notes |
|---|---|---|
| `name` | Yes | |
| `code` | Yes | Unique uppercase code |
| `sector` | Yes | UUID of an existing sector |
| `description` | No | |
| `requirements` | No | Requirements text for applicants |
| `eligibility_criteria` | No | |
| `required_documents` | No | Comma-separated document list |
| `fee_amount` | No | Application fee (default: 0) |
| `annual_fee` | No | Annual licence fee (default: 0) |
| `renewal_fee` | No | Renewal fee (default: 0) |
| `fee_currency` | No | Default: `BWP` |
| `validity_period_months` | No | Default: 12 |
| `is_domain_applicable` | No | Whether this type requires .bw domain (default: `false`) |
| `sort_order` | No | Display ordering (default: 0) |
| `is_active` | No | Default: `true` |

**Response `201 Created`**

```json
{
  "success": true,
  "message": "Licence type created successfully.",
  "data": { "..." },
  "errors": null
}
```

**Error `400`** — validation failure (e.g. duplicate code, deleted sector)

---

### GET `/staff/types/{id}/`

Full licence type detail for staff view.

**Auth**: Staff

**Response `200 OK`** — same shape as `GET /types/{id}/`

---

### PATCH `/staff/types/{id}/update/`

Update an existing licence type. Supports partial updates.

**Auth**: Staff

**Request body** (partial)

```json
{
  "fee_amount": "20000.00",
  "is_active": false
}
```

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Licence type updated successfully.",
  "data": { "..." },
  "errors": null
}
```

**Error `400`** — validation failure  
**Error `404`** — licence type not found

---

### DELETE `/staff/types/{id}/delete/`

Soft-delete a licence type. Will fail if the type has active (non-terminal) applications.

**Auth**: Staff

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Licence type deleted successfully.",
  "data": null,
  "errors": null
}
```

**Error `400`** — type has active applications  
**Error `404`** — licence type not found

---

*BOCRA Digital Platform — Licensing API — v1.0*
