"""Minimal Django settings for the test suite. Replaced in Task 2."""

from __future__ import annotations

SECRET_KEY = "test-suite-not-secret"
DEBUG = False
DATABASES = {
    "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"},
}
INSTALLED_APPS: list[str] = []
USE_TZ = True
