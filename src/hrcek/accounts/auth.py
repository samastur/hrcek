"""django-ninja authentication for Hrcek.

**Order matters where these are used.** django-ninja runs auth callbacks
in sequence and aborts the whole chain on the first exception. Ninja's
SessionAuth performs its CSRF check inside ``_get_key()``, before it even
reads the session cookie, and raises on any unsafe request without a
CSRF token. Listing it first would therefore reject every
token-authenticated POST with a CSRF error, without ever looking at the
perfectly valid token it carried.

So the root API declares ``auth=[ApiTokenAuth(), SessionAuth()]``.
``tests/accounts/test_api_auth.py::test_a_token_post_needs_no_csrf_token``
is the regression test for exactly this.
"""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest
from ninja.errors import HttpError
from ninja.security import HttpBearer
from ninja.security import SessionAuth as NinjaSessionAuth

from hrcek.accounts.errors import CSRF_FAILED, INVALID_API_TOKEN
from hrcek.accounts.models import ApiToken, User
from hrcek.core.errors import HrcekError


class ApiTokenAuth(HttpBearer):
    """Authenticate `Authorization: Bearer hrcek_...`."""

    def authenticate(self, request: HttpRequest, token: str) -> User | None:
        if not token.startswith(ApiToken.TOKEN_PREFIX):
            # Not ours; let the next authenticator have a look.
            return None

        api_token = (
            ApiToken.objects.select_related("user")
            .filter(token_hash=ApiToken.hash_token(token))
            .first()
        )
        if api_token is None or not api_token.is_usable or not api_token.user.is_active:
            # A token was presented and it is bad. Say so, rather than
            # falling through to "authentication required".
            raise HrcekError(INVALID_API_TOKEN)

        api_token.touch()
        request.user = api_token.user
        return api_token.user


class SessionAuth(NinjaSessionAuth):
    """Ninja's session auth, with its CSRF failure put on our contract."""

    def _get_key(self, request: HttpRequest) -> Any:
        try:
            return super()._get_key(request)
        except HttpError as exc:
            # Ninja raises a bare HttpError(403, "CSRF check Failed"),
            # which would escape the {"error": {...}} envelope.
            raise HrcekError(CSRF_FAILED) from exc
