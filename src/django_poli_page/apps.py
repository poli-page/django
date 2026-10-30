"""Django AppConfig — validates settings.POLI_PAGE at startup."""

from __future__ import annotations

import os
import re
import warnings
from typing import Any
from urllib.parse import urlparse

from django.apps import AppConfig
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.signals import setting_changed

from django_poli_page.middleware import MIDDLEWARE_PATH

# The SDK contract's full-key regex `^pp_{env}_{32 hex}$`, where {env} starts with
# a letter, then lowercase letters, digits and single inner hyphens, at most 20
# characters. fullmatch anchors both ends (unlike `$`, it also rejects a trailing
# newline).
_API_KEY_RE = re.compile(r"pp_(?=[a-z][a-z0-9-]{0,19}_)[a-z][a-z0-9]*(?:-[a-z0-9]+)*_[0-9a-f]{32}")
_KNOWN_KEYS = frozenset(
    {
        "API_KEY",
        "BASE_URL",
        "TIMEOUT",
        "RETRIES",
        "ON_RETRY",
        "ON_ERROR",
        "HTTP_CLIENT",
        "ERROR_HANDLER",
    }
)
_KNOWN_RETRY_KEYS = frozenset({"MAX_ATTEMPTS", "DELAY_SECONDS"})


class PoliPageConfig(AppConfig):
    name = "django_poli_page"
    verbose_name = "Poli Page"
    default = True
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        cfg = getattr(settings, "POLI_PAGE", None)
        if cfg is None:
            raise ImproperlyConfigured(
                "Set POLI_PAGE = {'API_KEY': 'pp_sandbox_...'} in your settings module. "
                "See https://docs.poli.page/integrations/django for the full schema.",
            )
        if not isinstance(cfg, dict):
            raise ImproperlyConfigured("POLI_PAGE must be a dict.")

        self._validate(cfg)
        if cfg.get("ERROR_HANDLER", True):
            _install_error_handler()
        setting_changed.connect(_reset_client_on_change, dispatch_uid="django_poli_page.client")

    def _validate(self, cfg: dict[str, Any]) -> None:
        api_key = cfg.get("API_KEY")
        if api_key is not None:
            if not isinstance(api_key, str) or not api_key:
                raise ImproperlyConfigured("POLI_PAGE['API_KEY'] must be a non-empty string.")
            _warn_if_malformed(api_key, "API_KEY")
        else:
            # The SDK falls back to this env var when API_KEY is absent; with no
            # usable value either, the SDK reports the missing key itself.
            env_key = os.environ.get("POLI_PAGE_API_KEY")
            if env_key:
                _warn_if_malformed(env_key, "API key from POLI_PAGE_API_KEY")

        base_url = cfg.get("BASE_URL")
        if base_url is not None:
            if not isinstance(base_url, str):
                raise ImproperlyConfigured("POLI_PAGE['BASE_URL'] must be a string.")
            scheme = urlparse(base_url).scheme
            if scheme not in {"http", "https"}:
                raise ImproperlyConfigured(
                    f"POLI_PAGE['BASE_URL'] must use http or https scheme. Got: {base_url!r}",
                )

        error_handler = cfg.get("ERROR_HANDLER")
        if error_handler is not None and not isinstance(error_handler, bool):
            raise ImproperlyConfigured("POLI_PAGE['ERROR_HANDLER'] must be True or False.")

        timeout = cfg.get("TIMEOUT")
        if timeout is not None:
            if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
                raise ImproperlyConfigured("POLI_PAGE['TIMEOUT'] must be a number.")
            if not (0 < timeout <= 600):
                raise ImproperlyConfigured(
                    f"POLI_PAGE['TIMEOUT'] must be > 0 and <= 600 seconds. Got: {timeout!r}",
                )

        retries = cfg.get("RETRIES")
        if retries is not None:
            if not isinstance(retries, dict):
                raise ImproperlyConfigured("POLI_PAGE['RETRIES'] must be a dict.")
            max_attempts = retries.get("MAX_ATTEMPTS")
            if max_attempts is not None:
                if isinstance(max_attempts, bool) or not isinstance(max_attempts, int):
                    raise ImproperlyConfigured("POLI_PAGE['RETRIES']['MAX_ATTEMPTS'] must be int.")
                if not (0 <= max_attempts <= 10):
                    raise ImproperlyConfigured(
                        "POLI_PAGE['RETRIES']['MAX_ATTEMPTS'] must be between 0 and 10. "
                        f"Got: {max_attempts!r}",
                    )
            delay = retries.get("DELAY_SECONDS")
            if delay is not None:
                if isinstance(delay, bool) or not isinstance(delay, (int, float)):
                    raise ImproperlyConfigured(
                        "POLI_PAGE['RETRIES']['DELAY_SECONDS'] must be number."
                    )
                if not (0 <= delay <= 30):
                    raise ImproperlyConfigured(
                        "POLI_PAGE['RETRIES']['DELAY_SECONDS'] must be between 0 and 30. "
                        f"Got: {delay!r}",
                    )
            unknown_retry = set(retries) - _KNOWN_RETRY_KEYS
            for key in unknown_retry:
                warnings.warn(f"Unknown POLI_PAGE['RETRIES'] key: {key!r}", stacklevel=2)

        unknown_top = set(cfg) - _KNOWN_KEYS
        for key in unknown_top:
            warnings.warn(f"Unknown POLI_PAGE key: {key!r}", stacklevel=2)


def _warn_if_malformed(api_key: str, label: str) -> None:
    # The API is the only authority on keys (a new environment needs no
    # release here), so a malformed key is flagged, never refused. The warning
    # shows no part of the key: even a pp_{env}_ prefix can be a pasted secret.
    if not _API_KEY_RE.fullmatch(api_key):
        warnings.warn(
            f"Poli Page {label} does not look like "
            "pp_{environment}_{32 lowercase hex characters}; "
            "starting anyway, the API decides whether it is valid.",
            stacklevel=3,
        )


def _install_error_handler() -> None:
    # Appended, so it is the innermost middleware: its process_exception() sees
    # a view's PoliPageError first. Django builds the middleware chain after
    # ready() (WSGI/ASGI handlers, the test client), so the change takes effect.
    middleware = list(getattr(settings, "MIDDLEWARE", None) or [])
    if MIDDLEWARE_PATH not in middleware:
        settings.MIDDLEWARE = [*middleware, MIDDLEWARE_PATH]


def _reset_client_on_change(*, setting: str, **kwargs: Any) -> None:
    # override_settings(POLI_PAGE=...) in a test: the next access to
    # `django_poli_page.client` builds a client from the new settings.
    if setting == "POLI_PAGE":
        from django_poli_page._client import reset_client

        reset_client()
