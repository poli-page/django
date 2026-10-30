"""Tests for django_poli_page.apps.PoliPageConfig.ready() validation."""

from __future__ import annotations

import logging
import warnings
from typing import Any

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from tests.keys import SANDBOX_KEY, SECRET


def _run_ready() -> None:
    """Trigger AppConfig.ready() with current settings."""
    from django.apps import apps

    app_config = apps.get_app_config("django_poli_page")
    app_config.ready()


ENV_20 = "a" * 20
ENV_21 = "a" * 21


def _ready_warnings(api_key: str | None) -> list[str]:
    """Run ready() with ``api_key`` (None: no API_KEY setting) and return its warnings."""
    cfg = {} if api_key is None else {"API_KEY": api_key}
    with (
        override_settings(POLI_PAGE=cfg),
        warnings.catch_warnings(record=True) as captured,
    ):
        warnings.simplefilter("always")
        _run_ready()
    return [str(w.message) for w in captured]


def _expected_warning(label: str) -> str:
    return (
        f"Poli Page {label} does not look like "
        "pp_{environment}_{32 lowercase hex characters}; "
        "starting anyway, the API decides whether it is valid."
    )


def _assert_one_warning_without_key_text(
    key: str,
    key_prefix: str | None,
    label: str,
    messages: list[str],
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # No part of the key may be shown, not even a grammar-valid pp_{env}_ prefix:
    # a mis-pasted secret fragment can be grammar-valid too.
    fragments = [key.strip(), SECRET[:8], SECRET[:8].upper()]
    if key_prefix is not None:
        fragments.append(key_prefix)
    captured = capsys.readouterr()
    assert messages == [_expected_warning(label)]
    for output in (messages[0], caplog.text, captured.out, captured.err):
        for fragment in fragments:
            assert fragment not in output


@pytest.fixture
def debug_caplog(caplog: pytest.LogCaptureFixture) -> pytest.LogCaptureFixture:
    # Lowering only the root logger is not enough: Django's logging config keeps
    # the "django" logger at INFO, which would drop a DEBUG leak on django.*.
    caplog.set_level(logging.DEBUG)
    caplog.set_level(logging.DEBUG, logger="django")
    return caplog


@pytest.fixture(autouse=True)
def _no_env_key(monkeypatch: pytest.MonkeyPatch) -> None:
    # The root conftest may load POLI_PAGE_API_KEY from .env; each test sets its own.
    monkeypatch.delenv("POLI_PAGE_API_KEY", raising=False)


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


# (malformed key, its leading pp_{env}_ part when it has one)
MALFORMED_KEYS = [
    ("pp_sandbox_x", "pp_sandbox_"),
    (f"pp_Sandbox_{SECRET}", "pp_Sandbox_"),
    (f"pp_2fa_{SECRET}", "pp_2fa_"),
    ("pp_0123456789abcdef0123_rest", "pp_0123456789abcdef0123_"),
    (f"pp_abc123_{SECRET[:16]}", "pp_abc123_"),
    (f"pp_deadbeef_{SECRET}x", "pp_deadbeef_"),
    (f"pp_a--b_{SECRET}", "pp_a--b_"),
    (f"pp_eu-_{SECRET}", "pp_eu-_"),
    (f"pp_-eu_{SECRET}", "pp_-eu_"),
    (f"pp_eu_prod_{SECRET}", "pp_eu_"),
    (f"pp_{ENV_20}_{SECRET[:31]}", f"pp_{ENV_20}_"),
    (f"pp_{ENV_20}_x", f"pp_{ENV_20}_"),
    (f"pp_sandbox_{SECRET}0", "pp_sandbox_"),
    (f"pp_sandbox_{SECRET.upper()}", "pp_sandbox_"),
    (f"pp_sandbox_{SECRET[:-1]}g", "pp_sandbox_"),
    (f"pp_sandbox_{SECRET}x", "pp_sandbox_"),
    (f"pp_sandbox_{SECRET}\n", "pp_sandbox_"),
    (f"pp_live_{SECRET}\n", "pp_live_"),
    (f" pp_sandbox_{SECRET}", "pp_sandbox_"),
    (f"xpp_sandbox_{SECRET}", "pp_sandbox_"),
    (f"sk_pp_sandbox_{SECRET}", "pp_sandbox_"),
    (f"pp_{ENV_21}_{SECRET}", f"pp_{ENV_21}_"),
    (f"pp__{SECRET}", "pp__"),
    (SECRET, None),
    ("not-a-poli-page-token", None),
]
ENV_LABEL = "API key from POLI_PAGE_API_KEY"


@pytest.mark.parametrize(("key", "key_prefix"), MALFORMED_KEYS)
def test_malformed_key_starts_with_one_warning_without_key_text(
    key: str,
    key_prefix: str | None,
    debug_caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    messages = _ready_warnings(key)
    _assert_one_warning_without_key_text(key, key_prefix, "API_KEY", messages, debug_caplog, capsys)


@pytest.mark.parametrize(("key", "key_prefix"), MALFORMED_KEYS)
def test_malformed_env_fallback_key_starts_with_one_warning_without_key_text(
    key: str,
    key_prefix: str | None,
    monkeypatch: pytest.MonkeyPatch,
    debug_caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # With no API_KEY setting the SDK reads POLI_PAGE_API_KEY, so that key is checked.
    monkeypatch.setenv("POLI_PAGE_API_KEY", key)
    messages = _ready_warnings(None)
    _assert_one_warning_without_key_text(key, key_prefix, ENV_LABEL, messages, debug_caplog, capsys)


@pytest.mark.parametrize("key", [SANDBOX_KEY, f"pp_eu-prod_{SECRET}"])
def test_well_formed_env_fallback_key_starts_without_warning(
    key: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("POLI_PAGE_API_KEY", key)
    assert _ready_warnings(None) == []


def test_api_key_setting_wins_over_a_malformed_env_key(monkeypatch: pytest.MonkeyPatch) -> None:
    # The SDK ignores the env var when API_KEY is set, so only the setting is checked.
    monkeypatch.setenv("POLI_PAGE_API_KEY", "pp_sandbox_x")
    assert _ready_warnings(SANDBOX_KEY) == []


def test_malformed_api_key_setting_warns_even_with_a_well_formed_env_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("POLI_PAGE_API_KEY", SANDBOX_KEY)
    assert _ready_warnings("pp_sandbox_x") == [_expected_warning("API_KEY")]


def test_missing_poli_page_setting_raises(settings: Any) -> None:
    if hasattr(settings, "POLI_PAGE"):
        del settings.POLI_PAGE
    hint = r"POLI_PAGE = \{'API_KEY': 'pp_sandbox_\.\.\.'\}"
    with pytest.raises(ImproperlyConfigured, match=hint):
        _run_ready()


@pytest.mark.parametrize("env_key", [None, ""])
def test_missing_api_key_defers_to_sdk_env_fallback(
    env_key: str | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    # When API_KEY is absent, defer to the SDK's POLI_PAGE_API_KEY
    # env-var fallback. With no usable env key either, ready() neither raises nor
    # warns: the SDK reports the missing key when it builds the client.
    if env_key is not None:
        monkeypatch.setenv("POLI_PAGE_API_KEY", env_key)
    assert _ready_warnings(None) == []


@pytest.mark.parametrize("empty_key", ["", 42, b"pp_sandbox_x"])
def test_empty_or_non_string_api_key_raises_without_key_text(
    empty_key: object,
    debug_caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with (
        override_settings(POLI_PAGE={"API_KEY": empty_key}),
        pytest.raises(ImproperlyConfigured) as raised,
    ):
        _run_ready()
    assert str(raised.value) == "POLI_PAGE['API_KEY'] must be a non-empty string."
    captured = capsys.readouterr()
    for output in (debug_caplog.text, captured.out, captured.err):
        assert "pp_sandbox_" not in output


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
