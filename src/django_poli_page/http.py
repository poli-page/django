"""HTTP response helpers — pure transformations from SDK output to Django responses.

Spec §8. These helpers DO NOT catch PoliPageError; users handle exceptions in
their views (per-view try/except, middleware, or DRF handler). See spec §10.5
for the rationale (delta from nextjs/nestjs).
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from urllib.parse import quote

from django.http import (
    HttpResponse,
    HttpResponsePermanentRedirect,
    HttpResponseRedirect,
    StreamingHttpResponse,
)
from poli_page import DocumentDescriptor, DocumentPreviewResult, PreviewResult


def pdf_response(
    pdf: bytes,
    filename: str = "document.pdf",
    *,
    as_attachment: bool = True,
) -> HttpResponse:
    """Return a Django HttpResponse carrying PDF bytes with all the right headers."""
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Length"] = str(len(pdf))
    response["Content-Disposition"] = _build_disposition(filename, as_attachment)
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def pdf_stream_response(
    chunks: Iterable[bytes] | Iterator[bytes],
    filename: str = "document.pdf",
    *,
    as_attachment: bool = True,
) -> StreamingHttpResponse:
    """Stream chunks of a PDF directly to the client."""
    response = StreamingHttpResponse(chunks, content_type="application/pdf")
    response["Content-Disposition"] = _build_disposition(filename, as_attachment)
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def preview_response(preview: PreviewResult | DocumentPreviewResult) -> HttpResponse:
    """Return the rendered HTML preview as an HttpResponse."""
    response = HttpResponse(preview.html, content_type="text/html; charset=utf-8")
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def document_redirect_response(
    descriptor: DocumentDescriptor,
    *,
    permanent: bool = False,
) -> HttpResponseRedirect | HttpResponsePermanentRedirect:
    """Redirect to the descriptor's presigned PDF URL (302, or 301 if permanent)."""
    cls = HttpResponsePermanentRedirect if permanent else HttpResponseRedirect
    response = cls(descriptor.presigned_pdf_url)
    response["Cache-Control"] = "private, no-store"
    return response


def _build_disposition(filename: str, as_attachment: bool) -> str:
    disp = "attachment" if as_attachment else "inline"
    try:
        filename.encode("ascii")
        return f'{disp}; filename="{filename}"'
    except UnicodeEncodeError:
        # RFC 5987 dual notation: ASCII fallback + UTF-8 percent-encoded extension.
        ascii_fallback = filename.encode("ascii", "replace").decode("ascii")
        encoded = quote(filename, safe="")
        return f"{disp}; filename=\"{ascii_fallback}\"; filename*=UTF-8''{encoded}"
