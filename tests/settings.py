"""Minimal Django settings for the test suite."""

from __future__ import annotations

SECRET_KEY = "test-suite-not-secret"
DEBUG = False
DATABASES = {
    "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"},
}
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django_poli_page",
]
USE_TZ = True

POLI_PAGE = {
    "API_KEY": "pp_test_unit_default",
}
