"""Sample context for each email, used by manage.py preview_emails.

Kept realistic on purpose: a preview full of "foo" does not show whether
a real name or a real date breaks the layout.
"""

from __future__ import annotations

from typing import Any

PREVIEW_CONTEXTS: dict[str, dict[str, Any]] = {
    "invitation": {
        "invited_by": "Marko Samastur",
        "accept_url": "https://hrcek.example.com/accounts/invitation/"
        "8Xr2mQ7pLk4vNs1TzYbW/",
        "expires_at": "18 September 2026",
    },
    "email_confirmation": {
        "confirm_url": "https://hrcek.example.com/accounts/confirm/"
        "aG9sYS1tdW5kbzpzaWduYXR1cmU/",
        "expires_hours": 48,
    },
    "signup_existing_account": {
        "reset_url": "https://hrcek.example.com/accounts/password/reset/",
    },
    "password_reset": {
        "reset_url": "https://hrcek.example.com/accounts/password/reset/"
        "MQ/ct1a2b-3c4d5e6f/",
    },
}
