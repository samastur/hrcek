"""The one place an entry is saved.

The web form and both API endpoints go through here, so upsert-on-URL
and tag handling exist once rather than in three slightly different
copies.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from hrcek.accounts.models import User
from hrcek.core.errors import HrcekError
from hrcek.entries.errors import UNKNOWN_FIELD
from hrcek.entries.models import Entry, FieldDefinition, FieldValue, Tag


# Six keyword-only arguments, one per thing an entry holds. Bundling
# them into an object would add a layer without removing a decision.
@transaction.atomic
def save_entry(  # noqa: PLR0913
    owner: User,
    *,
    url: str,
    title: str = "",
    notes: str = "",
    tag_names: list[str] | None = None,
    fields: dict[str, Any] | None = None,
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
    # A patch, not a replacement: only the names given are touched.
    # See docs/dev/entries.md for why this one attribute differs.
    if fields:
        set_field_values(entry, fields)
    return entry, created


def validate_field_value(definition: FieldDefinition, raw: str) -> str:
    """Check a value against its field, returning it unchanged."""
    if definition.kind == FieldDefinition.NUMBER:
        try:
            Decimal(raw)
        except InvalidOperation as exc:
            raise ValidationError(
                _("%(field)s takes a number.") % {"field": definition.name},
                code="not_a_number",
            ) from exc
    elif definition.kind == FieldDefinition.CHOICE and raw not in definition.options:
        raise ValidationError(
            _("%(field)s must be one of: %(options)s.")
            % {"field": definition.name, "options": ", ".join(definition.options)},
            code="not_an_option",
        )
    return raw


def set_field_values(entry: Entry, mapping: dict[str, Any]) -> None:
    """Set the values *mapping* names, and leave the rest alone.

    This is a patch, not a replacement. Names match without regard to
    case. A name with no field raises rather than being dropped: a typo
    should be reported, not silently ignored. A value of "" removes that
    field's value, which is the only way to remove one — omitting a
    field never destroys anything.
    """
    definitions = {
        definition.name.lower(): definition
        for definition in FieldDefinition.objects.filter(owner=entry.owner)
    }

    resolved: dict[FieldDefinition, str] = {}
    for name, raw in mapping.items():
        definition = definitions.get(str(name).strip().lower())
        if definition is None:
            raise HrcekError(UNKNOWN_FIELD, {"field": str(name)})
        resolved[definition] = "" if raw is None else str(raw).strip()

    # Everything is checked before anything is written, so a bad value in
    # the second field does not leave the first one changed.
    for definition, raw in resolved.items():
        if raw:
            validate_field_value(definition, raw)

    cleared = [d.pk for d, raw in resolved.items() if not raw]
    if cleared:
        FieldValue.objects.filter(entry=entry, definition__in=cleared).delete()

    for definition, raw in resolved.items():
        if not raw:
            continue
        value, _created = FieldValue.objects.get_or_create(
            entry=entry, definition=definition
        )
        value.value = raw
        value.save()
