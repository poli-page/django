"""The retry budget setting: `MAX_RETRIES`, and its deprecated alias `MAX_ATTEMPTS`."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from django.core.exceptions import ImproperlyConfigured

# `MAX_ATTEMPTS` was the first name of this setting. It always meant the SDK's
# `max_retries` (retries after the first attempt, so a call makes at most
# `MAX_RETRIES + 1` attempts), which the word "attempts" got wrong.
DEPRECATED_ALIAS = "MAX_ATTEMPTS"
KEY = "MAX_RETRIES"


def resolve_max_retries(retries: Mapping[str, Any]) -> int | None:
    """Return the validated retry budget of a `RETRIES` dict, or None when unset.

    Raises ImproperlyConfigured when the value is not an int in [0, 10], or when
    `MAX_RETRIES` and `MAX_ATTEMPTS` are both set to different values.
    """
    value = retries.get(KEY)
    alias = retries.get(DEPRECATED_ALIAS)
    if value is not None and alias is not None and value != alias:
        raise ImproperlyConfigured(
            f"POLI_PAGE['RETRIES'] sets both {KEY} ({value!r}) and its deprecated alias "
            f"{DEPRECATED_ALIAS} ({alias!r}) to different values. Keep {KEY} only.",
        )
    name = KEY if value is not None else DEPRECATED_ALIAS
    chosen = value if value is not None else alias
    if chosen is None:
        return None
    if isinstance(chosen, bool) or not isinstance(chosen, int):
        raise ImproperlyConfigured(f"POLI_PAGE['RETRIES']['{name}'] must be int.")
    if not (0 <= chosen <= 10):
        raise ImproperlyConfigured(
            f"POLI_PAGE['RETRIES']['{name}'] must be between 0 and 10. Got: {chosen!r}",
        )
    return chosen
