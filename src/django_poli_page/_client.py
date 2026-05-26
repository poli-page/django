"""Lazy singleton `client` — built on first attribute access, not at import."""

from __future__ import annotations

from typing import Any, cast

from django.utils.functional import SimpleLazyObject
from django.utils.module_loading import import_string
from poli_page import PoliPage

from django_poli_page.conf import get_config


def _build_client() -> PoliPage:
    cfg = get_config()
    kwargs: dict[str, Any] = {}

    api_key = cfg.get("API_KEY")
    if api_key:
        kwargs["api_key"] = api_key

    base_url = cfg.get("BASE_URL")
    if base_url is not None:
        kwargs["base_url"] = base_url

    timeout = cfg.get("TIMEOUT")
    if timeout is not None:
        kwargs["timeout"] = timeout

    retries = cfg.get("RETRIES") or {}
    max_attempts = retries.get("MAX_ATTEMPTS")
    if max_attempts is not None:
        kwargs["max_retries"] = max_attempts
    delay = retries.get("DELAY_SECONDS")
    if delay is not None:
        kwargs["retry_delay"] = delay

    on_retry_path = cfg.get("ON_RETRY")
    if on_retry_path is not None:
        kwargs["on_retry"] = import_string(on_retry_path)
    else:
        from django_poli_page._hooks import dispatch_retry

        kwargs["on_retry"] = dispatch_retry

    on_error_path = cfg.get("ON_ERROR")
    if on_error_path is not None:
        kwargs["on_error"] = import_string(on_error_path)
    else:
        from django_poli_page._hooks import dispatch_error

        kwargs["on_error"] = dispatch_error

    http_client_path = cfg.get("HTTP_CLIENT")
    if http_client_path is not None:
        factory = import_string(http_client_path)
        kwargs["http_client"] = factory()

    return PoliPage(**kwargs)


client: PoliPage = cast(PoliPage, SimpleLazyObject(_build_client))
"""Process-wide PoliPage singleton, built lazily on first attribute access."""
