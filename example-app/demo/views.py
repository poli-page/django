"""Demo views — one per SDK step + the / dashboard.

One view per step of the nine-step demo contract in poli-page/django#2.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from poli_page import PoliPageError, RenderInput
from poli_page.fs import render_to_file as sdk_render_to_file

from django_poli_page import client
from django_poli_page.http import (
    document_redirect_response,
    pdf_response,
    pdf_stream_response,
    preview_response,
)

PROJECT_INPUT: RenderInput = {
    "project": "getting-started",
    "template": "welcome",
    "data": {"name": "django-poli-page demo"},
}


def dashboard(request: HttpRequest) -> HttpResponse:
    """Interactive demo dashboard — one button per SDK feature."""
    return render(request, "demo/dashboard.html")


# Step 1: render.pdf
def render_pdf(request: HttpRequest) -> HttpResponse:
    pdf = client.render.pdf(PROJECT_INPUT)
    return pdf_response(pdf, "welcome.pdf", as_attachment=False)


# Step 2: render.pdf_stream
def render_stream(request: HttpRequest) -> HttpResponse:
    def chunks() -> Iterator[bytes]:
        with client.render.pdf_stream(PROJECT_INPUT) as stream:
            yield from stream

    return pdf_stream_response(chunks(), "welcome-streamed.pdf", as_attachment=False)


# Step 3: render_to_file
def render_to_file(request: HttpRequest) -> JsonResponse:
    output = Path(__file__).resolve().parent.parent / "output" / "welcome.pdf"
    output.parent.mkdir(parents=True, exist_ok=True)
    sdk_render_to_file(client, PROJECT_INPUT, output)
    return JsonResponse({"path": str(output), "size_bytes": output.stat().st_size})


# Step 4: render.document
def document_create(request: HttpRequest) -> JsonResponse:
    descriptor = client.render.document(PROJECT_INPUT)
    return JsonResponse(
        {
            "document_id": descriptor.document_id,
            "page_count": descriptor.page_count,
            "size_bytes": descriptor.size_bytes,
            "environment": descriptor.environment,
            "expires_at": descriptor.expires_at,
            "presigned_pdf_url": descriptor.presigned_pdf_url,
        }
    )


# Steps 5 + 8: documents.get (GET) + documents.delete (DELETE) share the URL.
def document_handle(request: HttpRequest, doc_id: str) -> HttpResponse:
    if request.method == "GET":
        descriptor = client.documents.get(doc_id)
        return document_redirect_response(descriptor)
    if request.method == "DELETE":
        client.documents.delete(doc_id)
        return HttpResponse(status=204)
    return HttpResponse(status=405)


# Step 6: documents.thumbnails
def document_thumbnails(request: HttpRequest, doc_id: str) -> JsonResponse:
    thumbs = client.documents.thumbnails(doc_id, {"width": 240})
    return JsonResponse(
        {
            "count": len(thumbs),
            "thumbnails": [
                {
                    "page": t.page,
                    "width": t.width,
                    "height": t.height,
                    "content_type": t.content_type,
                    "base64": t.data,
                }
                for t in thumbs
            ],
        }
    )


# Step 7: documents.preview
def document_preview(request: HttpRequest, doc_id: str) -> HttpResponse:
    result = client.documents.preview(doc_id)
    return preview_response(result)


# Step 9: deliberate 404 TEMPLATE_NOT_FOUND (getting-started has no such template)
def error_not_found(request: HttpRequest) -> JsonResponse:
    try:
        client.render.pdf(
            {
                "project": "getting-started",
                "template": "does-not-exist",
                "data": {},
            }
        )
    except PoliPageError as exc:
        payload = exc.to_payload()
        return JsonResponse(
            {
                "caught": True,
                "code": payload["code"],
                "message": payload["message"],
                "status": payload["status"],
                "requestId": payload["requestId"],
            },
            status=payload["status"] or 500,
        )
    return JsonResponse({"caught": False, "note": "expected error, got success"}, status=500)
