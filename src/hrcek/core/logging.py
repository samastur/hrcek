"""One-line JSON log records, so logs stay greppable and parseable."""

from __future__ import annotations

import json
import logging

from hrcek.core.request_id import get_request_id


def _request_id_for(record: logging.LogRecord) -> str:
    """The id of the request this record belongs to.

    Usually the context variable, set for the life of the request. It
    is empty for the one record that matters most: Django logs a
    failing response after the middleware chain has unwound. That
    record carries the request, which the middleware stamped, so the
    id survives the unwinding there.
    """
    active = get_request_id()
    if active:
        return active
    request = getattr(record, "request", None)
    return getattr(request, "request_id", "") or ""


class JSONFormatter(logging.Formatter):
    """Render a log record as a single JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": _request_id_for(record),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)
