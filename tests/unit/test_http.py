from __future__ import annotations

from collections.abc import Iterator
from typing import cast
from unittest.mock import MagicMock

import pytest
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


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        pytest.param(
            'say "hi".pdf',
            'attachment; filename="say \\"hi\\".pdf"',
            id="double-quote-is-escaped",
        ),
        pytest.param(
            "a\\b.pdf",
            'attachment; filename="a\\\\b.pdf"',
            id="backslash-is-escaped",
        ),
        pytest.param(
            "evil.pdf\r\nSet-Cookie: sid=1",
            'attachment; filename="evil.pdfSet-Cookie: sid=1"',
            id="crlf-is-stripped",
        ),
        pytest.param(
            "tab\there\x00\x1f\x7f.pdf",
            'attachment; filename="tabhere.pdf"',
            id="control-chars-are-stripped",
        ),
        pytest.param(
            'x.pdf"; filename="pwn.exe',
            'attachment; filename="x.pdf\\"; filename=\\"pwn.exe"',
            id="parameter-injection-stays-inside-the-quoted-string",
        ),
        pytest.param(
            "résumé François.pdf",
            'attachment; filename="r?sum? Fran?ois.pdf"; '
            "filename*=UTF-8''r%C3%A9sum%C3%A9%20Fran%C3%A7ois.pdf",
            id="non-ascii-uses-rfc5987-dual-notation",
        ),
        pytest.param(
            'résumé "final"\\v2.pdf',
            'attachment; filename="r?sum? \\"final\\"\\\\v2.pdf"; '
            "filename*=UTF-8''r%C3%A9sum%C3%A9%20%22final%22%5Cv2.pdf",
            id="non-ascii-fallback-is-escaped",
        ),
        pytest.param(
            "résumé\r\n\x85.pdf",
            "attachment; filename=\"r?sum?.pdf\"; filename*=UTF-8''r%C3%A9sum%C3%A9.pdf",
            id="non-ascii-control-chars-are-stripped-from-both-forms",
        ),
    ],
)
def test_pdf_response_content_disposition_is_rfc6266_safe(filename: str, expected: str) -> None:
    from django_poli_page.http import pdf_response

    response = pdf_response(b"%PDF-1.7", filename)
    assert response["Content-Disposition"] == expected


def test_pdf_stream_response_content_disposition_is_escaped() -> None:
    from django_poli_page.http import pdf_stream_response

    response = pdf_stream_response(iter([b"x"]), 'q"\r\n.pdf', as_attachment=False)
    assert response["Content-Disposition"] == 'inline; filename="q\\".pdf"'


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
