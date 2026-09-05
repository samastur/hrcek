"""Optional Sentry reporting.

Sentry is an enhancement, never a dependency: with no DSN the SDK is
never initialised and every ``sentry_sdk`` call elsewhere in the code
becomes a no-op. Nothing else changes.
"""

from __future__ import annotations

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration


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
        integrations=[
            DjangoIntegration(),
            # Errors arrive through capture_exception in the API's
            # catch-all handler; taking them from log records too would
            # double-count them.
            LoggingIntegration(level=None, event_level=None),
        ],
    )
    return True
