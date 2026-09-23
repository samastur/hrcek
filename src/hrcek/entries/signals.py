"""Giving a new account something to start from."""

from __future__ import annotations

from typing import Any

from django.db.models.signals import post_save
from django.dispatch import receiver

from hrcek.accounts.models import User
from hrcek.entries.models import FieldDefinition

#: Names are stored, not displayed from a catalogue, so they are not
#: translated: a person may rename them, and a name that changed with the
#: interface language would be two different fields to the API.
#: Price was here once. It was withdrawn because a price means little
#: without a currency, and carrying a currency needs a field type this
#: project does not have — see migration 0005.
DEFAULT_FIELDS: tuple[tuple[str, str, list[str]], ...] = (
    ("Priority", FieldDefinition.CHOICE, ["high", "medium", "low"]),
)


def seed_default_fields(user: User) -> None:
    """Give *user* the starting fields, if they do not have them.

    Idempotent: running it again on an account that kept its fields
    changes nothing, and on one that deleted them puts them back.
    """
    for name, kind, options in DEFAULT_FIELDS:
        FieldDefinition.objects.get_or_create(
            owner=user,
            name__iexact=name,
            defaults={"name": name, "kind": kind, "options": options},
        )


@receiver(post_save, sender=User, dispatch_uid="entries.seed_default_fields")
def seed_on_user_creation(
    sender: type[User], instance: User, created: bool, **kwargs: Any
) -> None:
    if created:
        seed_default_fields(instance)
