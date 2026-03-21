# System Architecture

> BOCRA Digital Platform — Architecture Documentation

## Table of Contents

- [Architecture Philosophy](#architecture-philosophy)
- [High-Level System Diagram](#high-level-system-diagram)
- [Layer Breakdown](#layer-breakdown)
- [Django App Structure](#django-app-structure)
- [Communication Flows](#communication-flows)
- [Authentication Flow](#authentication-flow)
- [Data Flow](#data-flow)
- [Infrastructure Overview](#infrastructure-overview)

---

## Architecture Philosophy

The platform is built **API-first**. Django + DRF is the single backend serving all data. The React/Next.js frontend is one consumer of these APIs — but the APIs are designed to be reusable so other platforms (mobile apps, third-party integrations, future BOCRA products) can be built on top without touching the backend.

**Every feature is an API endpoint first. The frontend is just one client.**

This is the key differentiator from the current Drupal setup, where business logic is tightly coupled to the presentation layer.

### Design Principles

1. **API-First** — Build the API, then build clients on top
2. **Separation of Concerns** — Backend handles business logic, frontend handles presentation
3. **Modular Design** — Each Django app owns its domain completely
4. **Stateless Auth** — JWT tokens, no server-side sessions for API consumers
5. **Convention over Configuration** — Consistent patterns across all modules
6. **12-Factor App** — Environment-based config, containerised, disposable processes

---

## High-Level System Diagram

```
                    ┌──────────────────────────────────────────┐
                    │              LOAD BALANCER                │
                    │           (Nginx / Cloud LB)             │
                    └──────┬──────────────┬────────────────────┘
                           │              │
              ┌────────────▼───┐   ┌──────▼──────────────┐
              │   Next.js 14   │   │   React Admin SPA   │
              │  (Public Site) │   │   (Staff Portal)    │
              │   SSR + CSR    │   │      CSR only       │
              └────────┬───────┘   └──────┬──────────────┘
                       │                  │
                       ▼                  ▼
              ┌────────────────────────────────────────────┐
              │          DJANGO + DRF API SERVER            │
              │                                            │
              │  ┌──────────┐  ┌───────────┐  ┌─────────┐│
              │  │ accounts │  │ licensing │  │complaints││
              │  └──────────┘  └───────────┘  └─────────┘│
              │  ┌──────────┐  ┌───────────┐  ┌─────────┐│
              │  │  news    │  │publications│  │ tenders ││
              │  └──────────┘  └───────────┘  └─────────┘│
              │  ┌──────────┐  ┌───────────┐  ┌─────────┐│
              │  │analytics │  │   core    │  │  notif  ││
              │  └──────────┘  └───────────┘  └─────────┘│
              │                                            │
              │  JWT Auth │ RBAC │ Filtering │ Pagination  │
              └──┬─────┬──────┬────────────┬──────────────┘
                 │     │      │            │
          ┌──────▼┐ ┌──▼───┐ ┌▼────────┐ ┌▼───────────┐
          │Postgres│ │Redis │ │S3/MinIO │ │   Celery   │
          │  16   │ │      │ │  Files  │ │  Workers   │
          └───────┘ └──┬───┘ └─────────┘ └──────┬─────┘
                       │                         │
                       └─────────┬───────────────┘
                                 │
                       ┌─────────▼──────────┐
                       │  Django Channels   │
                       │   (WebSockets)     │
                       │  Live Dashboards   │
                       └────────────────────┘
```

---

## Layer Breakdown

### Presentation Layer (Clients)

| Client | Technology | Purpose | Rendering |
|---|---|---|---|
| Public Website | Next.js 14 | Citizen-facing site — info, publications, portals | SSR/SSG for SEO + CSR for interactivity |
| Admin Portal | React SPA | Staff portal — case management, content admin | Client-side only (behind auth) |
| Mobile App | Future | React Native / Flutter | Post-hackathon |

### API Layer (Django + DRF)

The API layer is the heart of the system. It handles:

- **Request routing** — URL patterns map to viewsets
- **Authentication** — JWT token validation on every request
- **Authorization** — RBAC permission checks per endpoint
- **Serialization** — Model ↔ JSON transformation with validation
- **Business logic** — Application workflows, status transitions, notifications
- **Filtering & pagination** — Consistent query param handling across all endpoints

### Data Layer

| Component | Role | Details |
|---|---|---|
| PostgreSQL 16 | Primary data store | All relational data — users, licences, complaints, content |
| Redis | Cache + broker | API response caching, session data, Celery message broker |
| S3 / MinIO | File storage | Document uploads, licence certificates, publication PDFs |

### Background Processing

| Component | Role | Details |
|---|---|---|
| Celery | Task queue | Async tasks — email sending, PDF generation, report building |
| Redis | Broker | Message broker for Celery task distribution |
| Celery Beat | Scheduler | Periodic tasks — licence expiry alerts, SLA checks |

### Real-Time Layer

| Component | Role | Details |
|---|---|---|
| Django Channels | WebSocket server | Bi-directional real-time communication |
| Redis | Channel layer | Pub/sub backend for Channels |
| Use cases | — | Live dashboard updates, complaint status changes, QoS monitoring |

---

## Django App Structure

Each Django app is a self-contained module owning its domain:

```
apps/
├── accounts/           # User management, authentication, roles
│   ├── models.py       # User, Role, Profile
│   ├── serializers.py  # Registration, Login, Profile serializers
│   ├── views.py        # Auth viewsets, user management
│   ├── permissions.py  # Custom RBAC permission classes
│   ├── urls.py         # /api/v1/accounts/...
│   ├── admin.py        # Django Admin customisation
│   ├── signals.py      # Post-registration email, profile creation
│   └── tests/          # Unit + integration tests
│
├── licensing/          # Licence applications, renewals, verification
│   ├── models.py       # Licence, Application, LicenceType
│   ├── serializers.py  # Application form, status update serializers
│   ├── views.py        # CRUD + workflow endpoints
│   ├── services.py     # Business logic — status transitions, PDF gen
│   ├── urls.py         # /api/v1/licensing/...
│   └── tests/
│
├── complaints/         # Complaints & case management
│   ├── models.py       # Complaint, Case, CaseNote, Resolution
│   ├── serializers.py  # Submission, tracking, staff management
│   ├── views.py        # Public submission + staff case management
│   ├── services.py     # Reference number generation, SLA tracking
│   ├── urls.py         # /api/v1/complaints/...
│   └── tests/
│
├── publications/       # Documents, regulations, policies
│   ├── models.py       # Publication, Category, Document
│   ├── views.py        # Public CRUD with filtering
│   └── ...
│
├── tenders/            # Tender listings & management
│   ├── models.py       # Tender, TenderDocument
│   ├── views.py        # Public listings + admin management
│   └── ...
│
├── news/               # News articles, announcements
│   ├── models.py       # Article, Category, Author
│   ├── views.py        # Public news feed + admin publishing
│   └── ...
│
├── analytics/          # QoS data, telecoms stats, dashboards
│   ├── models.py       # QoSRecord, TelecomsStat, NetworkOperator
│   ├── views.py        # Aggregated data endpoints for charts
│   └── ...
│
├── notifications/      # Email, SMS, in-app dispatch
│   ├── models.py       # Notification, NotificationTemplate
│   ├── tasks.py        # Celery tasks for async dispatch
│   └── ...
│
└── core/               # Shared utilities & base models
    ├── models.py       # BaseModel (UUID, timestamps, soft delete)
    ├── mixins.py       # AuditMixin, PaginationMixin
    ├── permissions.py  # Shared permission classes
    ├── pagination.py   # Standard pagination class
    ├── renderers.py    # Consistent JSON response envelope
    ├── middleware.py    # Request logging, CORS, security headers
    └── utils.py        # Shared helper functions
```

### App Responsibilities

| App | Owns | Key Models | API Prefix |
|---|---|---|---|
| `accounts` | User management, auth, roles, profiles | User, Role, Profile, Permission | `/api/v1/accounts/` |
| `licensing` | Licence applications, renewals, verification | Licence, Application, LicenceType, ApplicationStatus | `/api/v1/licensing/` |
| `complaints` | Complaint submission, case tracking, resolution | Complaint, Case, CaseNote, Resolution | `/api/v1/complaints/` |
| `publications` | Documents, regulations, policies, reports | Publication, Category, Tag, Document | `/api/v1/publications/` |
| `tenders` | Tender listings, submissions, status tracking | Tender, TenderDocument, TenderSubmission | `/api/v1/tenders/` |
| `news` | News articles, press releases, announcements | Article, Category, Author | `/api/v1/news/` |
| `analytics` | QoS data, telecoms stats, dashboards | QoSRecord, TelecomsStat, NetworkOperator | `/api/v1/analytics/` |
| `notifications` | Email, SMS, in-app notification dispatch | Notification, NotificationTemplate | Internal (no public API) |
| `core` | Shared utilities, base models, middleware | BaseModel, AuditLog, SiteSettings | Shared across all apps |

---

## Communication Flows

### Synchronous Request Flow

```
Client Request
    │
    ▼
Nginx (Reverse Proxy)
    │
    ▼
Django Middleware Stack
    │  → SecurityMiddleware
    │  → CorsMiddleware
    │  → AuthenticationMiddleware (JWT)
    │  → RequestLoggingMiddleware
    │
    ▼
DRF Router → ViewSet
    │  → Permission Check (RBAC)
    │  → Serializer Validation
    │  → Business Logic
    │  → Database Query (ORM)
    │
    ▼
JSON Response (Standard Envelope)
    │
    ▼
Client
```

### Asynchronous Task Flow (Celery)

```
API Endpoint
    │
    ▼
Trigger Celery Task (.delay())
    │
    ▼
Redis (Message Broker)
    │
    ▼
Celery Worker Picks Up Task
    │  → Send Email
    │  → Generate PDF
    │  → Update Analytics
    │
    ▼
Task Complete (Result in Redis)
```

### Real-Time WebSocket Flow

```
Client (Browser)
    │
    ▼
WebSocket Connection
    │
    ▼
Django Channels (ASGI)
    │
    ▼
Channel Layer (Redis)
    │
    ▼
Consumer Group
    │  → Dashboard updates
    │  → Complaint status changes
    │  → QoS metric streams
    │
    ▼
Push to Connected Clients
```

---

## Authentication Flow

### Registration

```
1. POST /api/v1/accounts/register/
   Body: { email, password, first_name, last_name }
   
2. Server creates User (is_active=True, email_verified=False)

3. Celery sends verification email with token link

4. User clicks link → GET /api/v1/accounts/verify-email/?token=xxx

5. Server sets email_verified=True

6. User can now login
```

### Login

```
1. POST /api/v1/accounts/login/
   Body: { email, password }

2. Server validates credentials + checks email_verified

3. Response: {
     access_token: "eyJ..."   (15 min expiry)
     refresh_token: "eyJ..."  (7 day expiry)
   }

4. Client stores tokens, includes in all requests:
   Authorization: Bearer <access_token>
```

### Token Refresh

```
1. Access token expires (15 min)

2. POST /api/v1/accounts/token/refresh/
   Body: { refresh: "eyJ..." }

3. Response: {
     access: "new_eyJ..."
   }
```

---

## Data Flow

### Licence Application Flow

```
Citizen                          API                         Staff
  │                               │                            │
  │  POST /applications/          │                            │
  │  (form data + documents)      │                            │
  │──────────────────────────────▶│                            │
  │                               │  Create Application        │
  │                               │  Status: SUBMITTED         │
  │                               │  Generate ref number       │
  │                               │  Send confirmation email   │
  │  ◀──────────────────────────  │                            │
  │  { ref: "LIC-2026-001" }     │                            │
  │                               │                            │
  │                               │  GET /applications/        │
  │                               │  (staff queue)             │
  │                               │  ◀─────────────────────────│
  │                               │                            │
  │                               │  PATCH /applications/1/    │
  │                               │  status → UNDER_REVIEW     │
  │                               │  ◀─────────────────────────│
  │                               │  Send status email ──────▶ │
  │  ◀── email notification ──── │                            │
  │                               │                            │
  │                               │  PATCH /applications/1/    │
  │                               │  status → APPROVED         │
  │                               │  Generate PDF certificate  │
  │                               │  ◀─────────────────────────│
  │  ◀── approval email ──────── │                            │
  │                               │                            │
  │  GET /licences/1/certificate/ │                            │
  │──────────────────────────────▶│                            │
  │  ◀── PDF download ────────── │                            │
```

### Complaint Flow

```
Citizen                          API                         Staff
  │                               │                            │
  │  POST /complaints/            │                            │
  │  (category, description,      │                            │
  │   against_licensee, evidence) │                            │
  │──────────────────────────────▶│                            │
  │                               │  Create Complaint          │
  │                               │  Status: SUBMITTED         │
  │                               │  Ref: CMP-2026-001234     │
  │  ◀──────────────────────────  │                            │
  │                               │                            │
  │  GET /complaints/track/       │                            │
  │  ?ref=CMP-2026-001234        │                            │
  │──────────────────────────────▶│                            │
  │  ◀── status + timeline ───── │                            │
  │                               │                            │
  │                               │  PATCH /complaints/1/      │
  │                               │  assigned_to → staff_user  │
  │                               │  status → ASSIGNED         │
  │                               │  ◀─────────────────────────│
  │                               │                            │
  │                               │  POST /complaints/1/notes/ │
  │                               │  (internal investigation)  │
  │                               │  ◀─────────────────────────│
  │                               │                            │
  │                               │  POST /complaints/1/resolve│
  │                               │  (formal resolution)       │
  │                               │  ◀─────────────────────────│
  │  ◀── resolution email ────── │                            │
```

---

## Infrastructure Overview

### Development Environment

All services run directly on your machine:

| Service | How to Run |
|---|---|
| Django API | `python manage.py runserver` |
| PostgreSQL 16 | Local install or `brew install postgresql` |
| Redis | Local install: `redis-server` |
| Celery worker | `celery -A bocra_backend worker -l info` |
| Celery beat | `celery -A bocra_backend beat -l info` |

### Production Environment (AWS EC2)

```
┌──────────────────────────────────────────────┐
│                AWS EC2 Instance               │
│            (Ubuntu 22.04 LTS)                │
│                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │  Django   │  │ Postgres │  │  Redis   │  │
│  │ (Gunicorn)│  │   (DB)   │  │ (Cache)  │  │
│  └──────────┘  └──────────┘  └──────────┘  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │  Celery  │  │   S3     │  │  Nginx   │  │
│  │ (Worker) │  │ (Files)  │  │ (Proxy)  │  │
│  └──────────┘  └──────────┘  └──────────┘  │
│                                              │
│  HTTPS via Certbot │ systemd process manager │
└──────────────────────────────────────────────┘
```

### Key Environment Boundaries

| Concern | Development | Production |
|---|---|---|
| Database | Local PostgreSQL | EC2 PostgreSQL or AWS RDS |
| File Storage | AWS S3 (dev bucket) | AWS S3 (production bucket) |
| Email | Console backend (prints to terminal) | SMTP / SendGrid |
| Debug | DEBUG=True | DEBUG=False |
| HTTPS | Not required | Enforced via Certbot + Nginx |
| Static Files | Django dev server | Nginx serves from `/staticfiles/` |

---

*BOCRA Digital Platform Architecture — v1.0 — March 2026*
