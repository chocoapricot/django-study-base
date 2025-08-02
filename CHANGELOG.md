# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `apps/system/settings` application to consolidate system-wide settings.

### Changed
- Merged `apps/system/dropdowns`, `apps/system/menu`, and `apps/system/parameters` into the new `apps/system/settings` application.
- Updated all related imports and references throughout the codebase.
- Updated documentation to reflect the new application structure.

### Removed
- Deleted the old `apps/system/dropdowns`, `apps/system/menu`, and `apps/system/parameters` applications.
