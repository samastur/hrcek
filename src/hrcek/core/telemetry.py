"""Optional Sentry reporting.

Sentry is an enhancement, never a dependency: with no DSN the SDK is
never initialised and every ``sentry_sdk`` call elsewhere in the code
becomes a no-op. Nothing else changes.
"""

from __future__ import annotations

from typing import Any

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration


def strip_query_strings(event: Any, _hint: Any = None) -> Any:
    """Take the query string off an event before it is sent.

    `send_default_pii=False` covers cookies, bodies and user details;
    it does not cover the query string, which the WSGI integration
    attaches to every event. This project stores what a family reads,
    and anything that ends up in a query string would otherwise leave
    the machine on the next error.

    Deliberately forgiving: a `before_send` that raises loses the
    error it was called to report.
    """
    try:
        request = event.get("request")
        if not isinstance(request, dict):
            return event
        request.pop("query_string", None)
        url = request.get("url")
        if isinstance(url, str) and "?" in url:
            request["url"] = url.split("?", 1)[0]
    except (AttributeError, TypeError):  # pragma: no cover - belt and braces
        return event
    return event


def configure_sentry(
    dsn: str,
    *,
    environment: str,
    release: str,
    traces_sample_rate: float,
) -> bool:
    """Initialise Sentry when a DSN is present. Returns whether it did."""
    if not dsn:
        return False

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        traces_sample_rate=traces_sample_rate,
        # This project stores what a family reads. None of that should
        # leave the machine as a side effect of an error report.
        send_default_pii=False,
        # ...and the query string, which that flag does not cover.
        before_send=strip_query_strings,
        before_send_transaction=strip_query_strings,
        integrations=[
            DjangoIntegration(),
            # Errors arrive through capture_exception in the API's
            # catch-all handler; taking them from log records too would
            # double-count them.
            LoggingIntegration(level=None, event_level=None),
        ],
    )
    return True
