"""Project-level exception middleware mapping `PoliPageError` to JSON.

Per the django-poli-page spec §10.5, the integration package deliberately
ships no global exception handler; users wire one in their own project.
This middleware is the example project's implementation of that pattern.

Shape: flat `{code, message, status, requestId}` (camelCase, no `error:`
wrapper, no synthesised `"API error (NNN)"` prefix). Status from the SDK's
canonical payload (503 for connection failure, 504 for timeout, otherwise
the upstream HTTP status). Falls through for non-PoliPage exceptions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.http import JsonResponse
from poli_page import PoliPageError

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.http import HttpRequest, HttpResponse


class PoliPageErrorMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self._get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        return self._get_response(request)

    def process_exception(self, request: HttpRequest, exception: Exception) -> JsonResponse | None:
        if not isinstance(exception, PoliPageError):
            return None
        payload = exception.to_payload()
        status = payload["status"] or 500
        return JsonResponse(
            {
                "code": payload["code"],
                "message": payload["message"],
                "status": status,
                "requestId": payload["requestId"],
            },
            status=status,
        )
