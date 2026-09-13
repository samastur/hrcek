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
from hrcek.core.errors import NOT_FOUND, VALIDATION_ERROR, HrcekError
from hrcek.entries.errors import BATCH_TOO_LARGE
from hrcek.entries.models import Entry
from hrcek.entries.schemas import BatchOut, EntryIn, EntryOut
from hrcek.entries.services import save_entry

router = Router(tags=["entries"])


def _details(exc: ValidationError) -> dict[str, object]:
    """The offending fields, keyed by name.

    A URL problem is reported under "url"; a field value under the
    field's own name, which the service put there.
    """
    if hasattr(exc, "error_dict"):
        return {"fields": exc.message_dict}
    return {"fields": {"url": list(exc.messages)}}


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
            fields=payload.fields,
        )
    except ValidationError as exc:
        raise HrcekError(VALIDATION_ERROR, _details(exc)) from exc
    # 201 for a new entry, 200 for one that already existed: the status
    # says which happened without the client comparing ids.
    return Status(201 if created else 200, entry)


@router.get("/", response=list[EntryOut], operation_id="list_entries")
@paginate
def list_entries(request: HttpRequest) -> QuerySet[Entry]:
    owner = cast("User", request.user)
    return Entry.objects.filter(owner=owner).prefetch_related(
        "tags", "field_values__definition"
    )


@router.get("/by-url/", response=EntryOut, operation_id="get_entry_by_url")
def get_entry_by_url(request: HttpRequest, url: str) -> Entry:
    """Answer the entry held at *url*, so a client can compare.

    Posting is an upsert, which leaves a client no way to ask what an
    address currently says before writing over it. Listing and filtering
    client-side is the wrong shape once somebody holds thousands of
    entries.

    Declared before any /{id}/ route: whoever adds one must keep it
    below this, or "by-url" will be read as an id.
    """
    owner = cast("User", request.user)
    # The same normalisation the upsert uses, so the lookup and the save
    # agree on what counts as the same address.
    entry = (
        Entry.objects.filter(owner=owner, url=Entry.normalise_url(url))
        .prefetch_related("tags", "field_values__definition")
        .first()
    )
    if entry is None:
        # 404 rather than 403 for somebody else's address: a 403 would
        # confirm that somebody holds it.
        raise HrcekError(NOT_FOUND, {"url": url})
    return entry


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
                    fields=item.fields,
                )
        except HrcekError as exc:
            # An unknown field name, say: one row's mistake, reported as
            # that row's error rather than refusing the whole request.
            any_failed = True
            results.append(
                {
                    "index": index,
                    "status": "error",
                    "error": {
                        "code": exc.error_code.code,
                        "message": str(exc.error_code.message),
                        "details": exc.details,
                    },
                }
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
                        "details": _details(exc),
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
