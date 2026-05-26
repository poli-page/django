"""Helper to read settings.POLI_PAGE with a single import surface."""

from __future__ import annotations

from typing import Any

from django.conf import settings


def get_config() -> dict[str, Any]:
    """Return settings.POLI_PAGE (or an empty dict when unset)."""
    return getattr(settings, "POLI_PAGE", {}) or {}
