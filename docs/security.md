# Security

> BOCRA Digital Platform — Security Requirements & Implementation

## Table of Contents

- [Security Philosophy](#security-philosophy)
- [Authentication & Authorization](#authentication--authorization)
- [Data Protection](#data-protection)
- [API Security](#api-security)
- [Infrastructure Security](#infrastructure-security)
- [File Upload Security](#file-upload-security)
- [Audit & Monitoring](#audit--monitoring)
- [Security Checklist](#security-checklist)

---

## Security Philosophy

Security is not an afterthought — it is built into every layer:

1. **Defence in depth** — multiple security layers, not a single firewall
2. **Least privilege** — users and services get minimum required access
3. **Secure by default** — new endpoints are protected; public access is explicitly opted-in
4. **No security through obscurity** — assume attackers know the stack

---

## Authentication & Authorization

### JWT Implementation

| Setting | Value | Rationale |
|---|---|---|
| Access token lifetime | 15 minutes | Limits exposure if token is leaked |
| Refresh token lifetime | 7 days | Balances UX with security |
| Algorithm | HS256 | Django SimpleJWT default, sufficient for single-origin |
| Token rotation | Refresh token rotated on use | Prevents replay attacks |
| Blacklisting | Enabled | Revoke tokens on logout/password change |

### Token Security Rules

- Tokens are never stored in `localStorage` (XSS vulnerability) — use `httpOnly` cookies or in-memory storage on the frontend
- Refresh tokens are rotated on every use — old refresh tokens are blacklisted
- On password change, all existing tokens are invalidated
- On account deactivation, all tokens are revoked

### Role-Based Access Control (RBAC)

Every API endpoint has an explicit permission class:

```python
# Example permission configuration
class IsOwnerOrStaff(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.applicant == request.user or request.user.role.name in ['STAFF', 'ADMIN']
```

| Role | Public Endpoints | Own Resources | Other Users' Resources | Admin Functions |
|---|---|---|---|---|
| Public | Read | — | — | — |
| Registered | Read | CRUD | — | — |
| Licensee | Read | CRUD + Renew | — | — |
| Staff | Read | CRUD | Read + Status Update | — |
| Admin | Read | CRUD | Full CRUD | Full Access |

### Password Security

- Hashing: Django's default PBKDF2 with SHA256 (configurable to bcrypt/argon2)
- Minimum length: 8 characters
- Complexity: Must include uppercase, lowercase, number
- Common password check: Django's built-in `CommonPasswordValidator`
- Password reset tokens: One-time use, 1-hour expiry

### Two-Factor Authentication (2FA)

- Required for: Staff and Admin roles
- Method: TOTP (Time-based One-Time Password) via authenticator apps
- Implementation: `django-otp` or `pyotp`
- Recovery codes: 10 single-use backup codes generated on 2FA setup

---

## Data Protection

### Data at Rest

| Data Type | Protection | Implementation |
|---|---|---|
| Passwords | Hashed (PBKDF2/bcrypt) | Django's auth system |
| PII (ID numbers, addresses) | Encrypted fields | `django-encrypted-model-fields` or `django-fernet-fields` |
| JWT signing key | Environment variable | Never in code or version control |
| Database credentials | Environment variable | `django-environ` |
| File uploads | Private S3 bucket | Signed URLs for access, not public |

### Data in Transit

- **HTTPS enforced** on all endpoints — no HTTP fallback
- **HSTS header** — `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- **TLS 1.2+** minimum — older protocols disabled

### Data Retention

- Soft delete pattern — user data is deactivated, not destroyed
- Audit logs retained indefinitely
- Temporary tokens (password reset, email verification) auto-expire and are cleaned up

---

## API Security

### Input Validation

- All input validated through DRF serializers — no raw `request.data` access
- File uploads validated for type, size, and content
- Django ORM prevents SQL injection — no raw queries without parameterisation
- All user-generated content escaped on output (XSS prevention)

### Rate Limiting

| Endpoint Group | Rate Limit | Purpose |
|---|---|---|
| `/accounts/login/` | 5 requests / minute | Brute force prevention |
| `/accounts/register/` | 3 requests / minute | Spam prevention |
| `/accounts/password-reset/` | 3 requests / minute | Abuse prevention |
| General API (authenticated) | 100 requests / minute | Fair use |
| General API (anonymous) | 30 requests / minute | Abuse prevention |

Implementation: `djangorestframework` throttle classes or `django-ratelimit`.

### CORS Configuration

```python
CORS_ALLOWED_ORIGINS = [
    "https://bocra-platform.example.com",      # Production frontend
    "http://localhost:3000",                     # Local Next.js dev
]

CORS_ALLOW_CREDENTIALS = True   # For cookie-based auth

# Never use CORS_ALLOW_ALL_ORIGINS = True in production
```

### CSRF Protection

- Django's CSRF middleware is active for all state-changing requests
- For API endpoints using JWT (no cookies), CSRF is handled via the token itself
- For Django Admin (cookie-based sessions), standard CSRF tokens apply

### Security Headers

```python
# Django security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True  # Production only

# Content Security Policy (via django-csp)
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'",)
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")  # Tailwind requires this
CSP_IMG_SRC = ("'self'", "data:", "https:")
CSP_CONNECT_SRC = ("'self'",)
```

---

## Infrastructure Security

### Environment Variables

**Never commit secrets to version control.** All sensitive configuration via environment variables:

```env
# Required environment variables
DJANGO_SECRET_KEY=<random-50-char-string>
DATABASE_URL=postgres://user:pass@host:5432/db
REDIS_URL=redis://host:6379/0
AWS_ACCESS_KEY_ID=<key>
AWS_SECRET_ACCESS_KEY=<key>
EMAIL_HOST_PASSWORD=<smtp-password>
```

### Docker Security

- Use official Python slim images — minimise attack surface
- Run as non-root user inside containers
- No secrets in Dockerfile or docker-compose.yml — use `.env` files
- Pin image versions — avoid `:latest` tags
- Docker secrets for production deployments

### Database Security

- Connection via SSL in production
- Separate database user with limited privileges (no DROP, no SUPERUSER)
- Connection pooling via `django-db-connection-pool` or PgBouncer
- Regular backups (automated in production hosting)

---

## File Upload Security

### Validation Rules

| Check | Rule | Implementation |
|---|---|---|
| File type | Whitelist: PDF, DOCX, XLSX, PNG, JPG, JPEG | Check both extension and MIME type |
| File size | Max 10MB per file, 50MB per request | DRF `FileUploadParser` + custom validation |
| Filename | Sanitise — strip path traversal, special chars | `django.utils.text.get_valid_filename` |
| Content | Verify file header matches declared type | `python-magic` library |
| Storage | Private S3 bucket, signed URLs for access | `django-storages` + boto3 |
| Serving | Never serve files directly from Django | S3 signed URLs with expiry |

### Upload Flow

```
1. User uploads file via multipart/form-data
2. DRF serializer validates file type, size
3. python-magic validates file content/header
4. Filename sanitised
5. File uploaded to S3/MinIO with private ACL
6. Database stores file metadata (name, size, type, S3 key)
7. Download requests generate time-limited signed URL
```

---

## Audit & Monitoring

### Audit Log

Every significant action is logged:

| Event | Logged Data |
|---|---|
| User login / logout | User, IP, user agent, timestamp |
| Failed login attempt | Email attempted, IP, timestamp |
| Resource created/updated/deleted | User, model, object ID, changed fields, timestamp |
| Status transitions | User, from/to status, reason, timestamp |
| Admin actions | User, action, target, timestamp |
| File upload/download | User, file info, timestamp |

### Log Structure

```json
{
  "timestamp": "2026-03-21T10:30:00Z",
  "user_id": "uuid",
  "action": "UPDATE",
  "model": "Application",
  "object_id": "uuid",
  "changes": {
    "status": {"old": "SUBMITTED", "new": "UNDER_REVIEW"}
  },
  "ip_address": "196.x.x.x",
  "user_agent": "Mozilla/5.0..."
}
```

### Monitoring (Production)

- Application error tracking: Sentry (free tier)
- Uptime monitoring: UptimeRobot or similar
- Log aggregation: Cloud provider logging (Railway/Render built-in)
- Alerts: Critical errors, failed auth spikes, high error rates

---

## Security Checklist

### Before Deployment

| Check | Status | Notes |
|---|---|---|
| `DEBUG = False` in production | ⬜ | Leaks sensitive info if True |
| `SECRET_KEY` is unique and secret | ⬜ | Not the Django default |
| `ALLOWED_HOSTS` configured | ⬜ | Only production domains |
| HTTPS enforced | ⬜ | `SECURE_SSL_REDIRECT = True` |
| CORS restricted to allowed origins | ⬜ | No `ALLOW_ALL_ORIGINS` |
| Database user has limited privileges | ⬜ | No SUPERUSER |
| All environment variables set | ⬜ | No defaults for secrets |
| Rate limiting active | ⬜ | Auth endpoints especially |
| Security headers configured | ⬜ | HSTS, CSP, X-Frame-Options |
| File upload validation active | ⬜ | Type, size, content checks |
| Audit logging enabled | ⬜ | All admin actions logged |
| No raw SQL queries | ⬜ | ORM only (or parameterised) |
| Dependencies up to date | ⬜ | `pip-audit` or `safety check` |
| `.env` in `.gitignore` | ⬜ | Never committed |
| Admin URL not at `/admin/` (optional) | ⬜ | Obscure admin path |

---

*BOCRA Digital Platform Security — v1.0 — March 2026*
