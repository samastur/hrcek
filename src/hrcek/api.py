"""The root API and the single place failures become responses."""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse
from ninja import NinjaAPI
from ninja.errors import ValidationError as NinjaValidationError
from sentry_sdk import capture_exception

from hrcek.core.api import router as core_router
from hrcek.core.errors import (
    INTERNAL_ERROR,
    NOT_FOUND,
    VALIDATION_ERROR,
    ErrorCode,
    HrcekError,
)

logger = logging.getLogger(__name__)


def error_payload(
    error_code: ErrorCode, details: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Render an error code in the request's active language.

    ``str()`` on the lazy message resolves it now, which is why the
    caller must be inside the request whose locale it should use.
    """
    return {
        "error": {
            "code": error_code.code,
            "message": str(error_code.message),
            "details": details or {},
        }
    }


def register_exception_handlers(api: NinjaAPI) -> None:
    """Attach the failure-to-response mapping to *api*."""

    @api.exception_handler(HrcekError)
    def _handle_known(request: HttpRequest, exc: HrcekError) -> HttpResponse:
        return api.create_response(
            request,
            error_payload(exc.error_code, exc.details),
            status=exc.error_code.http_status,
        )

    @api.exception_handler(NinjaValidationError)
    def _handle_validation(
        request: HttpRequest, exc: NinjaValidationError
    ) -> HttpResponse:
        return api.create_response(
            request,
            error_payload(VALIDATION_ERROR, {"fields": exc.errors}),
            status=VALIDATION_ERROR.http_status,
        )

    @api.exception_handler(Http404)
    def _handle_not_found(request: HttpRequest, exc: Http404) -> HttpResponse:
        return api.create_response(
            request,
            error_payload(NOT_FOUND),
            status=NOT_FOUND.http_status,
        )

    @api.exception_handler(Exception)
    def _handle_unexpected(request: HttpRequest, exc: Exception) -> HttpResponse:
        # The traceback goes to the log and to Sentry; the client gets a
        # code and nothing else. Never widen this payload.
        logger.exception("Unhandled exception while serving %s", request.path)
        capture_exception(exc)
        return api.create_response(
            request,
            error_payload(INTERNAL_ERROR),
            status=INTERNAL_ERROR.http_status,
        )


api = NinjaAPI(
    title="Hrček API",
    version="1.0.0",
    # Interactive docs are useful in development and noise in production.
    docs_url="/docs" if settings.API_DOCS_ENABLED else None,
)
register_exception_handlers(api)
api.add_router("/", core_router)
