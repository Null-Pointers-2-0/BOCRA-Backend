# Alerts API

> Base URL: `/api/v1/alerts/`
> Swagger tags: **Alerts** . **Alerts -- Staff**

Proactive alert subscription system allowing citizens to subscribe to
categories of interest (e.g. network outages, licensing updates, tender
notices) and receive email notifications. Supports double opt-in,
one-click unsubscribe, and operator-specific filtering.

---

## Table of Contents

- [Endpoints Summary](#endpoints-summary)
- [Categories](#categories)
- [Subscribe](#subscribe)
- [Confirm Subscription](#confirm-subscription)
- [Unsubscribe](#unsubscribe)
- [My Subscriptions](#my-subscriptions)
- [Update Subscription](#update-subscription)
- [Delete Subscription](#delete-subscription)
- [Alert Logs](#alert-logs)
- [Alert Stats](#alert-stats)
- [Models & Enums](#models--enums)
- [Seed Data](#seed-data)

---

## Endpoints Summary

### Public (no auth required)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/categories/` | List all public alert categories |
| `POST` | `/subscribe/` | Subscribe email to categories |
| `GET` | `/confirm/{token}/` | Confirm subscription via email token |
| `GET` | `/unsubscribe/{token}/` | One-click unsubscribe via token |

### Authenticated (JWT required)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/subscriptions/` | List my subscriptions |
| `PATCH` | `/subscriptions/update/` | Update subscription categories |
| `DELETE` | `/subscriptions/delete/` | Soft-delete my subscription |

### Staff

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/logs/` | Staff | Paginated alert sending audit log |
| `GET` | `/stats/` | Staff | Subscription and delivery analytics |

---

## Categories

### GET `/categories/`

Returns all public, active alert categories.

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Alert categories retrieved.",
  "data": [
    {
      "id": "uuid",
      "name": "Network Outages",
      "code": "NETWORK_OUTAGE",
      "description": "Notifications about planned and unplanned network outages.",
      "icon": "wifi-off",
      "is_public": true,
      "is_active": true,
      "sort_order": 1
    }
  ]
}
```

---

## Subscribe

### POST `/subscribe/`

Subscribe an email address to one or more alert categories. A
confirmation email is sent (double opt-in). If the email already has a
subscription, the existing record is updated and reactivated.

**Rate limit:** 3 requests per email per hour.

**Request body**

```json
{
  "email": "citizen@example.com",
  "categories": ["NETWORK_OUTAGE", "QOE_DROP", "TENDER_NOTICE"],
  "operator_filter": "MASCOM"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `email` | string (email) | Yes | Subscriber email address |
| `categories` | string[] | Yes | List of category codes (min 1) |
| `operator_filter` | string | No | Filter by operator: `MASCOM`, `ORANGE`, `BTCL` |

**Response `201 Created`** (new subscription)

```json
{
  "success": true,
  "message": "Subscription created. Please check your email to confirm.",
  "data": {
    "id": "uuid",
    "email": "citizen@example.com",
    "categories": [
      {
        "id": "uuid",
        "name": "Network Outages",
        "code": "NETWORK_OUTAGE",
        "description": "...",
        "icon": "wifi-off",
        "is_public": true,
        "is_active": true,
        "sort_order": 1
      }
    ],
    "is_confirmed": false,
    "confirmed_at": null,
    "operator_filter": "MASCOM",
    "is_active": true,
    "created_at": "2026-03-25T12:00:00Z"
  }
}
```

**Response `200 OK`** (existing subscription updated)

**Response `400 Bad Request`** (validation error)

```json
{
  "success": false,
  "message": "Validation failed.",
  "errors": {
    "categories": ["Invalid category codes: INVALID_CODE. Valid codes: ..."]
  }
}
```

**Response `429 Too Many Requests`**

```json
{
  "success": false,
  "message": "Rate limit exceeded. Maximum 3 subscription requests per hour."
}
```

---

## Confirm Subscription

### GET `/confirm/{token}/`

Confirm a subscription using the token from the confirmation email.
Tokens expire after 72 hours.

| Parameter | Type | Location | Description |
|---|---|---|---|
| `token` | string | URL path | 64-character hex confirmation token |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Subscription confirmed successfully!",
  "data": {
    "email": "citizen@example.com",
    "confirmed_at": "2026-03-25T14:00:00Z",
    "categories": ["NETWORK_OUTAGE", "QOE_DROP"]
  }
}
```

**Response `200 OK`** (already confirmed)

```json
{
  "success": true,
  "message": "Subscription already confirmed.",
  "data": {
    "email": "citizen@example.com",
    "confirmed_at": "2026-03-25T14:00:00Z"
  }
}
```

**Response `404 Not Found`** -- Invalid token

**Response `410 Gone`** -- Token expired (72 hours)

```json
{
  "success": false,
  "message": "Confirmation token has expired. Please subscribe again."
}
```

---

## Unsubscribe

### GET `/unsubscribe/{token}/`

One-click unsubscribe using the token from any alert email. No login
required. Sets `is_active = false`.

| Parameter | Type | Location | Description |
|---|---|---|---|
| `token` | string | URL path | 64-character hex unsubscribe token |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Successfully unsubscribed. You will no longer receive alerts.",
  "data": {
    "email": "citizen@example.com"
  }
}
```

**Response `200 OK`** (already unsubscribed)

```json
{
  "success": true,
  "message": "Already unsubscribed.",
  "data": {
    "email": "citizen@example.com"
  }
}
```

**Response `404 Not Found`** -- Invalid token

---

## My Subscriptions

### GET `/subscriptions/`

**Auth:** JWT required

Returns all subscriptions linked to the authenticated user (by user FK
or matching email).

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Subscriptions retrieved.",
  "data": [
    {
      "id": "uuid",
      "email": "citizen@example.com",
      "categories": [
        {
          "id": "uuid",
          "name": "Network Outages",
          "code": "NETWORK_OUTAGE",
          "description": "...",
          "icon": "wifi-off",
          "is_public": true,
          "is_active": true,
          "sort_order": 1
        }
      ],
      "is_confirmed": true,
      "confirmed_at": "2026-03-25T14:00:00Z",
      "operator_filter": "",
      "is_active": true,
      "created_at": "2026-03-25T12:00:00Z"
    }
  ]
}
```

---

## Update Subscription

### PATCH `/subscriptions/update/`

**Auth:** JWT required

Update the categories and/or operator filter for your subscription.

**Request body**

```json
{
  "categories": ["NETWORK_OUTAGE", "COVERAGE_CHANGE"],
  "operator_filter": "ORANGE"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `categories` | string[] | Yes | New list of category codes (min 1) |
| `operator_filter` | string | No | Operator filter: `MASCOM`, `ORANGE`, `BTCL` |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Subscription updated.",
  "data": {
    "id": "uuid",
    "email": "citizen@example.com",
    "categories": [ ... ],
    "is_confirmed": true,
    "confirmed_at": "2026-03-25T14:00:00Z",
    "operator_filter": "ORANGE",
    "is_active": true,
    "created_at": "2026-03-25T12:00:00Z"
  }
}
```

**Response `404 Not Found`** -- No subscription for this account

---

## Delete Subscription

### DELETE `/subscriptions/delete/`

**Auth:** JWT required

Soft-deletes all subscriptions linked to the authenticated user.

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Subscription deleted.",
  "data": {
    "deleted": 1
  }
}
```

**Response `404 Not Found`** -- No subscription for this account

---

## Alert Logs

### GET `/logs/`

**Auth:** Staff only

Returns paginated alert sending audit log. Supports filtering by
category, status, and date range.

**Query parameters**

| Parameter | Type | Description |
|---|---|---|
| `category` | string | Filter by category code |
| `status` | string | Filter: `PENDING`, `SENT`, `FAILED` |
| `date_from` | date | Logs from this date (YYYY-MM-DD) |
| `date_to` | date | Logs up to this date (YYYY-MM-DD) |
| `page` | int | Page number |
| `page_size` | int | Items per page (default 50, max 200) |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Alert logs retrieved.",
  "data": {
    "count": 500,
    "next": "http://localhost:8000/api/v1/alerts/logs/?page=2",
    "previous": null,
    "results": [
      {
        "id": "uuid",
        "subscription_email": "citizen@example.com",
        "category_name": "Network Outages",
        "category_code": "NETWORK_OUTAGE",
        "subject": "MASCOM network outage reported in Gaborone",
        "body_preview": "Alert details...",
        "related_object_type": "outage",
        "related_object_id": "12345",
        "status": "SENT",
        "sent_at": "2026-03-25T12:30:00Z",
        "error_message": "",
        "created_at": "2026-03-25T12:30:00Z"
      }
    ]
  }
}
```

---

## Alert Stats

### GET `/stats/`

**Auth:** Staff only

Returns subscription and delivery analytics: total/confirmed/active
counts, per-category breakdown, and delivery stats.

**Query parameters**

| Parameter | Type | Description |
|---|---|---|
| `days` | int | Lookback window in days (default 30) |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Alert statistics retrieved.",
  "data": {
    "days": 30,
    "subscriptions": {
      "total": 200,
      "confirmed": 140,
      "active": 130,
      "recent_signups": 25
    },
    "by_category": [
      {
        "code": "NETWORK_OUTAGE",
        "name": "Network Outages",
        "active_subscribers": 98
      },
      {
        "code": "TENDER_NOTICE",
        "name": "Tender Notices",
        "active_subscribers": 76
      }
    ],
    "delivery": {
      "total_sent": 320,
      "total_failed": 15,
      "total_pending": 5,
      "by_category": [
        {
          "category__code": "NETWORK_OUTAGE",
          "category__name": "Network Outages",
          "total": 85,
          "sent": 80,
          "failed": 5
        }
      ]
    }
  }
}
```

---

## Models & Enums

### AlertStatus (enum)

| Value | Label |
|---|---|
| `PENDING` | Pending |
| `SENT` | Sent |
| `FAILED` | Failed |

### AlertCategory

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | PK (from BaseModel) |
| `name` | CharField(200) | Category display name |
| `code` | CharField(50) | Unique code, indexed |
| `description` | TextField | Optional description |
| `icon` | CharField(50) | Frontend icon identifier |
| `is_public` | BooleanField | Visible to anonymous users |
| `is_active` | BooleanField | Accepts new subscriptions |
| `sort_order` | PositiveIntegerField | Display ordering |
| `created_at` | DateTimeField | Auto (from BaseModel) |
| `updated_at` | DateTimeField | Auto (from BaseModel) |
| `is_deleted` | BooleanField | Soft delete (from BaseModel) |

### AlertSubscription

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | PK |
| `email` | EmailField | Unique, indexed |
| `user` | FK -> User | Nullable, linked if registered |
| `categories` | M2M -> AlertCategory | Subscribed categories |
| `is_confirmed` | BooleanField | Double opt-in confirmed |
| `confirm_token` | CharField(64) | Unique, auto-generated |
| `unsubscribe_token` | CharField(64) | Unique, auto-generated |
| `confirmed_at` | DateTimeField | Nullable |
| `operator_filter` | CharField(20) | Optional: MASCOM, ORANGE, BTCL |
| `is_active` | BooleanField | Master on/off switch |
| `created_at` | DateTimeField | Auto |
| `updated_at` | DateTimeField | Auto |
| `is_deleted` | BooleanField | Soft delete |

Token expiry: `confirm_token` expires 72 hours after `created_at`.

### AlertLog

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | PK |
| `subscription` | FK -> AlertSubscription | Recipient |
| `category` | FK -> AlertCategory | Alert category |
| `subject` | CharField(300) | Alert subject line |
| `body_preview` | TextField | Body preview / snippet |
| `related_object_type` | CharField(100) | E.g. "outage", "tender" |
| `related_object_id` | CharField(100) | Related object UUID/ID |
| `status` | AlertStatus | PENDING / SENT / FAILED |
| `sent_at` | DateTimeField | Nullable |
| `error_message` | TextField | Failure details |
| `created_at` | DateTimeField | Auto |

---

## Seed Data

Run: `python manage.py seed_alerts`

Creates:
- **8 categories:** NETWORK_OUTAGE, QOE_DROP, COVERAGE_CHANGE, LICENSE_UPDATE,
  COMPLAINT_RESOLVED, REGULATORY, TENDER_NOTICE, SCORECARD_UPDATE
- **200 subscriptions:** Random emails, ~70% confirmed, random operator filters,
  2-5 categories each
- **500 alert logs:** Spread across Oct 2025 -- Mar 2026, realistic subjects
  per category, ~70% SENT / ~20% PENDING / ~10% FAILED

### Subscription flow

1. Citizen calls `POST /subscribe/` with email + category codes
2. System creates subscription with `is_confirmed = false`
3. Confirmation email sent with link containing `confirm_token`
4. Citizen clicks link -> `GET /confirm/{token}/` sets `is_confirmed = true`
5. Alerts are only sent to confirmed, active subscriptions
6. Every alert email includes a one-click unsubscribe link (`unsubscribe_token`)
