"""The one place an entry is saved.

The web form and both API endpoints go through here, so upsert-on-URL
and tag handling exist once rather than in three slightly different
copies.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from hrcek.accounts.models import User
from hrcek.entries.models import Entry, Tag


@transaction.atomic
def save_entry(
    owner: User,
    *,
    url: str,
    title: str = "",
    notes: str = "",
    tag_names: list[str] | None = None,
) -> tuple[Entry, bool]:
    """Create or update this owner's entry for *url*.

    Returns the entry and whether it was created, so callers can report
    "created" or "updated" without asking again.
    """
    address = Entry.normalise_url(url)
    # The web form validates through its URLField; the API has no form in
    # front of it, so the shared path is where this belongs.
    URLValidator()(address)
    if len(address) > Entry.URL_MAX_LENGTH:
        raise ValidationError(_("That address is too long."), code="url_too_long")

    entry, created = Entry.objects.update_or_create(
        owner=owner,
        url=address,
        defaults={"title": title.strip(), "notes": notes.strip()},
    )
    Tag.set_for(entry, tag_names or [])
    return entry, created
