from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock


def test_dispatch_retry_sends_signal() -> None:
    from poli_page import RetryEvent

    from django_poli_page._hooks import dispatch_retry
    from django_poli_page.signals import poli_page_retry

    captured: list[dict[str, Any]] = []

    def listener(sender: Any, event: Any, **kwargs: Any) -> None:
        captured.append({"sender": sender, "event": event})

    poli_page_retry.connect(listener)
    try:
        event = RetryEvent(attempt=2, delay_seconds=0.25, reason=MagicMock(spec_set=Exception))
        dispatch_retry(event)
    finally:
        poli_page_retry.disconnect(listener)

    assert len(captured) == 1
    assert captured[0]["event"] is event


def test_dispatch_error_sends_signal() -> None:
    from poli_page import PoliPageError

    from django_poli_page._hooks import dispatch_error
    from django_poli_page.signals import poli_page_error

    captured: list[dict[str, Any]] = []

    def listener(sender: Any, error: Any, **kwargs: Any) -> None:
        captured.append({"sender": sender, "error": error})

    poli_page_error.connect(listener)
    try:
        err = PoliPageError("boom", code="INTERNAL", status=500)
        dispatch_error(err)
    finally:
        poli_page_error.disconnect(listener)

    assert len(captured) == 1
    assert captured[0]["error"] is err
