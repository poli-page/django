# Changelog

All notable changes to `django-poli-page` are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release scaffolding.
- Error handler, on by default: at startup the app appends `django_poli_page.middleware.PoliPageErrorMiddleware` to `MIDDLEWARE`. A `PoliPageError` a view does not catch answers `application/json` with the SDK's `to_payload()` body, `{code, message, status, requestId}`, and its `status` (`503` for `network_error`, `504` for `timeout`, `500` when the error has none). Set `POLI_PAGE["ERROR_HANDLER"] = False` to turn it off.
- `pdf_stream_response` accepts the SDK stream as is (`pdf_stream_response(client.render.pdf_stream(input))`): it enters the stream at once, so a render or download error raises in the view and reaches the error handler, and closes it when the response is done. Any iterable of bytes is still accepted.
- Django 6.0 support: classifier and CI legs (Python 3.12+). CI now also runs Django 5.2 on Python 3.11.
- A change of the `POLI_PAGE` setting (`override_settings` in tests) resets the lazy `client`, so the next access builds it from the new settings.
- Contract tests: `example-app/tests/test_contract.py` runs the API contract's integration cases (`impl.*`) against the example app. CI runs them against the pinned `poli-page/api-contract` v1.3.0, and Dependabot proposes each new contract version.

### Changed
- CI: the live API job runs on `main` (and on demand) against the production API with the sandbox key from the `POLI_PAGE_API_KEY` secret, and skips with a notice when the key is absent or not a `pp_sandbox_` key.
- **Breaking:** API keys are per environment (`pp_sandbox_…`, `pp_live_…`, or `pp_{environment}_…` for an environment created on Pro+). `AppConfig.ready()` no longer raises `ImproperlyConfigured` on a key that does not start with `pp_test_` or `pp_live_`. A missing `POLI_PAGE` setting or an empty `API_KEY` still raises. Any other key that does not match `pp_{environment}_{32 lowercase hex}` now emits one warning, which shows no part of the key (not even its `pp_{environment}_` prefix), and the app starts anyway: the API decides whether the key is valid. When `API_KEY` is absent, the `POLI_PAGE_API_KEY` env var the SDK falls back to gets the same check.
- **Breaking:** renders carry no template version. The API key's environment selects the published copy of the project. `manage.py poli_page_render` takes `--project` and `--template` and sends a `RenderInput` with no `version`.
- **Breaking:** `preview_response` accepts only a `DocumentPreviewResult` (from `client.documents.preview(id)`).
- The integration test runs only with a `pp_sandbox_…` key.
- **Breaking:** requires the `poli-page` SDK 0.11.0 (`poli-page>=0.11.0,<2`, from PyPI), the first release with environment API keys and no template versions.
- Example app: `GET /render/stream` hands the SDK stream to `pdf_stream_response`, so a render error answers the handler's JSON instead of a `200` PDF with an empty body.
- Example app: renders send no `version`, and the error demo is `GET /errors/not-found`. It renders the template `does-not-exist` and lets the error reach the default error handler, which answers `404 TEMPLATE_NOT_FOUND` with the `to_payload()` body. The example project's own error middleware is removed.
- CI installs the SDK from PyPI (no sdk-python checkout), builds and checks the example app, and runs each matrix leg's unit tests on that leg's Django version.

### Removed
- **Breaking:** `manage.py poli_page_render` options `--template-version`, `--preview` and `--html`. The SDK no longer has `render.preview()` or inline templates.
- Example app: `GET /render/preview` with its dashboard button and README row, and `GET /errors/bad-version` (`INVALID_VERSION_FORMAT` no longer exists).

### Fixed
- `pdf_response` / `pdf_stream_response`: the `Content-Disposition` filename is now escaped per RFC 6266 / RFC 9110 (`\` and `"` as quoted-pairs, ASCII fallback included) and stripped of control characters (CR/LF, TAB, DEL, C1), so a filename can no longer break the header or inject parameters.

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
