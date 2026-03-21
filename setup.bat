@echo off
echo BOCRA Digital Platform - Quick Setup
echo =====================================

echo.
echo 1. Setting up virtual environment...
python -m venv venv
call venv\Scripts\activate

echo.
echo 2. Installing dependencies...
pip install -r requirements.txt

echo.
echo 3. Setting up environment...
if not exist .env (
    copy .env.example .env
    echo Environment file created from template
)

echo.
echo 4. Setting up database (SQLite)...
python manage.py migrate

echo.
echo 5. Creating superuser...
python manage.py createsuperuser

echo.
echo =====================================
echo Setup Complete!
echo =====================================
echo.
echo Start development server with:
echo python manage.py runserver
echo.
echo Access at:
echo - API: http://localhost:8000
echo - Admin: http://localhost:8000/admin
echo - API Docs: http://localhost:8000/api/docs
echo.
pause
