# Complaints API

> Base URL: `/api/v1/complaints/`  
> Swagger tags: **Complaints — Public** · **Complaints — Complainant** · **Complaints — Staff**

Handles regulatory complaint submission (anonymous or authenticated), public tracking by reference number, case management, evidence upload, staff assignment, resolution workflow, and internal case notes.

---

## Table of Contents

- [Endpoints Summary](#endpoints-summary)
- [State Machine](#state-machine)
- [Public — Submit & Track](#public--submit--track)
- [Complainant — My Complaints](#complainant--my-complaints)
- [Staff — Case Management](#staff--case-management)
- [Enums & Reference](#enums--reference)

---

## Endpoints Summary

### Public

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/submit/` | Submit a new complaint | Public |
| `GET` | `/track/?ref=` | Track complaint by reference number | Public |
| `GET` | `/categories/` | List complaint categories | Public |

### Complainant (authenticated)

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/` | List my complaints | Registered |
| `GET` | `/{id}/` | Complaint detail with timeline | Owner / Staff |
| `POST` | `/{id}/documents/` | Upload evidence | Owner / Staff |

### Staff

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `PATCH` | `/{id}/assign/` | Assign case handler | Staff |
| `PATCH` | `/{id}/status/` | Update case status | Staff |
| `POST` | `/{id}/notes/` | Add internal case note | Staff |
| `POST` | `/{id}/resolve/` | Submit formal resolution | Staff |
| `GET` | `/staff/` | List all complaints (staff queue) | Staff |
| `GET` | `/staff/{id}/` | Full complaint detail with internal notes | Staff |

---

## State Machine

Complaints follow a defined state machine. Only valid transitions are allowed.

```
SUBMITTED → ASSIGNED → INVESTIGATING ↔ AWAITING_RESPONSE
                                      ↓
                                   RESOLVED → CLOSED
                                      ↑
                                   REOPENED ──→ INVESTIGATING
```

| From | Allowed To |
|---|---|
| `SUBMITTED` | `ASSIGNED` |
| `ASSIGNED` | `INVESTIGATING` |
| `INVESTIGATING` | `AWAITING_RESPONSE`, `RESOLVED` |
| `AWAITING_RESPONSE` | `INVESTIGATING`, `RESOLVED` |
| `RESOLVED` | `CLOSED`, `REOPENED` |
| `CLOSED` | `REOPENED` |
| `REOPENED` | `INVESTIGATING` |

### SLA Auto-Calculation

When a complaint is submitted, the SLA deadline is auto-calculated based on priority:

| Priority | SLA Deadline |
|---|---|
| `LOW` | 30 days |
| `MEDIUM` | 14 days |
| `HIGH` | 7 days |
| `URGENT` | 3 days |

---

## Public — Submit & Track

### POST `/submit/`

Submit a new regulatory complaint. Both anonymous and authenticated users can submit. Authenticated users have their name/email auto-populated from their account.

**Request body**

```json
{
  "complainant_name": "Mpho Kgosi",
  "complainant_email": "mpho@example.com",
  "complainant_phone": "+26771234567",
  "against_operator_name": "Mascom Wireless",
  "category": "SERVICE_QUALITY",
  "subject": "Frequent call drops in Gaborone CBD",
  "description": "I have been experiencing frequent call drops in the Gaborone CBD area for the past two weeks. The issue occurs multiple times daily and affects my ability to conduct business.",
  "priority": "MEDIUM"
}
```

| Field | Required | Notes |
|---|---|---|
| `complainant_name` | Yes* | Auto-filled if logged in |
| `complainant_email` | Yes* | Auto-filled if logged in |
| `complainant_phone` | No | Botswana format accepted |
| `against_operator_name` | Yes | Free-text operator name |
| `against_licensee` | No | UUID of a licence (optional link) |
| `category` | Yes | One of the complaint categories (see enum) |
| `subject` | Yes | Brief subject (max 300 chars) |
| `description` | Yes | Full complaint description |
| `priority` | No | Default: `MEDIUM` |

*Auto-populated from the user's account if authenticated.

**Response `201 Created`**

```json
{
  "success": true,
  "message": "Complaint submitted successfully. Your reference number is CMP-2026-000001.",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "reference_number": "CMP-2026-000001",
    "status": "SUBMITTED",
    "sla_deadline": "2026-04-04T12:00:00Z"
  },
  "errors": null
}
```

**Error `400 Bad Request`** — validation failure

---

### GET `/track/?ref=CMP-2026-000001`

Track a complaint status by reference number. No login required.

**Query parameters**

| Param | Required | Description |
|---|---|---|
| `ref` | Yes | Complaint reference number (e.g. `CMP-2026-000001`) |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Complaint found.",
  "data": {
    "reference_number": "CMP-2026-000001",
    "subject": "Frequent call drops in Gaborone CBD",
    "category": "SERVICE_QUALITY",
    "category_display": "Service Quality",
    "against_operator_name": "Mascom Wireless",
    "status": "INVESTIGATING",
    "status_display": "Under Investigation",
    "priority": "MEDIUM",
    "priority_display": "Medium",
    "is_overdue": false,
    "sla_deadline": "2026-04-04T12:00:00Z",
    "created_at": "2026-03-21T12:00:00Z",
    "resolved_at": null
  },
  "errors": null
}
```

**Error `400`** — no reference number provided  
**Error `404`** — complaint not found

---

### GET `/categories/`

List all available complaint categories.

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Complaint categories retrieved.",
  "data": [
    { "value": "SERVICE_QUALITY", "label": "Service Quality" },
    { "value": "BILLING", "label": "Billing Dispute" },
    { "value": "COVERAGE", "label": "Network Coverage" },
    { "value": "CONDUCT", "label": "Operator Conduct" },
    { "value": "INTERNET", "label": "Internet Services" },
    { "value": "BROADCASTING", "label": "Broadcasting" },
    { "value": "POSTAL", "label": "Postal Services" },
    { "value": "OTHER", "label": "Other" }
  ],
  "errors": null
}
```

---

## Complainant — My Complaints

### GET `/`

List complaints submitted by the authenticated user.

**Auth**: `Authorization: Bearer <access_token>`

**Query parameters** (optional filters)

| Param | Description |
|---|---|
| `status` | Filter by status (e.g. `SUBMITTED`, `INVESTIGATING`) |
| `category` | Filter by category |
| `priority` | Filter by priority |
| `ordering` | Sort by `created_at`, `status`, `priority`, `sla_deadline` |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Complaints retrieved successfully.",
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "reference_number": "CMP-2026-000001",
      "subject": "Frequent call drops in Gaborone CBD",
      "category": "SERVICE_QUALITY",
      "category_display": "Service Quality",
      "against_operator_name": "Mascom Wireless",
      "status": "INVESTIGATING",
      "status_display": "Under Investigation",
      "priority": "MEDIUM",
      "priority_display": "Medium",
      "is_overdue": false,
      "sla_deadline": "2026-04-04T12:00:00Z",
      "created_at": "2026-03-21T12:00:00Z",
      "resolved_at": null
    }
  ],
  "errors": null
}
```

---

### GET `/{id}/`

Full complaint detail including documents, status timeline, and non-internal case notes.

**Auth**: `Authorization: Bearer <access_token>` (complaint owner or staff)

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Complaint retrieved successfully.",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "reference_number": "CMP-2026-000001",
    "complainant_name": "Mpho Kgosi",
    "complainant_email": "mpho@example.com",
    "complainant_phone": "+26771234567",
    "against_operator_name": "Mascom Wireless",
    "against_licensee": null,
    "category": "SERVICE_QUALITY",
    "category_display": "Service Quality",
    "subject": "Frequent call drops in Gaborone CBD",
    "description": "...",
    "status": "INVESTIGATING",
    "status_display": "Under Investigation",
    "priority": "MEDIUM",
    "priority_display": "Medium",
    "assigned_to_name": "Jane Staff",
    "resolution": "",
    "resolved_at": null,
    "is_overdue": false,
    "days_until_sla": 12,
    "sla_deadline": "2026-04-04T12:00:00Z",
    "documents": [
      {
        "id": "...",
        "name": "Screenshot of error",
        "file": "/media/complaints/documents/2026/03/screenshot.png",
        "file_type": "image/png",
        "file_size": 245000,
        "uploaded_by_name": "Mpho Kgosi",
        "created_at": "2026-03-21T12:05:00Z"
      }
    ],
    "status_timeline": [
      {
        "id": "...",
        "from_status": "SUBMITTED",
        "from_status_display": "Submitted",
        "to_status": "ASSIGNED",
        "to_status_display": "Assigned",
        "changed_by_name": "Jane Staff",
        "reason": "Assigned to Jane Staff.",
        "changed_at": "2026-03-22T09:00:00Z"
      }
    ],
    "case_notes": [],
    "created_at": "2026-03-21T12:00:00Z",
    "updated_at": "2026-03-22T09:00:00Z"
  },
  "errors": null
}
```

> **Note**: Staff users see all case notes (including internal ones). Complainants only see non-internal notes.

---

### POST `/{id}/documents/`

Upload evidence to a complaint. Cannot upload to closed complaints.

**Auth**: `Authorization: Bearer <access_token>` (complaint owner or staff)  
**Content-Type**: `multipart/form-data`

| Field | Required | Notes |
|---|---|---|
| `name` | Yes | Descriptive label for the evidence |
| `file` | Yes | PDF, DOC, DOCX, JPG, or PNG — max 50 MB |

**Response `201 Created`**

```json
{
  "success": true,
  "message": "Evidence uploaded successfully.",
  "data": {
    "id": "...",
    "name": "Call log screenshot"
  },
  "errors": null
}
```

---

## Staff — Case Management

### PATCH `/{id}/assign/`

Assign a BOCRA staff member as the case handler. Auto-transitions status from `SUBMITTED` → `ASSIGNED`.

**Auth**: `Authorization: Bearer <access_token>` (Staff role)

**Request body**

```json
{
  "assigned_to": "660e8400-e29b-41d4-a716-446655440001"
}
```

| Field | Required | Notes |
|---|---|---|
| `assigned_to` | Yes | UUID of the staff user to assign |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Complaint assigned to Jane Staff.",
  "data": {
    "assigned_to": "660e8400-e29b-41d4-a716-446655440001",
    "assigned_to_name": "Jane Staff",
    "status": "ASSIGNED"
  },
  "errors": null
}
```

---

### PATCH `/{id}/status/`

Drive the complaint state machine. Only valid transitions are allowed.

**Auth**: `Authorization: Bearer <access_token>` (Staff role)

**Request body**

```json
{
  "status": "INVESTIGATING",
  "reason": "Starting investigation — contacting Mascom."
}
```

| Field | Required | Notes |
|---|---|---|
| `status` | Yes | Target status (must be a valid transition) |
| `reason` | No | Reason for the status change |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Complaint status updated to 'Under Investigation'.",
  "data": {
    "status": "INVESTIGATING"
  },
  "errors": null
}
```

**Error `400`** — invalid state transition

---

### POST `/{id}/notes/`

Add a case note. Notes can be internal (staff-only) or visible to the complainant.

**Auth**: `Authorization: Bearer <access_token>` (Staff role)

**Request body**

```json
{
  "content": "Contacted Mascom — awaiting their response on tower maintenance records.",
  "is_internal": true
}
```

| Field | Required | Notes |
|---|---|---|
| `content` | Yes | Note text |
| `is_internal` | No | Default `true`. Set `false` to make visible to complainant |

**Response `201 Created`**

```json
{
  "success": true,
  "message": "Case note added successfully.",
  "data": {
    "id": "...",
    "content": "Contacted Mascom — awaiting their response on tower maintenance records.",
    "is_internal": true,
    "author_name": "Jane Staff",
    "created_at": "2026-03-23T10:00:00Z"
  },
  "errors": null
}
```

---

### POST `/{id}/resolve/`

Submit a formal resolution for the complaint. Auto-transitions to `RESOLVED`. The complaint must be in `INVESTIGATING` or `AWAITING_RESPONSE` status.

**Auth**: `Authorization: Bearer <access_token>` (Staff role)

**Request body**

```json
{
  "resolution": "After investigating, Mascom confirmed the issue was caused by scheduled tower maintenance in Gaborone CBD. The maintenance has been completed and services have been restored. Mascom has committed to providing advance notice for future maintenance windows."
}
```

| Field | Required | Notes |
|---|---|---|
| `resolution` | Yes | Formal resolution text sent to complainant |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Complaint resolved successfully.",
  "data": {
    "status": "RESOLVED",
    "resolved_at": "2026-03-25T14:00:00Z"
  },
  "errors": null
}
```

**Error `400`** — complaint not in a resolvable status

---

### GET `/staff/`

List all complaints across all users. Supports filtering, search, and ordering.

**Auth**: `Authorization: Bearer <access_token>` (Staff role)

**Query parameters** (optional)

| Param | Description |
|---|---|
| `status` | Filter by status |
| `category` | Filter by category |
| `priority` | Filter by priority |
| `assigned_to` | Filter by handler UUID |
| `search` | Search reference number, subject, operator, complainant name/email |
| `ordering` | Sort by `created_at`, `status`, `priority`, `sla_deadline`, `category` |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Complaints retrieved successfully.",
  "data": [
    {
      "id": "...",
      "reference_number": "CMP-2026-000001",
      "subject": "Frequent call drops in Gaborone CBD",
      "category": "SERVICE_QUALITY",
      "category_display": "Service Quality",
      "against_operator_name": "Mascom Wireless",
      "status": "INVESTIGATING",
      "status_display": "Under Investigation",
      "priority": "MEDIUM",
      "priority_display": "Medium",
      "is_overdue": false,
      "sla_deadline": "2026-04-04T12:00:00Z",
      "created_at": "2026-03-21T12:00:00Z",
      "resolved_at": null,
      "complainant_name_display": "Mpho Kgosi",
      "complainant_email_display": "mpho@example.com",
      "assigned_to_name": "Jane Staff",
      "days_until_sla": 12
    }
  ],
  "errors": null
}
```

---

### GET `/staff/{id}/`

Retrieve any complaint with full detail including internal case notes.

**Auth**: `Authorization: Bearer <access_token>` (Staff role)

Same response structure as `GET /{id}/`, but includes all case notes (internal and non-internal).

---

## Enums & Reference

### Complaint Categories

| Value | Label |
|---|---|
| `SERVICE_QUALITY` | Service Quality |
| `BILLING` | Billing Dispute |
| `COVERAGE` | Network Coverage |
| `CONDUCT` | Operator Conduct |
| `INTERNET` | Internet Services |
| `BROADCASTING` | Broadcasting |
| `POSTAL` | Postal Services |
| `OTHER` | Other |

### Complaint Statuses

| Value | Label |
|---|---|
| `SUBMITTED` | Submitted |
| `ASSIGNED` | Assigned |
| `INVESTIGATING` | Under Investigation |
| `AWAITING_RESPONSE` | Awaiting Response |
| `RESOLVED` | Resolved |
| `CLOSED` | Closed |
| `REOPENED` | Reopened |

### Complaint Priorities

| Value | Label | SLA (days) |
|---|---|---|
| `LOW` | Low | 30 |
| `MEDIUM` | Medium | 14 |
| `HIGH` | High | 7 |
| `URGENT` | Urgent | 3 |

### Email Notifications

Complainants receive email notifications at every status change:

- **Submitted** — confirmation with reference number and SLA deadline
- **Assigned** — handler assigned, investigation starting soon
- **Investigating** — active investigation underway
- **Awaiting Response** — waiting for operator response
- **Resolved** — resolution text included in email
- **Closed** — formal closure confirmation
- **Reopened** — case reopened for further investigation
