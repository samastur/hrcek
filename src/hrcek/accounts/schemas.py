from __future__ import annotations

from datetime import datetime

from ninja import Schema


class UserOut(Schema):
    email: str
    display_name: str | None


class LoginIn(Schema):
    identifier: str
    password: str


class TokenCreateIn(Schema):
    """A name, and optionally a date it should stop working."""

    name: str
    expires_at: datetime | None = None


class TokenExchangeIn(Schema):
    """Credentials traded for a token, for a client with no session.

    `identifier` and `password` are the same pair `login` takes; the
    name is the one the clients page will show beside the token.
    """

    name: str
    identifier: str
    password: str
    expires_at: datetime | None = None


class TokenOut(Schema):
    """The only time the raw token exists outside the client.

    Only a hash is stored, so a client that loses this value has to
    make another token; nobody can look it up, including whoever runs
    this Hrček.
    """

    id: int
    name: str
    token: str
    created_at: datetime
    expires_at: datetime | None
