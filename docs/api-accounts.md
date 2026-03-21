# Accounts API

> Base URL: `/api/v1/accounts/`  
> Swagger tags: **Auth** · **Profile** · **Admin — Users**

Handles user registration, email verification, authentication (JWT), password management, profile editing, and admin user management.

---

## Table of Contents

- [Endpoints Summary](#endpoints-summary)
- [Auth — Registration & Verification](#auth--registration--verification)
- [Auth — Login & Token Management](#auth--login--token-management)
- [Auth — Password](#auth--password)
- [Profile](#profile)
- [Admin — User Management](#admin--user-management)

---

## Endpoints Summary

### Auth

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/register/` | Register a new user account | Public |
| `GET` | `/verify-email/?token=` | Verify email address via token | Public |
| `POST` | `/resend-verification/` | Resend email verification link | Public |
| `POST` | `/login/` | Authenticate and obtain JWT tokens | Public |
| `POST` | `/logout/` | Blacklist refresh token and log out | Registered |
| `POST` | `/token/refresh/` | Refresh expired access token | Public |
| `POST` | `/password-reset/` | Request a password reset email | Public |
| `POST` | `/password-reset/confirm/` | Confirm password reset with uid and token | Public |
| `POST` | `/change-password/` | Change password for authenticated user | Registered |

### Profile

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/profile/` | Retrieve current user profile | Registered |
| `PATCH` | `/profile/` | Update profile and personal details | Registered |

### Admin — Users

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/users/` | List all users | Admin |
| `GET` | `/users/{id}/` | Retrieve a user by ID | Admin |
| `PATCH` | `/users/{id}/` | Update user role or active status | Admin |

---

## Auth — Registration & Verification

### POST `/register/`

Register a new user account. Sends an email verification link after successful registration.

**Request body**

```json
{
  "email": "user@example.com",
  "username": "jsmith",
  "password": "SecurePass123!",
  "confirm_password": "SecurePass123!",
  "first_name": "John",
  "last_name": "Smith",
  "phone_number": "+26771234567",
  "id_number": "123456789"
}
```

| Field | Required | Notes |
|---|---|---|
| `email` | Yes | Must be unique; normalised to lowercase |
| `username` | Yes | Alphanumeric only; must be unique |
| `password` | Yes | Min 8 characters; Django password validators apply |
| `confirm_password` | Yes | Must match `password` |
| `first_name` | No | |
| `last_name` | No | |
| `phone_number` | No | Botswana numbers accepted (`+26771234567` or `71234567`) |
| `id_number` | No | Botswana Omang or passport number |

**Response `201 Created`**

```json
{
  "success": true,
  "message": "Registration successful. Please check your email to verify your account.",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "username": "jsmith"
  },
  "errors": null
}
```

**Error `400 Bad Request`** (validation failure)

```json
{
  "success": false,
  "message": "Validation failed",
  "data": null,
  "errors": {
    "email": ["An account with this email already exists."],
    "username": ["This username is already taken."]
  }
}
```

---

### GET `/verify-email/?token=<token>`

Verify a user's email address using the token sent in the registration email. The token is a one-time use signed value.

**Query parameters**

| Param | Required | Description |
|---|---|---|
| `token` | Yes | Signed verification token from email link |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Email verified successfully.",
  "data": null,
  "errors": null
}
```

**Error `400`** — token invalid or already used  
**Error `404`** — user not found for token

---

### POST `/resend-verification/`

Resend the email verification link to an unverified account.

**Request body**

```json
{ "email": "user@example.com" }
```

**Response `200 OK`** (always succeeds to avoid account enumeration)

```json
{
  "success": true,
  "message": "If this email is registered and unverified, a new verification link has been sent.",
  "data": null,
  "errors": null
}
```

---

## Auth — Login & Token Management

### POST `/login/`

Authenticate with email/username and password. Returns a JWT access token (15-minute expiry) and refresh token (7-day expiry).

**Request body**

```json
{
  "identifier": "user@example.com",
  "password": "SecurePass123!",
  "remember_me": false
}
```

| Field | Required | Notes |
|---|---|---|
| `identifier` | Yes | Email address or username |
| `password` | Yes | |
| `remember_me` | No | Extends refresh token to 30 days when `true` |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Login successful.",
  "data": {
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "user@example.com",
      "username": "jsmith",
      "full_name": "John Smith",
      "role": "REGISTERED",
      "role_display": "Registered User",
      "email_verified": true
    }
  },
  "errors": null
}
```

**Error `401`** — invalid credentials  
**Error `403`** — account locked  
**Error `403`** — email not verified

---

### POST `/logout/`

Blacklist the refresh token, invalidating the session. The access token expires naturally (15 min).

**Auth**: `Authorization: Bearer <access_token>`

**Request body**

```json
{ "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." }
```

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Logged out successfully.",
  "data": null,
  "errors": null
}
```

---

### POST `/token/refresh/`

Exchange a valid refresh token for a new access token.

**Request body**

```json
{ "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." }
```

**Response `200 OK`**

```json
{ "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." }
```

**Error `401`** — refresh token expired or blacklisted

---

## Auth — Password

### POST `/password-reset/`

Send a password reset link to the registered email address.

**Request body**

```json
{ "email": "user@example.com" }
```

**Response `200 OK`** (always succeeds to avoid enumeration)

```json
{
  "success": true,
  "message": "If an account with this email exists, a password reset link has been sent.",
  "data": null,
  "errors": null
}
```

---

### POST `/password-reset/confirm/`

Set a new password using the `uid` and `token` from the reset email link.

**Request body**

```json
{
  "uid": "Mg",
  "token": "6gm-abc1234567890abcdef",
  "new_password": "NewSecurePass456!"
}
```

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Password has been reset successfully.",
  "data": null,
  "errors": null
}
```

**Error `400`** — invalid or expired token

---

### POST `/change-password/`

Change the authenticated user's password. Requires the current password for verification.

**Auth**: `Authorization: Bearer <access_token>`

**Request body**

```json
{
  "old_password": "CurrentPass123!",
  "new_password": "NewSecurePass456!",
  "confirm_new_password": "NewSecurePass456!"
}
```

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Password changed successfully.",
  "data": null,
  "errors": null
}
```

**Error `400`** — old password incorrect or new passwords do not match

---

## Profile

### GET `/profile/`

Retrieve the authenticated user's full profile including personal details and embedded profile record.

**Auth**: `Authorization: Bearer <access_token>`

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Profile retrieved.",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "username": "jsmith",
    "first_name": "John",
    "last_name": "Smith",
    "full_name": "John Smith",
    "phone_number": "+26771234567",
    "id_number": "123456789",
    "role": "REGISTERED",
    "role_display": "Registered User",
    "email_verified": true,
    "is_active": true,
    "is_locked": false,
    "date_joined": "2026-01-15T10:30:00Z",
    "last_login": "2026-03-20T09:15:00Z",
    "profile": {
      "organisation": "ACME Corp",
      "position": "Director",
      "date_of_birth": "1985-06-20",
      "gender": "M",
      "bio": "",
      "address": "Plot 123, Main Mall",
      "city": "Gaborone",
      "postal_code": "0001",
      "country": "BW",
      "id_number": "123456789",
      "avatar": null,
      "age": 40,
      "is_complete": true
    }
  },
  "errors": null
}
```

---

### PATCH `/profile/`

Update the authenticated user's profile. All fields are optional (partial update).

**Auth**: `Authorization: Bearer <access_token>`

**Request body** (any subset of fields)

```json
{
  "first_name": "John",
  "last_name": "Smith",
  "phone_number": "+26771234567",
  "profile": {
    "organisation": "ACME Corp",
    "position": "Director",
    "date_of_birth": "1985-06-20",
    "gender": "M",
    "address": "Plot 123, Main Mall",
    "city": "Gaborone",
    "postal_code": "0001",
    "country": "BW"
  }
}
```

**Response `200 OK`** — returns full updated user object (same shape as GET `/profile/`)

---

## Admin — User Management

> All endpoints in this section require `Admin` or `SuperAdmin` role.

### GET `/users/`

List all registered users with lightweight fields. Supports filtering and ordering.

**Auth**: `Authorization: Bearer <access_token>` (Admin)

**Query parameters**

| Param | Description |
|---|---|
| `search` | Search by email, username, or name |
| `role` | Filter by role: `REGISTERED`, `STAFF`, `ADMIN`, `SUPERADMIN` |
| `is_active` | Filter by active status: `true` / `false` |
| `ordering` | Sort by: `date_joined`, `email`, `-date_joined` |
| `page` | Page number (default: 1) |
| `page_size` | Results per page (default: 20, max: 100) |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Users retrieved.",
  "data": {
    "count": 42,
    "next": "/api/v1/accounts/users/?page=2",
    "previous": null,
    "results": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "email": "user@example.com",
        "username": "jsmith",
        "full_name": "John Smith",
        "role": "REGISTERED",
        "role_display": "Registered User",
        "email_verified": true,
        "is_active": true,
        "date_joined": "2026-01-15T10:30:00Z"
      }
    ]
  },
  "errors": null
}
```

---

### GET `/users/{id}/`

Retrieve full details for a specific user by UUID.

**Auth**: `Authorization: Bearer <access_token>` (Admin)

**Response `200 OK`** — same shape as GET `/profile/` but for any user  
**Error `404`** — user not found

---

### PATCH `/users/{id}/`

Update a user's role, active status, or other admin-managed fields.

**Auth**: `Authorization: Bearer <access_token>` (Admin)

**Request body** (any subset)

```json
{
  "role": "STAFF",
  "is_active": true
}
```

**Role values**

| Value | Description |
|---|---|
| `REGISTERED` | Standard registered citizen |
| `STAFF` | BOCRA staff member |
| `ADMIN` | BOCRA administrator |
| `SUPERADMIN` | Superadministrator (full access) |

**Response `200 OK`** — returns updated user object  
**Error `400`** — invalid role value  
**Error `403`** — cannot escalate to `SUPERADMIN` unless caller is also `SUPERADMIN`  
**Error `404`** — user not found

---

*BOCRA Digital Platform — Accounts API — v1.0*
