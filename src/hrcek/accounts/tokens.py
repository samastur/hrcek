"""Signed, stateless email-confirmation tokens.

No table: the signature carries the user id and a timestamp, and
``max_age`` enforces expiry. A row would add nothing but cleanup.
"""

from __future__ import annotations

from django.conf import settings
from django.core import signing

from hrcek.accounts.models import User

CONFIRMATION_SALT = "hrcek.accounts.email-confirmation"


def make_confirmation_token(user: User) -> str:
    return signing.dumps({"user": user.pk}, salt=CONFIRMATION_SALT)


def read_confirmation_token(token: str) -> User | None:
    max_age = settings.HRCEK_EMAIL_CONFIRMATION_EXPIRY_HOURS * 3600
    try:
        payload = signing.loads(token, salt=CONFIRMATION_SALT, max_age=max_age)
    except signing.BadSignature:
        # Covers tampering and expiry alike: SignatureExpired subclasses it.
        return None
    return User.objects.filter(pk=payload.get("user")).first()


EMAIL_CHANGE_SALT = "hrcek.accounts.email-change"


def make_email_change_token(user: User, new_email: str) -> str:
    """Sign the target address into the token, not just the user id.

    Without it, a link issued for one pending address would apply
    whatever the pending address happened to be by the time it was used.
    """
    return signing.dumps({"user": user.pk, "email": new_email}, salt=EMAIL_CHANGE_SALT)


def read_email_change_token(token: str) -> tuple[User, str] | None:
    max_age = settings.HRCEK_EMAIL_CONFIRMATION_EXPIRY_HOURS * 3600
    try:
        payload = signing.loads(token, salt=EMAIL_CHANGE_SALT, max_age=max_age)
    except signing.BadSignature:
        return None
    user = User.objects.filter(pk=payload.get("user")).first()
    email = payload.get("email")
    if user is None or not email:
        return None
    return user, email
