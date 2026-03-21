# BOCRA Digital Platform

## Overview

The BOCRA Digital Platform is a comprehensive regulatory management system for the Botswana Communications Regulatory Authority. This backend provides authentication, licensing, and regulatory services.

## Technology Stack

- **Framework**: Django 5.x with Django REST Framework
- **Database**: SQLite (Development) / PostgreSQL (Production)
- **Cache/Queue**: Redis (optional for local dev)
- **Authentication**: JWT (Simple JWT)
- **File Storage**: Local filesystem (development) / MinIO (production)
- **Task Queue**: Celery (configured but optional)
- **Containerization**: Docker Compose (available)

## Quick Start

### 1. Clone and Setup
```bash
git clone [repository-url]
cd BOCRA-Backend
```

### 2. Quick Setup (Recommended)
```bash
# Windows
setup.bat

# PowerShell
setup.ps1
```

### 3. Manual Setup
```bash
# Virtual Environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install Dependencies
pip install -r requirements.txt

# Environment Setup
cp .env.example .env

# Database Setup
python manage.py migrate
python manage.py createsuperuser

# Start Server
python manage.py runserver
```

### 🚀 Access Services
- **API**: http://localhost:8000
- **Admin**: http://localhost:8000/admin
- **API Docs**: http://localhost:8000/api/docs
- **API Schema**: http://localhost:8000/api/schema

## Database Configuration

### Development (SQLite - Automatic)
- **No setup required** - SQLite works out of the box
- **Database file**: `backend/db.sqlite3`
- **Perfect for instant development**

### Production (PostgreSQL)
Set these environment variables:
```bash
DB_NAME=bocra_db
DB_USER=postgres
DB_PASSWORD=your-postgres-password
DB_HOST=localhost
DB_PORT=5432
```

## Docker Setup (Alternative)

```bash
# From project root
docker-compose up -d
```

This starts:
- PostgreSQL database
- Redis cache
- MinIO storage
- Django application

## Authentication Features ✅ COMPLETE

### Custom User Model
- **Email-based authentication** (username optional)
- **Role-based access control**: CITIZEN, STAFF, ADMIN
- **JWT authentication** with access & refresh tokens
- **Profile management** with comprehensive fields
- **Password reset** functionality
- **Email verification** system
- **Account security** features (login attempts, lockout)

### Authentication Endpoints ✅ TESTED
- **POST** `/api/v1/auth/register/` - User registration
- **POST** `/api/v1/auth/login/` - User login (JWT tokens)
- **GET** `/api/v1/auth/profile/` - Get user profile
- **PATCH** `/api/v1/auth/profile/` - Update profile
- **POST** `/api/v1/auth/logout/` - User logout
- **POST** `/api/v1/auth/refresh/` - Refresh JWT tokens
- **POST** `/api/v1/auth/password-reset/` - Password reset

### Admin Panel ✅ FUNCTIONAL
- **User management** with role-based filtering
- **Bulk actions** for user operations
- **Advanced search** and filtering
- **Security monitoring** (login attempts, lockouts)
- **Profile management** interface

## Project Structure

```
BOCRA-Backend/
├── manage.py
├── bocra_backend/
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   ├── wsgi.py
│   └── celery.py
├── apps/
│   ├── core/          # Base models and utilities
│   └── accounts/      # User authentication
├── requirements.txt
├── .env.example
├── setup.bat          # Windows setup script
├── setup.ps1          # PowerShell setup script
├── docker-compose.yml
└── README.md
```

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Django
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (Production only)
DB_NAME=bocra_db
DB_USER=postgres
DB_PASSWORD=your-postgres-password
DB_HOST=localhost
DB_PORT=5432

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

## Development Workflow

### For Team Members

1. **Clone repository**
2. **Setup virtual environment**
3. **Copy `.env.example` to `.env`**
4. **Run migrations** (SQLite auto-creates)
5. **Start development server**

### Environment Switching

- **Development**: SQLite (automatic when DEBUG=True)
- **Production**: PostgreSQL (when DEBUG=False + DB_* vars set)

## Security Features

- **JWT Authentication**: Secure token-based auth
- **Role-based Access Control**: User permissions by role
- **Password Validation**: Strong password requirements
- **Account Lockout**: Prevents brute force attacks
- **Email Verification**: Verify user email addresses
- **CSRF Protection**: Cross-site request forgery protection
- **Security Headers**: Production security headers

## API Documentation

- **Swagger UI**: http://localhost:8000/api/swagger/
- **ReDoc**: http://localhost:8000/api/redoc/
- **JSON Schema**: http://localhost:8000/api/schema/

## Deployment

### Production Deployment

1. Set environment variables for production
2. Set `DEBUG=False` in environment
3. Configure PostgreSQL database
4. Run `python manage.py migrate`
5. Collect static files: `python manage.py collectstatic`
6. Deploy with Gunicorn/uWSGI

### Docker Deployment

```bash
# Production Docker
docker-compose -f docker-compose.prod.yml up -d
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

© Botswana Communications Regulatory Authority (BOCRA)

---

**Status**: ✅ Authentication System Complete - Ready for Licensing Module Development


