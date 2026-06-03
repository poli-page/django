# django-poli-page

> Render Poli Page documents as Django HTTP responses.

## About

`django-poli-page` is a reusable Django app around the official `poli-page` Python SDK. You add it to `INSTALLED_APPS`, declare a `POLI_PAGE` settings dict, and you return PDFs, streamed PDFs, HTML previews, and presigned-URL redirects from your views with one helper call each. The app validates configuration at startup, exposes a lazy `PoliPage` singleton, and bridges the SDK's retry and error hooks onto Django signals.

**When to use this:**
- You render invoices, contracts, statements or reports from Django views and want the right `Content-Disposition`, `Cache-Control` and `Content-Type` without rewriting them on each route.
- You want SDK retries and terminal errors observable through `django.dispatch` instead of bespoke callbacks.
- You want `manage.py` to fail loudly when your `POLI_PAGE` settings are wrong.

**When not to:**
- You need a templatetag library, a class-based view mixin, or a database model for documents — this app deliberately does not ship those (see `docs/spec/django-app-specification.md`).

## Requirements

- Python 3.11+
- Django 4.2 LTS, 5.0, 5.1, or 5.2 LTS
- A Poli Page API key (`pp_test_*` or `pp_live_*`)

## Install

```bash
pip install django-poli-page
```

Add the app to `INSTALLED_APPS` and export your key:

```python
# settings.py
INSTALLED_APPS = [
    # ...
    "django_poli_page",
]

POLI_PAGE = {
    "API_KEY": os.environ["POLI_PAGE_API_KEY"],
}
```

```bash
export POLI_PAGE_API_KEY=pp_test_your_key_here
```

You get a key from the dashboard at [app.poli.page](https://app.poli.page) under **Settings → API Keys**. Smoke-test the wiring from the command line:

```bash
python manage.py poli_page_render \
    --project=getting-started \
    --template=welcome \
    --template-version=1.0.0 \
    --data='{"name":"World"}' \
    --output=welcome.pdf
```

## Quick start

```python
# views.py
from django_poli_page import client
from django_poli_page.http import pdf_response


def invoice_view(request, invoice_id):
    pdf = client.render.pdf({
        "project": "invoices",
        "template": "default",
        "version": "1.0.0",
        "data": {"invoice_id": invoice_id},
    })
    return pdf_response(pdf, f"invoice-{invoice_id}.pdf")
```

## Configuration

You configure everything through a single `POLI_PAGE` dict in your settings module. `AppConfig.ready()` validates the dict at startup and surfaces problems through `manage.py check`.

| Key | Default | Description |
|---|---|---|
| `API_KEY` | — (required) | Your Poli Page key. Must start with `pp_test_` or `pp_live_`. |
| `BASE_URL` | SDK default | Override the API host (e.g. for `api-develop.poli.page`). |
| `TIMEOUT` | SDK default | Per-request timeout in seconds (0 < value <= 600). |
| `RETRIES.MAX_ATTEMPTS` | SDK default | Retry budget for transient failures (0-10). |
| `RETRIES.DELAY_SECONDS` | SDK default | Base delay between retry attempts (0-30). |
| `ON_RETRY` | signal dispatch | Dotted path to a callable `(RetryEvent) -> None`. |
| `ON_ERROR` | signal dispatch | Dotted path to a callable `(PoliPageError) -> None`. |
| `HTTP_CLIENT` | SDK default | Dotted path to a factory returning an `httpx.Client`. |

```python
# settings.py
POLI_PAGE = {
    "API_KEY": os.environ["POLI_PAGE_API_KEY"],
    "TIMEOUT": 30,
    "RETRIES": {"MAX_ATTEMPTS": 3, "DELAY_SECONDS": 0.5},
}
```

When `ON_RETRY` or `ON_ERROR` is unset, the SDK hooks dispatch through Django signals instead (see API at a glance).

## API at a glance

| Symbol | Purpose |
|---|---|
| `django_poli_page.client` | Lazy `PoliPage` singleton, built on first attribute access. |
| `django_poli_page.http.pdf_response` | Wrap PDF bytes in an `HttpResponse` with PDF headers and disposition. |
| `django_poli_page.http.pdf_stream_response` | Wrap a chunk iterator in a `StreamingHttpResponse` for large PDFs. |
| `django_poli_page.http.preview_response` | Return a rendered HTML preview as `text/html`. |
| `django_poli_page.http.document_redirect_response` | Redirect (302 or 301) to a document's presigned PDF URL. |
| `django_poli_page.signals.poli_page_retry` | Sent before each SDK retry sleep with the `RetryEvent`. |
| `django_poli_page.signals.poli_page_error` | Sent on terminal SDK failure with the `PoliPageError`. |
| `manage.py poli_page_render` | Render a template end-to-end from the CLI; exits non-zero on `PoliPageError`. |

Full reference: [docs/api.md](docs/api.md).

## Errors

The response helpers do not catch SDK exceptions — handling stays explicit in your view, middleware, or DRF exception handler. The four categories you handle are re-exported from `poli_page`:

- **Auth** — `AuthenticationError`. Invalid or revoked API key (HTTP 401/403).
- **Rate limit** — `RateLimitError`. Your account or key is rate-limited (HTTP 429).
- **Request rejected** — `BadRequestError` (and `InternalServerError` for upstream-side failures). The request was rejected at HTTP 4xx/5xx.
- **Network / transport** — `APIConnectionError`. Network or transport failure before a response arrived.

All four inherit from `PoliPageError`, which carries `code`, `status`, `message`, and `request_id`.

```python
# views.py
from django.http import JsonResponse
from poli_page import PoliPageError

from django_poli_page import client
from django_poli_page.http import pdf_response


def invoice_view(request, invoice_id):
    try:
        pdf = client.render.pdf({
            "project": "invoices",
            "template": "default",
            "version": "1.0.0",
            "data": {"invoice_id": invoice_id},
        })
    except PoliPageError as exc:
        return JsonResponse(
            {"code": exc.code, "request_id": exc.request_id, "message": exc.message},
            status=exc.status or 500,
        )
    return pdf_response(pdf, f"invoice-{invoice_id}.pdf")
```

## Example app

A runnable Django 5 project under [`example-app/`](example-app/) covers every public method of the SDK through `django-poli-page`, with one route per demo step and an interactive dashboard at `/`. See [`example-app/README.md`](example-app/README.md) for the route map.

```bash
cd example-app
uv sync
export POLI_PAGE_API_KEY=pp_test_your_key
uv run python manage.py runserver
```

## Going further

- Streaming large PDFs through `pdf_stream_response` — forthcoming in `docs/streaming.md`.
- Document workflow: create, fetch, thumbnails, presigned-URL redirects — forthcoming in `docs/documents.md`.
- Signals: wiring `poli_page_retry` and `poli_page_error` into logging or metrics — forthcoming in `docs/signals.md`.
- Swapping the underlying `httpx.Client` for connection-pool tuning or instrumentation — forthcoming in `docs/http-client.md`.

## Compatibility

| Package version | Django | Python |
|---|---|---|
| 0.1.x | 4.2 LTS, 5.0, 5.1, 5.2 LTS | 3.11, 3.12, 3.13 |

The package follows the Django supported-versions policy; releases drop a Django row when upstream marks it end-of-life.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Released under the [MIT License](LICENSE).
