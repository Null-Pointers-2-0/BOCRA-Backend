# Domains API

> Base URL: `/api/v1/domains/`  
> Swagger tags: **Domains — Public** · **Domains — Applicant** · **Domains — Staff**

Manages the .bw domain registration lifecycle: zone catalogue, domain availability checks, WHOIS lookup, application submission with state machine workflow, domain registry management, and administrative statistics.

---

## Table of Contents

- [Endpoints Summary](#endpoints-summary)
- [Application Status Values](#application-status-values)
- [Application Type Values](#application-type-values)
- [Domain Status Values](#domain-status-values)
- [Domain Event Types](#domain-event-types)
- [Public — Zones, Availability & WHOIS](#public--zones-availability--whois)
- [Applicant — Applications](#applicant--applications)
- [Applicant — Domains](#applicant--domains)
- [Staff — Applications](#staff--applications)
- [Staff — Domain Registry](#staff--domain-registry)
- [Staff — Zone Management](#staff--zone-management)
- [Staff — Statistics](#staff--statistics)

---

## Endpoints Summary

### Public

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/zones/` | List all active domain zones | Public |
| `GET` | `/check/?name=` | Check domain availability | Public |
| `GET` | `/whois/?name=` | WHOIS lookup for a domain | Public |

### Applicant — Applications

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/apply/` | Create a new domain application | Authenticated |
| `GET` | `/my-applications/` | List my applications | Authenticated |
| `GET` | `/my-applications/{id}/` | Application detail | Owner |
| `PATCH` | `/my-applications/{id}/` | Update a draft application | Owner |
| `POST` | `/my-applications/{id}/submit/` | Submit a draft application | Owner |
| `POST` | `/my-applications/{id}/cancel/` | Cancel an application | Owner |
| `POST` | `/my-applications/{id}/respond/` | Respond to info request | Owner |

### Applicant — Domains

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/my-domains/` | List my registered domains | Authenticated |
| `GET` | `/my-domains/{id}/` | Domain detail | Owner |

### Staff — Applications

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/staff/applications/` | List all applications | Staff |
| `GET` | `/staff/applications/{id}/` | Application detail (staff) | Staff |
| `PATCH` | `/staff/applications/{id}/review/` | Start reviewing an application | Staff |
| `PATCH` | `/staff/applications/{id}/approve/` | Approve an application | Staff |
| `PATCH` | `/staff/applications/{id}/reject/` | Reject an application | Staff |
| `PATCH` | `/staff/applications/{id}/request-info/` | Request more information | Staff |

### Staff — Domain Registry

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/staff/list/` | List all registered domains | Staff |
| `GET` | `/staff/{id}/` | Domain detail (staff) | Staff |
| `PATCH` | `/staff/{id}/update/` | Update domain details | Staff |
| `PATCH` | `/staff/{id}/suspend/` | Suspend a domain | Staff |
| `PATCH` | `/staff/{id}/unsuspend/` | Unsuspend a domain | Staff |
| `PATCH` | `/staff/{id}/reassign/` | Reassign domain to new owner | Staff |
| `DELETE` | `/staff/{id}/delete/` | Soft-delete a domain | Staff |

### Staff — Zone Management

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/staff/zones/` | List all zones (including inactive) | Staff |
| `POST` | `/staff/zones/` | Create a new zone | Staff |
| `PATCH` | `/staff/zones/{id}/` | Update a zone | Staff |

### Staff — Statistics

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/staff/stats/` | Domain and application statistics | Staff |

---

## Application Status Values

Domain applications move through a defined state machine. Not all transitions are valid.

| Value | Display |
|---|---|
| `DRAFT` | Draft |
| `SUBMITTED` | Submitted |
| `UNDER_REVIEW` | Under Review |
| `INFO_REQUESTED` | Additional Information Requested |
| `APPROVED` | Approved |
| `REJECTED` | Rejected |
| `CANCELLED` | Cancelled |

### Valid Transitions

```
DRAFT
  ├─→ SUBMITTED       (applicant submits)
  └─→ CANCELLED       (applicant cancels)

SUBMITTED
  ├─→ UNDER_REVIEW    (staff picks up for review)
  └─→ CANCELLED       (applicant cancels)

UNDER_REVIEW
  ├─→ INFO_REQUESTED  (staff requests more info)
  ├─→ APPROVED        (staff approves → domain auto-created)
  └─→ REJECTED        (staff rejects)

INFO_REQUESTED
  ├─→ UNDER_REVIEW    (applicant responds → re-review)
  └─→ CANCELLED       (applicant cancels)

APPROVED  → (terminal)
REJECTED  → (terminal)
CANCELLED → (terminal)
```

> **Note:** When an application is approved via `PATCH /staff/applications/{id}/approve/`, a `Domain` record is **automatically created** with `ACTIVE` status, and a `DomainEvent` (type `REGISTERED`) is logged.

---

## Application Type Values

| Value | Display |
|---|---|
| `REGISTRATION` | Registration |
| `RENEWAL` | Renewal |
| `TRANSFER` | Transfer |

---

## Domain Status Values

| Value | Display |
|---|---|
| `ACTIVE` | Active |
| `EXPIRED` | Expired |
| `SUSPENDED` | Suspended |
| `PENDING_DELETE` | Pending Delete |
| `DELETED` | Deleted |

---

## Domain Event Types

Events are logged with structured metadata for auditing.

| Value | Display | Metadata |
|---|---|---|
| `REGISTERED` | Registered | `{ application_ref, period_years }` |
| `RENEWED` | Renewed | `{ old_expiry, new_expiry }` |
| `TRANSFERRED` | Transferred | `{ old_registrant, new_registrant, reason }` |
| `NS_UPDATED` | Nameservers Updated | `{ old_values, new_values }` |
| `CONTACT_UPDATED` | Contact Updated | `{ old_values, new_values }` |
| `SUSPENDED` | Suspended | `{ reason }` |
| `UNSUSPENDED` | Unsuspended | `{}` |
| `EXPIRED` | Expired | `{}` |
| `DELETED` | Deleted | `{ previous_status }` |

---

## Public — Zones, Availability & WHOIS

### GET `/zones/`

List all active domain zones available for registration (e.g. `.co.bw`, `.org.bw`).

**Auth**: None required

**Query parameters**

| Param | Description |
|---|---|
| `search` | Search by name, code, or description |
| `ordering` | Sort by `name` |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Domain zones retrieved successfully.",
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": ".co.bw",
      "code": "CO_BW",
      "description": "Commercial entities registered in Botswana.",
      "registration_fee": "500.00",
      "renewal_fee": "350.00",
      "fee_currency": "BWP",
      "min_registration_years": 1,
      "max_registration_years": 10,
      "is_restricted": false,
      "eligibility_criteria": "",
      "is_active": true
    }
  ],
  "errors": null
}
```

---

### GET `/check/?name=`

Check whether a domain name is available for registration.

**Auth**: None required

**Query parameters**

| Param | Required | Description |
|---|---|---|
| `name` | Yes | Fully qualified domain name (e.g. `mycompany.co.bw`) |

**Response `200 OK`** — domain available

```json
{
  "success": true,
  "message": "Domain is available for registration.",
  "data": {
    "domain_name": "mycompany.co.bw",
    "available": true,
    "zone": {
      "id": "...",
      "name": ".co.bw",
      "code": "CO_BW",
      "registration_fee": "500.00",
      "renewal_fee": "350.00",
      "fee_currency": "BWP"
    },
    "message": "This domain is available for registration."
  },
  "errors": null
}
```

**Response `200 OK`** — domain unavailable

```json
{
  "success": true,
  "message": "Domain is not available.",
  "data": {
    "domain_name": "mascom.co.bw",
    "available": false,
    "zone": { "..." },
    "message": "This domain is already registered."
  },
  "errors": null
}
```

**Error `400`** — `name` not provided or invalid zone

---

### GET `/whois/?name=`

Public WHOIS lookup. Returns limited registrant information for privacy.

**Auth**: None required

**Query parameters**

| Param | Required | Description |
|---|---|---|
| `name` | Yes | Fully qualified domain name (e.g. `mascom.co.bw`) |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "WHOIS record found.",
  "data": {
    "domain_name": "mascom.co.bw",
    "zone_name": ".co.bw",
    "status": "ACTIVE",
    "status_display": "Active",
    "registrant_name": "Mascom Wireless",
    "organisation_name": "Mascom Wireless (Pty) Ltd",
    "registered_at": "2020-01-15T00:00:00Z",
    "expires_at": "2026-01-15T00:00:00Z",
    "nameserver_1": "ns1.mascom.bw",
    "nameserver_2": "ns2.mascom.bw"
  },
  "errors": null
}
```

**Error `400`** — `name` not provided  
**Error `404`** — domain not found in registry

---

## Applicant — Applications

### POST `/apply/`

Create a new domain application. By default creates a `DRAFT`; set `"submit": true` to submit immediately.

**Auth**: `Authorization: Bearer <access_token>`

**Request body**

```json
{
  "application_type": "REGISTRATION",
  "domain_name": "mycompany.co.bw",
  "zone": "550e8400-e29b-41d4-a716-446655440000",
  "registration_period_years": 2,
  "organisation_name": "My Company (Pty) Ltd",
  "organisation_registration_number": "BW-2020-12345",
  "registrant_name": "Jane Doe",
  "registrant_email": "jane@mycompany.bw",
  "registrant_phone": "+26771234567",
  "registrant_address": "Plot 123, Gaborone, Botswana",
  "nameserver_1": "ns1.mycompany.bw",
  "nameserver_2": "ns2.mycompany.bw",
  "tech_contact_name": "John Smith",
  "tech_contact_email": "john@mycompany.bw",
  "justification": "Corporate website for our Botswana operations.",
  "submit": true
}
```

| Field | Required | Notes |
|---|---|---|
| `application_type` | No | `REGISTRATION` (default), `RENEWAL`, or `TRANSFER` |
| `domain_name` | Yes | FQDN ending with a valid zone (e.g. `example.co.bw`) |
| `zone` | Yes | UUID of an active zone |
| `registration_period_years` | No | 1–10 years (default: 1) |
| `organisation_name` | Yes | |
| `organisation_registration_number` | No | |
| `registrant_name` | Yes | |
| `registrant_email` | Yes | |
| `registrant_phone` | No | |
| `registrant_address` | No | |
| `nameserver_1`–`nameserver_4` | No | Required for submission, not for drafts |
| `tech_contact_name` | No | |
| `tech_contact_email` | No | |
| `transfer_from_registrant` | Conditional | Required for `TRANSFER` type |
| `transfer_auth_code` | Conditional | Required for `TRANSFER` type |
| `justification` | No | Free-text justification |
| `submit` | No | `true` = submit immediately; `false` (default) = save as draft |

**Validations**:
- Zone must be active
- Domain name must end with the zone name
- For `REGISTRATION`: domain must not be already registered or have pending applications
- For `TRANSFER`: `transfer_auth_code` and `transfer_from_registrant` are required

**Response `201 Created`**

```json
{
  "success": true,
  "message": "Domain application created successfully.",
  "data": {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "reference_number": "DOM-2026-00001",
    "application_type": "REGISTRATION",
    "application_type_display": "Registration",
    "domain_name": "mycompany.co.bw",
    "zone": "550e8400-e29b-41d4-a716-446655440000",
    "zone_name": ".co.bw",
    "status": "SUBMITTED",
    "status_display": "Submitted",
    "submitted_at": "2026-03-10T08:00:00Z",
    "created_at": "2026-03-10T08:00:00Z"
  },
  "errors": null
}
```

**Error `400`** — validation failure

---

### GET `/my-applications/`

List all domain applications belonging to the authenticated user.

**Auth**: `Authorization: Bearer <access_token>`

**Query parameters**

| Param | Description |
|---|---|
| `status` | Filter by application status |
| `application_type` | Filter by `REGISTRATION`, `RENEWAL`, or `TRANSFER` |
| `zone` | Filter by zone UUID |
| `ordering` | Sort by `created_at`, `submitted_at`, `status` |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Applications retrieved successfully.",
  "data": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "reference_number": "DOM-2026-00001",
      "application_type": "REGISTRATION",
      "application_type_display": "Registration",
      "domain_name": "mycompany.co.bw",
      "zone": "550e8400-e29b-41d4-a716-446655440000",
      "zone_name": ".co.bw",
      "organisation_name": "My Company (Pty) Ltd",
      "status": "SUBMITTED",
      "status_display": "Submitted",
      "submitted_at": "2026-03-10T08:00:00Z",
      "decision_date": null,
      "created_at": "2026-03-10T08:00:00Z",
      "updated_at": "2026-03-10T08:00:00Z"
    }
  ],
  "errors": null
}
```

---

### GET `/my-applications/{id}/`

Full application detail including documents and status timeline.

**Auth**: Owner

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Application retrieved successfully.",
  "data": {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "reference_number": "DOM-2026-00001",
    "application_type": "REGISTRATION",
    "application_type_display": "Registration",
    "domain_name": "mycompany.co.bw",
    "zone": {
      "id": "...",
      "name": ".co.bw",
      "code": "CO_BW",
      "description": "Commercial entities registered in Botswana.",
      "registration_fee": "500.00",
      "renewal_fee": "350.00",
      "fee_currency": "BWP"
    },
    "status": "SUBMITTED",
    "status_display": "Submitted",
    "registration_period_years": 2,
    "organisation_name": "My Company (Pty) Ltd",
    "organisation_registration_number": "BW-2020-12345",
    "registrant_name": "Jane Doe",
    "registrant_email": "jane@mycompany.bw",
    "registrant_phone": "+26771234567",
    "registrant_address": "Plot 123, Gaborone, Botswana",
    "nameserver_1": "ns1.mycompany.bw",
    "nameserver_2": "ns2.mycompany.bw",
    "nameserver_3": "",
    "nameserver_4": "",
    "tech_contact_name": "John Smith",
    "tech_contact_email": "john@mycompany.bw",
    "transfer_from_registrant": "",
    "transfer_auth_code": "",
    "justification": "Corporate website for our Botswana operations.",
    "submitted_at": "2026-03-10T08:00:00Z",
    "decision_date": null,
    "decision_reason": "",
    "info_request_message": "",
    "can_cancel": true,
    "has_domain": false,
    "domain_id": null,
    "documents": [],
    "status_timeline": [
      {
        "id": "...",
        "from_status": "DRAFT",
        "from_status_display": "Draft",
        "to_status": "SUBMITTED",
        "to_status_display": "Submitted",
        "changed_by_name": "Jane Doe",
        "reason": "Submitted by applicant.",
        "changed_at": "2026-03-10T08:00:00Z"
      }
    ],
    "created_at": "2026-03-10T08:00:00Z",
    "updated_at": "2026-03-10T08:00:00Z"
  },
  "errors": null
}
```

**Error `404`** — application not found or not owned by user

---

### PATCH `/my-applications/{id}/`

Update a draft application. Only `DRAFT` applications can be updated.

**Auth**: Owner

**Request body** (partial)

```json
{
  "nameserver_1": "ns1.updated.bw",
  "nameserver_2": "ns2.updated.bw",
  "justification": "Updated justification."
}
```

**Updatable fields**: `domain_name`, `zone`, `registration_period_years`, `organisation_name`, `organisation_registration_number`, `registrant_name`, `registrant_email`, `registrant_phone`, `registrant_address`, `nameserver_1`–`nameserver_4`, `tech_contact_name`, `tech_contact_email`, `transfer_from_registrant`, `transfer_auth_code`, `justification`

**Response `200 OK`** — updated application detail

**Error `400`** — application is not in DRAFT status  
**Error `404`** — application not found

---

### POST `/my-applications/{id}/submit/`

Submit a draft application for staff review. Transitions `DRAFT` → `SUBMITTED`.

**Auth**: Owner

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Application submitted successfully.",
  "data": null,
  "errors": null
}
```

**Error `400`** — application is not in DRAFT status  
**Error `404`** — application not found

---

### POST `/my-applications/{id}/cancel/`

Cancel an application. Valid from `DRAFT`, `SUBMITTED`, or `INFO_REQUESTED` status.

**Auth**: Owner

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

**Error `400`** — application cannot be cancelled from current status  
**Error `404`** — application not found

---

### POST `/my-applications/{id}/respond/`

Respond to an information request from staff. Transitions `INFO_REQUESTED` → `UNDER_REVIEW`.

**Auth**: Owner

**Request body**

```json
{ "message": "Please find attached the updated company registration document." }
```

| Field | Required | Notes |
|---|---|---|
| `message` | Yes | Applicant's response to the staff request |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Response submitted. Your application will be reviewed again.",
  "data": null,
  "errors": null
}
```

**Error `400`** — application is not in INFO_REQUESTED status or message missing  
**Error `404`** — application not found

---

## Applicant — Domains

### GET `/my-domains/`

List all domains owned by the authenticated user.

**Auth**: `Authorization: Bearer <access_token>`

**Query parameters**

| Param | Description |
|---|---|
| `status` | Filter by domain status (`ACTIVE`, `EXPIRED`, etc.) |
| `zone` | Filter by zone UUID |
| `ordering` | Sort by `domain_name`, `registered_at`, `expires_at` |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Domains retrieved successfully.",
  "data": [
    {
      "id": "990e8400-e29b-41d4-a716-446655440005",
      "domain_name": "mycompany.co.bw",
      "zone": "550e8400-e29b-41d4-a716-446655440000",
      "zone_name": ".co.bw",
      "status": "ACTIVE",
      "status_display": "Active",
      "organisation_name": "My Company (Pty) Ltd",
      "registered_at": "2026-03-15T00:00:00Z",
      "expires_at": "2028-03-15T00:00:00Z",
      "is_expired": false,
      "days_until_expiry": 720
    }
  ],
  "errors": null
}
```

---

### GET `/my-domains/{id}/`

Full domain detail for the authenticated registrant.

**Auth**: Owner

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Domain retrieved successfully.",
  "data": {
    "id": "990e8400-e29b-41d4-a716-446655440005",
    "domain_name": "mycompany.co.bw",
    "zone": {
      "id": "...",
      "name": ".co.bw",
      "code": "CO_BW",
      "description": "...",
      "registration_fee": "500.00",
      "renewal_fee": "350.00",
      "fee_currency": "BWP"
    },
    "status": "ACTIVE",
    "status_display": "Active",
    "registrant_name": "Jane Doe",
    "registrant_email": "jane@mycompany.bw",
    "registrant_phone": "+26771234567",
    "registrant_address": "Plot 123, Gaborone, Botswana",
    "organisation_name": "My Company (Pty) Ltd",
    "nameserver_1": "ns1.mycompany.bw",
    "nameserver_2": "ns2.mycompany.bw",
    "nameserver_3": "",
    "nameserver_4": "",
    "tech_contact_name": "John Smith",
    "tech_contact_email": "john@mycompany.bw",
    "registered_at": "2026-03-15T00:00:00Z",
    "expires_at": "2028-03-15T00:00:00Z",
    "last_renewed_at": null,
    "is_expired": false,
    "days_until_expiry": 720,
    "created_at": "2026-03-15T00:00:00Z",
    "updated_at": "2026-03-15T00:00:00Z"
  },
  "errors": null
}
```

**Error `404`** — domain not found or not owned by user

---

## Staff — Applications

> All endpoints in this section require `Staff`, `Admin`, or `SuperAdmin` role.

### GET `/staff/applications/`

List all domain applications across all users.

**Auth**: Staff

**Query parameters**

| Param | Description |
|---|---|
| `status` | Filter by application status |
| `application_type` | Filter by `REGISTRATION`, `RENEWAL`, or `TRANSFER` |
| `zone` | Filter by zone UUID |
| `search` | Search by reference number, domain name, organisation name, or applicant email |
| `ordering` | Sort by `created_at`, `submitted_at`, `status`, `domain_name` |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Applications retrieved successfully.",
  "data": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "reference_number": "DOM-2026-00001",
      "application_type": "REGISTRATION",
      "application_type_display": "Registration",
      "domain_name": "mycompany.co.bw",
      "zone": "...",
      "zone_name": ".co.bw",
      "organisation_name": "My Company (Pty) Ltd",
      "status": "SUBMITTED",
      "status_display": "Submitted",
      "submitted_at": "2026-03-10T08:00:00Z",
      "decision_date": null,
      "applicant_name": "Jane Doe",
      "applicant_email": "jane@mycompany.bw",
      "created_at": "2026-03-10T08:00:00Z",
      "updated_at": "2026-03-10T08:00:00Z"
    }
  ],
  "errors": null
}
```

---

### GET `/staff/applications/{id}/`

Full application detail with staff-only fields including `reviewed_by_name`.

**Auth**: Staff

**Response `200 OK`** — same shape as `GET /my-applications/{id}/` plus:

```json
{
  "applicant_name": "Jane Doe",
  "applicant_email": "jane@mycompany.bw",
  "reviewed_by_name": "Staff Member"
}
```

**Error `404`** — application not found

---

### PATCH `/staff/applications/{id}/review/`

Start reviewing a submitted application. Transitions `SUBMITTED` → `UNDER_REVIEW`.

**Auth**: Staff

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Application is now under review.",
  "data": null,
  "errors": null
}
```

**Error `400`** — invalid transition from current status  
**Error `404`** — application not found

---

### PATCH `/staff/applications/{id}/approve/`

Approve an application. Transitions `UNDER_REVIEW` or `INFO_REQUESTED` → `APPROVED`. **Automatically creates a `Domain` record** with `ACTIVE` status and logs a `REGISTERED` event.

**Auth**: Staff

**Request body** (optional)

```json
{ "reason": "All documentation verified." }
```

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Application approved. Domain mycompany.co.bw registered.",
  "data": {
    "domain_id": "990e8400-e29b-41d4-a716-446655440005",
    "domain_name": "mycompany.co.bw"
  },
  "errors": null
}
```

**Auto-created domain record includes**:
- `status` = `ACTIVE`
- `registrant` = application's applicant
- All registrant details, nameservers, and tech contact copied from application
- `registered_at` = now
- `expires_at` = now + (`registration_period_years` × 365 days)
- `created_from_application` = this application

**Error `400`** — invalid transition from current status  
**Error `404`** — application not found

---

### PATCH `/staff/applications/{id}/reject/`

Reject an application. Transitions `UNDER_REVIEW` or `INFO_REQUESTED` → `REJECTED`.

**Auth**: Staff

**Request body**

```json
{ "reason": "Domain violates naming policy." }
```

| Field | Required | Notes |
|---|---|---|
| `reason` | Yes | Rejection reason (shown to applicant) |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Application rejected.",
  "data": null,
  "errors": null
}
```

**Error `400`** — reason not provided or invalid transition  
**Error `404`** — application not found

---

### PATCH `/staff/applications/{id}/request-info/`

Request additional information from the applicant. Transitions `UNDER_REVIEW` → `INFO_REQUESTED`.

**Auth**: Staff

**Request body**

```json
{ "message": "Please provide proof of organization registration in Botswana." }
```

| Field | Required | Notes |
|---|---|---|
| `message` | Yes | Message sent to the applicant |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Information requested from applicant.",
  "data": null,
  "errors": null
}
```

**Error `400`** — message not provided or invalid transition  
**Error `404`** — application not found

---

## Staff — Domain Registry

> All endpoints in this section require `Staff`, `Admin`, or `SuperAdmin` role.

### GET `/staff/list/`

List all registered domains across all registrants. Includes extra fields for staff.

**Auth**: Staff

**Query parameters**

| Param | Description |
|---|---|
| `status` | Filter by domain status |
| `zone` | Filter by zone UUID |
| `is_seeded` | Filter by seeded/imported status |
| `search` | Search by domain name, organisation name, registrant name, or registrant email |
| `ordering` | Sort by `domain_name`, `registered_at`, `expires_at`, `status` |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Domains retrieved successfully.",
  "data": [
    {
      "id": "990e8400-e29b-41d4-a716-446655440005",
      "domain_name": "mycompany.co.bw",
      "zone": "...",
      "zone_name": ".co.bw",
      "status": "ACTIVE",
      "status_display": "Active",
      "organisation_name": "My Company (Pty) Ltd",
      "registered_at": "2026-03-15T00:00:00Z",
      "expires_at": "2028-03-15T00:00:00Z",
      "is_expired": false,
      "days_until_expiry": 720,
      "registrant_name": "Jane Doe",
      "registrant_email": "jane@mycompany.bw",
      "is_seeded": false
    }
  ],
  "errors": null
}
```

---

### GET `/staff/{id}/`

Full domain detail with staff fields including events audit log.

**Auth**: Staff

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Domain retrieved successfully.",
  "data": {
    "id": "990e8400-e29b-41d4-a716-446655440005",
    "domain_name": "mycompany.co.bw",
    "zone": { "..." },
    "status": "ACTIVE",
    "status_display": "Active",
    "registrant_name": "Jane Doe",
    "registrant_email": "jane@mycompany.bw",
    "registrant_phone": "+26771234567",
    "registrant_address": "Plot 123, Gaborone, Botswana",
    "organisation_name": "My Company (Pty) Ltd",
    "nameserver_1": "ns1.mycompany.bw",
    "nameserver_2": "ns2.mycompany.bw",
    "nameserver_3": "",
    "nameserver_4": "",
    "tech_contact_name": "John Smith",
    "tech_contact_email": "john@mycompany.bw",
    "registered_at": "2026-03-15T00:00:00Z",
    "expires_at": "2028-03-15T00:00:00Z",
    "last_renewed_at": null,
    "is_expired": false,
    "days_until_expiry": 720,
    "is_seeded": false,
    "created_from_application_ref": "DOM-2026-00001",
    "events": [
      {
        "id": "...",
        "event_type": "REGISTERED",
        "description": "Domain registered via application DOM-2026-00001.",
        "performed_by_name": "Staff Member",
        "metadata": {
          "application_ref": "DOM-2026-00001",
          "period_years": 2
        },
        "created_at": "2026-03-15T00:00:00Z"
      }
    ],
    "created_at": "2026-03-15T00:00:00Z",
    "updated_at": "2026-03-15T00:00:00Z"
  },
  "errors": null
}
```

**Error `404`** — domain not found

---

### PATCH `/staff/{id}/update/`

Update domain details (nameservers, contact info). Creates a `DomainEvent` recording old vs new values.

**Auth**: Staff

**Request body** (partial)

```json
{
  "nameserver_1": "ns1.updated.bw",
  "nameserver_2": "ns2.updated.bw",
  "registrant_name": "Jane Smith",
  "registrant_email": "jane.smith@mycompany.bw"
}
```

**Updatable fields**: `nameserver_1` (required), `nameserver_2` (required), `nameserver_3`, `nameserver_4`, `tech_contact_name`, `tech_contact_email`, `registrant_name` (required), `registrant_email` (required), `registrant_phone`, `registrant_address`, `organisation_name`

**Side effects**: Creates a `DomainEvent` with type `NS_UPDATED` (if nameservers changed) or `CONTACT_UPDATED` (if only contact info changed), with `metadata` containing `old_values` and `new_values`.

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Domain updated successfully.",
  "data": null,
  "errors": null
}
```

**Error `400`** — validation failure  
**Error `404`** — domain not found

---

### PATCH `/staff/{id}/suspend/`

Suspend an active domain.

**Auth**: Staff

**Precondition**: Domain status must be `ACTIVE`

**Request body**

```json
{ "reason": "Non-payment of renewal fees." }
```

| Field | Required | Notes |
|---|---|---|
| `reason` | Yes | Reason for suspension |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Domain suspended successfully.",
  "data": null,
  "errors": null
}
```

**Error `400`** — domain is not in ACTIVE status  
**Error `404`** — domain not found

---

### PATCH `/staff/{id}/unsuspend/`

Unsuspend (reactivate) a suspended domain.

**Auth**: Staff

**Precondition**: Domain status must be `SUSPENDED`

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Domain unsuspended successfully.",
  "data": null,
  "errors": null
}
```

**Error `400`** — domain is not in SUSPENDED status  
**Error `404`** — domain not found

---

### PATCH `/staff/{id}/reassign/`

Reassign a domain to a different registered user.

**Auth**: Staff

**Request body**

```json
{
  "new_owner_id": "aa0e8400-e29b-41d4-a716-446655440099",
  "reason": "Transfer of ownership following company acquisition."
}
```

| Field | Required | Notes |
|---|---|---|
| `new_owner_id` | Yes | UUID of the new registrant (must be an active user) |
| `reason` | Yes | Reason for reassignment |

**Side effects**: Creates a `TRANSFERRED` event with `old_registrant`, `new_registrant`, and `reason` in metadata. Updates `registrant`, `registrant_name`, and `registrant_email` from the new user.

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Domain reassigned successfully.",
  "data": null,
  "errors": null
}
```

**Error `400`** — `new_owner_id` not found or inactive  
**Error `404`** — domain not found

---

### DELETE `/staff/{id}/delete/`

Soft-delete a domain. Creates a `DELETED` event and marks as `is_deleted=True`.

**Auth**: Staff

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Domain deleted successfully.",
  "data": null,
  "errors": null
}
```

**Error `404`** — domain not found

---

## Staff — Zone Management

### GET `/staff/zones/`

List all zones including inactive ones.

**Auth**: Staff

**Query parameters**

| Param | Description |
|---|---|
| `search` | Search by name or code |
| `ordering` | Sort by `name` |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Zones retrieved successfully.",
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": ".co.bw",
      "code": "CO_BW",
      "description": "Commercial entities registered in Botswana.",
      "registration_fee": "500.00",
      "renewal_fee": "350.00",
      "fee_currency": "BWP",
      "min_registration_years": 1,
      "max_registration_years": 10,
      "is_restricted": false,
      "eligibility_criteria": "",
      "is_active": true,
      "created_at": "2026-01-01T00:00:00Z",
      "updated_at": "2026-01-01T00:00:00Z"
    }
  ],
  "errors": null
}
```

---

### POST `/staff/zones/`

Create a new domain zone.

**Auth**: Staff

**Request body**

```json
{
  "name": ".gov.bw",
  "code": "GOV_BW",
  "description": "Government entities in Botswana.",
  "registration_fee": "0.00",
  "renewal_fee": "0.00",
  "fee_currency": "BWP",
  "min_registration_years": 1,
  "max_registration_years": 10,
  "is_restricted": true,
  "eligibility_criteria": "Must be a government ministry or department.",
  "is_active": true
}
```

| Field | Required | Notes |
|---|---|---|
| `name` | Yes | Zone name (e.g. `.gov.bw`) |
| `code` | Yes | Unique code (e.g. `GOV_BW`) |
| `description` | Yes | |
| `registration_fee` | Yes | Fee in BWP |
| `renewal_fee` | Yes | Annual renewal fee |
| `fee_currency` | No | Default: `BWP` |
| `min_registration_years` | No | Default: 1 |
| `max_registration_years` | No | Default: 10 |
| `is_restricted` | No | Default: `false` |
| `eligibility_criteria` | No | |
| `is_active` | No | Default: `true` |

**Response `201 Created`**

```json
{
  "success": true,
  "message": "Zone created successfully.",
  "data": { "..." },
  "errors": null
}
```

**Error `400`** — validation failure (e.g. duplicate code)

---

### PATCH `/staff/zones/{id}/`

Update an existing zone. Supports partial updates.

**Auth**: Staff

**Request body** (partial)

```json
{
  "registration_fee": "600.00",
  "is_active": false
}
```

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Zone updated successfully.",
  "data": { "..." },
  "errors": null
}
```

**Error `400`** — validation failure  
**Error `404`** — zone not found

---

## Staff — Statistics

### GET `/staff/stats/`

Aggregate statistics for domains and applications.

**Auth**: Staff

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Statistics retrieved successfully.",
  "data": {
    "total_domains": 150,
    "active_domains": 120,
    "expired_domains": 15,
    "suspended_domains": 5,
    "expiring_soon": 8,
    "pending_applications": 12,
    "domains_by_zone": [
      { "zone__name": ".co.bw", "zone__code": "CO_BW", "count": 80 },
      { "zone__name": ".org.bw", "zone__code": "ORG_BW", "count": 30 },
      { "zone__name": ".ac.bw", "zone__code": "AC_BW", "count": 20 }
    ],
    "domains_by_status": [
      { "status": "ACTIVE", "count": 120 },
      { "status": "EXPIRED", "count": 15 },
      { "status": "SUSPENDED", "count": 5 }
    ],
    "applications_by_status": [
      { "status": "SUBMITTED", "count": 5 },
      { "status": "UNDER_REVIEW", "count": 4 },
      { "status": "INFO_REQUESTED", "count": 3 }
    ]
  },
  "errors": null
}
```

| Field | Description |
|---|---|
| `total_domains` | All non-deleted domains |
| `active_domains` | Domains with `ACTIVE` status |
| `expired_domains` | Domains with `EXPIRED` status |
| `suspended_domains` | Domains with `SUSPENDED` status |
| `expiring_soon` | Active domains expiring within 30 days |
| `pending_applications` | Applications in `SUBMITTED`, `UNDER_REVIEW`, or `INFO_REQUESTED` |
| `domains_by_zone` | Breakdown of domains by zone |
| `domains_by_status` | Breakdown of domains by status |
| `applications_by_status` | Breakdown of applications by status |

---

*BOCRA Digital Platform — Domains API — v1.0*
