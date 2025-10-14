# AGENTS.md

This file provides guidance for AI agents working on this codebase.

## Project Overview

This is a Django-based web application called "django-study-base", a business management system with the following key features:

- **Staff Management**: Manage and track employee data
- **Client Management**: Customer relationship management functionality
- **Contract Management**: Manage and track client and staff contracts
- **Company/Department Management**: Systematic management of company information and departments
- **Connection Management**: Connection request/approval function with staff and client representatives
- **Profile Management**: User profiles, "My Number" management
- **Master Management**: Master data management for qualifications, skills, banks/branches, payment terms, etc.
- **System Management**: User management, menus, parameters, dropdown settings
- **API Layer**: RESTful API endpoints for data access
- **Authentication**: Custom user authentication with role-based access

This application is designed for Japanese users (ja-JP locale, Asia/Tokyo timezone) and includes data import/export for business workflows, PDF generation, and Excel integration features.

### Key Business Areas
- Staff management and contact tracking, qualification/skill management
- Client relationship management, department/contact person management
- Contract management (creation, update, deletion, status tracking of client and staff contracts)
- Company/Department management (corporate number search, postal code search, change history tracking)
- Connection management (connection requests/approvals with staff/client representatives, automatic permission granting)
- Profile management (`StaffProfile`, `StaffProfileMynumber`)
- Master data management (qualifications, skills, banks/branches, payment terms, company banks)
- System settings (dropdowns, menus, parameters), user management, and log management
- **Unified Change History Management**: Tracking and displaying all data changes using the AppLog system
- Common utilities and shared functions
- CSS test environment for UI development

### Change History Management Features
- **Unified Approach**: Uses the same history management system for all models (staff, clients, contracts, etc.)
- **Detailed Screen Integration**: A change history section is standard on the detail screen of each entity
- **Operation Tracking**: Automatically records create, update, and delete operations, saving the operator and timestamp
- **Visual Display**: Intuitive history display using badges and tables

## Build and Test Commands

Use the following commands to set up the development environment and run the application.

- **Install dependencies:**
  ```bash
  pip install -r requirements.txt
  ```

- **Run tests:**
  ```bash
  python manage.py test
  ```

- **Run development server:**
  ```bash
  python manage.py runserver
  ```

## Code Style Guidelines

## Line Ending Unification Rule
- **Windows Environment**: Use CRLF (\r\n) for all files
- **Git Configuration**: `git config core.autocrlf true` is already set
- **Target Files**: All Python, HTML, CSS, JavaScript, Markdown, and configuration files
- **Reason**: Consistency in the Windows environment and to avoid Git warnings

## HTML/Template Editing Policy
- **Line Break Limit**: Do not break lines until about 200 characters
- **Keep Comments**: Do not delete existing comments without permission
- **Preserve Formatting**: Maintain the original file's line break structure
- **Minimal Modifications**: Make only the minimum necessary modifications

## Basic Principles for File Editing
1. Respect the original format
2. Avoid unnecessary line breaks or whitespace changes
3. Preserve comments and descriptions
4. Focus only on functional modifications
5. Unify line endings to CRLF

## Template Files (HTML)
- Write long attribute lists on a single line if they are within 200 characters
- Maintain existing indentation levels
- Preserve comments (<!-- -->)
- Do not add unnecessary blank lines

## Bootstrap Button Style Unification
- **Mandatory Rule**: Add the `btn-sm` class to all buttons
- **Examples**: `class="btn btn-sm btn-primary"`, `class="btn btn-sm btn-secondary"`
- **Target**: All form buttons, link buttons, and action buttons
- **Exception**: Exceptions are allowed only for special reasons

## Back Button Placement Rule
- **Basic Principle**: Place the back button at the bottom left within the content
- **Forbidden**: Placing the back button in the card-footer is prohibited
- **card-footer allowed**: Auxiliary links such as "Show All" can use card-footer
- **Recommended Layout**:
  ```html
  <div class="row mt-3">
      <div class="col text-left">
          <a href="..." class="btn btn-sm btn-secondary">Back</a>
      </div>
  </div>
  ```
- **Reference**: Comply with the layout of the client change history list

## Form Design Unification Rule
- **Label Placement**: Right-align with `col-form-label` + `text-align:right`
- **Label Style**: Do not use bold (`<strong>`), use normal font weight
- **Input Field Size**: Add the `form-control-sm` class to all input fields
- **Button Separation**: Place API call buttons in a separate column from input fields
- **Recommended Layout**:
  ```html
  <div class="row mb-3 align-items-center">
      <label for="..." class="col-sm-2 col-form-label" style="text-align:right">Label</label>
      <div class="col-sm-4">
          <input class="form-control form-control-sm" ...>
      </div>
      <div class="col-sm">
          <button type="button" class="btn btn-sm btn-secondary">Button</button>
      </div>
  </div>
  ```
- **Reference**: Comply with the layout of the client form

## Tooltip Unification Rule
- **Use Template Tag**: Use the custom template tag `{% load help_tags %}` (automatically loaded in _base.html)
- **Basic Usage**:
  ```html
  <!-- Using preset help text -->
  <label>Label Name {% my_help_preset "corporate_number" %}</label>

  <!-- Using custom help text -->
  <label>Label Name {% my_help_icon "Custom description" %}</label>

  <!-- Specifying placement (default is top) -->
  {% my_help_preset "postal_code" "right" %}
  ```
- **Available Presets**:
  - `corporate_number`: 13-digit half-width number without hyphens
  - `postal_code`: 7-digit half-width number without hyphens
  - `gbiz_api`: Obtained from the Ministry of Economy, Trade and Industry's gBizINFO-API
  - `postal_api`: Obtained from a free postal code API
  - `staff_selection`: Only staff with a registered employee number and hire date can be selected
  - `client_selection`: Only clients with a registered basic contract date can be selected
  - `hire_date`: Cannot register a contract without registering a hire date
  - `employee_no`: Up to 10 half-width alphanumeric characters (can be blank), cannot register a contract without registering an employee number
  - `bank_code`: Enter as a 4-digit number (optional)
  - `branch_code`: Enter as a 3-digit number (optional)
  - `account_number`: Enter as a 1-8 digit number
  - Many others (see HELP_TEXTS in `apps/common/templatetags/help_tags.py`)
- **Adding New Presets**: Add to the HELP_TEXTS dictionary in `apps/common/templatetags/help_tags.py`
- **Directly writing is deprecated**: Please use the new template tags

## Delete Button Unification Rule
- **All Delete Buttons**: Use `btn-dark` for unification
- **Target**:
  - Delete buttons on detail screens
  - Icon delete buttons on list screens
  - Execute buttons on delete confirmation screens
- **Reason**:
  - Emphasize visual unity throughout the project
  - `btn-danger` is reserved for high-urgency errors and alerts
- **Recommended Implementation**:
  ```html
  <!-- Detail screen -->
  <a href="..." class="btn btn-sm btn-dark">Delete</a>

  <!-- Delete confirmation screen -->
  <button type="submit" class="btn btn-sm btn-dark">Delete</button>

  <!-- Icon on list screen -->
  <a href="..." class="btn btn-dark btn-sm" title="Delete">
      <i class="bi bi-x"></i>
  </a>
  ```

## Delete Confirmation Screen Alert Message Rule
- **Required Element**: Display a warning alert on all delete confirmation screens
- **Alert Class**: Use `alert alert-warning`
- **Icon**: Use `bi-exclamation-triangle-fill`
- **Message**: Must include "This action cannot be undone."
- **Recommended Implementation**:
  ```html
  <div class="alert alert-warning" role="alert">
      <i class="bi bi-exclamation-triangle-fill"></i>
      Are you sure you want to delete [Target]? This action cannot be undone.
  </div>
  ```
- **Placement**: Place at the beginning of the card body
- **Purpose**: To clearly inform the user of the importance and irreversibility of the delete operation

## Form Widget Unification Rule
- **Required Class**: Apply `form-control form-control-sm` to all form input fields
- **Text Input**: `forms.TextInput(attrs={'class': 'form-control form-control-sm'})`
- **Text Area**: `forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3})`
- **URL Input**: `forms.URLInput(attrs={'class': 'form-control form-control-sm'})`
- **Select**: `forms.Select(attrs={'class': 'form-control form-control-sm'})`

## Recommended Column Width Settings
- **Label**: `col-sm-2` (fixed)
- **Short Input Field**: `col-sm-3` (e.g., postal code)
- **Medium Input Field**: `col-sm-4` (e.g., corporate number)
- **Standard Input Field**: `col-sm-6` (e.g., name)
- **Long Input Field**: `col-sm-8` (e.g., URL, memo)
- **Max Width Input Field**: `col-sm-10` (e.g., address)
- **For Buttons**: `col-sm` (auto-adjusts remaining width)

## Python Files
- Comply with PEP 8
- Actively use Japanese comments
- Write docstrings in Japanese
- Variable and function names in English

## JavaScript Files
- Match existing style
- Write comments in Japanese
- Avoid unnecessary line breaks

## CSS Files
- Maintain existing format
- Preserve comments
- Do not change the order of properties
##
 Change History Display Unification Rule
- **Placement**: Place at the bottom of the detail screen
- **Title**: Unify as "Change History"
- **Table Structure**: 5-column structure: Target, Operation, Changes, Changed By, Date
- **Badge Style**:
  - Target: Color-coded by model (Basic Info=primary, Qualification=info, Skill=success, Contract Info=primary/success)
  - Operation: Create=success, Edit=warning, Delete=danger
- **Date Format**: Unify as `Y/m/d H:i:s`
- **Data Source**: Use the `AppLog` model and display only `create`, `update`, and `delete` operations
- **Number of Items Limit**: Display up to the latest 10 items
- **Empty State**: Display "No change history" message
- **Recommended Implementation**:
  ```html
  <!-- Change History -->
  <div class="content-box card bg-light mt-2 mb-4" style="max-width: 100%;">
      <div class="card-header d-flex justify-content-between align-items-center">
          Change History
      </div>
      <div class="card-body mb-0">
          <table class="table table-hover me-2 mt-2 mb-0" style="border-top: 1px solid #ddd;">
              <!-- Table content -->
          </table>
      </div>
  </div>
  ```
## Test Procedures

Since you cannot run with pytest, please use the `python manage.py test` command.

## Test File Structure Rules

### Basic Principles
- **Tests must always be placed in the `tests/` directory**
- Do not use the single file format (`tests.py`)
- Split test files by functionality to improve maintainability

### Directory Structure
```
apps/
└── [app_name]/
    ├── tests/
    │   ├── __init__.py
    │   ├── test_models.py      # Model tests
    │   ├── test_views.py       # View tests
    │   ├── test_forms.py       # Form tests
    │   ├── test_utils.py       # Utility tests
    │   └── test_[feature].py   # Feature-specific tests
    ├── models.py
    ├── views.py
    └── forms.py
```

### File Naming Convention
- Start test file names with `test_`
- Include the name of the feature or module being tested
- Examples: `test_staff_form.py`, `test_client_views.py`, `test_contract_models.py`

### Test Class Naming Convention
- End test class names with `Test`
- Clearly indicate the target of the test
- Examples: `StaffFormTest`, `ClientViewTest`, `ContractModelTest`

### Test Method Naming Convention
- Start test method names with `test_`
- Descriptively write the content of the test
- Explain the test content with a Japanese docstring
- Example:
  ```python
  def test_staff_create_with_valid_data(self):
      """Test that staff creation succeeds with valid data"""
      pass
  ```

## Existing App Test Structure Example

### ✅ Good Example (Recommended)
```
apps/staff/tests/
├── __init__.py
├── test_models.py
├── test_views.py
├── test_forms.py
├── test_staff_form.py
├── test_staff_qualification.py
├── test_staff_skill.py
├── test_staff_sorting.py
└── test_staff_regist_status_filter.py
```

### ❌ Bad Example (Not Recommended)
```
apps/api/
└── tests.py  # Do not use single file format
```

## Test Execution Commands

### Run tests for the entire app
```bash
python manage.py test apps.staff.tests
```

### Run a specific test file
```bash
python manage.py test apps.staff.tests.test_staff_form
```

### Run a specific test class
```bash
python manage.py test apps.staff.tests.test_staff_form.StaffFormTest
```

### Run a specific test method
```bash
python manage.py test apps.staff.tests.test_staff_form.StaffFormTest.test_valid_data
```

## Test Data Management

### Fixture Files
- Place JSON fixtures in the `_sample_data/` directory
- Centrally manage sample data used in tests

### Test Database
- A test database is automatically created when tests are run
- It is automatically deleted after the tests are finished

## Coverage Goals

### Minimum Test Coverage
- **Models**: All custom methods and validations
- **Forms**: All validation rules
- **Views**: Main CRUD operations
- **Utilities**: All public methods

### Test Types
1. **Unit Tests**: Test individual functions
2. **Integration Tests**: Test the interaction between multiple components
3. **Functional Tests**: Test user operation flows

## Logic Information Display System

### Overview
This system provides users with information about validation logic and automatic processing for each page through a modal interface.

### Implementation Rules
- **Coffee Cup Icon**: Display in the header to indicate the presence/absence of page logic information
  - `bi-cup`: No logic information (empty cup)
  - `bi-cup-hot`: Logic information available (steaming cup)
- **Modal Display**: Click to show page-specific validation logic
- **Category Classification**:
  - **Single Item Check**: Individual field validation
  - **Correlation Check**: Relationship checks between multiple fields
  - **Automatic Processing**: System automatic conversion/acquisition processing
- **Unified Design**: Organized in card format with shadows for visual distinction

### Technical Implementation
1. **Base Template Setup**: Add modal structure and JavaScript to `templates/common/_base.html`
2. **Page-Specific Logic**: Add logic information in each form template's JavaScript
3. **Icon State Management**: Use `data-has-logic` attribute to control icon state
4. **Content Structure**: Use card-based layout with consistent styling

### Maintenance Rule
**IMPORTANT**: When adding or modifying validation logic or automatic processing in forms, always update the corresponding logic information display. This ensures users have accurate information about page behavior.

### Example Implementation
```javascript
// Set page logic information
document.addEventListener('DOMContentLoaded', function() {
    // Notify that this page has logic information
    document.body.setAttribute('data-has-logic', 'true');

    const logicContent = document.getElementById('logic-info-content');
    if (logicContent) {
        logicContent.innerHTML = `
            <!-- Logic information content -->
        `;
    }

    // Notify completion of logic information setup
    document.dispatchEvent(new Event('logicInfoSet'));
});
```
