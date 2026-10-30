"""One smoke integration test that hits the develop API.

Skipped when POLI_PAGE_API_KEY is unset. Runs only with a pp_sandbox_ key: every
other environment (live, or one created on Pro+) counts renders toward the
organization's monthly quota.
"""

from __future__ import annotations

import os

import pytest
from django.test import override_settings


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("POLI_PAGE_API_KEY"),
    reason="POLI_PAGE_API_KEY not set; skipping develop-API integration test.",
)
def test_render_getting_started_welcome_returns_pdf() -> None:
    api_key = os.environ["POLI_PAGE_API_KEY"]
    if not api_key.startswith("pp_sandbox_"):
        pytest.skip(
            "POLI_PAGE_API_KEY must be a pp_sandbox_ key; refusing to run in a counted environment."
        )

    with override_settings(
        POLI_PAGE={
            "API_KEY": api_key,
            "BASE_URL": os.environ.get("POLI_PAGE_TEST_BASE_URL"),
            "TIMEOUT": 30.0,
        },
    ):
        from django_poli_page._client import _build_client

        c = _build_client()
        pdf = c.render.pdf(
            {
                "project": "getting-started",
                "template": "welcome",
                "data": {"name": "django-poli-page integration test"},
            },
        )

    assert pdf
    assert pdf.startswith(b"%PDF-")
