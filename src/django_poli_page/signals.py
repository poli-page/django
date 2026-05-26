"""Django signals bridging the SDK's on_retry / on_error callable hooks."""

from __future__ import annotations

from django.dispatch import Signal

poli_page_retry = Signal()
"""Sent before each SDK retry sleep.

Receivers get:
- sender: django_poli_page.apps.PoliPageConfig (the class, not instance)
- event:  poli_page.RetryEvent (with .attempt, .delay_seconds, .reason)
"""

poli_page_error = Signal()
"""Sent on terminal failure (retries exhausted or non-retryable).

Receivers get:
- sender: django_poli_page.apps.PoliPageConfig (the class, not instance)
- error:  poli_page.PoliPageError
"""
