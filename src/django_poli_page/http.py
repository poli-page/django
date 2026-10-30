"""HTTP response helpers — pure transformations from SDK output to Django responses.

These helpers do not catch `PoliPageError`: a view lets it propagate to the
error handler (`django_poli_page.middleware`, on by default) or catches it itself.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from contextlib import AbstractContextManager
from urllib.parse import quote

from django.http import (
    HttpResponse,
    HttpResponsePermanentRedirect,
    HttpResponseRedirect,
    StreamingHttpResponse,
)
from poli_page import DocumentDescriptor, DocumentPreviewResult


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


class _OpenedStream:
    """The chunks of an SDK stream entered at once; exhausting or closing them exits it.

    Django calls `close()` when it is done with the response, iterated or not.
    """

    def __init__(self, stream: AbstractContextManager[Iterator[bytes]]) -> None:
        self._stream = stream
        self._chunks = iter(stream.__enter__())
        self._open = True

    def __iter__(self) -> Iterator[bytes]:
        return self

    def __next__(self) -> bytes:
        try:
            return next(self._chunks)
        except BaseException:
            self.close()
            raise

    def close(self) -> None:
        if self._open:
            self._open = False
            self._stream.__exit__(None, None, None)


def pdf_stream_response(
    chunks: AbstractContextManager[Iterator[bytes]] | Iterable[bytes],
    filename: str = "document.pdf",
    *,
    as_attachment: bool = True,
) -> StreamingHttpResponse:
    """Stream a PDF to the client.

    Pass the SDK's stream as is: `pdf_stream_response(client.render.pdf_stream(input))`.
    The render and the download start here, in the view, so a `PoliPageError` raises
    before the response exists and reaches the error handler. The stream is closed when
    the response is done. Any other iterable of bytes is streamed as given.
    """
    content = _OpenedStream(chunks) if isinstance(chunks, AbstractContextManager) else chunks
    response = StreamingHttpResponse(content, content_type="application/pdf")
    response["Content-Disposition"] = _build_disposition(filename, as_attachment)
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def preview_response(preview: DocumentPreviewResult) -> HttpResponse:
    """Return a stored document's HTML (``client.documents.preview(id)``) as an HttpResponse."""
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
