# BOCRA Digital Platform - Quick Setup
Write-Host "BOCRA Digital Platform - Quick Setup" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green

Write-Host "`n1. Setting up virtual environment..." -ForegroundColor Yellow
python -m venv venv
& .\venv\Scripts\Activate.ps1

Write-Host "`n2. Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

Write-Host "`n3. Setting up environment..." -ForegroundColor Yellow
if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "Environment file created from template" -ForegroundColor Green
}

Write-Host "`n4. Setting up database (SQLite)..." -ForegroundColor Yellow
python manage.py migrate

Write-Host "`n5. Creating superuser..." -ForegroundColor Yellow
python manage.py createsuperuser

Write-Host "`n=====================================" -ForegroundColor Green
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host "`nStart development server with:" -ForegroundColor Cyan
Write-Host "python manage.py runserver" -ForegroundColor White
Write-Host "`nAccess at:" -ForegroundColor Cyan
Write-Host "- API: http://localhost:8000" -ForegroundColor White
Write-Host "- Admin: http://localhost:8000/admin" -ForegroundColor White
Write-Host "- API Docs: http://localhost:8000/api/docs" -ForegroundColor White
Write-Host ""
Read-Host "Press Enter to continue"
