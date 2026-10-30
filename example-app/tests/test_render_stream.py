"""`GET /render/stream`: an SDK error answers the error handler's JSON, not a started PDF."""

from __future__ import annotations

import base64
import json
from collections.abc import Mapping, Sequence
from typing import Any

import pytest
from django.conf import settings
from django.test import Client, override_settings
from mock_api import MockServer

TEST_API_KEY = "pp_sandbox_0123456789abcdef0123456789abcdef"
PDF = b"%PDF-1.4\n%%EOF\n"

DESCRIPTOR: dict[str, Any] = {
    "apiKeyId": None,
    "createdAt": "2026-09-29T09:45:22.000Z",
    "diagnostics": [],
    "documentId": "doc_abc123",
    "environment": "sandbox",
    "expiresAt": "2026-09-29T10:00:22.000Z",
    "format": "A4",
    "locale": None,
    "metadata": {},
    "organizationId": "org_xyz",
    "orientation": "portrait",
    "pageCount": 1,
    "presignedPdfUrl": "{{mock}}/storage/doc_abc123.pdf",
    "projectId": None,
    "projectSlug": "getting-started",
    "sizeBytes": len(PDF),
    "templateId": None,
    "templateSlug": "welcome",
}


def _get_stream(responses: Sequence[Mapping[str, Any]]) -> tuple[Any, bytes, MockServer]:
    server = MockServer(responses)
    try:
        poli_page = {**settings.POLI_PAGE, "API_KEY": TEST_API_KEY, "BASE_URL": server.origin}
        with override_settings(POLI_PAGE=poli_page):
            response = Client(raise_request_exception=False).get("/render/stream")
            body = response.getvalue()  # joins streaming_content for a streamed answer
            response.close()
    finally:
        server.close()
    return response, body, server


def test_streams_the_pdf() -> None:
    response, body, server = _get_stream(
        [
            {"status": 200, "json": DESCRIPTOR},
            {
                "status": 200,
                "headers": {"content-type": "application/pdf"},
                "base64": base64.b64encode(PDF).decode(),
            },
        ]
    )

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response["Content-Disposition"] == 'inline; filename="welcome-streamed.pdf"'
    assert body == PDF
    assert [(r.method, r.path) for r in server.requests] == [
        ("POST", "/v1/render"),
        ("GET", "/storage/doc_abc123.pdf"),
    ]


@pytest.mark.parametrize(
    ("responses", "status", "payload"),
    [
        pytest.param(
            [
                {
                    "status": 404,
                    "headers": {"x-request-id": "req_stream_404"},
                    "json": {
                        "error": "TEMPLATE_NOT_FOUND",
                        "detail": "Template 'welcome' not found in project 'getting-started'.",
                        "requestId": "req_stream_404",
                    },
                }
            ],
            404,
            {
                "code": "TEMPLATE_NOT_FOUND",
                "message": "Template 'welcome' not found in project 'getting-started'.",
                "status": 404,
                "requestId": "req_stream_404",
            },
            id="render-404",
        ),
        pytest.param(
            [{"fault": "drop"}, {"fault": "drop"}, {"fault": "drop"}],
            503,
            {
                "code": "network_error",
                "message": "Network request failed",
                "status": 503,
                "requestId": None,
            },
            id="network-error",
        ),
        pytest.param(
            [{"status": 200, "json": DESCRIPTOR}, {"status": 403, "text": "AccessDenied"}],
            403,
            {
                "code": "DOWNLOAD_FAILED",
                "message": "Failed to download PDF: HTTP 403",
                "status": 403,
                "requestId": None,
            },
            id="download-403",
        ),
    ],
)
def test_sdk_error_answers_the_error_handler_json(
    responses: list[dict[str, Any]], status: int, payload: dict[str, Any]
) -> None:
    response, body, _ = _get_stream(responses)

    assert response.status_code == status
    assert response["Content-Type"] == "application/json"
    assert "Content-Disposition" not in response
    assert json.loads(body) == payload
