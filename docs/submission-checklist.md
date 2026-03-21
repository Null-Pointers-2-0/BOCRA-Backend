# Submission Checklist

> BOCRA Digital Platform — Hackathon Deliverables & Status

**Deadline: 27 March 2026 | 17:00hrs CAT — NO EXTENSIONS**

---

## Submission Platforms

| Platform | Details |
|---|---|
| **Primary** | BDIH Skillsranker — skillsranker.bih.co.bw — attach files + cloud drive link |
| **Follow-up email** | hackathon@bih.co.bw — attach cloud drive link |
| **Max file size** | 150MB for direct uploads |
| **Cloud drive** | Google Drive or OneDrive — share link set to "Anyone with link can view" |

---

## Technical Deliverables

| # | Item | Status | Owner | Notes |
|---|---|---|---|---|
| 1 | **Live URL** — deployed and accessible | ⬜ TODO | DevOps | Must be accessible on submission day |
| 2 | **Source code on GitHub** — public or shared | ⬜ TODO | All | Clean commits, meaningful messages |
| 3 | **README** — setup, installation, how to run | ✅ DONE | Lead Dev | Thorough with local + EC2 setup |
| 4 | **Walkthrough video** — full demo of all features | ⬜ TODO | All | Screen record with narration, 5-10 min |
| 6 | **Technical proposal** — max 10 pages | ⬜ TODO | BA / Lead | Motivation, architecture, stack, lessons |
| 7 | **OpenAPI docs** — Swagger UI at `/api/docs/` | ⬜ TODO | Backend | Auto-generated via drf-spectacular |

---

## Technical Proposal Outline (Max 10 Pages)

| Section | Content |
|---|---|
| 1. Motivation | Why BOCRA needs this platform, what problems it solves |
| 2. Solution Design & Architecture | System diagram, module overview, how components interact |
| 3. Software Stack | Why Django + React, why this architecture, key libraries |
| 4. Key Features | Licensing, complaints, dashboard, public site — what each does |
| 5. Security Approach | JWT, RBAC, HTTPS, audit logging, data protection |
| 6. Accessibility Approach | WCAG 2.1 AA, semantic HTML, keyboard nav, screen reader support |
| 7. Scalability | How the platform grows beyond the prototype |
| 8. Lessons Learned | Challenges during the build, how they were solved |
| 9. Future Roadmap | Domain registry, mobile app, payments, real integrations |
| 10. Team & Roles | Who did what |

---

## Feature Checklist — Demo Ready

### Auth System

| Feature | Status | Notes |
|---|---|---|
| User registration | ⬜ | Email + password |
| Email verification | ⬜ | Confirmation link |
| JWT login (access + refresh) | ⬜ | 15min / 7 day |
| Token refresh | ⬜ | |
| Password reset | ⬜ | Email link |
| Role-based access control | ⬜ | 6 roles |
| User profile management | ⬜ | |
| Django Admin user management | ⬜ | |

### Licensing Portal

| Feature | Status | Notes |
|---|---|---|
| Browse licence types (public) | ⬜ | |
| Public licence verification | ⬜ | Search by number/company |
| Online application submission | ⬜ | Multi-step form + documents |
| Application status tracking | ⬜ | Applicant view |
| Staff review workflow | ⬜ | Queue, assign, review |
| Status transitions | ⬜ | Full state machine |
| Email notifications | ⬜ | On status change |
| PDF certificate generation | ⬜ | On approval |
| Licence renewal | ⬜ | |
| Licensee dashboard | ⬜ | |

### Complaints System

| Feature | Status | Notes |
|---|---|---|
| Submit complaint | ⬜ | Categorised, against licensee |
| Reference number generation | ⬜ | CMP-2026-XXXXXX |
| Public tracker (no login) | ⬜ | By reference number |
| Citizen dashboard | ⬜ | All complaints + statuses |
| Staff case queue | ⬜ | View + assign |
| Case status transitions | ⬜ | Full state machine |
| Internal case notes | ⬜ | Staff-only |
| Resolution workflow | ⬜ | Formal resolution |
| Email notifications | ⬜ | On status change |
| Evidence upload | ⬜ | |

### Analytics Dashboard

| Feature | Status | Notes |
|---|---|---|
| Telecoms market overview | ⬜ | Subscribers by operator/tech |
| QoS performance data | ⬜ | Call rates, speeds, latency |
| Complaints analytics | ⬜ | Volume, category, resolution |
| Licensing stats | ⬜ | Active, renewals, pipeline |
| Date range filtering | ⬜ | |
| Public dashboard subset | ⬜ | No login required |
| Staff dashboard (full) | ⬜ | Role-gated |
| Demo data seeded | ⬜ | Management command |

### Public Website API

| Feature | Status | Notes |
|---|---|---|
| Homepage data endpoint | ⬜ | Hero, news, tenders, stats |
| Publications library | ⬜ | List, filter, download |
| News & announcements | ⬜ | List + detail |
| Tenders listing | ⬜ | Status, deadline, documents |
| Global search | ⬜ | Across all content |
| About BOCRA | ⬜ | Static content API |
| Consumer info / FAQs | ⬜ | |

### Admin Portal

| Feature | Status | Notes |
|---|---|---|
| Django Admin enhanced | ⬜ | Custom list displays |
| Content management | ⬜ | News, publications, tenders |
| Licence application queue | ⬜ | Custom admin view |
| Complaints case queue | ⬜ | Custom admin view |
| User management | ⬜ | Roles, activate/deactivate |
| Audit log | ⬜ | All actions logged |
| Site settings | ⬜ | Homepage content |

---

## Video Walkthrough Script

Suggested flow for the 5-10 minute demo video:

1. **Introduction** (30 sec) — Team name, project overview
2. **Public Website** (1.5 min) — Homepage, navigation, publications, news, tenders, search
3. **Registration & Login** (1 min) — Register, verify email, login
4. **Licensing Portal** (2 min) — Browse types, submit application, track status
5. **Complaints System** (1.5 min) — Submit complaint, track by reference
6. **Staff Portal** (1.5 min) — Login as staff, review application, manage complaint
7. **Analytics Dashboard** (1 min) — Show charts, filter by date, public vs staff view
8. **Technical Highlights** (1 min) — API docs (Swagger), Nginx + Gunicorn setup, architecture
9. **Closing** (30 sec) — Summary, future roadmap

---

## Pre-Submission Final Checks

| Check | Status |
|---|---|
| All features working on live URL | ⬜ |
| No console errors in browser | ⬜ |
| API returns proper error messages (not 500s) | ⬜ |
| Swagger UI loads at `/api/docs/` | ⬜ |
| Admin panel accessible | ⬜ |
| Demo data is seeded | ⬜ |
| Video uploaded and accessible | ⬜ |
| Technical proposal PDF ready | ⬜ |
| Cloud drive link is "Anyone can view" | ⬜ |
| Email sent to hackathon@bih.co.bw | ⬜ |
| Submitted on Skillsranker | ⬜ |

---

*BOCRA Digital Platform Submission Checklist — v1.0 — March 2026*
