# Project Structure

## Root Directory Layout
```
django-study-base/
├── apps/                    # Django applications (modular components)
├── config/                  # Project configuration
├── templates/               # HTML templates organized by app
├── statics/                 # Static assets (CSS, JS, fonts)
├── _sample_data/           # JSON fixtures for data import/export
├── venv/                   # Python virtual environment
├── manage.py               # Django management script
└── db.sqlite3             # SQLite database file
```

## Apps Directory Structure
Each app follows Django conventions with these standard files:
- `models.py`: Database models
- `views.py`: View logic
- `urls.py`: URL routing
- `forms.py`: Form definitions
- `admin.py`: Django admin configuration
- `apps.py`: App configuration
- `migrations/`: Database migration files

### Application Modules
- **`apps/system/`**: Core system functionality
  - `dropdowns/`: Dropdown/select options management
  - `useradmin/`: Custom user management and authentication
  - `menu/`: Navigation menu system
  - `parameters/`: System configuration parameters
- **`apps/staff/`**: Employee management
- **`apps/client/`**: Customer relationship management
- **`apps/api/`**: REST API endpoints
- **`apps/common/`**: Shared utilities and common functionality
- **`apps/home/`**: Homepage and landing pages
- **`apps/csstest/`**: CSS testing and development

## Configuration Structure
```
config/
├── settings/
│   ├── settings.py         # Main settings
│   ├── develop.py          # Development-specific settings
│   └── product.py          # Production-specific settings
├── urls.py                 # Root URL configuration
├── wsgi.py                 # WSGI application
└── asgi.py                 # ASGI application
```

## Templates Organization
Templates are organized by application with shared templates in common:
```
templates/
├── common/                 # Shared templates
├── registration/           # Authentication templates
├── home/                   # Homepage templates
├── staff/                  # Staff management templates
├── client/                 # Client management templates
└── useradmin/             # User administration templates
```

## Static Assets
```
statics/
├── css/                    # Stylesheets
├── js/                     # JavaScript files
└── fonts/                  # Font files
```

## Naming Conventions
- **Apps**: Lowercase, descriptive names (e.g., `staff`, `client`)
- **Models**: PascalCase (e.g., `CustomUser`)
- **URLs**: Lowercase with hyphens (e.g., `/staff/contact-list/`)
- **Templates**: Lowercase with underscores (e.g., `staff_list.html`)
- **Static files**: Organized by type in respective subdirectories

## Import Patterns
- Use relative imports within apps: `from .models import MyModel`
- Use absolute imports for cross-app references: `from apps.common.utils import helper_function`
- System apps are referenced as: `apps.system.useradmin.models.CustomUser`