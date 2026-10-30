"""Error handler: answers a `PoliPageError` raised by a view as JSON.

`AppConfig.ready()` appends `PoliPageErrorMiddleware` to `settings.MIDDLEWARE`
unless `POLI_PAGE["ERROR_HANDLER"]` is `False`, so the handler is on as soon as
the app is installed. The answer is the SDK's canonical payload:

- body: `error.to_payload()`, exactly `{"code", "message", "status", "requestId"}`;
- status: the payload's `status` (the API's status, 503 for `network_error`,
  504 for `timeout`), or 500 when the error has none.

Exceptions that are not a `PoliPageError` go on to Django's own handling.
"""

from __future__ import annotations

from django.http import HttpRequest, JsonResponse
from django.utils.deprecation import MiddlewareMixin
from poli_page import PoliPageError

#: The dotted path `AppConfig.ready()` adds to `settings.MIDDLEWARE`.
MIDDLEWARE_PATH = "django_poli_page.middleware.PoliPageErrorMiddleware"


def error_response(error: PoliPageError) -> JsonResponse:
    """The handler's answer for `error`: its `to_payload()` body and status (500 when none)."""
    payload = error.to_payload()
    status = payload["status"]
    return JsonResponse(payload, status=status if isinstance(status, int) else 500)


class PoliPageErrorMiddleware(MiddlewareMixin):
    """Turns a `PoliPageError` raised by a view into its JSON answer (sync and async)."""

    def process_exception(self, request: HttpRequest, exception: Exception) -> JsonResponse | None:
        if isinstance(exception, PoliPageError):
            return error_response(exception)
        return None
