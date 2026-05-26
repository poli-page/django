#!/usr/bin/env python
"""Django's command-line utility for the example project."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _load_root_env() -> None:
    """Load the workspace-root .env if present; never overwrite real env vars."""
    # Look two levels up: example-app/manage.py -> django/ -> Projects/.env
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if not env_path.exists():
        # Fallback: example-app's own .env (template defaults).
        env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        os.environ.setdefault(key, val)


def main() -> None:
    _load_root_env()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example_project.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
