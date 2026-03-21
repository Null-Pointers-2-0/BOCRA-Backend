# Development Plan

> BOCRA Digital Platform — Day-by-Day Build Timeline

## Overview

**Total Duration:** 7 working days (20 March – 27 March 2026)
**Submission Deadline:** 27 March 2026 | 17:00hrs CAT
**Strategy:** 4 fully working modules > 10 half-built ones. Depth over breadth. Every feature we demo must actually work.

---

## MVP Scope — What Gets Built

| # | Module | What We Demo | Status Target | **Actual Status** |
|---|---|---|---|---|
| 1 | Auth System | Register, login, JWT, role-based access — all working E2E | 100% | ✅ **Complete** |
| 2 | Public Website API | Homepage data, publications, news, tenders, search | 100% | ⏳ Pending |
| 3 | Licensing Portal | Browse types, apply (multi-step), track status, staff review | 100% | ✅ **Complete** |
| 4 | Complaints System | Submit complaint, reference tracking, staff case management | 100% | ⏳ Pending |
| 5 | Analytics Dashboard | QoS charts, telecoms stats, complaints volume (mock data) | 100% | ⏳ Pending |
| 6 | Admin Portal | Django Admin + custom views for licence & complaint queues | 100% | ⚠️ Partial (licensing admin done) |

## What We Are NOT Building (Post-Hackathon)
---

## 📊 Build Status (Updated: 21 March 2026)

### ✅ Done

| App | Models | Serializers | Views | URLs | Admin | Tests |
|---|---|---|---|---|---|---|
| `core` | ✅ | — | ✅ | ✅ | ✅ | ✅ |
| `accounts` | ✅ | ✅ | ✅ (11 views) | ✅ | ✅ | ✅ |
| `licensing` | ✅ | ✅ | ✅ (14 views) | ✅ | ✅ | ✅ |

**API Documentation:**
- Swagger UI: `/api/swagger/` — all 27 endpoints visible, tagged, and summarised
- ReDoc: `/api/redoc/` — clean reference docs
- Schema: `/api/schema/` — raw OpenAPI 3.0 JSON/YAML
- All views tagged (`tags=`) and have `summary=` set

**Test suite:** 173 tests — all passing

### ⏳ To Build Next

| App | Status | Next Action |
|---|---|---|
| `complaints` | 🔴 Stub only | Day 4 — full implementation (same pattern as licensing) |
| `publications` | 🔴 Stub only | Day 6 — models + CRUD views |
| `tenders` | 🔴 Stub only | Day 6 — models + CRUD views |
| `news` | 🔴 Stub only | Day 6 — models + CRUD views |
| `analytics` | 🔴 Stub only | Day 5 — models + seed data command + chart endpoints |
| `notifications` | 🔴 Stub only | Day 4 — notification model + task dispatch |

---

- Domain registry (.bw) — too complex for 7 days
- Spectrum management portal
- Actual payment gateway integration — placeholder only
- SMS notifications — email only for demo
- Social login (Google OAuth)
- Full multilingual (Setswana) support
- Mobile app (Flutter / React Native)
- Real BOCRA data integrations — mock data only

---

## Day-by-Day Timeline

### Day 1 — Thursday 20 March 2026 ✅ DONE
**Focus: Project Setup + Auth System**

| Task | Priority | Details |
|---|---|---|
| Project initialisation | Critical | Django project, Git repo, `.gitignore`, initial commit |
| Server environment setup | Critical | Python venv, PostgreSQL, Redis installed and running locally |
| Environment config | Critical | `django-environ`, `.env.example`, settings split |
| `core` app | Critical | BaseModel (UUID, timestamps, soft delete), AuditLog, pagination, renderers |
| `accounts` app — models | Critical | Custom User model (email-based), Role, Profile |
| `accounts` app — auth | Critical | Registration, email verification, JWT login/refresh |
| `accounts` app — RBAC | Critical | Permission classes — Citizen, Licensee, Staff, Admin |
| DRF configuration | Critical | Default auth, pagination, filtering, renderer setup |
| drf-spectacular | High | OpenAPI schema generation, Swagger UI at `/api/docs/` |
| CORS setup | High | `django-cors-headers` configured for frontend origins |

**Deliverable:** Auth system fully working — register, verify email, login, get JWT, access protected endpoints.

---

### Day 2 — Friday 21 March 2026 ⚠️ PARTIAL
**Focus: Core Models + APIs (All Apps Scaffolded)**

| Task | Priority | Details |
|---|---|---|
| `licensing` app — models | Critical | Licence, LicenceType, Application, ApplicationDocument, ApplicationStatus |
| `licensing` app — serializers | Critical | Application submission, status tracking, type listing |
| `licensing` app — views | Critical | Public type browsing, user application CRUD, staff review |
| `complaints` app — models | Critical | Complaint, Case, CaseNote, Resolution, ComplaintDocument |
| `complaints` app — serializers | Critical | Submission, public tracking, staff management |
| `complaints` app — views | Critical | Public submission + tracking, user dashboard, staff queue |
| `publications` app — models | High | Publication, Category, Tag, Document |
| `publications` app — views | High | Public listing with filtering, admin CRUD |
| `tenders` app — models | High | Tender, TenderDocument, TenderSubmission |
| `tenders` app — views | High | Public listings with status badges, admin management |
| `news` app — models | High | Article, Category, Author |
| `news` app — views | High | Public news feed, admin publishing |
| `analytics` app — models | High | QoSRecord, TelecomsStat, NetworkOperator |
| URL routing | Critical | Wire all apps to `/api/v1/{module}/` pattern |
| Admin registration | High | Register all models in Django Admin with list displays |

**Deliverable:** All Django apps scaffolded with models, serializers, and basic CRUD APIs. All endpoints responding correctly.

---

### Day 3 — Saturday 22 March 2026 ✅ DONE
**Focus: Licensing Module (Full Feature)**

| Task | Priority | Details |
|---|---|---|
| Licence type browsing | Critical | Public endpoint — list types with descriptions and requirements |
| Application submission | Critical | Multi-step form handling — personal info, licence type, documents |
| Document upload | Critical | AWS S3 upload for supporting documents |
| Application tracking | Critical | Applicant can see their application status and timeline |
| Staff review workflow | Critical | Staff can view queue, assign, review, request info |
| Status transitions | Critical | SUBMITTED → UNDER_REVIEW → INFO_REQUESTED → APPROVED/REJECTED |
| Email notifications | High | Celery tasks — status change emails to applicant |
| Public verification | Critical | Search by licence number or company name |
| Reference number generation | Critical | Auto-generated human-readable refs (e.g., LIC-2026-0001) |
| PDF certificate generation | High | Auto-generated licence certificate on approval |
| Licence renewal | High | Renewal endpoint with expiry alerts |
| Licensee dashboard data | High | All licences, statuses, renewal dates for logged-in licensee |

**Deliverable:** Complete licensing flow working — from browsing types through application to staff approval and certificate download.

---

### Day 4 — Sunday 23 March 2026 ⏳ NEXT
**Focus: Complaints Module + BOCRA Briefing**

> **Note:** BOCRA Briefing at 0900hrs — attend and take requirements.

| Task | Priority | Details |
|---|---|---|
| Complaint submission | Critical | Categorised by type, against specific licensee, with evidence upload |
| Reference number | Critical | Auto-generated (e.g., CMP-2026-001234) for tracking |
| Public tracker | Critical | Track by reference number — no login required |
| Citizen dashboard | High | View all complaints and statuses if logged in |
| Staff case management | Critical | View queue, assign handler, update status |
| Case stages | Critical | SUBMITTED → ASSIGNED → INVESTIGATING → RESOLVED → CLOSED |
| Internal notes | High | Staff-only notes on complaints |
| Resolution workflow | High | Staff sends formal resolution to complainant |
| Email notifications | High | Celery tasks — status change emails to complainant |
| SLA tracking | Medium | Flag complaints exceeding resolution time targets |
| `notifications` app | High | Notification model, email templates, Celery task dispatch |

**Deliverable:** Complete complaints flow — submission through case management to resolution. Public tracking by reference number working.

---

### Day 5 — Monday 24 March 2026
**Focus: Analytics Dashboard**

| Task | Priority | Details |
|---|---|---|
| Seed demo data | Critical | Management command to populate QoS, telecoms, operator data |
| Telecoms market overview | Critical | Subscriber counts by operator and technology (2G/3G/4G/5G) |
| QoS performance data | Critical | Call success rates, data speeds, latency by operator |
| Complaints analytics | High | Volume over time, by category, by operator, resolution rates |
| Licensing analytics | High | Active licences by type, renewals due, applications in progress |
| Date range filtering | High | All analytics endpoints support date range params |
| Public dashboard data | High | Non-sensitive stats available without login |
| Staff dashboard data | High | Full operational metrics — role-gated |
| Data export | Medium | CSV/Excel download for chart data |
| Aggregate endpoints | Critical | Optimised queries for chart-ready data |

**Deliverable:** Analytics API endpoints returning chart-ready data. Seeded with realistic mock data for demo.

---

### Day 6 — Tuesday 25 March 2026
**Focus: Public Website API + Polish**

| Task | Priority | Details |
|---|---|---|
| Homepage API | Critical | Hero content, quick links, latest news, open tenders, stats summary |
| Global search | High | Search across publications, news, tenders, FAQs |
| Site settings API | High | Dynamic homepage content management |
| Content filtering | High | All list endpoints — filter by category, date, type, status |
| Error handling | High | Consistent error responses across all endpoints |
| Admin customisation | High | Custom Django Admin views for licence and complaint queues |
| Performance | High | Add caching (Redis) to frequently-hit public endpoints |
| Bug fixes | Critical | Fix all known issues from previous days |
| API documentation | High | Ensure all endpoints documented in Swagger |
| Edge cases | High | Handle empty states, invalid inputs, permission errors |

**Deliverable:** All public-facing APIs polished and performing well. Admin portal ready for demo.

---

### Day 7 — Wednesday 26 March 2026
**Focus: Testing + Docs + Video**

| Task | Priority | Details |
|---|---|---|
| Unit tests | Critical | Models, serializers, views — aim for 80%+ coverage on core modules |
| Integration tests | High | Auth flow, licensing flow, complaints flow end-to-end |
| Bug fixes | Critical | Fix any remaining issues found during testing |
| README finalisation | Critical | Setup instructions, API docs link, architecture overview |
| Technical proposal | Critical | 10-page document — motivation, design, stack, features, lessons |
| Walkthrough video | Critical | Screen recording with narration — 5-10 minutes |
| Deployment check | Critical | Verify live demo URL is working |
| API docs review | High | Swagger UI at `/api/swagger/` accurate and complete |
| Code cleanup | Medium | Remove debug code, unused imports, commented-out code |

**Deliverable:** Everything tested, documented, and ready for submission.

---

### Buffer Day — Thursday 27 March 2026
**Focus: Final Submission**

| Task | Priority | Details |
|---|---|---|
| Final deployment | Critical | Ensure live URL is accessible |
| Smoke test | Critical | Quick run-through of all features on live deployment |
| Package submission | Critical | Cloud drive link, README, video, technical proposal |
| Submit on Skillsranker | Critical | Upload to skillsranker.bih.co.bw |
| Send email | Critical | Follow-up email to hackathon@bih.co.bw |

**Deadline: 17:00hrs CAT — NO EXTENSIONS**

---

## Task Ownership Template

Use this to assign tasks across team members:

| Role | Responsibilities |
|---|---|
| **Lead Backend Dev** | Django apps, models, serializers, views, business logic |
| **Backend Dev 2** | Auth system, permissions, Celery tasks, email templates |
| **DevOps / Infra** | AWS EC2 setup, Nginx, Gunicorn, CI/CD, environment config |
| **QA / Testing** | Test writing, bug reports, edge case discovery |
| **Docs / BA** | Technical proposal, README, video, submission |

---

## Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| Running out of time | High | Strict MVP scope — cut features, not quality |
| Complex licensing workflow | High | Build incrementally — submission first, then review, then PDF |
| Deployment issues | Medium | Set up EC2 + Nginx + Gunicorn early, not on Day 7 |
| Database schema changes mid-build | Medium | Plan models carefully on Day 2, minimize migrations after |
| Team availability (Day 4 briefing) | Low | Front-load work on Days 1-3, lighter workload on Day 4 |
| Bug cascade in final days | High | Test continuously, don't save testing for Day 7 |

---

## Definition of Done

A feature is "done" when:

1. API endpoint exists and returns correct data
2. Authentication and permissions work correctly
3. Input validation catches invalid data with helpful error messages
4. Happy path and error cases are tested
5. Endpoint is documented in Swagger
6. Admin can manage the data via Django Admin
7. Email notifications fire where required (Celery)
8. Code is committed with a meaningful commit message

---

*BOCRA Digital Platform Development Plan — v1.0 — March 2026*
