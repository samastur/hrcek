from __future__ import annotations

from typing import Any, ClassVar

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from hrcek.accounts.managers import UserManager
from hrcek.accounts.validators import validate_display_name


class User(AbstractBaseUser, PermissionsMixin):
    """Someone who uses Hrcek.

    ``password`` (the hash) and ``last_login`` come from
    ``AbstractBaseUser``; ``is_superuser``, ``groups`` and
    ``user_permissions`` from ``PermissionsMixin``.

    ``is_active`` is redeclared here deliberately: the base class defines
    it as a plain class attribute fixed at ``True``, and only a real
    field can be switched off from the admin.
    """

    email = models.EmailField(_("email address"), max_length=254, unique=True)
    # null=True is deliberate and DJ001 is wrong here: NULL means "no
    # display name", and SQL treats NULLs in a unique index as distinct,
    # which is exactly what lets many users have none while set names
    # stay unique. An empty string would collide with itself.
    display_name = models.CharField(  # noqa: DJ001
        _("display name"),
        max_length=50,
        blank=True,
        null=True,
        validators=[validate_display_name],
        help_text=_("Optional. Can be used to sign in instead of the email."),
    )
    email_verified_at = models.DateTimeField(
        _("email confirmed at"), null=True, blank=True
    )
    is_active = models.BooleanField(_("active"), default=True)
    is_staff = models.BooleanField(_("staff status"), default=False)
    date_joined = models.DateTimeField(_("date joined"), default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            # unique=True on email already satisfies Django's auth.E003
            # check; these add the case-insensitive guarantee. NULL
            # display names never collide, because SQL treats NULLs in a
            # unique index as distinct.
            models.UniqueConstraint(Lower("email"), name="user_email_ci_unique"),
            models.UniqueConstraint(
                Lower("display_name"), name="user_display_name_ci_unique"
            ),
        ]

    def __str__(self) -> str:
        return self.display_name or self.email

    def normalise(self) -> None:
        self.email = self.email.strip().lower()
        if self.display_name is not None:
            self.display_name = self.display_name.strip() or None

    def clean(self) -> None:
        self.normalise()
        super().clean()

    def save(self, **kwargs: Any) -> None:
        self.normalise()
        super().save(**kwargs)

    @property
    def is_email_confirmed(self) -> bool:
        return self.email_verified_at is not None
