#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input --settings=config.settings.product

# Run migrations (Normal)
python manage.py migrate --settings=config.settings.product

# Run initial setup if INITIAL_SETUP environment variable is set to True
if [ "$INITIAL_SETUP" = "True" ]; then
    echo "🚀 Running initial setup script..."
    # setup.py 内部で設定ファイルを読み込めるよう環境変数を指定
    export DJANGO_SETTINGS_MODULE=config.settings.product
    python _scripts/setup.py
fi
