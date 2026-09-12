"""Entry endpoints.

Authentication comes from the root API, which accepts a bearer token or
a session.
"""

from __future__ import annotations

from typing import cast

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import QuerySet
from django.http import HttpRequest
from ninja import Router, Status
from ninja.pagination import paginate

from hrcek.accounts.models import User
from hrcek.core.errors import VALIDATION_ERROR, HrcekError
from hrcek.entries.errors import BATCH_TOO_LARGE
from hrcek.entries.models import Entry
from hrcek.entries.schemas import BatchOut, EntryIn, EntryOut
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


@router.post(
    "/batch/",
    response={200: BatchOut, 207: BatchOut},
    operation_id="create_entries",
)
def create_entries(
    request: HttpRequest, payload: list[EntryIn]
) -> Status[dict[str, object]]:
    owner = cast("User", request.user)
    if len(payload) > settings.HRCEK_MAX_BATCH:
        raise HrcekError(
            BATCH_TOO_LARGE,
            {"limit": settings.HRCEK_MAX_BATCH, "received": len(payload)},
        )

    results: list[dict[str, object]] = []
    any_failed = False
    for index, item in enumerate(payload):
        try:
            # Each row in its own atomic block: one failure must not
            # poison the rows that follow it.
            with transaction.atomic():
                entry, created = save_entry(
                    owner,
                    url=item.url,
                    title=item.title,
                    notes=item.notes,
                    tag_names=item.tags,
                )
        except ValidationError as exc:
            any_failed = True
            results.append(
                {
                    "index": index,
                    "status": "error",
                    "error": {
                        "code": VALIDATION_ERROR.code,
                        "message": str(VALIDATION_ERROR.message),
                        "details": {"url": list(exc.messages)},
                    },
                }
            )
        else:
            results.append(
                {
                    "index": index,
                    "status": "created" if created else "updated",
                    "id": entry.pk,
                }
            )

    # 207 when any row failed: a flat 200 would hide the failure from a
    # client that only checks the status.
    return Status(207 if any_failed else 200, {"results": results})
