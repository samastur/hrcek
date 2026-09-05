"""The error-code registry.

Every failure a client can see is registered here (or in another app's
``errors`` module) with a stable code and a translatable description.
Codes are ``HRC-<DOMAIN>-<NNNN>``: greppable, sortable, and namespaced
per area. Uniqueness is enforced at import time and re-checked by the
test suite, so a duplicate cannot reach a release.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from django.utils.functional import Promise
from django.utils.translation import gettext_lazy as _

CODE_PATTERN = re.compile(r"^HRC-[A-Z]{3,6}-\d{4}$")


@dataclass(frozen=True, slots=True)
class ErrorCode:
    """A stable identifier plus the translatable text shown to a user."""

    code: str
    http_status: int
    message: Promise


_REGISTRY: dict[str, ErrorCode] = {}


def register(code: str, http_status: int, message: Promise) -> ErrorCode:
    """Register and return an error code, refusing anything malformed."""
    if not CODE_PATTERN.match(code):
        raise ValueError(
            f"Malformed error code {code!r}; expected HRC-<DOMAIN>-<NNNN>."
        )
    if not isinstance(message, Promise):
        raise TypeError(
            f"Message for {code} must be a lazy translatable string "
            f"(use gettext_lazy), got {type(message).__name__}."
        )
    if code in _REGISTRY:
        raise ValueError(f"Duplicate error code {code}.")
    entry = ErrorCode(code=code, http_status=http_status, message=message)
    _REGISTRY[code] = entry
    return entry


def registry() -> dict[str, ErrorCode]:
    """Return a copy of the registry, so callers cannot corrupt it."""
    return dict(_REGISTRY)


class HrcekError(Exception):
    """Any failure that should reach the client as a registered code."""

    def __init__(
        self, error_code: ErrorCode, details: dict[str, Any] | None = None
    ) -> None:
        self.error_code = error_code
        self.details: dict[str, Any] = details or {}
        super().__init__(error_code.code)


INTERNAL_ERROR = register("HRC-CORE-0001", 500, _("An unexpected error occurred."))
VALIDATION_ERROR = register("HRC-CORE-0002", 422, _("The submitted data is not valid."))
NOT_FOUND = register("HRC-CORE-0003", 404, _("The requested resource does not exist."))
