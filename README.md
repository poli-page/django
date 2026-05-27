# django-poli-page

[![CI](https://github.com/poli-page/django/actions/workflows/ci.yml/badge.svg)](https://github.com/poli-page/django/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/django-poli-page.svg)](https://pypi.org/project/django-poli-page/)
[![License](https://img.shields.io/pypi/l/django-poli-page.svg)](LICENSE)

Official Django integration for [Poli Page](https://poli.page) — render polished PDFs from HTML templates via the Poli Page API. Wraps the [official Python SDK](https://pypi.org/project/poli-page/) with a Django-native AppConfig, lazy client singleton, HTTP response helpers, Django signals for retry/error hooks, and a `manage.py poli_page_render` smoke-test command.

→ API reference (auto-generated from the SDK source): **https://docs.poli.page/reference/sdk/python/**

> **Status:** pre-release. `django-poli-page` and the underlying `poli-page` SDK are not on PyPI yet — install from source (see below) until v0.1.0 ships.

## Requirements

- Python 3.11+
- Django 4.2 LTS, 5.0, 5.1, or 5.2 LTS

## Install

Once published, install from PyPI:

```bash
pip install django-poli-page
# or
uv add django-poli-page
```

Until then, install both repos editable from a checkout:

```bash
git clone git@github.com:poli-page/sdk-python.git
git clone git@github.com:poli-page/django.git
cd django
uv sync               # picks up ../sdk-python via [tool.uv.sources]
```

## Setup (3 lines)

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

That's it. The `AppConfig.ready()` hook validates the dict at startup; `manage.py check` surfaces misconfiguration.

## Get an API key

Sign up at [app.poli.page](https://app.poli.page) (or [app-develop.poli.page](https://app-develop.poli.page) for develop), then **Settings → API Keys** → create a `pp_test_*` key.

```bash
export POLI_PAGE_API_KEY=pp_test_your_key_here
```

## Quick start — render a PDF from a view

```python
from django.http import HttpResponse
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

`pdf_response(...)` sets the right `Content-Type`, RFC 5987 `Content-Disposition`, `Cache-Control: private, no-store`, and `X-Content-Type-Options: nosniff` — the parts you'd otherwise get wrong.

## Smoke-test your config

```bash
python manage.py poli_page_render \
    --project=getting-started \
    --template=welcome \
    --template-version=1.0.0 \
    --data='{"name":"World"}' \
    --output=welcome.pdf
```

## Full settings

```python
POLI_PAGE = {
    "API_KEY": "pp_test_...",          # required
    "BASE_URL": None,                  # optional; SDK default applies
    "TIMEOUT": None,                   # seconds (float); SDK default applies
    "RETRIES": {
        "MAX_ATTEMPTS": None,          # SDK default applies
        "DELAY_SECONDS": None,         # SDK default applies
    },
    "ON_RETRY": None,                  # dotted path to a callable(RetryEvent)
    "ON_ERROR": None,                  # dotted path to a callable(PoliPageError)
    "HTTP_CLIENT": None,               # dotted path to a callable returning httpx.Client
}
```

## Streaming

```python
from django_poli_page.http import pdf_stream_response

def big_doc_view(request):
    def chunks():
        with client.render.pdf_stream({...}) as stream:
            yield from stream
    return pdf_stream_response(chunks(), "big.pdf")
```

## Document workflow

```python
from django_poli_page.http import document_redirect_response

def get_doc(request, doc_id):
    descriptor = client.documents.get(doc_id)
    return document_redirect_response(descriptor)   # 302 to the presigned URL
```

## Signals for retry / error hooks

```python
from django.dispatch import receiver
from django_poli_page.signals import poli_page_retry

@receiver(poli_page_retry)
def log_retries(sender, event, **kwargs):
    print(f"Retrying #{event.attempt} in {event.delay_seconds}s: {event.reason.code}")
```

## Error handling

`PoliPageError` (and subclasses: `BadRequestError`, `AuthenticationError`, `RateLimitError`, `InternalServerError`, `APIConnectionError`, ...) propagate from view code. The response helpers do NOT auto-catch — see [spec §10.5](docs/spec/django-app-specification.md) for the rationale.

```python
from poli_page import PoliPageError

def my_view(request):
    try:
        pdf = client.render.pdf({...})
    except PoliPageError as exc:
        return JsonResponse(
            {"code": exc.code, "request_id": exc.request_id, "message": exc.message},
            status=exc.status or 500,
        )
    return pdf_response(pdf)
```

## Example project

A full runnable Django 5 project showing every public method is in `example-app/`. See `example-app/README.md` for the walkthrough.

## License

[MIT](LICENSE).
