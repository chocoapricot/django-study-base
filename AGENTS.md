# AGENTS.md

This file provides guidance for AI agents working with this codebase.

## Project overview

This is a Django-based web application. Based on the project structure, it appears to be a comprehensive system for managing clients, staff, contracts, and company information. It includes features for user authentication, data management, and potentially reporting.

## Build and test commands

To set up the development environment and run the application, use the following commands:

- **Install dependencies:**
  ```bash
  pip install -r requirements.txt
  ```

- **Run tests:**
  ```bash
  python manage.py test
  ```

- **Run the development server:**
  ```bash
  python manage.py runserver
  ```

## Code style guidelines

This project follows the **PEP 8** style guide for Python code. To ensure consistency, we use the following tools:

- **Black:** For automated code formatting.
- **Flake8:** For linting and identifying potential issues.

Before committing any changes, please ensure your code is formatted with Black and passes Flake8 checks.

## Testing instructions

To run the full test suite, use the following command:

```bash
python manage.py test
```

You can also run tests for a specific app:

```bash
python manage.py test apps.app_name
```

For example, to run tests for the `client` app:

```bash
python manage.py test apps.client
```

New tests should be added to the `tests.py` file within the relevant app's directory, or in a `tests` subdirectory for more complex test suites.

## Security considerations

When working on this project, please keep the following security best practices in mind:

- **Keep dependencies updated:** Regularly update dependencies to patch security vulnerabilities.
- **Do not expose `SECRET_KEY`:** Ensure the `SECRET_KEY` is not hardcoded in settings files and is loaded from environment variables in production.
- **Use Django's security features:** Leverage built-in protections against common vulnerabilities like Cross-Site Scripting (XSS), Cross-Site Request Forgery (CSRF), and SQL Injection.
- **Data validation:** Always validate and sanitize user-provided data to prevent security risks.
- **Permissions and access control:** Ensure that views and API endpoints have appropriate permission checks to prevent unauthorized access.
