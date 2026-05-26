"""Django AppConfig — validates settings.POLI_PAGE at startup."""

from __future__ import annotations

import re
import warnings
from typing import Any
from urllib.parse import urlparse

from django.apps import AppConfig
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

_API_KEY_RE = re.compile(r"^pp_(test|live)_")
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
                "Set POLI_PAGE = {'API_KEY': 'pp_test_...'} in your settings module. "
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
            if not _API_KEY_RE.match(api_key):
                raise ImproperlyConfigured(
                    "Poli Page API_KEY must start with pp_test_ or pp_live_. "
                    "Get one at https://app.poli.page/settings/api-keys.",
                )

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
