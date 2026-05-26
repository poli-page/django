from __future__ import annotations

from collections.abc import Iterator
from typing import cast
from unittest.mock import MagicMock

from django.http import HttpResponseRedirect, StreamingHttpResponse


def test_pdf_response_default_attachment() -> None:
    from django_poli_page.http import pdf_response

    pdf = b"%PDF-1.7\n%stub bytes\n%%EOF\n"
    response = pdf_response(pdf, "invoice.pdf")

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response["Content-Length"] == str(len(pdf))
    assert "attachment" in response["Content-Disposition"]
    assert 'filename="invoice.pdf"' in response["Content-Disposition"]
    assert response["Cache-Control"] == "private, no-store"
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response.content == pdf


def test_pdf_response_inline_flips_disposition() -> None:
    from django_poli_page.http import pdf_response

    response = pdf_response(b"%PDF-1.7", "report.pdf", as_attachment=False)
    assert "inline" in response["Content-Disposition"]


def test_pdf_response_non_ascii_filename_uses_rfc5987() -> None:
    from django_poli_page.http import pdf_response

    response = pdf_response(b"%PDF-1.7", "résumé François.pdf")
    disposition = response["Content-Disposition"]
    assert "filename=" in disposition
    assert "filename*=" in disposition.lower()
    assert "utf-8" in disposition.lower()


def test_pdf_stream_response_streams_chunks() -> None:
    from django_poli_page.http import pdf_stream_response

    def gen() -> Iterator[bytes]:
        yield b"%PDF-1.7"
        yield b"\nstreamed bytes\n"
        yield b"%%EOF\n"

    response = pdf_stream_response(gen(), "streamed.pdf")

    assert isinstance(response, StreamingHttpResponse)
    assert response["Content-Type"] == "application/pdf"
    assert response["Cache-Control"] == "private, no-store"
    assert 'filename="streamed.pdf"' in response["Content-Disposition"]
    assert response["X-Content-Type-Options"] == "nosniff"

    body = b"".join(cast(Iterator[bytes], response.streaming_content))
    assert body == b"%PDF-1.7\nstreamed bytes\n%%EOF\n"


def test_pdf_stream_response_non_ascii_filename() -> None:
    from django_poli_page.http import pdf_stream_response

    response = pdf_stream_response(iter([b"x"]), "résumé.pdf")
    disposition = response["Content-Disposition"]
    assert "filename=" in disposition
    assert "filename*=" in disposition.lower()


def test_preview_response_html() -> None:
    from poli_page import PreviewResult

    from django_poli_page.http import preview_response

    preview = PreviewResult(
        html="<html><body>Hi</body></html>", total_pages=3, environment="sandbox"
    )
    response = preview_response(preview)

    assert response.status_code == 200
    assert response["Content-Type"] == "text/html; charset=utf-8"
    assert response["Cache-Control"] == "private, no-store"
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response.content == b"<html><body>Hi</body></html>"


def test_preview_response_accepts_document_preview_result() -> None:
    from poli_page import DocumentPreviewResult

    from django_poli_page.http import preview_response

    preview = DocumentPreviewResult(html="<html>stored</html>", page_count=5)
    response = preview_response(preview)
    assert response.content == b"<html>stored</html>"


def test_document_redirect_response_302() -> None:
    from django_poli_page.http import document_redirect_response

    descriptor = MagicMock()
    descriptor.presigned_pdf_url = "https://cdn.example/abc.pdf?sig=xyz"

    response = document_redirect_response(descriptor)
    assert isinstance(response, HttpResponseRedirect)
    assert response.status_code == 302
    assert response["Location"] == "https://cdn.example/abc.pdf?sig=xyz"
    assert response["Cache-Control"] == "private, no-store"


def test_document_redirect_response_permanent_301() -> None:
    from django_poli_page.http import document_redirect_response

    descriptor = MagicMock()
    descriptor.presigned_pdf_url = "https://cdn.example/abc.pdf"
    response = document_redirect_response(descriptor, permanent=True)
    assert response.status_code == 301
