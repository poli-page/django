# `django-poli-page` example project

Minimal Django 5 project demonstrating every public method of the Poli Page Python SDK through `django-poli-page`. Each route corresponds 1:1 to a step in the SDK's canonical demo (`../../sdk-python/demo/sync_demo.py`).

## Setup

```bash
cd example-app
uv sync
# Export your key (real shell env wins over the .env template):
export POLI_PAGE_API_KEY=pp_test_your_key
uv run python manage.py runserver
```

Then open <http://localhost:8000/> — the interactive demo dashboard. One button per SDK feature, inline PDF/HTML previews, JSON pretty-print.

## Routes (mirror SDK demo steps 1–10)

| SDK demo step | URL | View |
|---|---|---|
| (UI) | `GET /` | `dashboard` |
| 1. `render.pdf` | `GET /render/pdf` | `render_pdf` |
| 2. `render.pdf_stream` | `GET /render/stream` | `render_stream` |
| 3. `render_to_file` | `POST /render/file` | `render_to_file` |
| 4. `render.preview` | `GET /render/preview[?html=...]` | `render_preview` |
| 5. `render.document` | `POST /documents` | `document_create` |
| 6. `documents.get` | `GET /documents/<id>` | `document_handle` |
| 7. `documents.thumbnails` | `GET /documents/<id>/thumbnails` | `document_thumbnails` |
| 8. `documents.preview` | `GET /documents/<id>/preview` | `document_preview` |
| 9. `documents.delete` | `DELETE /documents/<id>` | `document_handle` |
| 10. Error handling | `GET /errors/bad-version` | `error_bad_version` |

## Smoke-test via the management command

```bash
uv run python manage.py poli_page_render \
    --project=getting-started \
    --template=welcome \
    --template-version=1.0.0 \
    --data='{"name":"CLI"}' \
    --output=./welcome.pdf
```

If the file at `./welcome.pdf` opens to a styled welcome page, the integration works end-to-end.
