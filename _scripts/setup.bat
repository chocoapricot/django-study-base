@echo off
rem
rem 開発環境のセットアップスクリプト
rem データベースのリセット、スーパーユーザーの作成、サンプルデータのロードを一度に実行します。
rem

echo [INFO] Starting development environment setup...

rem --- STEP 1: Reset Database ---
echo [STEP 1/4] Resetting database...
python _scripts/reset_database.py
if %errorlevel% neq 0 (
    echo [ERROR] Failed to reset database.
    goto :eof
)
echo [SUCCESS] Database reset successfully.

rem --- STEP 2: Set Superuser Password ---
echo [STEP 2/4] Setting up superuser credentials...
set DJANGO_SUPERUSER_PASSWORD=admin
echo [SUCCESS] Superuser password set as environment variable.

rem --- STEP 3: Create Superuser ---
echo [STEP 3/4] Creating superuser (admin / admin@test.com)...
python manage.py createsuperuser --noinput --username admin --email admin@test.com
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create superuser.
    goto :eof
)
echo [SUCCESS] Superuser created successfully.

rem --- STEP 4: Load Sample Data ---
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
