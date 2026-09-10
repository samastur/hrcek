from __future__ import annotations

from typing import Any

from django.contrib.auth.backends import BaseBackend
from django.db.models import Q
from django.http import HttpRequest

from hrcek.accounts.models import User


class EmailOrDisplayNameBackend(BaseBackend):
    """Authenticate against either identifier a person may have.

    A display name can never contain "@" (see ``validate_display_name``),
    so the two identifier spaces cannot overlap.

    Email confirmation is deliberately *not* checked here. A backend can
    only return a user or None, so folding that check in would collapse
    "wrong password" and "unconfirmed address" into one indistinct
    failure. Callers check ``is_email_confirmed`` after the password is
    confirmed, which leaks nothing.
    """

    def authenticate(
        self,
        request: HttpRequest | None,
        username: str | None = None,
        password: str | None = None,
        **kwargs: Any,
    ) -> User | None:
        identifier = username or kwargs.get(User.USERNAME_FIELD)
        if not identifier or not password:
            return None

        user = User.objects.filter(
            Q(email__iexact=identifier) | Q(display_name__iexact=identifier)
        ).first()
        if user is None:
            # Hash anyway: without this, a missing account answers
            # measurably faster than a wrong password.
            User().set_password(password)
            return None

        if user.check_password(password) and user.is_active:
            return user
        return None

    def get_user(self, user_id: int) -> User | None:
        user = User.objects.filter(pk=user_id).first()
        return user if user is not None and user.is_active else None
