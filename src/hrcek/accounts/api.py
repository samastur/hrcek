"""Authentication endpoints.

There is deliberately no registration endpoint: accounts are created
through the admin and the web pages.
"""

from __future__ import annotations

from typing import cast

from django.contrib.auth import authenticate
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.http import HttpRequest
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from ninja import Router, Status

from hrcek.accounts.errors import (
    EMAIL_NOT_CONFIRMED,
    INVALID_CREDENTIALS,
    SESSION_REQUIRED,
)
from hrcek.accounts.models import ApiToken, User
from hrcek.accounts.schemas import LoginIn, TokenCreateIn, TokenOut, UserOut
from hrcek.core.errors import VALIDATION_ERROR, HrcekError

# Field-level messages. Not registered codes: they travel inside
# HRC-CORE-0002's details, keyed by the field they belong to, which is
# the shape every other validation failure already uses.
NAME_REQUIRED = _("Give the token a name.")
NAME_TOO_LONG = _("That name is too long.")
EXPIRY_IN_THE_PAST = _("That expiry has already passed.")

router = Router(tags=["auth"])


@router.post("/login", response=UserOut, auth=None, operation_id="login")
def login(request: HttpRequest, payload: LoginIn) -> User:
    user = authenticate(request, username=payload.identifier, password=payload.password)
    # authenticate() is typed as returning AbstractBaseUser; narrowing to
    # our model is what makes is_email_confirmed reachable.
    if not isinstance(user, User):
        # Covers a wrong password, an unknown identifier and a disabled
        # account alike; telling them apart would leak who exists.
        raise HrcekError(INVALID_CREDENTIALS)
    if not user.is_email_confirmed:
        # Safe to be specific: reaching here required the right password.
        raise HrcekError(EMAIL_NOT_CONFIRMED)
    django_login(request, user)
    return user


@router.post("/logout", response={204: None}, operation_id="logout")
def logout(request: HttpRequest) -> Status[None]:
    django_logout(request)
    # Status(), not a (code, body) tuple: django-ninja 1.7 deprecates the
    # tuple form, and this project turns warnings into failures.
    return Status(204, None)


@router.get("/me", response=UserOut, operation_id="current_user")
def me(request: HttpRequest) -> User:
    # Authentication has already run, so only a real User gets here.
    return cast("User", request.user)


@router.post(
    "/tokens",
    response={201: TokenOut},
    operation_id="create_api_token",
)
def create_api_token(request: HttpRequest, payload: TokenCreateIn) -> Status[dict]:
    """Make a bearer token for a script or another client.

    Session-authenticated only. A token that could mint tokens would
    make revoking a leaked one pointless: the holder would simply issue
    a replacement, and the original could be revoked without ending
    their access.
    """
    if getattr(request, "authenticated_by_token", False):
        raise HrcekError(SESSION_REQUIRED)

    user = cast("User", request.user)
    name = payload.name.strip()
    if not name:
        raise HrcekError(VALIDATION_ERROR, {"fields": {"name": [str(NAME_REQUIRED)]}})
    if len(name) > ApiToken.NAME_MAX_LENGTH:
        raise HrcekError(
            VALIDATION_ERROR,
            {"fields": {"name": [str(NAME_TOO_LONG)]}},
        )
    if payload.expires_at is not None and payload.expires_at <= timezone.now():
        raise HrcekError(
            VALIDATION_ERROR,
            {"fields": {"expires_at": [str(EXPIRY_IN_THE_PAST)]}},
        )

    token, raw = ApiToken.issue(user, name=name, expires_at=payload.expires_at)
    # The raw value is returned here and never again; only its hash is
    # stored.
    return Status(
        201,
        {
            "id": token.pk,
            "name": token.name,
            "token": raw,
            "created_at": token.created_at,
            "expires_at": token.expires_at,
        },
    )
