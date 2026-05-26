"""Unit-test conftest — snapshots global handler / signal-receiver state per test.

Carries the pattern from symfony-bundle/tests/RestoresGlobalHandlers.php and
nextjs/tests/setup.ts. Documented in INTEGRATIONS_PLAN.md §4.
"""

from __future__ import annotations

import importlib
import signal
from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True)
def restore_signal_handlers() -> Iterator[None]:
    """Snapshot global signal.signal(...) handlers; restore after each test.

    Django's runserver and several management commands install SIGINT handlers.
    Tests that boot one and forget to restore the previous handler will leak
    into the next test and pytest-django will flag the leak.
    """
    sigint = signal.getsignal(signal.SIGINT)
    sigterm = signal.getsignal(signal.SIGTERM)
    try:
        yield
    finally:
        signal.signal(signal.SIGINT, sigint)
        signal.signal(signal.SIGTERM, sigterm)


@pytest.fixture(autouse=True)
def restore_poli_page_signal_receivers() -> Iterator[None]:
    """Snapshot Django signal receivers for poli_page_retry / poli_page_error.

    Tests that connect a listener for these signals MUST balance with disconnect
    in teardown. This fixture provides the safety net: any receivers added during
    the test are disconnected at teardown.
    """
    # Why: signals module is added in Task 5. Dynamic import keeps the snapshot
    # fixture forward-compatible without a static reference that mypy can't
    # resolve before Task 5 lands.
    try:
        signals = importlib.import_module("django_poli_page.signals")
    except ImportError:
        yield
        return

    retry = signals.poli_page_retry
    error = signals.poli_page_error
    snapshot_retry = list(retry.receivers)
    snapshot_error = list(error.receivers)
    try:
        yield
    finally:
        retry.receivers = snapshot_retry
        error.receivers = snapshot_error
