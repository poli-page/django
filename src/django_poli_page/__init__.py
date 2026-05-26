"""Django integration for the Poli Page PDF rendering SDK."""

from __future__ import annotations

from django_poli_page._client import client
from django_poli_page._version import __version__

__all__ = ["__version__", "client"]

default_app_config = "django_poli_page.apps.PoliPageConfig"
