"""Entry endpoints.

Authentication comes from the root API, which accepts a bearer token or
a session.
"""

from __future__ import annotations

from typing import cast

from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.http import HttpRequest
from ninja import Router, Status
from ninja.pagination import paginate

from hrcek.accounts.models import User
from hrcek.core.errors import VALIDATION_ERROR, HrcekError
from hrcek.entries.models import Entry
from hrcek.entries.schemas import EntryIn, EntryOut
from hrcek.entries.services import save_entry

router = Router(tags=["entries"])


@router.post("/", response={200: EntryOut, 201: EntryOut}, operation_id="create_entry")
def create_entry(request: HttpRequest, payload: EntryIn) -> Status[Entry]:
    owner = cast("User", request.user)
    try:
        entry, created = save_entry(
            owner,
            url=payload.url,
            title=payload.title,
            notes=payload.notes,
            tag_names=payload.tags,
        )
    except ValidationError as exc:
        raise HrcekError(
            VALIDATION_ERROR, {"fields": {"url": list(exc.messages)}}
        ) from exc
    # 201 for a new entry, 200 for one that already existed: the status
    # says which happened without the client comparing ids.
    return Status(201 if created else 200, entry)


@router.get("/", response=list[EntryOut], operation_id="list_entries")
@paginate
def list_entries(request: HttpRequest) -> QuerySet[Entry]:
    owner = cast("User", request.user)
    return Entry.objects.filter(owner=owner).prefetch_related("tags")
