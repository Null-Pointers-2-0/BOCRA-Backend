# BOCRA Digital Platform — Backend

> A unified, API-first web platform built to replace BOCRA's fragmented digital infrastructure.

**BOCRA Youth Hackathon — Website Development Challenge**

| Field | Detail |
|---|---|
| Hackathon | BOCRA Youth Hackathon — BOCRA Website Development |
| Submission Deadline | **27 March 2026 \| 17:00hrs CAT** |
| Backend Stack | Django 5.x + Django REST Framework (DRF) |
| Frontend Stack | React / Next.js (separate repo) |
| Database | PostgreSQL 16 |
| Deployment | AWS EC2 + Gunicorn + Nginx |

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Running Locally](#running-locally)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Platform Modules](#platform-modules)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [Submission Checklist](#submission-checklist)

---

## Overview

BOCRA (Botswana Communications Regulatory Authority) currently operates a Drupal-based website bolted onto separate ASP.NET portals for licensing, spectrum management, and domain registration. These systems do not communicate with each other, creating a fragmented experience for citizens, licensees, and BOCRA staff.

This project replaces that with a **single, integrated, API-driven platform** covering all of BOCRA's digital touchpoints — accessible, mobile-first, and built to scale.

### What This Platform Does

- **Public Website** — Information, publications, news, tenders, consumer resources
- **Licensing Portal** — Online licence applications, renewals, tracking, verification
- **Complaints System** — Submit, track, and manage complaints with full case lifecycle
- **Analytics Dashboard** — QoS metrics, telecoms stats, real-time regulatory data
- **Admin Portal** — Internal content management, case queues, user administration
- **Unified Auth** — Single sign-on with JWT + role-based access control

---

## Architecture

The platform is built **API-first**. Django + DRF is the single backend serving all data. The frontend is one consumer of these APIs — but the APIs are designed to be reusable for mobile apps, third-party integrations, and future BOCRA products.

```
┌─────────────────────────────────────────────────────────┐
│                      Clients                            │
│  Next.js (Public)  │  React (Admin)  │  Mobile (Future) │
└────────┬───────────┴────────┬────────┴────────┬─────────┘
         │                    │                  │
         ▼                    ▼                  ▼
┌─────────────────────────────────────────────────────────┐
│                   Django + DRF API                       │
│  /api/v1/accounts/  /api/v1/licensing/  /api/v1/...     │
├─────────────────────────────────────────────────────────┤
│  JWT Auth  │  RBAC  │  Filtering  │  Pagination         │
├─────────────────────────────────────────────────────────┤
│  Celery (Background Tasks)  │  Channels (WebSockets)    │
└────────┬───────────┬────────┴───────────────────────────┘
         │           │
    ┌────▼──┐   ┌────▼──┐   ┌────────┐
    │ Postgres│   │ Redis │   │ S3/MinIO│
    └────────┘   └───────┘   └────────┘
```

> Full architecture documentation: [docs/architecture.md](docs/architecture.md)

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Framework | Django 5.x | Core web framework |
| API | Django REST Framework 3.15.x | REST API toolkit |
| Auth | SimpleJWT | JWT access + refresh tokens |
| Database | PostgreSQL 16 | Primary data store |
| Cache / Broker | Redis | Caching + Celery broker |
| Background Tasks | Celery | Email notifications, report generation |
| Real-time | Django Channels | WebSocket support for live dashboards |
| File Storage | AWS S3 / MinIO | Document uploads, certificates |
| API Docs | drf-spectacular | Auto-generated OpenAPI / Swagger |
| Testing | pytest-django + coverage | Unit and integration tests |
| Web Server | Nginx | Reverse proxy — routes traffic to Gunicorn |
| App Server | Gunicorn | Python WSGI HTTP server for production |
| CI/CD | GitHub Actions | Automated testing and deployment |

---

## Project Structure

```
BOCRA-Backend/
├── manage.py
├── requirements.txt
├── db.sqlite3
├── bocra_backend/            # Project configuration
│   ├── settings.py
│   ├── urls.py
│   ├── celery.py
│   ├── wsgi.py
│   └── asgi.py
├── core/                     # Shared base models, utils, managers
├── accounts/                 # User management, auth, roles, JWT
├── licensing/                # Licence applications, renewals, certificates
├── complaints/               # Complaints & case management
├── publications/             # Documents, regulations, reports
├── tenders/                  # Tender listings & management
├── news/                     # News articles, announcements
├── analytics/                # QoS data, telecoms stats, dashboards
├── notifications/            # Email, SMS, in-app notifications
├── docs/                     # Project documentation
│   ├── api/                  # API reference (one file per module)
│   │   ├── design.md
│   │   ├── core.md
│   │   ├── accounts.md
│   │   ├── licensing.md
│   │   ├── complaints.md
│   │   ├── publications.md
│   │   ├── tenders.md
│   │   ├── analytics.md
│   │   ├── news.md
│   │   └── notifications.md
│   ├── architecture.md
│   ├── development-plan.md
│   ├── data-models.md
│   ├── srs.md
│   ├── security.md
│   ├── deployment.md
│   └── submission-checklist.md
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 16
- Redis

### Environment Variables

Create a `.env` file in the project root (see `.env.example`):

```env
# Django
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgres://bocra:bocra@localhost:5432/bocra_db

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_ACCESS_TOKEN_LIFETIME=15        # minutes
JWT_REFRESH_TOKEN_LIFETIME=10080    # minutes (7 days)

# File Storage
AWS_STORAGE_BUCKET_NAME=bocra-uploads
AWS_S3_ENDPOINT_URL=http://localhost:9000  # MinIO for local dev

# Email
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

### Running Locally

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Set up database
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

---

## API Documentation

Once the server is running, API documentation is available at:

| URL | Description |
|---|---|
| `/api/swagger/` | Swagger UI — interactive API explorer with "Try it out" |
| `/api/redoc/` | ReDoc — clean, readable API reference |
| `/api/schema/` | Raw OpenAPI 3.0 schema (JSON/YAML download) |
| `/admin/` | Django Admin panel |

### Authentication

All protected endpoints require a JWT Bearer token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

**Token flow:**

```bash
# 1. Register
POST /api/v1/accounts/register/

# 2. Verify email (link sent to inbox)
GET  /api/v1/accounts/verify-email/?token=<jwt>

# 3. Login — returns access + refresh tokens
POST /api/v1/accounts/login/
{ "identifier": "user@example.com", "password": "..." }

# 4. Refresh access token (15-min lifetime)
POST /api/v1/accounts/token/refresh/
{ "refresh": "<refresh_token>" }

# 5. Logout — blacklists the refresh token
POST /api/v1/accounts/logout/
{ "refresh": "<refresh_token>" }
```

### API Conventions

- **Base URL**: `/api/v1/{module}/{resource}/`
- **Auth**: JWT Bearer token on all protected endpoints
- **Response format**: `{ "success": bool, "data": ..., "message": str, "errors": [...] }`
- **Pagination**: `?page=1&page_size=20` on all list endpoints
- **Filtering**: Query params on list endpoints (e.g., `?status=OPEN&category=BILLING`)
- **Versioning**: `/api/v1/` — future breaking changes go to `/api/v2/`

---

## Testing

```bash
# Run all tests
python manage.py test

# Run with verbosity
python manage.py test --verbosity=2

# Run specific app tests
python manage.py test core accounts licensing

# Run single test class
python manage.py test accounts.tests.LoginViewTests

# With coverage (requires coverage.py)
coverage run manage.py test && coverage report
```

---

## Platform Modules

### MVP Scope (Hackathon Demo)

| # | Module | Description | Target |
|---|---|---|---|
| 1 | **Auth System** | Register, login, JWT, role-based access | 100% |
| 2 | **Public Website API** | Homepage data, publications, news, tenders, search | 100% |
| 3 | **Licensing Portal** | Browse types, apply, track status, staff review queue | 100% |
| 4 | **Complaints System** | Submit, reference tracking, staff case management | 100% |
| 5 | **Analytics Dashboard** | QoS charts, telecoms stats, complaints analytics | 100% |
| 6 | **Admin Portal** | Django Admin + custom views for queues | 100% |

### Post-Hackathon

- Domain registry (.bw)
- Spectrum management portal
- Payment gateway integration
- SMS notifications
- Social login (Google OAuth)
- Full multilingual support (Setswana)
- Mobile app

---

## Documentation

Detailed documentation lives in the [`docs/`](docs/) folder:

| Document | Description |
|---|---|
| [Architecture](docs/architecture.md) | System architecture, layers, technology choices |
| [Development Plan](docs/development-plan.md) | Day-by-day build timeline and task breakdown |
| [Data Models](docs/data-models.md) | All entity schemas and relationships |
| [SRS](docs/srs.md) | Full Software Requirements Specification |
| [Security](docs/security.md) | Security requirements, auth flow, threat mitigations |
| [Deployment](docs/deployment.md) | Gunicorn + Nginx setup, CI/CD pipeline, AWS deployment |
| [Submission Checklist](docs/submission-checklist.md) | Hackathon deliverables and status tracking |

### API Reference (`docs/api/`)

| Document | Endpoints | Description |
|---|---|---|
| [API Design](docs/api/design.md) | — | Standards, conventions, response format, auth |
| [Core](docs/api/core.md) | 2 | API root, health check |
| [Accounts](docs/api/accounts.md) | 13 | Registration, JWT auth, profile, admin users |
| [Licensing](docs/api/licensing.md) | 18 | Licence types, applications, renewals, certificates |
| [Complaints](docs/api/complaints.md) | 12 | Submit, track, case management, resolution |
| [Publications](docs/api/publications.md) | 11 | Documents, reports, publish/archive workflow |
| [Tenders](docs/api/tenders.md) | 14 | Procurement, documents, addenda, award workflow |
| [Analytics](docs/api/analytics.md) | 15 | Dashboards, telecoms, QoS, users, licensing, complaints, publications, tenders, news |
| [News](docs/api/news.md) | 10 | Articles, press releases, publish/archive workflow |
| [Notifications](docs/api/notifications.md) | 5 | In-app notifications, read/dismiss |

---

## Contributing

1. Create a feature branch from `main`: `git checkout -b feature/module-name`
2. Write code with tests
3. Run linting: `black .` and `flake8 .`
4. Commit with meaningful messages: `feat(licensing): add application submission endpoint`
5. Push and open a PR
6. Get code reviewed before merging

### Commit Convention

```
feat(module): description     — new feature
fix(module): description      — bug fix
docs(module): description     — documentation
refactor(module): description — code refactoring
test(module): description     — adding tests
chore: description            — tooling, deps, config
```

---

## Submission Checklist

| Item | Status |
|---|---|
| Live URL — deployed and accessible | ⬜ TODO |
| Source code on GitHub | ⬜ TODO |
| README — setup, installation, how to run | ✅ Done |
| Walkthrough video (5-10 min) | ⬜ TODO |
| Technical proposal (max 10 pages) | ⬜ TODO |
| OpenAPI docs at `/api/swagger/` | ✅ Done |

**Deadline: 27 March 2026 | 17:00hrs CAT**

---

## License

This project was built for the BOCRA Youth Hackathon 2026.

---

*BOCRA Digital Platform — v1.0 — March 2026*
