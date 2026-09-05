"""Response shapes shared across the API."""

from __future__ import annotations

from ninja import Schema


class HealthOut(Schema):
    status: str
    service: str
    version: str
    message: str
