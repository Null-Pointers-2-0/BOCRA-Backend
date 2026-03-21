# Deployment

> BOCRA Digital Platform — Gunicorn + Nginx + AWS EC2 Deployment

## Table of Contents

- [Stack Overview](#stack-overview)
- [Local Development Setup](#local-development-setup)
- [Environment Configuration](#environment-configuration)
- [Production Server Setup (AWS EC2)](#production-server-setup-aws-ec2)
- [Gunicorn Configuration](#gunicorn-configuration)
- [Nginx Configuration](#nginx-configuration)
- [SSL / HTTPS with Certbot](#ssl--https-with-certbot)
- [Celery as a System Service](#celery-as-a-system-service)
- [CI/CD Pipeline](#cicd-pipeline)
- [Production Checklist](#production-checklist)

---

## Stack Overview

| Component | Technology | Role |
|---|---|---|
| App Server | Gunicorn | Python WSGI server — runs Django workers |
| Reverse Proxy | Nginx | Handles HTTP/HTTPS, static files, proxies to Gunicorn |
| Database | PostgreSQL 16 | Installed directly on EC2 or RDS |
| Cache / Broker | Redis | Installed on EC2 |
| Background Tasks | Celery | Managed as systemd service |
| File Storage | AWS S3 | Document uploads, certificates |
| Hosting | AWS EC2 | Ubuntu 22.04 LTS recommended |
| SSL | Let's Encrypt (Certbot) | Free HTTPS certificate |
| Process Manager | systemd | Manages Gunicorn and Celery services |

```
Internet
    │
    ▼
Nginx (port 80/443)
    │  → /api/   → Gunicorn (127.0.0.1:8000)
    │  → /admin/ → Gunicorn (127.0.0.1:8000)
    │  → /static/ → Serve directly from filesystem
    │  → /        → Proxy to Next.js frontend
    ▼
Django + DRF (Gunicorn workers)
    │
    ├── PostgreSQL (localhost:5432)
    ├── Redis (localhost:6379)
    └── AWS S3 (file storage)
```

---

## Local Development Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 16
- Redis

### Steps

```bash
# Clone the repository
git clone https://github.com/your-team/BOCRA-Backend.git
cd BOCRA-Backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file and configure
cp .env.example .env
# Edit .env with your local database credentials

# Create the database
createdb bocra_db

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Seed demo data
python manage.py seed_data

# Run development server
python manage.py runserver
```

Services to run separately in development:

```bash
# Redis (in a separate terminal)
redis-server

# Celery worker (in a separate terminal)
celery -A bocra_backend worker -l info

# Celery beat scheduler (in a separate terminal)
celery -A bocra_backend beat -l info
```

---

## Environment Configuration

### .env.example

```env
# ===================
# Django Settings
# ===================
DJANGO_SECRET_KEY=change-me-to-a-random-50-character-string
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# ===================
# Database
# ===================
DATABASE_URL=postgres://bocra:bocra@localhost:5432/bocra_db

# ===================
# Redis
# ===================
REDIS_URL=redis://localhost:6379/0

# ===================
# JWT Settings
# ===================
JWT_ACCESS_TOKEN_LIFETIME=15
JWT_REFRESH_TOKEN_LIFETIME=10080

# ===================
# File Storage (AWS S3)
# ===================
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_STORAGE_BUCKET_NAME=bocra-uploads
AWS_S3_REGION_NAME=af-south-1

# ===================
# Email
# ===================
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=

# ===================
# CORS
# ===================
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

### Environment Differences

| Setting | Development | Production |
|---|---|---|
| `DJANGO_DEBUG` | `True` | `False` |
| `DJANGO_SECRET_KEY` | Any string | Cryptographically random, 50+ chars |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Your domain (e.g., `api.bocra-demo.com`) |
| `DATABASE_URL` | Local PostgreSQL | EC2 PostgreSQL or AWS RDS |
| `REDIS_URL` | Local Redis | EC2 Redis |
| `EMAIL_BACKEND` | `console.EmailBackend` | `smtp.EmailBackend` |
| `CORS_ALLOWED_ORIGINS` | `localhost:3000` | Production frontend URL |
| `SECURE_SSL_REDIRECT` | `False` | `True` |

---

## Production Server Setup (AWS EC2)

### 1. Launch EC2 Instance

- **AMI**: Ubuntu Server 22.04 LTS
- **Instance type**: t3.small or t3.medium (minimum)
- **Security Group inbound rules**:
  - Port 22 (SSH) — your IP only
  - Port 80 (HTTP) — 0.0.0.0/0
  - Port 443 (HTTPS) — 0.0.0.0/0
- **Storage**: 20GB+ SSD

### 2. Connect and Update Server

```bash
ssh -i your-key.pem ubuntu@<EC2-PUBLIC-IP>

# Update packages
sudo apt-get update && sudo apt-get upgrade -y
```

### 3. Install System Dependencies

```bash
sudo apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    postgresql \
    postgresql-contrib \
    nginx \
    redis-server \
    certbot \
    python3-certbot-nginx \
    git \
    libpq-dev \
    python3-dev \
    gcc
```

### 4. Set Up PostgreSQL

```bash
sudo -u postgres psql

# Inside psql:
CREATE USER bocra WITH PASSWORD 'your-strong-password';
CREATE DATABASE bocra_db OWNER bocra;
GRANT ALL PRIVILEGES ON DATABASE bocra_db TO bocra;
\q
```

### 5. Start Redis

```bash
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

### 6. Deploy the Application

```bash
# Create app directory
sudo mkdir -p /var/www/bocra-backend
sudo chown ubuntu:ubuntu /var/www/bocra-backend
cd /var/www/bocra-backend

# Clone repo
git clone https://github.com/your-team/BOCRA-Backend.git .

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn

# Create .env file
cp .env.example .env
nano .env   # Set all production values

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Create superuser
python manage.py createsuperuser

# Seed demo data
python manage.py seed_data
```

---

## Gunicorn Configuration

### Gunicorn systemd Service

Create `/etc/systemd/system/bocra-gunicorn.service`:

```ini
[Unit]
Description=BOCRA Backend Gunicorn Daemon
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/var/www/bocra-backend
EnvironmentFile=/var/www/bocra-backend/.env
ExecStart=/var/www/bocra-backend/venv/bin/gunicorn \
    --workers 3 \
    --bind 127.0.0.1:8000 \
    --timeout 90 \
    --access-logfile /var/log/gunicorn/access.log \
    --error-logfile /var/log/gunicorn/error.log \
    bocra_backend.wsgi:application
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# Create log directory
sudo mkdir -p /var/log/gunicorn
sudo chown ubuntu:ubuntu /var/log/gunicorn

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable bocra-gunicorn
sudo systemctl start bocra-gunicorn

# Check status
sudo systemctl status bocra-gunicorn
```

### Gunicorn Workers

Number of workers formula: `2 * CPU_cores + 1`

```bash
# Check CPU count
nproc
# t3.small (2 vCPUs) → 5 workers
# t3.medium (2 vCPUs) → 5 workers
```

For Django Channels (WebSockets), use `uvicorn` workers:

```ini
ExecStart=/var/www/bocra-backend/venv/bin/gunicorn \
    --workers 3 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:8000 \
    bocra_backend.asgi:application
```

---

## Nginx Configuration

Create `/etc/nginx/sites-available/bocra-backend`:

```nginx
server {
    listen 80;
    server_name api.your-domain.com;

    # Redirect HTTP to HTTPS (uncomment after SSL setup)
    # return 301 https://$host$request_uri;

    client_max_body_size 50M;

    location /static/ {
        alias /var/www/bocra-backend/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /var/www/bocra-backend/mediafiles/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 90;
        proxy_send_timeout 90;
        proxy_read_timeout 90;
    }

    # WebSocket support for Django Channels
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
# Enable the site
sudo ln -s /etc/nginx/sites-available/bocra-backend /etc/nginx/sites-enabled/

# Test config
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

---

## SSL / HTTPS with Certbot

```bash
# Obtain certificate (replace with your actual domain)
sudo certbot --nginx -d api.your-domain.com

# Certbot will automatically update the Nginx config for HTTPS
# Auto-renewal is configured automatically

# Test auto-renewal
sudo certbot renew --dry-run
```

After Certbot runs, the Nginx config will be updated to handle HTTPS automatically, and HTTP will redirect to HTTPS.

---

## Celery as a System Service

### Celery Worker Service

Create `/etc/systemd/system/bocra-celery.service`:

```ini
[Unit]
Description=BOCRA Celery Worker
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/var/www/bocra-backend
EnvironmentFile=/var/www/bocra-backend/.env
ExecStart=/var/www/bocra-backend/venv/bin/celery \
    -A bocra_backend worker \
    -l info \
    --logfile=/var/log/celery/worker.log
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Celery Beat Service (Scheduler)

Create `/etc/systemd/system/bocra-celery-beat.service`:

```ini
[Unit]
Description=BOCRA Celery Beat Scheduler
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/var/www/bocra-backend
EnvironmentFile=/var/www/bocra-backend/.env
ExecStart=/var/www/bocra-backend/venv/bin/celery \
    -A bocra_backend beat \
    -l info \
    --logfile=/var/log/celery/beat.log
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# Create log directory
sudo mkdir -p /var/log/celery
sudo chown ubuntu:ubuntu /var/log/celery

# Enable and start services
sudo systemctl daemon-reload
sudo systemctl enable bocra-celery bocra-celery-beat
sudo systemctl start bocra-celery bocra-celery-beat

# Check status
sudo systemctl status bocra-celery
sudo systemctl status bocra-celery-beat
```

---

## CI/CD Pipeline

### GitHub Actions Workflow

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: bocra
          POSTGRES_PASSWORD: bocra
          POSTGRES_DB: bocra_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run linting
        run: |
          flake8 .
          black --check .

      - name: Run tests
        env:
          DATABASE_URL: postgres://bocra:bocra@localhost:5432/bocra_test
          REDIS_URL: redis://localhost:6379/0
          DJANGO_SECRET_KEY: test-secret-key-not-for-production
          DJANGO_DEBUG: "True"
        run: |
          pytest --cov=apps --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
      - name: Deploy to EC2
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.EC2_HOST }}
          username: ubuntu
          key: ${{ secrets.EC2_SSH_KEY }}
          script: |
            cd /var/www/bocra-backend
            git pull origin main
            source venv/bin/activate
            pip install -r requirements.txt
            python manage.py migrate --noinput
            python manage.py collectstatic --noinput
            sudo systemctl restart bocra-gunicorn
            sudo systemctl restart bocra-celery
            sudo systemctl restart bocra-celery-beat
```

### Required GitHub Secrets

| Secret | Value |
|---|---|
| `EC2_HOST` | EC2 public IP or domain |
| `EC2_SSH_KEY` | Contents of your `.pem` private key |

### Pipeline Stages

```
Push to GitHub
    │
    ▼
┌─────────────────┐
│   Lint Check    │  flake8 + black --check
└────────┬────────┘
         │ Pass
         ▼
┌─────────────────┐
│   Run Tests     │  pytest with PostgreSQL + Redis
└────────┬────────┘
         │ Pass
         ▼
┌─────────────────┐
│  Coverage Report│  Upload to Codecov
└────────┬────────┘
         │
         ▼ (main branch only)
┌─────────────────┐
│  SSH Deploy     │  git pull → migrate → collectstatic
│  to EC2         │  → restart Gunicorn, Celery
└─────────────────┘
```

---

## Useful Commands

### Service Management

```bash
# Restart all services after a deploy
sudo systemctl restart bocra-gunicorn bocra-celery bocra-celery-beat nginx

# View Gunicorn logs
sudo journalctl -u bocra-gunicorn -f
tail -f /var/log/gunicorn/error.log

# View Celery logs
tail -f /var/log/celery/worker.log

# View Nginx logs
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

### Application Management

```bash
cd /var/www/bocra-backend
source venv/bin/activate

# Pull latest code
git pull origin main

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Django shell
python manage.py shell

# Check for deployment issues
python manage.py check --deploy
```

---

## Production Checklist

| Item | Status | Command / Check |
|---|---|---|
| `DEBUG = False` | ⬜ | Check `.env` on server |
| `SECRET_KEY` is unique and long | ⬜ | `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `ALLOWED_HOSTS` set to domain | ⬜ | Only your domain — no `*` |
| Database migrations run | ⬜ | `python manage.py migrate` |
| Static files collected | ⬜ | `python manage.py collectstatic` |
| Superuser created | ⬜ | `python manage.py createsuperuser` |
| Demo data seeded | ⬜ | `python manage.py seed_data` |
| Gunicorn service running | ⬜ | `sudo systemctl status bocra-gunicorn` |
| Nginx service running | ⬜ | `sudo systemctl status nginx` |
| Celery worker running | ⬜ | `sudo systemctl status bocra-celery` |
| Celery beat running | ⬜ | `sudo systemctl status bocra-celery-beat` |
| HTTPS working | ⬜ | Certbot installed, certificate active |
| CORS configured | ⬜ | Only frontend origin allowed |
| Email sending works | ⬜ | Test password reset flow |
| File uploads work | ⬜ | Test document upload to S3 |
| API docs accessible | ⬜ | Visit `/api/docs/` |
| Admin panel accessible | ⬜ | Visit `/admin/` |
| `python manage.py check --deploy` clean | ⬜ | No critical warnings |
| All features work | ⬜ | Full E2E smoke test |

---

*BOCRA Digital Platform Deployment — v1.0 — March 2026*

# ===================
# Redis
# ===================
REDIS_URL=redis://redis:6379/0

# ===================
# JWT Settings
# ===================
JWT_ACCESS_TOKEN_LIFETIME=15
JWT_REFRESH_TOKEN_LIFETIME=10080

# ===================
# File Storage (MinIO for local, S3 for production)
# ===================
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
AWS_STORAGE_BUCKET_NAME=bocra-uploads
AWS_S3_ENDPOINT_URL=http://minio:9000
AWS_S3_USE_SSL=False

# ===================
# Email
# ===================
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=

# ===================
# CORS
# ===================
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### Environment Differences

| Setting | Development | Production |
|---|---|---|
| `DJANGO_DEBUG` | `True` | `False` |
| `DJANGO_SECRET_KEY` | Any string | Cryptographically random |
| `DATABASE_URL` | Local Docker Postgres | Managed Postgres (Railway) |
| `REDIS_URL` | Local Docker Redis | Managed Redis |
| `EMAIL_BACKEND` | `console.EmailBackend` | `smtp.EmailBackend` |
| `AWS_S3_ENDPOINT_URL` | MinIO (localhost:9000) | AWS S3 (remove this var) |
| `CORS_ALLOWED_ORIGINS` | localhost:3000 | Production frontend URL |
| `SECURE_SSL_REDIRECT` | `False` | `True` |

---

## CI/CD Pipeline

### GitHub Actions Workflow

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: bocra
          POSTGRES_PASSWORD: bocra
          POSTGRES_DB: bocra_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run linting
        run: |
          flake8 .
          black --check .

      - name: Run tests
        env:
          DATABASE_URL: postgres://bocra:bocra@localhost:5432/bocra_test
          REDIS_URL: redis://localhost:6379/0
          DJANGO_SECRET_KEY: test-secret-key-not-for-production
          DJANGO_DEBUG: "True"
        run: |
          pytest --cov=apps --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v4

      # Deploy to Railway / Render
      # Add deployment steps specific to your hosting provider
      - name: Deploy to production
        run: echo "Add deployment command here"
```

### Pipeline Stages

```
Push to GitHub
    │
    ▼
┌─────────────────┐
│   Lint Check     │  flake8 + black --check
└────────┬────────┘
         │ Pass
         ▼
┌─────────────────┐
│   Run Tests     │  pytest with PostgreSQL + Redis services
└────────┬────────┘
         │ Pass
         ▼
┌─────────────────┐
│  Coverage Report │  Upload to Codecov
└────────┬────────┘
         │
         ▼ (main branch only)
┌─────────────────┐
│    Deploy       │  Auto-deploy to Railway/Render
└─────────────────┘
```

---

## Cloud Deployment

### Railway Deployment

Railway provides easy Docker-based deployment with managed Postgres and Redis.

**Setup Steps:**

1. Create Railway account and project
2. Connect GitHub repository
3. Add services:
   - **Web** — from Dockerfile
   - **PostgreSQL** — Railway managed plugin
   - **Redis** — Railway managed plugin
4. Set environment variables in Railway dashboard
5. Configure custom domain (optional for demo)

**Railway-specific settings:**

```env
# Railway auto-injects these
DATABASE_URL=<auto-injected by Railway Postgres plugin>
REDIS_URL=<auto-injected by Railway Redis plugin>
PORT=<auto-injected>

# You set these
DJANGO_SECRET_KEY=<your-production-secret>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=your-project.up.railway.app
```

### Render Deployment

**Setup Steps:**

1. Create Render account
2. New Web Service → Connect GitHub repo
3. Build command: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
4. Start command: `gunicorn bocra_backend.wsgi:application`
5. Add PostgreSQL database (Render managed)
6. Add Redis instance (Render managed)
7. Set environment variables in Render dashboard

### Post-Deployment Steps

```bash
# Run on first deployment (or via deploy hook)
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_data          # Seed demo data
python manage.py collectstatic      # Collect static files
```

---

## Production Checklist

| Item | Status | Command / Check |
|---|---|---|
| `DEBUG = False` | ⬜ | Check environment variable |
| `SECRET_KEY` is unique | ⬜ | `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `ALLOWED_HOSTS` set | ⬜ | Only production domain(s) |
| Database migrations run | ⬜ | `python manage.py migrate` |
| Static files collected | ⬜ | `python manage.py collectstatic` |
| Superuser created | ⬜ | `python manage.py createsuperuser` |
| Demo data seeded | ⬜ | `python manage.py seed_data` |
| HTTPS working | ⬜ | Check browser padlock icon |
| CORS configured | ⬜ | Only frontend origin allowed |
| Email sending works | ⬜ | Test password reset flow |
| File uploads work | ⬜ | Test document upload |
| Celery worker running | ⬜ | Background emails sending |
| API docs accessible | ⬜ | Visit `/api/docs/` |
| Admin panel accessible | ⬜ | Visit `/admin/` |
| All features work | ⬜ | Full E2E smoke test |

---

*BOCRA Digital Platform Deployment — v1.0 — March 2026*
