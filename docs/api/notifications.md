# Notifications API

> Base URL: `/api/v1/notifications/`  
> Swagger tag: **Notifications**

In-app notification system for authenticated users. Notifications are created programmatically by other parts of the system (e.g. licence status changes, complaint updates) using the `notify_user()` utility. Users can list, read, and dismiss their notifications.

> **MVP scope**: In-app notifications only. Email and SMS channels are planned for a future release.

---

## Table of Contents

- [Endpoints Summary](#endpoints-summary)
- [Notification Model](#notification-model)
- [Endpoints](#endpoints)
- [Creating Notifications (Backend)](#creating-notifications-backend)
- [Enums & Reference](#enums--reference)

---

## Endpoints Summary

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/` | List my notifications | Authenticated |
| `GET` | `/unread-count/` | Get unread notification count | Authenticated |
| `PATCH` | `/{id}/read/` | Mark a notification as read | Owner |
| `PATCH` | `/read-all/` | Mark all notifications as read | Authenticated |
| `DELETE` | `/{id}/` | Dismiss (permanently delete) a notification | Owner |

---

## Notification Model

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `notification_type` | string | `IN_APP`, `EMAIL`, `SMS` (MVP: `IN_APP` only) |
| `title` | string | Short notification title |
| `message` | text | Notification body |
| `is_read` | boolean | Default: `false` |
| `read_at` | datetime | Set when marked as read |
| `status` | string | `PENDING`, `SENT`, `READ`, `FAILED` |
| `related_object_type` | string | Optional. E.g. `"licence"`, `"complaint"` |
| `related_object_id` | UUID | Optional. Links to the related object |
| `created_at` | datetime | Auto-set on creation |

---

## Endpoints

### GET `/`

List all notifications for the authenticated user, newest first.

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Notifications retrieved.",
  "data": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "notification_type": "IN_APP",
      "title": "Licence Application Approved",
      "message": "Your licence application #LIC-2026-001 has been approved.",
      "is_read": false,
      "read_at": null,
      "status": "SENT",
      "related_object_type": "licence",
      "related_object_id": "550e8400-e29b-41d4-a716-446655440000",
      "created_at": "2026-03-20T14:30:00Z"
    },
    {
      "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      "notification_type": "IN_APP",
      "title": "Complaint Updated",
      "message": "Your complaint has been assigned to an investigator.",
      "is_read": true,
      "read_at": "2026-03-20T15:00:00Z",
      "status": "SENT",
      "related_object_type": "complaint",
      "related_object_id": "660e8400-e29b-41d4-a716-446655440001",
      "created_at": "2026-03-19T09:00:00Z"
    }
  ],
  "errors": null
}
```

---

### GET `/unread-count/`

Quick badge count for the UI.

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Unread count retrieved.",
  "data": {
    "unread_count": 3
  },
  "errors": null
}
```

---

### PATCH `/{id}/read/`

Mark a single notification as read. Sets `is_read=true` and `read_at` to the current time. Only the notification owner can perform this action.

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Notification marked as read.",
  "data": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "notification_type": "IN_APP",
    "title": "Licence Application Approved",
    "message": "Your licence application #LIC-2026-001 has been approved.",
    "is_read": true,
    "read_at": "2026-03-20T15:05:00Z",
    "status": "SENT",
    "related_object_type": "licence",
    "related_object_id": "550e8400-e29b-41d4-a716-446655440000",
    "created_at": "2026-03-20T14:30:00Z"
  },
  "errors": null
}
```

**Error `404`** — notification not found or not owned by the requesting user

---

### PATCH `/read-all/`

Mark all unread notifications as read in a single bulk operation.

**Response `200 OK`**

```json
{
  "success": true,
  "message": "3 notification(s) marked as read.",
  "data": {
    "marked_read": 3
  },
  "errors": null
}
```

---

### DELETE `/{id}/`

Permanently delete (dismiss) a notification. Only the notification owner can dismiss it.

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Notification dismissed.",
  "data": null,
  "errors": null
}
```

**Error `404`** — notification not found or not owned by the requesting user

---

## Creating Notifications (Backend)

Other apps create notifications using the `notify_user()` utility:

```python
from notifications.utils import notify_user

notify_user(
    recipient=user,
    title="Licence Approved",
    message="Your licence application has been approved.",
    related_object_type="licence",
    related_object_id=licence.pk,
)
```

| Parameter | Required | Type | Notes |
|---|---|---|---|
| `recipient` | Yes | User | The user to notify |
| `title` | Yes | string | Short title |
| `message` | Yes | string | Notification body |
| `related_object_type` | No | string | E.g. `"licence"`, `"complaint"` |
| `related_object_id` | No | UUID | ID of the related object |
| `notification_type` | No | string | Default: `"IN_APP"` |

---

## Enums & Reference

### NotificationType

| Value | Label | MVP |
|---|---|---|
| `IN_APP` | In-App | Yes |
| `EMAIL` | Email | Planned |
| `SMS` | SMS | Planned |

### NotificationStatus

| Value | Label |
|---|---|
| `PENDING` | Pending |
| `SENT` | Sent |
| `READ` | Read |
| `FAILED` | Failed |
