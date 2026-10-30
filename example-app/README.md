# `django-poli-page` example project

Minimal Django 5 project demonstrating every public method of the Poli Page Python SDK through `django-poli-page`. Each route is one step of the nine-step demo contract in [poli-page/django#2](https://github.com/poli-page/django/issues/2).

## Setup

```bash
cd example-app
uv sync
# Export your key (real shell env wins over the .env template):
export POLI_PAGE_API_KEY=pp_sandbox_your_key
# Optional: point at another API host
# export POLI_PAGE_BASE_URL=https://api.example.com
uv run python manage.py runserver
```

Then open <http://localhost:8000/> — the interactive demo dashboard. One button per SDK feature, inline PDF and stored-HTML previews, JSON pretty-print.

## Routes (demo steps 1–9)

| Demo step | URL | View |
|---|---|---|
| (UI) | `GET /` | `dashboard` |
| 1. `render.pdf` | `GET /render/pdf` | `render_pdf` |
| 2. `render.pdf_stream` | `GET /render/stream` | `render_stream` |
| 3. `render_to_file` | `POST /render/file` | `render_to_file` |
| 4. `render.document` | `POST /documents` | `document_create` |
| 5. `documents.get` | `GET /documents/<id>` | `document_handle` |
| 6. `documents.thumbnails` | `GET /documents/<id>/thumbnails` | `document_thumbnails` |
| 7. `documents.preview` | `GET /documents/<id>/preview` | `document_preview` |
| 8. `documents.delete` | `DELETE /documents/<id>` | `document_handle` |
| 9. Error handling | `GET /errors/not-found` | `error_not_found` |

Every render uses the `getting-started` project's `welcome` template, provisioned into the `sandbox` environment of every organization. The key's environment selects the published copy, so no input carries a version. `GET /documents/<id>` answers a `302` redirect to the document's presigned PDF URL. `GET /errors/not-found` renders the template `does-not-exist` with data `{}` and does not catch the error: django-poli-page's error handler, on by default, answers `404` with the error's `to_payload()` body, `{"code": "TEMPLATE_NOT_FOUND", "message": …, "status": 404, "requestId": …}`.

## Contract tests

`tests/test_contract.py` runs the integration cases of the [Poli Page API contract](https://github.com/poli-page/api-contract) against this app, with its SDK pointed at a local mock server:

```bash
uv sync
POLI_CONTRACT=<path to contract.json> uv run pytest
```

## Smoke-test via the management command

```bash
uv run python manage.py poli_page_render \
    --project=getting-started \
    --template=welcome \
    --data='{"name":"CLI"}' \
    --output=./welcome.pdf
```

If the file at `./welcome.pdf` opens to a styled welcome page, the integration works end-to-end.
