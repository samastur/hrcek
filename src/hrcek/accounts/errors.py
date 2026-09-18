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
SESSION_REQUIRED = register(
    "HRC-AUTH-0006",
    403,
    _("Creating a token needs a signed-in session, not another token."),
)
INVITATION_INVALID = register(
    "HRC-ACCT-0002",
    400,
    _("This invitation link is not valid. It may have expired or been used."),
)
DISPLAY_NAME_TAKEN = register(
    "HRC-ACCT-0004", 409, _("That display name is already taken.")
)
SIGNUP_NOT_ALLOWED = register(
    "HRC-ACCT-0001",
    403,
    _("This email address is not allowed to create an account here."),
)
CONFIRMATION_INVALID = register(
    "HRC-ACCT-0003",
    400,
    _("This confirmation link is not valid. It may have expired."),
)
EMAIL_CHANGE_INVALID = register(
    "HRC-ACCT-0005",
    400,
    _("This email change link is not valid. It may have expired."),
)
EMAIL_ALREADY_IN_USE = register(
    "HRC-ACCT-0006", 409, _("That email address is already in use.")
)
