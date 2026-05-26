# Changelog

All notable changes to `django-poli-page` are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release scaffolding.

## [0.1.0] — TBD

### Added
- Django AppConfig with `settings.POLI_PAGE` validation at startup.
- Lazy singleton `django_poli_page.client` (SimpleLazyObject) wrapping the SDK's `PoliPage`.
- HTTP response helpers: `pdf_response`, `pdf_stream_response`, `preview_response`, `document_redirect_response`.
- Django signals (`poli_page_retry`, `poli_page_error`) bridging the SDK's `on_retry` / `on_error` hooks.
- `manage.py poli_page_render` management command for end-to-end smoke testing.
- Example Django 5 project at `example-app/` covering all 10 SDK demo steps, with an interactive dashboard at `/`.

[Unreleased]: https://github.com/poli-page/django/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/poli-page/django/releases/tag/v0.1.0
