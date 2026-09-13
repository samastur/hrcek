from __future__ import annotations

from datetime import datetime
from typing import Any

from ninja import Field, Schema

from hrcek.entries.models import Entry, FieldValue


class EntryIn(Schema):
    """Everything but the address has a default.

    A minimal client can post {"url": "..."} and nothing else, which
    matters more once custom fields arrive.
    """

    url: str
    title: str = ""
    notes: str = ""
    tags: list[str] = Field(default_factory=list)
    # A patch, not a replacement: the names it carries are set and every
    # other field keeps what it had. Every other attribute here replaces,
    # so this is the one exception — deliberately, so that a client which
    # predates custom fields cannot destroy values it knows nothing
    # about. Clearing one is an explicit "": {"price": ""}.
    fields: dict[str, Any] | None = None


class EntryOut(Schema):
    id: int
    url: str
    title: str
    notes: str
    tags: list[str]
    fields: dict[str, str]
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_tags(obj: Entry) -> list[str]:
        return [tag.name for tag in obj.tags.all()]

    @staticmethod
    def resolve_fields(obj: Entry) -> dict[str, str]:
        """Keyed by the field's name, and always strings.

        A client never has to guess whether a price arrives as a number
        or a string, and the name is what it sent.
        """
        return {
            value.definition.name: value.value
            for value in FieldValue.objects.filter(entry=obj).select_related(
                "definition"
            )
        }


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
