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


SECRET = "0123456789abcdef0123456789abcdef"
SANDBOX_KEY = f"pp_sandbox_{SECRET}"
ENV_20 = "a" * 20
ENV_21 = "a" * 21


def _ready_warnings(api_key: str) -> list[str]:
    """Run ready() with ``api_key`` and return every warning message it emitted."""
    with (
        override_settings(POLI_PAGE={"API_KEY": api_key}),
        warnings.catch_warnings(record=True) as captured,
    ):
        warnings.simplefilter("always")
        _run_ready()
    return [str(w.message) for w in captured]


@pytest.mark.parametrize(
    "key",
    [
        SANDBOX_KEY,
        f"pp_live_{SECRET}",
        f"pp_eu-prod_{SECRET}",
        f"pp_{ENV_20}_{SECRET}",
        f"pp_a_{SECRET}",
        f"pp_a1-b2-c3_{SECRET}",
    ],
)
def test_well_formed_key_starts_without_warning(key: str) -> None:
    assert _ready_warnings(key) == []


@pytest.mark.parametrize(
    ("key", "shown_prefix"),
    [
        ("pp_sandbox_x", "pp_sandbox_"),
        (f"pp_Sandbox_{SECRET}", "pp_Sandbox_"),
        (f"pp_2fa_{SECRET}", "pp_2fa_"),
        (f"pp_a--b_{SECRET}", "pp_a--b_"),
        (f"pp_eu-_{SECRET}", "pp_eu-_"),
        (f"pp_eu_prod_{SECRET}", "pp_eu_"),
        (f"pp_{ENV_20}_{SECRET[:31]}", f"pp_{ENV_20}_"),
        (f"pp_sandbox_{SECRET}0", "pp_sandbox_"),
        (f"pp_sandbox_{SECRET.upper()}", "pp_sandbox_"),
        (f"pp_sandbox_{SECRET[:-1]}g", "pp_sandbox_"),
        (f"pp_sandbox_{SECRET}x", "pp_sandbox_"),
        (f"pp_sandbox_{SECRET}\n", "pp_sandbox_"),
        (f" pp_sandbox_{SECRET}", None),
        (f"xpp_sandbox_{SECRET}", None),
        (f"sk_pp_sandbox_{SECRET}", None),
        (f"pp_{ENV_21}_{SECRET}", None),
        (f"pp__{SECRET}", None),
        (SECRET, None),
        ("not-a-poli-page-token", None),
    ],
)
def test_malformed_key_starts_with_one_warning_without_the_secret(
    key: str, shown_prefix: str | None
) -> None:
    messages = _ready_warnings(key)

    assert len(messages) == 1
    message = messages[0]
    assert message.endswith(
        "does not look like pp_{environment}_{32 hex characters}; "
        "starting anyway, the API decides whether it is valid."
    )
    assert key.strip() not in message
    assert SECRET[:8] not in message
    assert SECRET[:8].upper() not in message
    if shown_prefix is None:
        assert message.startswith("Poli Page API_KEY does not look like")
    else:
        assert message.startswith(f'Poli Page API_KEY "{shown_prefix}…" does not look like')


def test_malformed_key_shows_a_20_character_environment_prefix() -> None:
    (message,) = _ready_warnings(f"pp_{ENV_20}_x")
    assert message.startswith(f'Poli Page API_KEY "pp_{ENV_20}_…" does not look like')


def test_malformed_key_hides_a_21_character_environment_prefix() -> None:
    (message,) = _ready_warnings(f"pp_{ENV_21}_x")
    assert message.startswith("Poli Page API_KEY does not look like")
    assert ENV_20 not in message


def test_missing_poli_page_setting_raises(settings: Any) -> None:
    if hasattr(settings, "POLI_PAGE"):
        del settings.POLI_PAGE
    hint = r"POLI_PAGE = \{'API_KEY': 'pp_sandbox_\.\.\.'\}"
    with pytest.raises(ImproperlyConfigured, match=hint):
        _run_ready()


@override_settings(POLI_PAGE={})
def test_missing_api_key_defers_to_sdk_env_fallback() -> None:
    # Per spec §6.2: when API_KEY is absent, defer to the SDK's POLI_PAGE_API_KEY
    # env-var fallback. ready() must not raise.
    _run_ready()


@pytest.mark.parametrize("empty_key", ["", 42, b"pp_sandbox_x"])
def test_empty_or_non_string_api_key_raises(empty_key: object) -> None:
    with (
        override_settings(POLI_PAGE={"API_KEY": empty_key}),
        pytest.raises(ImproperlyConfigured, match="non-empty string"),
    ):
        _run_ready()


@override_settings(POLI_PAGE={"API_KEY": SANDBOX_KEY, "BASE_URL": "ftp://api.poli.page"})
def test_bad_base_url_scheme_raises() -> None:
    with pytest.raises(ImproperlyConfigured, match="BASE_URL"):
        _run_ready()


@pytest.mark.parametrize("bad_timeout", [0, -1, 601])
def test_timeout_out_of_range_raises(bad_timeout: float | int) -> None:
    with (
        override_settings(POLI_PAGE={"API_KEY": SANDBOX_KEY, "TIMEOUT": bad_timeout}),
        pytest.raises(ImproperlyConfigured, match="TIMEOUT"),
    ):
        _run_ready()


def test_retries_max_attempts_out_of_range_raises() -> None:
    with (
        override_settings(POLI_PAGE={"API_KEY": SANDBOX_KEY, "RETRIES": {"MAX_ATTEMPTS": 11}}),
        pytest.raises(ImproperlyConfigured, match="MAX_ATTEMPTS"),
    ):
        _run_ready()


def test_retries_delay_seconds_out_of_range_raises() -> None:
    with (
        override_settings(POLI_PAGE={"API_KEY": SANDBOX_KEY, "RETRIES": {"DELAY_SECONDS": 31}}),
        pytest.raises(ImproperlyConfigured, match="DELAY_SECONDS"),
    ):
        _run_ready()


def test_unknown_key_warns_does_not_raise() -> None:
    with override_settings(POLI_PAGE={"API_KEY": SANDBOX_KEY, "UNKNOWN_KEY": "x"}):
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            _run_ready()
        assert any("UNKNOWN_KEY" in str(w.message) for w in captured)
