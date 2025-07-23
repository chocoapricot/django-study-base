# Technology Stack

## Framework & Core
- **Django 5.0.4**: Main web framework
- **Python**: Backend language
- **SQLite**: Default database (configurable for MySQL)

## Key Dependencies
- `django-import-export`: Data import/export functionality
- `django-currentuser`: Track current user in models
- `pillow`: Image processing (profile photos)
- `requests`: HTTP client for API calls
- `openpyxl`: Excel file processing
- `pymupdf`: PDF processing (replaced pdfrw)
- `mysqlclient`: MySQL database connector (optional)

## Project Structure
- **Apps-based architecture**: Modular Django apps in `apps/` directory
- **Environment-specific settings**: Separate settings files for development/production
- **Custom user model**: Extended authentication via `apps.system.useradmin.CustomUser`

## Common Commands

### Environment Setup
```bash
# Activate virtual environment
.\venv\Scripts\Activate

# Install/upgrade dependencies
python.exe -m pip install --upgrade pip
pip list --outdated
pip install --upgrade <package>
```

### Database Operations
```bash
# Create migrations for all apps
python manage.py makemigrations dropdowns
python manage.py makemigrations useradmin
python manage.py makemigrations menu
python manage.py makemigrations parameters
python manage.py makemigrations staff
python manage.py makemigrations client
python manage.py makemigrations common
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Database shell access
python manage.py dbshell
```

### Data Management
```bash
# Export data to JSON
python manage.py dumpdata <app> --format=json --indent=4 > _sample_data/<app>.json

# Import data from JSON (ensure UTF-8 encoding)
python manage.py loaddata _sample_data/<app>.json
```

### Development
```bash
# Run development server
python manage.py runserver

# Run tests
python manage.py test apps.api.tests
```

## Configuration Notes
- Settings module: `config.settings.settings`
- Japanese localization (ja-JP, Asia/Tokyo)
- Static files served from `statics/` directory
- Templates in `templates/` directory with app-specific subdirectories