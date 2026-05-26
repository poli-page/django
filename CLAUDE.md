# CLAUDE.md

> Instructions for Claude Code agents working in `poli-page/django`.

## 1. Repo at a glance

| Field        | Value |
| ------------ | ----- |
| Repository   | `poli-page/django` |
| Type         | Framework integration (Django reusable app) |
| Language     | Python 3.10+ |
| Django       | 4.2 LTS, 5.0, 5.1, 5.2 LTS |
| Registry     | PyPI — `django-poli-page` |
| Depends on   | `poli-page` (PyPI; `^1.0`) |
| Roadmap slot | P1.3 |

**Source-of-truth docs (read first):**
- `docs/spec/django-app-specification.md` — full design spec for v0.1.0
- `docs/plan/2026-05-26-implementation.md` — implementation plan
- `/Users/mickael/Projects/INTEGRATIONS_PLAN.md` — cross-repo umbrella note, esp. §"Cross-cutting DX patterns"
- `/Users/mickael/Projects/symfony-bundle/CLAUDE.md` — closest structural model (DI/config tree/AppConfig parallels)
- `/Users/mickael/Projects/nextjs/CLAUDE.md` §10 — battle-tested cross-cutting gotchas

## 2. The app's job

This package is a **thin reusable Django app** that wraps the official Poli Page Python SDK (`poli-page` on PyPI, source at `/Users/mickael/Projects/sdk-python/`). It provides:

- A Django app installable via `INSTALLED_APPS = [..., "django_poli_page"]`
- A `settings.POLI_PAGE` config dict, validated at startup by `AppConfig.ready()`
- A lazy singleton: `from django_poli_page import client` returns a `SimpleLazyObject` wrapping the SDK's `PoliPage` — initialised on first access, not at import-time
- `django_poli_page.http` response helpers — `FileResponse` for PDFs, `StreamingHttpResponse` for streamed PDFs, `HttpResponse` for HTML previews, `HttpResponseRedirect` for presigned document URLs
- Django signals (`poli_page_retry`, `poli_page_error`) bridging the SDK's `on_retry` / `on_error` hooks
- A management command `python manage.py poli_page_render` for smoke-testing config
- An example Django project at `example-app/` with an interactive demo dashboard at `/`

**This app does NOT** reimplement HTTP transport, retries, error mapping, idempotency, stream chunking, or anything else the SDK already does. Bug in those areas? Fix it in `sdk-python`, not here.

**This app does NOT** ship: a database model, REST framework integration, a Channels consumer, a generic class-based view, or a templatetag library. See `docs/spec/django-app-specification.md` §1 for the explicit "isn't" list.

## 3. Working language

- **Code, comments, file names, commit messages, PR descriptions, repository documentation**: English.
- **Day-to-day conversation with Xavier/Mickael**: French, tutoiement.
- **Conversation in this Claude Code session**: French is fine for the chat; artifacts stay English.

## 4. TDD is mandatory

RED → GREEN → refactor for every change. Tests live in `tests/unit/` (mocked SDK, 95%+ of the suite) and `tests/integration/` (one happy-path test against `api-develop.poli.page`, gated on `POLI_PAGE_API_KEY`).

### What to test (integration-specific!)
- **AppConfig validation**: missing `POLI_PAGE` setting → `ImproperlyConfigured`; missing `API_KEY` → `ImproperlyConfigured`; bad-prefix key (no `pp_test_` / `pp_live_`) → `ImproperlyConfigured`; out-of-range `TIMEOUT` / `RETRIES.*` → `ImproperlyConfigured`.
- **Lazy client**: `from django_poli_page import client; client._setup()` does not run until first attribute access; settings overridden by `@override_settings` are picked up on next access.
- **Response helpers**: `pdf_response`, `pdf_stream_response`, `preview_response`, `document_redirect_response` each set the right `Content-Type`, RFC 5987 `Content-Disposition`, `Cache-Control`, `X-Content-Type-Options`. ASCII AND non-ASCII filenames both encode correctly.
- **Management command**: option parsing, JSON data parsing, exit codes for `PoliPageError` families (4xx → 1, 5xx → 2, network → 3). Verified via `call_command(...)` + `StringIO`.
- **Signals**: when the SDK's `on_retry` callable fires, `poli_page_retry` is sent with the `RetryEvent`. Same for `poli_page_error`.

### What NOT to test (the SDK already does)
- HTTP transport behaviour (`httpx` edge cases, connection pooling)
- Retry policy (backoff, max attempts, `Retry-After`, never-retry-4xx)
- 4xx / 5xx → `PoliPageError` subclass mapping
- Idempotency-Key generation
- Stream chunking correctness
- API contract drift — the SDK's contract tests own that

Re-testing these here doubles maintenance burden. **If you find yourself writing a mock HTTP server with `respx`, stop — you're doing the SDK's job.**

## 5. Robustness over shortcuts

Mickael's hard rule (validated across symfony-bundle and nextjs sessions): **no hacks to make a test pass or a corner case go away**. Fix root causes. If a workaround is genuinely required (framework bug, SDK quirk), document it inline with a `# Why:` comment naming the constraint.

Concretely: **no `# type: ignore`, no `# noqa` to silence warnings, no `pytest.skip` to mask flakes**. The skip we DO allow is `pytest.mark.skipif(os.getenv("POLI_PAGE_API_KEY") is None)` for the gated integration test — that one is by design.

## 6. Code conventions

- **ruff** for linting AND formatting. Config in `pyproject.toml`, mirrors the SDK's rules: `select = ["E", "F", "W", "I", "B", "UP", "RUF", "SIM", "DJ"]` (the `DJ` ruleset is Django-specific).
- **mypy strict mode** + `django-stubs`. Configured in `pyproject.toml`.
- **No commented-out code, no `TODO` without a linked issue, no `print()` in committed code** (use the `poli_page` logger).
- **Default to no comments.** Add one only when the *why* is non-obvious. Comments restating *what* the code does are noise.
- **`from __future__ import annotations`** at the top of every module — keeps `django-stubs` happy on `4.2`/`5.0`.

## 7. Commits and PRs

- **Conventional Commits**: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`.
- **One concern per PR**, reviewable in under 30 minutes.
- PR description: what changed, why, how it was tested.
- CI must be green before merge.

## 8. CI

Workflow: `.github/workflows/ci.yml`. Matrix: Python `3.10`/`3.11`/`3.12`/`3.13` × Django `4.2`/`5.0`/`5.1`/`5.2`, with `tox-gh-actions` slicing per-Python (avoids a 16-cell grid). Each step auto-skips if the relevant config file is missing (so a freshly scaffolded repo is green from day one). Don't change that behaviour.

Local mirror:
```bash
uv sync --all-extras
uv run ruff check .
uv run ruff format --check .
uv run mypy src tests
uv run pytest
```

## 9. Unpublished-SDK note (dev-time only)

The Python SDK (`poli-page` on PyPI) is **already published**, so for normal dev you just `uv sync` / `pip install -e .[dev]`. When iterating against unreleased SDK changes, install the local checkout in editable mode:

```bash
uv pip install -e ../sdk-python    # from inside the django repo's venv
```

The integration's `pyproject.toml` stays clean (`"poli-page>=1.0,<2"`). When the SDK ships a new version, just bump the pin — no source-code changes here.

## 10. Known gotchas (battle-tested — don't relearn the hard way)

These caught us once in `symfony-bundle` / `nextjs` or surface from Django / pytest-django specifics. Recorded so future agents don't burn a session rediscovering them.

### 10.1 Django management commands reserve a fixed set of option names

`django.core.management.base.BaseCommand` registers these on every command BEFORE `add_arguments()` runs:

```
--verbosity / -v   --settings   --pythonpath   --traceback
--no-color   --force-color   --skip-checks
```

Declaring a custom option named `--verbosity` or `-v` silently shadows the built-in and breaks `manage.py help <cmd>`. The symfony-bundle hit the equivalent on Symfony Console (`--version` reserved as `-V`) and had to rename to `--template-version` — same lesson here.

**Pattern**: prefix option names with the noun they describe (`--template-version`, not `--version`). Audit `add_arguments()` against the list above before adding anything.

### 10.2 Signal-handler / pytest fixture leak hygiene

pytest-django flags global-state leaks between tests. Two specific hazards:

1. **`signal.signal(SIGINT, ...)` handlers** — Django's `runserver` and management commands register them. If a test installs one and doesn't restore the previous handler, the next test sees the leak.
2. **Django signal receivers** — `poli_page_retry.connect(my_listener)` in test setup must be balanced by `disconnect(...)` in teardown, or the receiver leaks into the next test.

**Fix in place**: `tests/conftest.py` ships an autouse `restore_signal_handlers` fixture that snapshots `signal.getsignal(SIGINT)` and Django's `poli_page_retry` / `poli_page_error` receiver lists in setup, then unwinds in teardown. Apply to any test that calls `signal.signal(...)` or `<signal>.connect(...)`.

Pattern carried from `symfony-bundle/tests/RestoresGlobalHandlers.php` (PHP equivalent) and `nextjs/tests/setup.ts` (`process.on(...)` equivalent). Documented as cross-cutting in `INTEGRATIONS_PLAN.md` §4.

**Do NOT** "fix" this by disabling pytest-django's strictness. Same rule as symfony-bundle §10.1 and nextjs §10.1.

### 10.3 Single root `.env`, no per-app `.env.local`

Both the test runner (`tests/conftest.py`) and the example project (`example-app/manage.py`, `example-app/example_project/settings.py`) load the repo-root `.env` via a tiny hand-rolled parser (or `python-dotenv` if already installed), **only when the variable isn't already set in `os.environ`**. Real shell exports always win.

**Do NOT** introduce a `.env.local` in `example-app/` or instruct users to `cp .env .env.local`. This was an explicit hard requirement from Mickael during the symfony-bundle session. See `INTEGRATIONS_PLAN.md` §"Cross-cutting DX patterns" §2.

### 10.4 The client MUST be lazy

`from django_poli_page import client` returns `django.utils.functional.SimpleLazyObject(_build_client)`. Initialising at import-time breaks Django's settings-loading order — `settings.POLI_PAGE` isn't readable yet when `django_poli_page/__init__.py` runs in many contexts (e.g. when imported transitively from `INSTALLED_APPS` resolution).

If you find yourself wanting to "eagerly construct the client because lazy is annoying to mock", stop. Read `django-storages`' `S3Boto3Storage` or `sentry-sdk[django]`'s init flow — both lazy for the same reason.

### 10.5 Response helpers do NOT auto-catch `PoliPageError`

Django has no global Nest-style `ExceptionFilter` or Next.js route-handler-factory equivalent. The response helpers in `django_poli_page.http` are pure transformations: `(SDK output) → HttpResponse`. They do NOT wrap the SDK call in `try/except`. Users handle exceptions in their views — either with a per-view `try/except PoliPageError`, a project-level `process_exception` middleware, or DRF's exception handler.

This is a **deliberate delta** from `@poli-page/nextjs`'s `createPoliPageRouteHandler()` (which DOES catch and map) and `@poli-page/nestjs`'s exception filter. Django's idiom is "explicit `try/except` in views" — we don't paper over it. Documented in spec §10.

### 10.6 Demo lives in a Django template at `/`, not in `README` curl recipes

The example project's home page (`/`, served by a `demo` view) is a single-page interactive dashboard with one button per SDK feature, inline `<iframe>` PDF previews, JSON pretty-print, and a document-lifecycle state machine in client-side JS. Aesthetic copied from `/Users/mickael/Projects/symfony-bundle/example-app/templates/demo.html`: white surface, brand indigo `#4f5d99`, Manrope display sans + IBM Plex Sans body + JetBrains Mono code.

**Do NOT** replace this with a README listing `curl` commands. Cross-cutting requirement from `INTEGRATIONS_PLAN.md` §"Cross-cutting DX patterns" §1.

## 11. When stuck

- Re-read `docs/spec/django-app-specification.md` first; most "open questions" are answered there or in §18 "Resolved decisions".
- Compare with `sdk-python` at `/Users/mickael/Projects/sdk-python/` — public classes, exception hierarchy, `RetryEvent` shape.
- Compare patterns with `django-storages`, `sentry-sdk[django]`, `django-allauth`, `djangorestframework`, `django-redis` (the app's industry benchmarks).
- Ask Mickael early. A two-line message is faster than a half-day rebuilding the wrong thing.
- If a CI failure looks unrelated to your change, check `main` first before assuming you caused it.
