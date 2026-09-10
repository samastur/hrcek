from __future__ import annotations

from ninja import Schema


class UserOut(Schema):
    email: str
    display_name: str | None


class LoginIn(Schema):
    identifier: str
    password: str
