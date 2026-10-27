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

# `pp_{env}_`, where {env} follows the SDK contract's environment-name grammar
# (a letter first, then lowercase letters, digits and single inner hyphens, at
# most 20 characters).
_ENV_PREFIX = r"pp_(?=[a-z][a-z0-9-]{0,19}_)[a-z][a-z0-9]*(?:-[a-z0-9]+)*_"
# The SDK contract's full-key regex `^pp_{env}_{32 hex}$`; fullmatch anchors both
# ends (unlike `$`, it also rejects a trailing newline).
_API_KEY_RE = re.compile(_ENV_PREFIX + r"[0-9a-f]{32}")
# The only part of a malformed key a warning may show.
_SHOWABLE_PREFIX_RE = re.compile(_ENV_PREFIX)
_KNOWN_KEYS = frozenset(
    {"API_KEY", "BASE_URL", "TIMEOUT", "RETRIES", "ON_RETRY", "ON_ERROR", "HTTP_CLIENT"}
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
    # release here), so a malformed key is flagged, never refused.
    if not _API_KEY_RE.fullmatch(api_key):
        prefix = _SHOWABLE_PREFIX_RE.match(api_key)
        shown = f'"{prefix.group()}…" ' if prefix else ""
        warnings.warn(
            f"Poli Page {label} {shown}does not look like "
            "pp_{environment}_{32 hex characters}; "
            "starting anyway, the API decides whether it is valid.",
            stacklevel=3,
        )
