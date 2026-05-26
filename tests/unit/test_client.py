from __future__ import annotations

import importlib
from typing import Any
from unittest.mock import MagicMock

from django.test import override_settings


def test_build_client_passes_api_key_only_when_no_other_options(mocker: Any) -> None:
    fake_polipage_cls = mocker.patch("django_poli_page._client.PoliPage")
    from django_poli_page._client import _build_client

    with override_settings(POLI_PAGE={"API_KEY": "pp_test_only"}):
        _build_client()

    args, kwargs = fake_polipage_cls.call_args
    assert args == ()
    assert kwargs["api_key"] == "pp_test_only"
    # Optional kwargs must be ABSENT when settings don't set them — never pass None.
    assert "base_url" not in kwargs
    assert "timeout" not in kwargs
    assert "max_retries" not in kwargs
    assert "retry_delay" not in kwargs


def test_build_client_passes_all_options(mocker: Any) -> None:
    fake_polipage_cls = mocker.patch("django_poli_page._client.PoliPage")
    from django_poli_page._client import _build_client

    with override_settings(
        POLI_PAGE={
            "API_KEY": "pp_test_full",
            "BASE_URL": "https://api-develop.poli.page",
            "TIMEOUT": 42.0,
            "RETRIES": {"MAX_ATTEMPTS": 5, "DELAY_SECONDS": 0.1},
        },
    ):
        _build_client()

    _, kwargs = fake_polipage_cls.call_args
    assert kwargs["api_key"] == "pp_test_full"
    assert kwargs["base_url"] == "https://api-develop.poli.page"
    assert kwargs["timeout"] == 42.0
    assert kwargs["max_retries"] == 5
    assert kwargs["retry_delay"] == 0.1


def test_lazy_client_is_not_built_at_import(mocker: Any) -> None:
    fake_polipage_cls = mocker.patch("django_poli_page._client.PoliPage")

    import django_poli_page._client

    importlib.reload(django_poli_page._client)

    assert fake_polipage_cls.call_count == 0


def test_lazy_client_is_built_on_first_access(mocker: Any) -> None:
    fake_polipage_cls = mocker.patch("django_poli_page._client.PoliPage")
    fake_polipage_cls.return_value = MagicMock(name="PoliPage instance")

    from django_poli_page import client

    # Trigger the lazy load by accessing any attribute.
    _ = client.render

    assert fake_polipage_cls.call_count == 1


def test_user_on_retry_dotted_path_wins_over_default_bridge(mocker: Any) -> None:
    fake_polipage_cls = mocker.patch("django_poli_page._client.PoliPage")
    fake_listener = mocker.patch("django_poli_page._client.import_string")
    fake_listener.return_value = MagicMock(name="user_listener")

    from django_poli_page._client import _build_client

    with override_settings(
        POLI_PAGE={
            "API_KEY": "pp_test_x",
            "ON_RETRY": "myapp.callbacks.custom",
        },
    ):
        _build_client()

    fake_listener.assert_any_call("myapp.callbacks.custom")
    _, kwargs = fake_polipage_cls.call_args
    assert kwargs["on_retry"] is fake_listener.return_value
