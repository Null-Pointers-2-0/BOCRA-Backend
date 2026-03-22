# News API

> Base URL: `/api/v1/news/`  
> Swagger tags: **News — Public** · **News — Staff**

Manages press releases, announcements, events, and regulatory update articles. Staff create and manage articles through a draft → publish → archive lifecycle. The public can browse published articles.

---

## Table of Contents

- [Endpoints Summary](#endpoints-summary)
- [Lifecycle](#lifecycle)
- [Public — Browse Articles](#public--browse-articles)
- [Staff — Create & Manage](#staff--create--manage)
- [Enums & Reference](#enums--reference)

---

## Endpoints Summary

### Public

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/categories/` | List news categories | Public |
| `GET` | `/` | List published articles | Public |
| `GET` | `/{id}/` | Article detail (increments view count) | Public |

### Staff

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/staff/` | Create new article (draft) | Staff |
| `GET` | `/staff/list/` | List all articles (inc. drafts) | Staff |
| `GET` | `/staff/{id}/` | Full article detail (staff) | Staff |
| `PATCH` | `/staff/{id}/edit/` | Update article fields | Staff |
| `PATCH` | `/staff/{id}/publish/` | Publish a draft | Staff |
| `PATCH` | `/staff/{id}/archive/` | Archive an article | Staff |
| `DELETE` | `/staff/{id}/delete/` | Soft-delete an article | Staff |

---

## Lifecycle

Articles follow a simple state model:

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
- **PUBLISHED**: Visible in public listings. `published_at` is auto-set.
- **ARCHIVED**: Removed from public view. Cannot be re-published directly.

---

## Public — Browse Articles

### GET `/categories/`

Returns all available news categories.

**Response `200 OK`**

```json
{
  "success": true,
  "message": "News categories retrieved.",
  "data": [
    { "value": "PRESS_RELEASE", "label": "Press Release" },
    { "value": "ANNOUNCEMENT", "label": "Announcement" },
    { "value": "EVENT", "label": "Event" },
    { "value": "REGULATORY_UPDATE", "label": "Regulatory Update" },
    { "value": "OTHER", "label": "Other" }
  ],
  "errors": null
}
```

---

### GET `/`

Browse published news articles. Only `PUBLISHED` status items are returned.

**Query parameters**

| Param | Type | Description |
|---|---|---|
| `category` | string | Filter by category (e.g. `PRESS_RELEASE`) |
| `is_featured` | boolean | Filter featured articles |
| `search` | string | Search title and excerpt |
| `ordering` | string | Sort by `published_at`, `title`, `view_count`, `created_at` (prefix `-` for descending) |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Articles retrieved.",
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "BOCRA Awards New Spectrum Licences",
      "slug": "bocra-awards-new-spectrum-licences",
      "excerpt": "BOCRA has awarded new broadband spectrum licences to three operators...",
      "category": "PRESS_RELEASE",
      "category_display": "Press Release",
      "author_name": "Kago Mosweu",
      "featured_image": "/media/news/images/spectrum-award.jpg",
      "published_at": "2026-03-20T10:00:00Z",
      "is_featured": true,
      "view_count": 245
    }
  ],
  "errors": null
}
```

---

### GET `/{id}/`

Full article detail including content. Increments view counter atomically.

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Article retrieved.",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "BOCRA Awards New Spectrum Licences",
    "slug": "bocra-awards-new-spectrum-licences",
    "excerpt": "BOCRA has awarded new broadband spectrum licences to three operators...",
    "content": "<p>Full HTML content of the article...</p>",
    "category": "PRESS_RELEASE",
    "category_display": "Press Release",
    "author_name": "Kago Mosweu",
    "featured_image": "/media/news/images/spectrum-award.jpg",
    "published_at": "2026-03-20T10:00:00Z",
    "is_featured": true,
    "view_count": 246,
    "created_at": "2026-03-19T14:00:00Z"
  },
  "errors": null
}
```

**Error `404`** — article not found or not in `PUBLISHED` status

---

## Staff — Create & Manage

> All staff endpoints require a valid JWT token from a user with **Staff** role or above.

### POST `/staff/`

Create a new article in `DRAFT` status.

**Request body** (`multipart/form-data` or JSON)

```json
{
  "title": "New Cybersecurity Guidelines Released",
  "excerpt": "BOCRA publishes updated cybersecurity guidelines for telecom operators.",
  "content": "<p>Full article content...</p>",
  "category": "REGULATORY_UPDATE",
  "featured_image": "<binary>",
  "is_featured": false
}
```

| Field | Required | Type | Notes |
|---|---|---|---|
| `title` | Yes | string | Max 300 characters |
| `excerpt` | No | string | Short summary for listing views |
| `content` | No | text | Supports HTML or Markdown |
| `category` | Yes | string | One of the category enum values |
| `featured_image` | No | image | JPEG, PNG, etc. |
| `is_featured` | No | boolean | Default: `false` |

**Response `201 Created`** — Returns full staff detail serializer

```json
{
  "success": true,
  "message": "Article created successfully.",
  "data": {
    "id": "...",
    "title": "New Cybersecurity Guidelines Released",
    "slug": "new-cybersecurity-guidelines-released",
    "status": "DRAFT",
    "status_display": "Draft",
    "..."
  },
  "errors": null
}
```

---

### GET `/staff/list/`

List all articles including drafts and archived. Supports filtering and search.

**Query parameters**

| Param | Type | Description |
|---|---|---|
| `category` | string | Filter by category |
| `status` | string | Filter by status (`DRAFT`, `PUBLISHED`, `ARCHIVED`) |
| `is_featured` | boolean | Filter featured |
| `search` | string | Search title and excerpt |
| `ordering` | string | Sort by `published_at`, `title`, `created_at`, `status` |

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Articles retrieved.",
  "data": [
    {
      "id": "...",
      "title": "New Cybersecurity Guidelines Released",
      "slug": "new-cybersecurity-guidelines-released",
      "category": "REGULATORY_UPDATE",
      "category_display": "Regulatory Update",
      "status": "DRAFT",
      "status_display": "Draft",
      "author_name": "Kago Mosweu",
      "published_at": null,
      "is_featured": false,
      "view_count": 0,
      "created_at": "2026-03-20T10:00:00Z"
    }
  ],
  "errors": null
}
```

---

### GET `/staff/{id}/`

Full article detail including audit info.

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Article retrieved.",
  "data": {
    "id": "...",
    "title": "New Cybersecurity Guidelines Released",
    "slug": "new-cybersecurity-guidelines-released",
    "excerpt": "...",
    "content": "<p>Full content...</p>",
    "category": "REGULATORY_UPDATE",
    "category_display": "Regulatory Update",
    "status": "DRAFT",
    "status_display": "Draft",
    "author_name": "Kago Mosweu",
    "featured_image": null,
    "published_at": null,
    "is_featured": false,
    "view_count": 0,
    "created_by_name": "Kago Mosweu",
    "created_at": "2026-03-20T10:00:00Z",
    "updated_at": "2026-03-20T10:00:00Z"
  },
  "errors": null
}
```

---

### PATCH `/staff/{id}/edit/`

Update article fields. Only provided fields are changed.

**Request body** (partial update)

```json
{
  "title": "Updated Title",
  "is_featured": true
}
```

**Response `200 OK`** — Returns updated staff detail

---

### PATCH `/staff/{id}/publish/`

Transition an article from `DRAFT` to `PUBLISHED`. Automatically sets `published_at` to current time.

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Article published.",
  "data": {
    "id": "...",
    "status": "PUBLISHED",
    "published_at": "2026-03-20T14:30:00Z",
    "..."
  },
  "errors": null
}
```

**Error `400`** — Article is not in `DRAFT` status

---

### PATCH `/staff/{id}/archive/`

Transition an article to `ARCHIVED` status. Works from `DRAFT` or `PUBLISHED`.

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Article archived.",
  "data": { "...": "..." },
  "errors": null
}
```

**Error `400`** — Article is already `ARCHIVED`

---

### DELETE `/staff/{id}/delete/`

Soft-delete an article. Sets `is_deleted=True`. The article will no longer appear in any listing.

**Response `200 OK`**

```json
{
  "success": true,
  "message": "Article deleted.",
  "data": null,
  "errors": null
}
```

---

## Enums & Reference

### NewsCategory

| Value | Label |
|---|---|
| `PRESS_RELEASE` | Press Release |
| `ANNOUNCEMENT` | Announcement |
| `EVENT` | Event |
| `REGULATORY_UPDATE` | Regulatory Update |
| `OTHER` | Other |

### ArticleStatus

| Value | Label |
|---|---|
| `DRAFT` | Draft |
| `PUBLISHED` | Published |
| `ARCHIVED` | Archived |
