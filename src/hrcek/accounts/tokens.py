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
