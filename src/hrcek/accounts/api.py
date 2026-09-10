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
from ninja import Router, Status

from hrcek.accounts.errors import EMAIL_NOT_CONFIRMED, INVALID_CREDENTIALS
from hrcek.accounts.models import User
from hrcek.accounts.schemas import LoginIn, UserOut
from hrcek.core.errors import HrcekError

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
