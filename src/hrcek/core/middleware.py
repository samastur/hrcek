"""Request-scoped plumbing."""

from __future__ import annotations

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse
from sentry_sdk import set_tag

from hrcek.core.request_id import (
    REQUEST_ID_HEADER,
    is_acceptable,
    new_request_id,
    reset_request_id,
    set_request_id,
)


class RequestIDMiddleware:
    """Give every request an id, and put it where it can be found again.

    An id supplied by a caller is honoured when it is well formed, so a
    reverse proxy can correlate its own logs with ours.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        incoming = request.headers.get(REQUEST_ID_HEADER, "").strip()
        request_id = incoming if is_acceptable(incoming) else new_request_id()
        token = set_request_id(request_id)
        try:
            # A no-op when Sentry is not configured.
            set_tag("request_id", request_id)
            response = self.get_response(request)
            response[REQUEST_ID_HEADER] = request_id
            return response
        finally:
            reset_request_id(token)
