"""Endpoints belonging to the core app."""

from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest
from django.utils.translation import gettext as _
from ninja import Router

from hrcek.core.schemas import HealthOut

router = Router(tags=["core"])


@router.get("/health", response=HealthOut, operation_id="health", auth=None)
def health(request: HttpRequest) -> dict[str, str]:
    """Report that the service is up, in the caller's language."""
    return {
        "status": "ok",
        "service": "hrcek",
        "version": settings.HRCEK_VERSION,
        "message": _("Service is running."),
    }
