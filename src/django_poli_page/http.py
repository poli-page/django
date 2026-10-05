"""HTTP response helpers — pure transformations from SDK output to Django responses.

Spec §8. These helpers DO NOT catch PoliPageError; users handle exceptions in
their views (per-view try/except, middleware, or DRF handler). See spec §10.5
for the rationale (delta from nextjs/nestjs).
"""

from __future__ import annotations

import re
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


# C0 controls (incl. TAB, CR, LF), DEL and C1 controls. None of them belong in a
# filename, and CR/LF would split the header (response splitting).
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f-\x9f]")


def _build_disposition(filename: str, as_attachment: bool) -> str:
    """Build a Content-Disposition value per RFC 6266 / RFC 8187 (ex-5987).

    ASCII filenames use a quoted-string ``filename="..."``. Non-ASCII filenames use
    the dual notation: an ASCII ``filename="..."`` fallback for legacy clients plus a
    UTF-8 percent-encoded ``filename*=UTF-8''...`` that modern clients prefer.
    """
    disp = "attachment" if as_attachment else "inline"
    clean = _CONTROL_CHARS.sub("", filename)
    if clean.isascii():
        return f'{disp}; filename="{_quoted_string_content(clean)}"'
    ascii_fallback = clean.encode("ascii", "replace").decode("ascii")
    encoded = quote(clean, safe="")
    return (
        f"{disp}; filename=\"{_quoted_string_content(ascii_fallback)}\"; filename*=UTF-8''{encoded}"
    )


def _quoted_string_content(value: str) -> str:
    """Escape ``\\`` and ``"`` as quoted-pairs (RFC 9110 §5.6.4)."""
    return value.replace("\\", "\\\\").replace('"', '\\"')
