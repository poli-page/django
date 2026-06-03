<<<<<<< HEAD
"""Project-level middleware for the example app.

The `django-poli-page` package deliberately does NOT wrap SDK calls in
`try/except` (see the repo's CLAUDE.md §10.5 — Django's idiom is explicit
error handling in views). For the demo, we want SDK errors to surface as
proper HTTP responses (e.g. 404 when a document does not exist) instead of
Django's default 500 debug page. This middleware does that mapping once at
the project boundary.
=======
"""Project-level exception middleware mapping `PoliPageError` to JSON.

Per the django-poli-page spec §10.5, the integration package deliberately
ships no global exception handler; users wire one in their own project.
This middleware is the example project's implementation of that pattern.

Shape: flat `{code, message, status, requestId}` (camelCase, no `error:`
wrapper, no synthesised `"API error (NNN)"` prefix). Status from the SDK's
canonical payload (503 for connection failure, 504 for timeout, otherwise
the upstream HTTP status). Falls through for non-PoliPage exceptions.
>>>>>>> 2999d51 (feat(example-app): canonical error middleware via SDK to_payload())
"""

from __future__ import annotations

<<<<<<< HEAD
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse, JsonResponse
from poli_page import PoliPageError


class PoliPageErrorMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        return self.get_response(request)

    def process_exception(self, request: HttpRequest, exc: Exception) -> HttpResponse | None:
        if not isinstance(exc, PoliPageError):
            return None
        status = exc.status if exc.status and exc.status >= 400 else 500
        return JsonResponse(
            {
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "status": exc.status,
                    "request_id": exc.request_id,
                }
=======
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
                "requestId": payload["request_id"],
>>>>>>> 2999d51 (feat(example-app): canonical error middleware via SDK to_payload())
            },
            status=status,
        )
