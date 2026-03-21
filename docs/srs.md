# Software Requirements Specification (SRS)

> BOCRA Digital Platform — Full Requirements Reference

| Field | Detail |
|---|---|
| Document Version | 1.0 — Initial Draft |
| Date | March 2026 |
| Hackathon | BOCRA Youth Hackathon — BOCRA Website Development |
| Submission Deadline | 27 March 2026 \| 17:00hrs CAT |
| Backend Stack | Django 5.x + Django REST Framework (DRF) |
| Frontend Stack | React / Next.js |
| Database | PostgreSQL |
| Deployment Target | AWS EC2 + Gunicorn + Nginx |
| Document Status | Living Document — update as build progresses |

This document defines what we are building, how it is architected, and what each module must do. It is the single source of truth for the entire hackathon build.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Scope](#2-scope)
3. [Definitions & Acronyms](#3-definitions--acronyms)
4. [Functional Requirements](#4-functional-requirements)
   - [Authentication & User Management](#41-authentication--user-management)
   - [Public Website & Content](#42-public-website--content)
   - [Licensing Portal](#43-licensing-portal)
   - [Complaints & Case Management](#44-complaints--case-management)
   - [Regulatory Analytics Dashboard](#45-regulatory-analytics-dashboard)
   - [Publications & Document Library](#46-publications--document-library)
   - [Tenders Module](#47-tenders-module)
   - [Admin & Staff Portal](#48-admin--staff-portal)
5. [Non-Functional Requirements](#5-non-functional-requirements)
6. [MVP Scope](#6-mvp-scope)

---

## 1. Introduction

### 1.1 Purpose

This Software Requirements Specification (SRS) defines the functional and non-functional requirements for the BOCRA Digital Platform — a modern, unified, API-first web platform built to replace BOCRA's current fragmented digital infrastructure.

### 1.2 Project Overview

BOCRA (Botswana Communications Regulatory Authority) currently operates a Drupal-based website bolted onto separate ASP.NET portals for licensing, spectrum management, and domain registration. These systems do not communicate with each other, creating a fragmented experience for citizens, licensees, and BOCRA staff.

The goal is to replace this with a single, integrated, API-driven platform that covers all of BOCRA's digital touchpoints — accessible, mobile-first, and built to scale.

---

## 2. Scope

The platform covers the following primary domains:

- **Public-facing website** — information, publications, news, tenders
- **Licensing portal** — applications, renewals, tracking, verification
- **Complaints & case management** — submission, tracking, resolution
- **Regulatory analytics dashboard** — QoS, telecoms stats, real-time data
- **Domain registry (.bw)** — self-service domain management *(post-hackathon)*
- **Spectrum management** — public-facing spectrum information *(post-hackathon)*
- **Admin & staff portal** — internal content and case management
- **Authentication system** — unified SSO for all modules

---

## 3. Definitions & Acronyms

| Term | Definition |
|---|---|
| BOCRA | Botswana Communications Regulatory Authority |
| DRF | Django REST Framework — toolkit for building Web APIs in Django |
| SRS | Software Requirements Specification |
| API | Application Programming Interface |
| REST | Representational State Transfer — architectural style for APIs |
| JWT | JSON Web Token — stateless authentication standard |
| RBAC | Role-Based Access Control — permissions based on user roles |
| QoS | Quality of Service — telecoms performance metrics |
| WCAG | Web Content Accessibility Guidelines |
| SSO | Single Sign-On — one login for all platform modules |
| MVP | Minimum Viable Product — core features for hackathon demo |
| CAT | Central Africa Time (UTC+2) |

---

## 4. Functional Requirements

Requirements are tagged by ID and priority:
- **Critical** = must be in the hackathon demo
- **High** = should be in the demo
- **Medium** = nice to have
- **Low** = post-hackathon

### 4.1 Authentication & User Management

#### User Roles

| Role | Description | Access Level |
|---|---|---|
| Citizen / Public | General public — no login required for public content | Read-only public endpoints |
| Registered User | Citizen with an account | Personal dashboard, applications, complaints |
| Licensee | Company/individual holding a BOCRA licence | Licence management, renewal, compliance |
| BOCRA Staff | Internal employees — case handlers, content editors | Case management, content admin, reports |
| BOCRA Admin | System administrators | Full platform access, user management, settings |
| Super Admin | Technical admin — developer-level access | Full access including system configuration |

#### Auth Requirements

| ID | Requirement | Priority | Notes |
|---|---|---|---|
| AUTH-01 | User registration with email verification | Critical | Email confirmation required before login |
| AUTH-02 | JWT-based login — access + refresh token pair | Critical | Access: 15min, Refresh: 7 days |
| AUTH-03 | Role-based access control on all endpoints | Critical | DRF permissions + custom permission classes |
| AUTH-04 | Password reset via email link | High | Token expires in 1 hour |
| AUTH-05 | Two-factor authentication (2FA) for staff/admin | High | TOTP via authenticator app |
| AUTH-06 | User profile management | High | Personal details, contact info |
| AUTH-07 | Session audit log — last login, IP, device | Medium | Security requirement |
| AUTH-08 | Account deactivation without deletion | Medium | Soft delete pattern |
| AUTH-09 | Social login (Google OAuth) | Low | Post-hackathon |

---

### 4.2 Public Website & Content

| ID | Requirement | Priority | Notes |
|---|---|---|---|
| PUB-01 | Homepage with hero, quick links, news, tenders, stats | Critical | First impression |
| PUB-02 | Navigation — mega menu covering all sections | Critical | Clear IA |
| PUB-03 | Publications library — list, filter, download | Critical | Replaces static docs |
| PUB-04 | News & announcements | High | |
| PUB-05 | Tenders — list, status badge, deadline countdown | High | |
| PUB-06 | About BOCRA — mandate, board, leadership | High | |
| PUB-07 | Consumer information — rights, FAQs | High | |
| PUB-08 | Global search | High | Replaces broken Lucene search |
| PUB-09 | Auto-generated XML sitemap | Medium | SEO |
| PUB-10 | Multilingual (English + Setswana) | Low | Post-hackathon |

---

### 4.3 Licensing Portal

#### Licence Types

- Telecommunications Network Operator
- Internet Service Provider (ISP)
- Broadcasting (Radio / TV)
- Type Approval (device certification)
- Spectrum / Frequency Assignment
- Postal / Courier Services

#### Requirements

| ID | Requirement | Priority | Notes |
|---|---|---|---|
| LIC-01 | Browse available licence types | Critical | Public — no login needed |
| LIC-02 | Public licence verification | Critical | Search by licence number or company |
| LIC-03 | Online licence application — multi-step form + documents | Critical | Core feature |
| LIC-04 | Application status tracking | Critical | Replaces offline follow-up |
| LIC-05 | Staff review and approval workflow | Critical | Internal workflow |
| LIC-06 | Application stages: Submitted → Under Review → Info Requested → Approved/Rejected | Critical | Status machine |
| LIC-07 | Email notifications at each stage change | High | Celery + email |
| LIC-08 | Licence renewal with expiry alerts (90/60/30 days) | High | |
| LIC-09 | Digital licence certificate (PDF) | High | Auto-generated on approval |
| LIC-10 | Licensee dashboard | High | All licences, statuses, renewals |
| LIC-11 | Payment placeholder — fee schedule, reference generation | Medium | Actual payment: post-hackathon |
| LIC-12 | Bulk licence management | Low | Post-hackathon |

---

### 4.4 Complaints & Case Management

| ID | Requirement | Priority | Notes |
|---|---|---|---|
| CMP-01 | Submit complaint — categorised by type | Critical | Core demo feature |
| CMP-02 | Against specific licensee — auto-linked to registry | Critical | |
| CMP-03 | Evidence/document upload | High | Images, screenshots, bills |
| CMP-04 | Unique reference number on submission | Critical | For no-login tracking |
| CMP-05 | Public complaint tracker — by reference number | Critical | Key differentiator |
| CMP-06 | Citizen dashboard — all complaints, statuses | High | |
| CMP-07 | Case stages: Submitted → Assigned → Investigating → Resolved/Closed | Critical | Status machine |
| CMP-08 | Staff assignment as case handler | High | |
| CMP-09 | Internal case notes — BOCRA-only | High | |
| CMP-10 | Resolution response to complainant | High | |
| CMP-11 | Email notifications at every status change | High | |
| CMP-12 | SLA tracking — flag overdue complaints | Medium | |
| CMP-13 | Complaints analytics | Medium | For dashboard |
| CMP-14 | Escalation workflow | Low | Post-hackathon |

---

### 4.5 Regulatory Analytics Dashboard

| ID | Requirement | Priority | Notes |
|---|---|---|---|
| ANL-01 | Telecoms market overview — subscribers by operator/tech | Critical | Mock data for demo |
| ANL-02 | QoS charts — call success, speeds, latency by operator | Critical | Key BOCRA metric |
| ANL-03 | Complaints analytics — volume, category, resolution rates | High | Live from complaints |
| ANL-04 | Licensing stats — active, renewals due, pipeline | High | Live from licensing |
| ANL-05 | Coverage map — Botswana geographic overlay | Medium | Leaflet/Google Maps |
| ANL-06 | Date range filtering on all charts | High | |
| ANL-07 | Data export — CSV/Excel | Medium | |
| ANL-08 | Public dashboard — non-sensitive stats | High | Transparency |
| ANL-09 | Admin dashboard — full operational metrics | High | Role-gated |
| ANL-10 | Real-time WebSocket updates | Medium | Django Channels |

---

### 4.6 Publications & Document Library

| ID | Requirement | Priority | Notes |
|---|---|---|---|
| DOC-01 | Categorised document library | Critical | Regulations, Policies, Reports, Guidelines |
| DOC-02 | Search within publications | Critical | Full text or metadata |
| DOC-03 | Filter by category, year, type | High | |
| DOC-04 | Admin file upload — PDF, DOCX, XLSX | High | AWS S3 |
| DOC-05 | Public download — no login required | Critical | |
| DOC-06 | Document version control | Medium | Track revisions |
| DOC-07 | Featured/pinned documents on homepage | Medium | |
| DOC-08 | Email notification on new publication | Low | Post-hackathon |

---

### 4.7 Tenders Module

| ID | Requirement | Priority | Notes |
|---|---|---|---|
| TND-01 | Tender listings with status (Open, Closing Soon, Closed, Awarded) | Critical | |
| TND-02 | Tender detail page | Critical | |
| TND-03 | Countdown timer on open tenders | High | |
| TND-04 | Tender document download | Critical | |
| TND-05 | Addenda / clarifications | Medium | |
| TND-06 | Award announcement | Medium | |
| TND-07 | Email alert subscription | Low | |

---

### 4.8 Admin & Staff Portal

| ID | Requirement | Priority | Notes |
|---|---|---|---|
| ADM-01 | Django Admin — enhanced with custom views | Critical | DRF + Django Admin |
| ADM-02 | Content management — news, publications, tenders | Critical | |
| ADM-03 | Licence application queue | Critical | View, assign, action |
| ADM-04 | Complaints case queue | Critical | View, assign, manage |
| ADM-05 | User management — create, deactivate, change roles | High | |
| ADM-06 | Audit log — every admin action logged | High | |
| ADM-07 | Site settings management | High | |
| ADM-08 | Bulk actions — approve/reject multiple | Medium | |
| ADM-09 | Staff performance dashboard | Low | |

---

## 5. Non-Functional Requirements

### 5.1 Performance

| ID | Requirement | Target |
|---|---|---|
| PERF-01 | API list endpoint response time | < 300ms (with caching) |
| PERF-02 | API detail endpoint response time | < 150ms |
| PERF-03 | Page load time (SSR) | < 2 seconds on 4G |
| PERF-04 | Dashboard chart render | < 1 second |
| PERF-05 | Search results return | < 500ms |
| PERF-06 | File download initiation | < 1 second (S3 signed URL) |
| PERF-07 | Concurrent users (demo) | 50+ simultaneous |

### 5.2 Security

| ID | Requirement | Priority |
|---|---|---|
| SEC-01 | HTTPS enforced — no HTTP fallback | Critical |
| SEC-02 | JWT with short expiry + refresh rotation | Critical |
| SEC-03 | RBAC on every endpoint | Critical |
| SEC-04 | SQL injection prevention — ORM only | Critical |
| SEC-05 | XSS prevention — input sanitisation | Critical |
| SEC-06 | CSRF protection on state-changing endpoints | Critical |
| SEC-07 | Rate limiting on auth endpoints | High |
| SEC-08 | File upload validation — type, size | High |
| SEC-09 | Passwords bcrypt, PII encrypted at rest | High |
| SEC-10 | Audit logging with user + timestamp + IP | High |
| SEC-11 | CORS — only allowed origins | Critical |
| SEC-12 | Security headers — CSP, X-Frame-Options, HSTS | High |

### 5.3 Accessibility

| ID | Requirement | Standard |
|---|---|---|
| ACC-01 | WCAG 2.1 Level AA compliance target | WCAG 2.1 AA |
| ACC-02 | Semantic HTML — proper headings, landmarks | WCAG |
| ACC-03 | All images have descriptive alt text | WCAG 1.1.1 |
| ACC-04 | Colour contrast minimum 4.5:1 | WCAG 1.4.3 |
| ACC-05 | All elements keyboard navigable | WCAG 2.1.1 |
| ACC-06 | Visible focus indicators | WCAG 2.4.7 |
| ACC-07 | Form labels associated with inputs | WCAG 1.3.1 |
| ACC-08 | Clear error messages | WCAG 3.3.1 |
| ACC-09 | Skip navigation link | WCAG 2.4.1 |
| ACC-10 | Screen reader tested | WCAG |

### 5.4 Scalability & Maintainability

- Modular Django app structure — each domain is self-contained
- API versioning — `/api/v1/` allows future breaking changes
- Environment-based config — `django-environ`, no secrets in code
- Comprehensive test coverage — pytest-django
- DRY principle — shared base models, mixins, utilities in core app

### 5.5 Mobile Responsiveness

- Mobile-first CSS approach — 320px and up
- All interactive elements minimum 44x44px touch target
- Navigation collapses to hamburger on mobile
- Horizontal scroll for tables on small screens
- Single-column full-width forms on mobile

---

## 6. MVP Scope

### What We Are Building (Demo-Ready)

| # | Module | What We Demo | Target |
|---|---|---|---|
| 1 | Auth System | Register, login, JWT, RBAC — end to end | 100% |
| 2 | Public Website | Homepage, publications, news, tenders, search | 100% |
| 3 | Licensing Portal | Browse types, apply, track, staff review queue | 100% |
| 4 | Complaints System | Submit, reference tracking, staff case management | 100% |
| 5 | Analytics Dashboard | QoS charts, telecoms stats, complaints (mock data) | 100% |
| 6 | Admin Portal | Django Admin + custom queue views | 100% |

### What We Are NOT Building (Post-Hackathon)

- Domain registry (.bw)
- Spectrum management portal
- Payment gateway integration
- SMS notifications
- Social login (Google OAuth)
- Full multilingual support (Setswana)
- Mobile app (Flutter / React Native)
- Real BOCRA data integrations

---

*BOCRA Digital Platform SRS — v1.0 — March 2026*
