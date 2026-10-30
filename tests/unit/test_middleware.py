"""The error handler: on by default, off with ERROR_HANDLER=False, the to_payload() answer."""

from __future__ import annotations

import json
from typing import Any

import pytest
from asgiref.sync import async_to_sync
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest, HttpResponse
from django.test import AsyncClient, Client, override_settings
from django.urls import path
from poli_page import (
    APIConnectionError,
    APITimeoutError,
    NotFoundError,
    PoliPageError,
)

from django_poli_page.middleware import MIDDLEWARE_PATH
from tests.keys import SANDBOX_KEY

ERRORS: dict[str, PoliPageError] = {
    "api": NotFoundError(
        "Template 'does-not-exist' not found in project 'getting-started'.",
        code="TEMPLATE_NOT_FOUND",
        status=404,
        request_id="req_123",
    ),
    "network": APIConnectionError("Network request failed", code="network_error"),
    "timeout": APITimeoutError("Request timed out after 60000ms", code="timeout"),
    "no-status": PoliPageError("apiKey is required", code="invalid_options"),
}


def _raise(request: HttpRequest, kind: str) -> HttpResponse:
    if kind == "other":
        raise ValueError("not a Poli Page error")
    raise ERRORS[kind]


async def _raise_async(request: HttpRequest, kind: str) -> HttpResponse:
    raise ERRORS[kind]


urlpatterns = [
    path("sync/<str:kind>", _raise),
    path("async/<str:kind>", _raise_async),
]


def _run_ready() -> None:
    from django.apps import apps

    apps.get_app_config("django_poli_page").ready()


def test_handler_is_installed_at_startup_by_default() -> None:
    # tests/settings.py sets no MIDDLEWARE: the app added its handler at startup.
    assert list(settings.MIDDLEWARE) == [MIDDLEWARE_PATH]


def test_handler_is_appended_after_the_project_middleware_once() -> None:
    with override_settings(
        MIDDLEWARE=["django.middleware.common.CommonMiddleware"],
        POLI_PAGE={"API_KEY": SANDBOX_KEY},
    ):
        _run_ready()
        _run_ready()
        assert list(settings.MIDDLEWARE) == [
            "django.middleware.common.CommonMiddleware",
            MIDDLEWARE_PATH,
        ]


def test_error_handler_true_installs_the_handler() -> None:
    with override_settings(
        MIDDLEWARE=[], POLI_PAGE={"API_KEY": SANDBOX_KEY, "ERROR_HANDLER": True}
    ):
        _run_ready()
        assert list(settings.MIDDLEWARE) == [MIDDLEWARE_PATH]


def test_error_handler_false_leaves_middleware_alone() -> None:
    with override_settings(
        MIDDLEWARE=["django.middleware.common.CommonMiddleware"],
        POLI_PAGE={"API_KEY": SANDBOX_KEY, "ERROR_HANDLER": False},
    ):
        _run_ready()
        assert list(settings.MIDDLEWARE) == ["django.middleware.common.CommonMiddleware"]


@pytest.mark.parametrize("value", ["false", 0, 1, "off"])
def test_error_handler_must_be_a_bool(value: Any) -> None:
    with (
        override_settings(POLI_PAGE={"API_KEY": SANDBOX_KEY, "ERROR_HANDLER": value}),
        pytest.raises(ImproperlyConfigured, match=r"ERROR_HANDLER'\] must be True or False"),
    ):
        _run_ready()


@pytest.mark.parametrize(
    ("kind", "status", "body"),
    [
        pytest.param(
            "api",
            404,
            {
                "code": "TEMPLATE_NOT_FOUND",
                "message": "Template 'does-not-exist' not found in project 'getting-started'.",
                "status": 404,
                "requestId": "req_123",
            },
            id="api-error",
        ),
        pytest.param(
            "network",
            503,
            {
                "code": "network_error",
                "message": "Network request failed",
                "status": 503,
                "requestId": None,
            },
            id="network_error",
        ),
        pytest.param(
            "timeout",
            504,
            {
                "code": "timeout",
                "message": "Request timed out after 60000ms",
                "status": 504,
                "requestId": None,
            },
            id="timeout",
        ),
        pytest.param(
            "no-status",
            500,
            {
                "code": "invalid_options",
                "message": "apiKey is required",
                "status": None,
                "requestId": None,
            },
            id="no-status",
        ),
    ],
)
@override_settings(ROOT_URLCONF=__name__)
def test_handler_answers_the_error_payload(kind: str, status: int, body: dict[str, Any]) -> None:
    response = Client().get(f"/sync/{kind}")

    assert response.status_code == status
    assert response["Content-Type"] == "application/json"
    assert json.loads(response.content) == body
    assert json.loads(response.content) == ERRORS[kind].to_payload()


@override_settings(ROOT_URLCONF=__name__)
def test_handler_answers_an_async_view_error() -> None:
    response = async_to_sync(AsyncClient().get)("/async/api")

    assert response.status_code == 404
    assert response["Content-Type"] == "application/json"
    assert json.loads(response.content) == ERRORS["api"].to_payload()


@override_settings(ROOT_URLCONF=__name__)
def test_handler_lets_other_exceptions_through() -> None:
    with pytest.raises(ValueError, match="not a Poli Page error"):
        Client().get("/sync/other")


@override_settings(ROOT_URLCONF=__name__, MIDDLEWARE=[])
def test_disabled_handler_lets_the_error_propagate() -> None:
    with override_settings(POLI_PAGE={"API_KEY": SANDBOX_KEY, "ERROR_HANDLER": False}):
        _run_ready()
        with pytest.raises(NotFoundError):
            Client().get("/sync/api")


def test_override_of_poli_page_rebuilds_the_client(mocker: Any) -> None:
    fake = mocker.patch("django_poli_page._client.PoliPage")
    # From _client itself: test_client.py reloads that module, which rebinds it.
    from django_poli_page._client import client

    with override_settings(POLI_PAGE={"API_KEY": SANDBOX_KEY, "BASE_URL": "http://one.test"}):
        _ = client.render
    with override_settings(POLI_PAGE={"API_KEY": SANDBOX_KEY, "BASE_URL": "http://two.test"}):
        _ = client.render

    assert [call.kwargs["base_url"] for call in fake.call_args_list[-2:]] == [
        "http://one.test",
        "http://two.test",
    ]
