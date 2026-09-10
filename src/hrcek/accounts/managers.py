from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.contrib.auth.base_user import BaseUserManager
from django.utils import timezone

if TYPE_CHECKING:
    from hrcek.accounts.models import User


class UserManager(BaseUserManager):
    """Creates users from an email address rather than a username.

    The ValueError messages here report programming errors to a
    developer, not conditions to a user, so they are not translated.
    """

    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra: Any) -> User:
        if not email:
            raise ValueError("An email address is required.")
        display_name = (extra.pop("display_name", None) or "").strip() or None
        user = self.model(
            email=self.normalize_email(email).strip().lower(),
            display_name=display_name,
            **extra,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(
        self, email: str, password: str | None = None, **extra: Any
    ) -> User:
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(
        self, email: str, password: str | None = None, **extra: Any
    ) -> User:
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        # The admin refuses unconfirmed accounts, and nobody can send a
        # confirmation email to the very first user.
        extra.setdefault("email_verified_at", timezone.now())
        if extra["is_staff"] is not True:
            raise ValueError("A superuser must have is_staff=True.")
        if extra["is_superuser"] is not True:
            raise ValueError("A superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra)
