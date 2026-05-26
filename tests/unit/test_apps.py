"""Tests for django_poli_page.apps.PoliPageConfig.ready() validation."""

from __future__ import annotations

import warnings
from typing import Any

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings


def _run_ready() -> None:
    """Trigger AppConfig.ready() with current settings."""
    from django.apps import apps

    app_config = apps.get_app_config("django_poli_page")
    app_config.ready()


@override_settings(POLI_PAGE={"API_KEY": "pp_test_valid"})
def test_minimal_valid_config_passes() -> None:
    _run_ready()


@override_settings(POLI_PAGE={"API_KEY": "pp_live_prod"})
def test_pp_live_prefix_passes() -> None:
    _run_ready()


def test_missing_poli_page_setting_raises(settings: Any) -> None:
    if hasattr(settings, "POLI_PAGE"):
        del settings.POLI_PAGE
    with pytest.raises(ImproperlyConfigured, match="POLI_PAGE"):
        _run_ready()


@override_settings(POLI_PAGE={})
def test_missing_api_key_defers_to_sdk_env_fallback() -> None:
    # Per spec §6.2: when API_KEY is absent, defer to the SDK's POLI_PAGE_API_KEY
    # env-var fallback. ready() must not raise.
    _run_ready()


@pytest.mark.parametrize("bad_key", ["abc", "sk_test_x", "pp_abc", "pp_prod_x"])
def test_bad_prefix_api_key_raises(bad_key: str) -> None:
    with (
        override_settings(POLI_PAGE={"API_KEY": bad_key}),
        pytest.raises(ImproperlyConfigured, match="pp_test_ or pp_live_"),
    ):
        _run_ready()


@override_settings(POLI_PAGE={"API_KEY": "pp_test_x", "BASE_URL": "ftp://api.poli.page"})
def test_bad_base_url_scheme_raises() -> None:
    with pytest.raises(ImproperlyConfigured, match="BASE_URL"):
        _run_ready()


@pytest.mark.parametrize("bad_timeout", [0, -1, 601])
def test_timeout_out_of_range_raises(bad_timeout: float | int) -> None:
    with (
        override_settings(POLI_PAGE={"API_KEY": "pp_test_x", "TIMEOUT": bad_timeout}),
        pytest.raises(ImproperlyConfigured, match="TIMEOUT"),
    ):
        _run_ready()


def test_retries_max_attempts_out_of_range_raises() -> None:
    with (
        override_settings(POLI_PAGE={"API_KEY": "pp_test_x", "RETRIES": {"MAX_ATTEMPTS": 11}}),
        pytest.raises(ImproperlyConfigured, match="MAX_ATTEMPTS"),
    ):
        _run_ready()


def test_retries_delay_seconds_out_of_range_raises() -> None:
    with (
        override_settings(POLI_PAGE={"API_KEY": "pp_test_x", "RETRIES": {"DELAY_SECONDS": 31}}),
        pytest.raises(ImproperlyConfigured, match="DELAY_SECONDS"),
    ):
        _run_ready()


def test_unknown_key_warns_does_not_raise() -> None:
    with override_settings(POLI_PAGE={"API_KEY": "pp_test_x", "UNKNOWN_KEY": "x"}):
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            _run_ready()
        assert any("UNKNOWN_KEY" in str(w.message) for w in captured)
