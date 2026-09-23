from __future__ import annotations

from datetime import datetime
from typing import Any

from django.urls import reverse
from ninja import Field, Schema

from hrcek.entries.models import Entry, EntryImage, FieldValue


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
    # Fetched and attached when given. Absent leaves any existing
    # picture alone, like `fields` and unlike everything else here: a
    # client that predates images must not strip them. Removing one is
    # DELETE /entries/{id}/image, never an empty string.
    image_url: str | None = None


class EntryLookupIn(Schema):
    """The address to look up.

    In a body rather than a query string: an address is the private
    part of an entry, and a query string is written into every access
    log the request passes through.
    """

    url: str


class ImageOut(Schema):
    """What a client needs to show the picture, and nothing more.

    Neither copy of the bytes appears here. The original is archival
    and never leaves the server; the display copy is fetched from
    `url`, which is access-controlled.
    """

    url: str
    width: int
    height: int


class EntryOut(Schema):
    id: int
    url: str
    title: str
    notes: str
    tags: list[str]
    fields: dict[str, str]
    image: ImageOut | None
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_image(obj: Entry) -> ImageOut | None:
        image = EntryImage.objects.filter(entry=obj).first()
        if image is None:
            return None
        return ImageOut(
            url=reverse("entries:image", args=[obj.pk]),
            width=image.width,
            height=image.height,
        )

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


class FieldOut(Schema):
    """One of the fields this account's entries may carry.

    `name` is the key: it is what an entry's `fields` object uses, so a
    client writes back what it read here. `options` is empty except
    for a choice field, where it is the only way to know what the
    choices are.
    """

    name: str
    kind: str
    options: list[str]


class LabelOut(Schema):
    """A label already in use on this account's entries."""

    name: str
