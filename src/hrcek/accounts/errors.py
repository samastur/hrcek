"""Error codes owned by the accounts app."""

from django.utils.translation import gettext_lazy as _

from hrcek.core.errors import register

INVALID_CREDENTIALS = register(
    "HRC-AUTH-0001", 401, _("The email address or password is not correct.")
)
EMAIL_NOT_CONFIRMED = register(
    "HRC-AUTH-0002", 403, _("Confirm your email address before signing in.")
)
AUTHENTICATION_REQUIRED = register(
    "HRC-AUTH-0003", 401, _("You must sign in to do that.")
)
INVALID_API_TOKEN = register(
    "HRC-AUTH-0004", 401, _("This API token is invalid or has expired.")
)
CSRF_FAILED = register(
    "HRC-AUTH-0005", 403, _("The request could not be verified. Try again.")
)
