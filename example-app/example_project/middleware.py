"""Project-level middleware for the example app.

The `django-poli-page` package deliberately does NOT wrap SDK calls in
`try/except` (see the repo's CLAUDE.md §10.5 — Django's idiom is explicit
error handling in views). For the demo, we want SDK errors to surface as
proper HTTP responses (e.g. 404 when a document does not exist) instead of
Django's default 500 debug page. This middleware does that mapping once at
the project boundary.
"""

from __future__ import annotations

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
            },
            status=status,
        )
