"""Internal SDK-hook → Django-signal bridges.

Wired by _client.py when the user doesn't supply ON_RETRY / ON_ERROR dotted
paths in settings.POLI_PAGE. The SDK invokes these as plain callables; they
translate to Django signal sends.
"""

from __future__ import annotations

from poli_page import PoliPageError, RetryEvent

from django_poli_page.signals import poli_page_error, poli_page_retry


def dispatch_retry(event: RetryEvent) -> None:
    from django_poli_page.apps import PoliPageConfig

    poli_page_retry.send(sender=PoliPageConfig, event=event)


def dispatch_error(err: PoliPageError) -> None:
    from django_poli_page.apps import PoliPageConfig

    poli_page_error.send(sender=PoliPageConfig, error=err)
