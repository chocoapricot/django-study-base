@echo off

echo [INFO] Starting development environment setup...

echo [STEP 1/4] Resetting database...
python _scripts/reset_database.py
if %errorlevel% neq 0 (
    echo [ERROR] Failed to reset database.
    goto :eof
)
echo [SUCCESS] Database reset successfully.

echo [STEP 2/4] Setting up superuser credentials...
set DJANGO_SUPERUSER_PASSWORD=passwordforstudybase!
echo [SUCCESS] Superuser password set as environment variable.

echo [STEP 3/4] Creating superuser (admin / admin@test.com)...
python manage.py createsuperuser --noinput --username admin --email admin@test.com
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create superuser.
    goto :eof
)
echo [SUCCESS] Superuser created successfully.

echo [STEP 4/4] Loading sample data...
python _scripts/load_sample_data.py
if %errorlevel% neq 0 (
    echo [ERROR] Failed to load sample data.
    goto :eof
)
echo [SUCCESS] Sample data loaded successfully.

echo.
echo [COMPLETE] Development environment setup is complete.
echo You can now run the server with 'python manage.py runserver'.
