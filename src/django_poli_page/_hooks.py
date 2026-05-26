"""Internal SDK-hook → Django-signal bridges.

Real implementation lands in Task 5; the stubs here let client.py import
without crashing.
"""

from __future__ import annotations

from typing import Any


def dispatch_retry(event: Any) -> None:
    del event


def dispatch_error(err: Any) -> None:
    del err
