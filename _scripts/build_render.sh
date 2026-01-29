#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input --settings=config.settings.product

# Run initial setup script (Reset DB, Migrate, Create Superuser, Load Sample Data)
# デプロイのたびにデータベースを最新の初期状態にリセットします
echo "🔄 Running setup script to initialize database..."
export DJANGO_SETTINGS_MODULE=config.settings.product
python _scripts/setup.py
