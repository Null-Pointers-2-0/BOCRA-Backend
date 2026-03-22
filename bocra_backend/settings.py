"""
Django settings for bocra_backend project.
"""

from pathlib import Path
from datetime import timedelta
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent


# ─── CORE ─────────────────────────────────────────────────────────────────────

SECRET_KEY = config("DJANGO_SECRET_KEY")
DEBUG = config("DJANGO_DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("DJANGO_ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())


# ─── APPLICATIONS ─────────────────────────────────────────────────────────────

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "drf_spectacular",
    "django_filters",
]

LOCAL_APPS = [
    "core",
    "accounts",
    "licensing",
    "complaints",
    "publications",
    "tenders",
    "news",
    "analytics",
    "notifications",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS


# ─── MIDDLEWARE ───────────────────────────────────────────────────────────────

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "bocra_backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "bocra_backend.wsgi.application"


# ─── DATABASE ────────────────────────────────────────────────────────────────

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / config("DB_NAME", default="db.sqlite3"),
    }
}


# ─── AUTH ────────────────────────────────────────────────────────────────────

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ─── INTERNATIONALISATION ────────────────────────────────────────────────────

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Gaborone"
USE_I18N = True
USE_TZ = True


# ─── STATIC ───────────────────────────────────────────────────────────────────

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ─── DJANGO REST FRAMEWORK ───────────────────────────────────────────────────

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
    },
}


# ─── SIMPLE JWT ──────────────────────────────────────────────────────────────

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=config("JWT_ACCESS_TOKEN_LIFETIME", default=15, cast=int)),
    "REFRESH_TOKEN_LIFETIME": timedelta(minutes=config("JWT_REFRESH_TOKEN_LIFETIME", default=10080, cast=int)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}


# ─── CORS ────────────────────────────────────────────────────────────────────

CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", default="http://localhost:3000", cast=Csv())
CORS_ALLOW_CREDENTIALS = True


# ─── DRF SPECTACULAR (API DOCS) ──────────────────────────────────────────────

SPECTACULAR_SETTINGS = {
    "TITLE": "BOCRA Digital Platform API",
    "DESCRIPTION": (
        "Unified REST API for the Botswana Communications Regulatory Authority (BOCRA) "
        "digital platform.\n\n"
        "## Modules\n"
        "- **Accounts** — Registration, authentication, profile management\n"
        "- **Licensing** — Licence applications, renewals, verification\n"
        "- **Complaints** — Submit and track regulatory complaints\n"
        "- **Publications** — Documents, regulations, policy papers\n"
        "- **Tenders** — Open tenders and procurement notices\n"
        "- **News** — BOCRA announcements and press releases\n"
        "- **Analytics** — QoS metrics and telecoms statistics\n"
        "- **Notifications** — In-app and email notification management\n\n"
        "## Authentication\n"
        "All protected endpoints require a JWT Bearer token in the `Authorization` header:\n"
        "```\nAuthorization: Bearer <access_token>\n```\n"
        "Obtain tokens via `POST /api/v1/accounts/login/`. "
        "Refresh via `POST /api/v1/accounts/token/refresh/`.\n\n"
        "## Response Format\n"
        "All responses use a consistent envelope:\n"
        "```json\n"
        '{"success": true, "message": "...", "data": {...}, "errors": null}\n'
        "```"
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    # Group endpoints by the @extend_schema(tags=[...]) decorator on each view
    "TAGS": [
        {"name": "Auth", "description": "Registration, login, logout, email verification, and password management."},
        {"name": "Profile", "description": "Authenticated user profile retrieval and update."},
        {"name": "Admin — Users", "description": "Admin-only user listing, detail, and role management."},
        {"name": "Licensing — Public", "description": "Public licence type catalogue and licence verification."},
        {"name": "Licensing — Applications", "description": "Applicant-facing application submission, status tracking, and document upload."},
        {"name": "Licensing — Licences", "description": "Issued licences — detail, renewal, and certificate download."},
        {"name": "Licensing — Staff", "description": "Staff-only application queue management and status state machine."},
        {"name": "Complaints — Public", "description": "Submit complaints and track status (no login required)."},
        {"name": "Complaints — Complainant", "description": "Authenticated complainant — view own complaints, upload evidence."},
        {"name": "Complaints — Staff", "description": "Staff complaint queue, assignment, status updates, and resolution."},
        {"name": "Publications — Public", "description": "Browse and download regulatory documents (no login required)."},
        {"name": "Publications — Staff", "description": "Staff management of publications — create, edit, publish, archive."},
        {"name": "Tenders — Public", "description": "Browse open tenders and download documents (no login required)."},
        {"name": "Tenders — Staff", "description": "Staff management of tenders — create, edit, publish, award."},
        {"name": "News — Public", "description": "Browse published news articles (no login required)."},
        {"name": "News — Staff", "description": "Staff management of articles — create, edit, publish, archive."},
        {"name": "Analytics — Public", "description": "Public telecoms statistics and QoS metrics."},
        {"name": "Analytics — Staff", "description": "Staff-only analytics — users, complaints, licensing, publications, tenders, news, and content summaries."},
        {"name": "Analytics — Dashboard", "description": "Dashboard endpoints — public and staff operational dashboards."},
        {"name": "Notifications", "description": "In-app notification management — list, read, dismiss."},
        {"name": "Core", "description": "API root and health check."},
    ],
    # JWT Bearer auth displayed in the Swagger UI Authorize dialog
    "SECURITY": [{"BearerAuth": []}],
    "COMPONENTS": {
        "securitySchemes": {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
        }
    },
    "SWAGGER_UI_SETTINGS": {
        "persistAuthorization": True,
        "displayRequestDuration": True,
        "filter": True,
        "tryItOutEnabled": True,
    },
    "REDOC_UI_SETTINGS": {
        "hideDownloadButton": False,
    },
    "CONTACT": {
        "name": "BOCRA Digital Platform",
        "email": "digital@bocra.org.bw",
        "url": "https://www.bocra.org.bw",
    },
    "LICENSE": {"name": "Proprietary"},
    # Ensure enum values show labels not just codes in the schema
    "ENUM_GENERATE_CHOICE_DESCRIPTION": True,
    # Resolve enum naming collisions for the shared `status` field name
    "ENUM_NAME_OVERRIDES": {
        "ApplicationStatusEnum": "licensing.models.ApplicationStatus",
        "LicenceStatusEnum": "licensing.models.LicenceStatus",
        "ComplaintStatusEnum": "complaints.models.ComplaintStatus",
        "ComplaintCategoryEnum": "complaints.models.ComplaintCategory",
        "ContentStatusEnum": "publications.models.PublicationStatus",
        "PublicationCategoryEnum": "publications.models.PublicationCategory",
        "TenderStatusEnum": "tenders.models.TenderStatus",
        "TenderCategoryEnum": "tenders.models.TenderCategory",
        "NewsCategoryEnum": "news.models.NewsCategory",
    },
    # Postprocess hook to add the standard response envelope to all responses
    "POSTPROCESSING_HOOKS": [
        "drf_spectacular.hooks.postprocess_schema_enums",
    ],
}


# ─── CACHE ───────────────────────────────────────────────────────────────────
# In-process memory cache — no Redis required.
# Fast enough for this platform's scale; each worker keeps its own cache
# (rate limit counters, session data). Swap for Redis if multi-worker
# horizontal scaling becomes a requirement.

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "bocra-backend",
    }
}


# ─── CELERY ──────────────────────────────────────────────────────────────────

CELERY_BROKER_URL = config("REDIS_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = config("REDIS_URL", default="redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Africa/Gaborone"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300  # 5 minutes hard limit per task


# ─── EMAIL ────────────────────────────────────────────────────────────────────

EMAIL_BACKEND = config(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = config("EMAIL_HOST", default="")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="BOCRA Platform <noreply@bocra.org.bw>")

FRONTEND_URL = config("FRONTEND_URL", default="http://localhost:3000")


# ─── AUTHENTICATION BACKENDS ─────────────────────────────────────────────────
# Allows login with either email OR username.

AUTHENTICATION_BACKENDS = [
    "accounts.backends.UsernameOrEmailBackend",
    "django.contrib.auth.backends.ModelBackend",
]


# ─── LOGGING ─────────────────────────────────────────────────────────────────

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "accounts": {"handlers": ["console"], "level": "DEBUG", "propagate": False},
    },
}


# ─── CELERY ──────────────────────────────────────────────────────────────────

CELERY_BROKER_URL = config("REDIS_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = config("REDIS_URL", default="redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Africa/Gaborone"


# ─── EMAIL ───────────────────────────────────────────────────────────────────

EMAIL_BACKEND = config("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = config("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@bocra.org.bw")


# ─── FILE STORAGE (local — dev only, swap for S3 in prod) ──────────────────

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / config("MEDIA_ROOT", default="media")
