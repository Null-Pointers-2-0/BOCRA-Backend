# Data Models

> BOCRA Digital Platform — Entity Schemas & Relationships

## Table of Contents

- [Base Model](#base-model)
- [Accounts](#accounts)
- [Licensing](#licensing)
- [Complaints](#complaints)
- [Publications](#publications)
- [Tenders](#tenders)
- [News](#news)
- [Analytics](#analytics)
- [Notifications](#notifications)
- [Core / System](#core--system)
- [Entity Relationship Summary](#entity-relationship-summary)

---

## Conventions

All models inherit from `BaseModel` unless otherwise noted:

- **Primary key**: UUID v4 (not auto-incrementing integer)
- **Timestamps**: `created_at`, `updated_at` on every model (auto-managed)
- **Soft delete**: `is_deleted` flag + `deleted_at` timestamp — never hard delete user data
- **Enum fields**: Use Django `TextChoices` for all status/type/category fields

---

## Base Model

```python
class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True
```

---

## Accounts

### User

Custom user model — email-based login (not username).

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK | Primary key |
| `email` | EmailField | unique, indexed | Login identifier |
| `password` | CharField | hashed (bcrypt) | Django's built-in password hashing |
| `first_name` | CharField(150) | required | |
| `last_name` | CharField(150) | required | |
| `phone` | CharField(20) | optional | Contact number |
| `role` | ForeignKey → Role | required | Citizen, Staff, Admin, etc. |
| `is_active` | BooleanField | default=True | Soft deactivation |
| `email_verified` | BooleanField | default=False | Must be True before login |
| `date_joined` | DateTimeField | auto | When account was created |
| `last_login` | DateTimeField | auto | Last successful login |

### Role

| Field | Type | Description |
|---|---|---|
| `id` | UUID | PK |
| `name` | CharField(50) | Unique role name |
| `description` | TextField | Role description |
| `permissions` | M2M → Permission | Assigned permissions |

### Role Definitions

| Role | Code | Description |
|---|---|---|
| Citizen / Public | `CITIZEN` | General public — read-only public content |
| Registered User | `REGISTERED` | Account holder — can apply, file complaints |
| Licensee | `LICENSEE` | Licence holder — manage licences, renewals |
| BOCRA Staff | `STAFF` | Internal BOCRA — case handling, content editing |
| BOCRA Admin | `ADMIN` | System admin — full access, user management |
| Super Admin | `SUPERADMIN` | Technical admin — system configuration |

### Profile

Extended user info — separated from User to keep auth model clean.

| Field | Type | Description |
|---|---|---|
| `id` | UUID | PK |
| `user` | OneToOne → User | |
| `organisation` | CharField(255) | Company/org name (for licensees) |
| `position` | CharField(150) | Job title |
| `address` | TextField | Physical address |
| `city` | CharField(100) | |
| `country` | CharField(100) | Default: Botswana |
| `id_number` | CharField(50) | National ID / Passport (encrypted at rest) |
| `avatar` | FileField | Profile picture |

---

## Licensing

### LicenceType

| Field | Type | Description |
|---|---|---|
| `id` | UUID | PK |
| `name` | CharField(200) | e.g., "Telecommunications Network Operator" |
| `code` | CharField(20) | e.g., "TNO", "ISP", "BROADCAST" |
| `description` | TextField | Full description for applicants |
| `requirements` | TextField | Documents/info required to apply |
| `fee_amount` | DecimalField | Application fee (display only for MVP) |
| `fee_currency` | CharField(3) | Default: "BWP" |
| `validity_period_months` | IntegerField | How long the licence is valid |
| `is_active` | BooleanField | Whether this type is currently available |

### Application

| Field | Type | Description |
|---|---|---|
| `id` | UUID | PK |
| `reference_number` | CharField(50) | Unique, auto-generated (e.g., LIC-2026-0001) |
| `applicant` | ForeignKey → User | Who is applying |
| `licence_type` | ForeignKey → LicenceType | What they're applying for |
| `status` | CharField (enum) | Current application status |
| `organisation_name` | CharField(255) | Applying organisation |
| `organisation_registration` | CharField(100) | Company registration number |
| `contact_person` | CharField(200) | Contact name for the application |
| `contact_email` | EmailField | |
| `contact_phone` | CharField(20) | |
| `description` | TextField | Business description / purpose |
| `submitted_at` | DateTimeField | When application was submitted |
| `reviewed_by` | ForeignKey → User (null) | BOCRA staff assigned to review |
| `notes` | TextField | Internal staff notes |
| `decision_date` | DateTimeField (null) | When final decision was made |
| `decision_reason` | TextField | Required if rejected |

#### Application Status Enum

```python
class ApplicationStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SUBMITTED = "SUBMITTED", "Submitted"
    UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
    INFO_REQUESTED = "INFO_REQUESTED", "Additional Information Requested"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    CANCELLED = "CANCELLED", "Cancelled"
```

### ApplicationDocument

| Field | Type | Description |
|---|---|---|
| `id` | UUID | PK |
| `application` | ForeignKey → Application | Parent application |
| `name` | CharField(255) | Document name/label |
| `file` | FileField | Uploaded file (S3/MinIO) |
| `file_type` | CharField(50) | MIME type |
| `file_size` | IntegerField | Size in bytes |
| `uploaded_by` | ForeignKey → User | Who uploaded |
| `uploaded_at` | DateTimeField | auto |

### Licence

Issued upon application approval.

| Field | Type | Description |
|---|---|---|
| `id` | UUID | PK |
| `licence_number` | CharField(50) | Unique licence number |
| `application` | OneToOne → Application | Originating application |
| `licence_type` | ForeignKey → LicenceType | Type of licence |
| `holder` | ForeignKey → User | Licence owner |
| `organisation_name` | CharField(255) | Licensed organisation |
| `issued_date` | DateField | Date of issue |
| `expiry_date` | DateField | Expiration date |
| `status` | CharField (enum) | ACTIVE, SUSPENDED, EXPIRED, REVOKED |
| `certificate_file` | FileField | Generated PDF certificate |
| `conditions` | TextField | Licence-specific conditions |

### ApplicationStatusLog

Tracks every status change for audit trail.

| Field | Type | Description |
|---|---|---|
| `id` | UUID | PK |
| `application` | ForeignKey → Application | |
| `from_status` | CharField | Previous status |
| `to_status` | CharField | New status |
| `changed_by` | ForeignKey → User | Who made the change |
| `reason` | TextField | Reason for change |
| `changed_at` | DateTimeField | auto |

---

## Complaints

### Complaint

| Field | Type | Description |
|---|---|---|
| `id` | UUID | PK |
| `reference_number` | CharField(50) | Unique (e.g., CMP-2026-001234) |
| `complainant` | ForeignKey → User (null) | Null if anonymous |
| `complainant_name` | CharField(200) | Required if anonymous |
| `complainant_email` | EmailField | Required if anonymous |
| `complainant_phone` | CharField(20) | Optional |
| `against_licensee` | ForeignKey → Licence (null) | Which operator it's about |
| `against_operator_name` | CharField(255) | Free-text if no licence link |
| `category` | CharField (enum) | Complaint category |
| `subject` | CharField(300) | Brief complaint subject |
| `description` | TextField | Full complaint description |
| `status` | CharField (enum) | Case status |
| `priority` | CharField (enum) | LOW, MEDIUM, HIGH, URGENT |
| `assigned_to` | ForeignKey → User (null) | BOCRA case handler |
| `resolution` | TextField (null) | Formal resolution |
| `resolved_at` | DateTimeField (null) | When resolved |
| `sla_deadline` | DateTimeField (null) | Target resolution date |

#### Complaint Category Enum

```python
class ComplaintCategory(models.TextChoices):
    SERVICE_QUALITY = "SERVICE_QUALITY", "Service Quality"
    BILLING = "BILLING", "Billing Dispute"
    COVERAGE = "COVERAGE", "Network Coverage"
    CONDUCT = "CONDUCT", "Operator Conduct"
    INTERNET = "INTERNET", "Internet Service"
    BROADCASTING = "BROADCASTING", "Broadcasting"
    POSTAL = "POSTAL", "Postal / Courier Service"
    OTHER = "OTHER", "Other"
```

#### Complaint Status Enum

```python
class ComplaintStatus(models.TextChoices):
    SUBMITTED = "SUBMITTED", "Submitted"
    ASSIGNED = "ASSIGNED", "Assigned to Handler"
    INVESTIGATING = "INVESTIGATING", "Under Investigation"
    AWAITING_RESPONSE = "AWAITING_RESPONSE", "Awaiting Operator Response"
    RESOLVED = "RESOLVED", "Resolved"
    CLOSED = "CLOSED", "Closed"
    REOPENED = "REOPENED", "Reopened"
```

### ComplaintDocument

| Field | Type | Description |
|---|---|---|
| `id` | UUID | PK |
| `complaint` | ForeignKey → Complaint | |
| `name` | CharField(255) | |
| `file` | FileField | Evidence files |
| `file_type` | CharField(50) | |
| `uploaded_by` | ForeignKey → User (null) | |

### CaseNote

Internal staff-only notes on complaints.

| Field | Type | Description |
|---|---|---|
| `id` | UUID | PK |
| `complaint` | ForeignKey → Complaint | |
| `author` | ForeignKey → User | Staff member |
| `content` | TextField | Note content |
| `is_internal` | BooleanField | default=True — not shown to complainant |

### ComplaintStatusLog

| Field | Type | Description |
|---|---|---|
| `id` | UUID | PK |
| `complaint` | ForeignKey → Complaint | |
| `from_status` | CharField | |
| `to_status` | CharField | |
| `changed_by` | ForeignKey → User | |
| `reason` | TextField | |
| `changed_at` | DateTimeField | auto |

---

## Publications

### Publication

| Field | Type | Description |
|---|---|---|
| `id` | UUID | PK |
| `title` | CharField(300) | Document title |
| `slug` | SlugField | URL-friendly identifier |
| `category` | ForeignKey → PublicationCategory | |
| `description` | TextField | Summary/abstract |
| `file` | FileField | Downloadable document (PDF, DOCX, etc.) |
| `file_type` | CharField(50) | MIME type |
| `file_size` | IntegerField | Size in bytes |
| `published_date` | DateField | Publication date |
| `is_published` | BooleanField | Visibility toggle |
| `is_featured` | BooleanField | Show on homepage |
| `author` | CharField(200) | Author / department |
| `tags` | M2M → Tag | Searchable tags |
| `download_count` | IntegerField | Track popularity |
| `version` | CharField(20) | Document version |

### PublicationCategory

| Field | Type | Description |
|---|---|---|
| `id` | UUID | PK |
| `name` | CharField(100) | e.g., Regulations, Policies, Annual Reports |
| `slug` | SlugField | |
| `description` | TextField | |
| `order` | IntegerField | Display order |

### Tag

| Field | Type | Description |
|---|---|---|
| `id` | UUID | PK |
| `name` | CharField(50) | |
| `slug` | SlugField | |

---

## Tenders

### Tender

| Field | Type | Description |
|---|---|---|
| `id` | UUID | PK |
| `title` | CharField(300) | Tender title |
| `slug` | SlugField | |
| `reference_number` | CharField(50) | Tender reference |
| `description` | TextField | Full tender description |
| `requirements` | TextField | Eligibility requirements |
| `status` | CharField (enum) | OPEN, CLOSING_SOON, CLOSED, AWARDED, CANCELLED |
| `published_date` | DateField | When tender was published |
| `closing_date` | DateTimeField | Application deadline |
| `opening_date` | DateTimeField (null) | Bid opening date |
| `is_published` | BooleanField | Visibility toggle |
| `contact_person` | CharField(200) | BOCRA contact for queries |
| `contact_email` | EmailField | |
| `awarded_to` | CharField(255) (null) | Winner (post-award) |
| `award_amount` | DecimalField (null) | Contract value (post-award) |

### TenderDocument

| Field | Type | Description |
|---|---|---|
| `id` | UUID | PK |
| `tender` | ForeignKey → Tender | |
| `name` | CharField(255) | Document name |
| `file` | FileField | Downloadable file |
| `document_type` | CharField (enum) | MAIN, ADDENDUM, CLARIFICATION |

---

## News

### Article

| Field | Type | Description |
|---|---|---|
| `id` | UUID | PK |
| `title` | CharField(300) | Article title |
| `slug` | SlugField | |
| `excerpt` | TextField | Short summary for listings |
| `content` | TextField | Full article body (HTML/Markdown) |
| `category` | ForeignKey → NewsCategory | |
| `author` | ForeignKey → User | Author |
| `featured_image` | FileField (null) | Header image |
| `is_published` | BooleanField | |
| `published_at` | DateTimeField (null) | |
| `is_featured` | BooleanField | Homepage feature |
| `tags` | M2M → Tag | Reuse tag model from publications |
| `view_count` | IntegerField | Track popularity |

### NewsCategory

| Field | Type | Description |
|---|---|---|
| `id` | UUID | PK |
| `name` | CharField(100) | e.g., Press Release, Announcement, Event |
| `slug` | SlugField | |

---

## Analytics

### NetworkOperator

| Field | Type | Description |
|---|---|---|
| `id` | UUID | PK |
| `name` | CharField(200) | e.g., Mascom, Orange, beMobile |
| `code` | CharField(20) | Short code |
| `logo` | FileField (null) | Operator logo |
| `is_active` | BooleanField | |

### TelecomsStat

| Field | Type | Description |
|---|---|---|
| `id` | UUID | PK |
| `operator` | ForeignKey → NetworkOperator | |
| `period` | DateField | Reporting period (month/quarter) |
| `technology` | CharField (enum) | 2G, 3G, 4G, 5G |
| `subscriber_count` | IntegerField | Number of subscribers |
| `market_share_percent` | DecimalField | Market share % |
| `revenue` | DecimalField (null) | Revenue (if reported) |

### QoSRecord

Quality of Service measurement.

| Field | Type | Description |
|---|---|---|
| `id` | UUID | PK |
| `operator` | ForeignKey → NetworkOperator | |
| `period` | DateField | Measurement period |
| `metric_type` | CharField (enum) | CALL_SUCCESS, DATA_SPEED, LATENCY, DROP_RATE |
| `value` | DecimalField | Metric value |
| `unit` | CharField(20) | e.g., "%", "Mbps", "ms" |
| `region` | CharField(100) (null) | Geographic region |
| `benchmark` | DecimalField (null) | Target/benchmark value |

---

## Notifications

### Notification

| Field | Type | Description |
|---|---|---|
| `id` | UUID | PK |
| `recipient` | ForeignKey → User | |
| `notification_type` | CharField (enum) | EMAIL, SMS, IN_APP |
| `subject` | CharField(300) | |
| `message` | TextField | Notification body |
| `is_read` | BooleanField | For in-app notifications |
| `read_at` | DateTimeField (null) | |
| `sent_at` | DateTimeField (null) | |
| `status` | CharField (enum) | PENDING, SENT, FAILED |
| `related_object_type` | CharField(50) (null) | Content type for linking |
| `related_object_id` | UUIDField (null) | FK to related object |

### NotificationTemplate

| Field | Type | Description |
|---|---|---|
| `id` | UUID | PK |
| `name` | CharField(100) | e.g., "application_submitted", "complaint_resolved" |
| `subject_template` | CharField(300) | Subject with placeholders |
| `body_template` | TextField | Body with placeholders (Django template syntax) |
| `notification_type` | CharField (enum) | EMAIL, SMS |

---

## Core / System

### AuditLog

| Field | Type | Description |
|---|---|---|
| `id` | UUID | PK |
| `user` | ForeignKey → User (null) | Who performed the action |
| `action` | CharField(50) | CREATE, UPDATE, DELETE, LOGIN, etc. |
| `model_name` | CharField(100) | Which model was affected |
| `object_id` | UUIDField (null) | ID of the affected object |
| `changes` | JSONField | What changed (old/new values) |
| `ip_address` | GenericIPAddressField (null) | Request IP |
| `user_agent` | TextField (null) | Browser/client info |
| `timestamp` | DateTimeField | auto |

### SiteSettings

Singleton model for site-wide configuration.

| Field | Type | Description |
|---|---|---|
| `id` | UUID | PK |
| `site_name` | CharField(200) | "BOCRA Digital Platform" |
| `hero_title` | CharField(300) | Homepage hero heading |
| `hero_subtitle` | TextField | Homepage hero subtext |
| `contact_email` | EmailField | Official contact email |
| `contact_phone` | CharField(20) | Official phone |
| `address` | TextField | Physical address |
| `social_facebook` | URLField (null) | |
| `social_twitter` | URLField (null) | |
| `maintenance_mode` | BooleanField | Toggle site availability |

---

## Entity Relationship Summary

```
User ──────────┬──── Profile (1:1)
               │
               ├──── Application (1:M) ──── ApplicationDocument (1:M)
               │         │
               │         └──── Licence (1:1) ──── LicenceType (M:1)
               │
               ├──── Complaint (1:M) ──── ComplaintDocument (1:M)
               │         │
               │         ├──── CaseNote (1:M)
               │         │
               │         └──── ComplaintStatusLog (1:M)
               │
               ├──── Article (1:M — as author)
               │
               ├──── Notification (1:M — as recipient)
               │
               └──── AuditLog (1:M — as actor)

LicenceType ──── Application (1:M)
                      │
                      └──── ApplicationStatusLog (1:M)

NetworkOperator ──── TelecomsStat (1:M)
                │
                └──── QoSRecord (1:M)

PublicationCategory ──── Publication (1:M) ──── Tag (M:M)

NewsCategory ──── Article (1:M) ──── Tag (M:M)

Tender ──── TenderDocument (1:M)

Licence ──── Complaint.against_licensee (1:M)
```

---

*BOCRA Digital Platform Data Models — v1.0 — March 2026*
