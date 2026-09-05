"""The identifier that ties a log line, a response and a Sentry event
to one request."""

from __future__ import annotations

import re
import uuid
from contextvars import ContextVar, Token

REQUEST_ID_HEADER = "X-Request-ID"

# Deliberately strict: the value is echoed back in a response header, so
# anything that could smuggle CR/LF or header syntax is rejected rather
# than sanitised.
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

_request_id: ContextVar[str] = ContextVar("hrcek_request_id", default="")


def new_request_id() -> str:
    return uuid.uuid4().hex


def get_request_id() -> str:
    return _request_id.get()


def set_request_id(value: str) -> Token[str]:
    return _request_id.set(value)


def reset_request_id(token: Token[str]) -> None:
    _request_id.reset(token)


def is_acceptable(value: str) -> bool:
    return bool(REQUEST_ID_PATTERN.match(value))
