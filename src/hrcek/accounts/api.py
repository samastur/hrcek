"""Authentication endpoints.

There is deliberately no registration endpoint: accounts are created
through the admin and the web pages.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import cast

from django.contrib.auth import authenticate
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.http import HttpRequest
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from ninja import Router, Status
from ninja.throttling import AnonRateThrottle, SimpleRateThrottle

from hrcek.accounts.errors import (
    EMAIL_NOT_CONFIRMED,
    INVALID_CREDENTIALS,
    SESSION_REQUIRED,
)
from hrcek.accounts.models import ApiToken, User
from hrcek.accounts.schemas import (
    LoginIn,
    TokenCreateIn,
    TokenExchangeIn,
    TokenOut,
    UserOut,
)
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
    return _issue_token(user, name=payload.name, expires_at=payload.expires_at)


def _issue_token(user: User, *, name: str, expires_at: datetime | None) -> Status[dict]:
    """Validate what was asked for, then make the token.

    Shared by both routes, so the rules cannot differ depending on how
    the caller proved who they are.
    """
    name = name.strip()
    if not name:
        raise HrcekError(VALIDATION_ERROR, {"fields": {"name": [str(NAME_REQUIRED)]}})
    if len(name) > ApiToken.NAME_MAX_LENGTH:
        raise HrcekError(
            VALIDATION_ERROR,
            {"fields": {"name": [str(NAME_TOO_LONG)]}},
        )
    if expires_at is not None and expires_at <= timezone.now():
        raise HrcekError(
            VALIDATION_ERROR,
            {"fields": {"expires_at": [str(EXPIRY_IN_THE_PAST)]}},
        )

    token, raw = ApiToken.issue(user, name=name, expires_at=expires_at)
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


class TokenExchangeThrottle(AnonRateThrottle):
    """Counted per calling address, right credentials or wrong.

    The route is unauthenticated and hands out a durable credential,
    so guessing at it has to get expensive. Successes count too: a
    client needs this once per install, not repeatedly.

    Which address counts depends on `NINJA_NUM_PROXIES`; see the note
    beside it in the settings. Left unset, the header decides, and a
    header is whatever the caller says it is.
    """

    scope = "token_exchange"


class TokenExchangeAccountThrottle(SimpleRateThrottle):
    """Counted per account named in the request.

    The address limit above does nothing against somebody with a pool
    of addresses working through one account's password. This counts
    the account instead, so the guessing is expensive however many
    places it comes from.
    """

    scope = "token_exchange_account"

    def get_cache_key(self, request: HttpRequest) -> str | None:
        identifier = self._identifier(request)
        if not identifier:
            # Nothing to count against; the address limit still applies
            # and the request is about to fail validation anyway.
            return None
        # Hashed, so a cache dump is not a list of who has an account.
        digest = hashlib.sha256(identifier.casefold().encode()).hexdigest()
        return f"throttle_{self.scope}_{digest}"

    @staticmethod
    def _identifier(request: HttpRequest) -> str:
        """The identifier from the body, without disturbing the view.

        Django caches `request.body`, so reading it here does not stop
        the view parsing the same bytes afterwards.
        """
        try:
            payload = json.loads(request.body or b"{}")
        except (ValueError, UnicodeDecodeError):
            return ""
        if not isinstance(payload, dict):
            return ""
        value = payload.get("identifier")
        return value.strip() if isinstance(value, str) else ""


@router.post(
    "/tokens/exchange",
    response={201: TokenOut},
    auth=None,
    throttle=[TokenExchangeThrottle(), TokenExchangeAccountThrottle()],
    operation_id="exchange_credentials_for_token",
)
def exchange_credentials_for_token(
    request: HttpRequest, payload: TokenExchangeIn
) -> Status[dict]:
    """Trade an email address and password for a bearer token.

    For clients that cannot hold a session. A browser extension is the
    case: Firefox sends `Origin: moz-extension://<uuid>` on every
    request, the uuid differs per install so it cannot be trusted in
    advance, and Django refuses the origin before it reads anything
    else — so an extension can sign in and then do nothing unsafe with
    the session it got.

    This route reads no session at all, which is also what makes it
    safe without a CSRF check: there is no path through it that a
    cookie alone can take. A signed-in browser gains nothing here.
    """
    user = authenticate(request, username=payload.identifier, password=payload.password)
    if not isinstance(user, User):
        # One answer for a wrong password, an unknown identifier and a
        # disabled account alike, exactly as login does: telling them
        # apart would leak who has an account.
        raise HrcekError(INVALID_CREDENTIALS)
    if not user.is_email_confirmed:
        raise HrcekError(EMAIL_NOT_CONFIRMED)

    return _issue_token(user, name=payload.name, expires_at=payload.expires_at)
