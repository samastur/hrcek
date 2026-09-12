from __future__ import annotations

from datetime import datetime

from ninja import Field, Schema

from hrcek.entries.models import Entry


class EntryIn(Schema):
    """Everything but the address has a default.

    A minimal client can post {"url": "..."} and nothing else, which
    matters more once custom fields arrive.
    """

    url: str
    title: str = ""
    notes: str = ""
    tags: list[str] = Field(default_factory=list)


class EntryOut(Schema):
    id: int
    url: str
    title: str
    notes: str
    tags: list[str]
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_tags(obj: Entry) -> list[str]:
        return [tag.name for tag in obj.tags.all()]


class BatchError(Schema):
    code: str
    message: str
    details: dict = Field(default_factory=dict)


class BatchResult(Schema):
    """One row of a batch, in the order it was submitted."""

    index: int
    status: str  # "created", "updated" or "error"
    id: int | None = None
    error: BatchError | None = None


class BatchOut(Schema):
    results: list[BatchResult]
