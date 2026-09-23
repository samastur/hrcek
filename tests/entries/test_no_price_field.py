"""Price is no longer a field every account starts with.

A price without a currency is ambiguous, and carrying a currency would
mean a field type this project does not have. Anybody who wants one
can make a number field and call it what they like.
"""

import importlib

import pytest
from django.apps import apps as live_apps
from django.utils import timezone

from hrcek.accounts.models import User
from hrcek.entries.models import Entry, FieldDefinition, FieldValue

pytestmark = pytest.mark.django_db

retirement = importlib.import_module("hrcek.entries.migrations.0005_retire_price_field")


def _person(email="nina@example.com"):
    return User.objects.create_user(
        email=email,
        password="a-long-enough-passphrase",
        email_verified_at=timezone.now(),
    )


def test_a_new_account_starts_with_priority_only():
    nina = _person()
    assert list(
        FieldDefinition.objects.filter(owner=nina).values_list("name", flat=True)
    ) == ["Priority"]


def test_an_unused_price_field_is_retired():
    nina = _person()
    FieldDefinition.objects.create(
        owner=nina, name="Price", kind=FieldDefinition.NUMBER
    )
    retirement.retire_price(live_apps, None)
    assert not FieldDefinition.objects.filter(owner=nina, name="Price").exists()


def test_a_price_field_holding_values_is_left_alone():
    """It is somebody's data by then, whatever we think of the idea."""
    nina = _person()
    price = FieldDefinition.objects.create(
        owner=nina, name="Price", kind=FieldDefinition.NUMBER
    )
    entry = Entry.objects.create(owner=nina, url="https://example.com/watch")
    FieldValue.objects.create(entry=entry, definition=price, value_number=1450)

    retirement.retire_price(live_apps, None)

    assert FieldDefinition.objects.filter(pk=price.pk).exists()
    assert FieldValue.objects.filter(definition=price).exists()


def test_a_field_somebody_renamed_to_price_is_left_alone():
    """Only the seeded field is being withdrawn, and a renamed one is
    no longer that."""
    nina = _person()
    theirs = FieldDefinition.objects.create(
        owner=nina, name="Price", kind=FieldDefinition.TEXT
    )
    retirement.retire_price(live_apps, None)
    assert FieldDefinition.objects.filter(pk=theirs.pk).exists(), (
        "a text field called Price was never the seeded one"
    )


def test_priority_is_untouched():
    nina = _person()
    retirement.retire_price(live_apps, None)
    assert FieldDefinition.objects.filter(owner=nina, name="Priority").exists()


def test_anybody_can_still_make_their_own_price_field():
    nina = _person()
    FieldDefinition.objects.create(
        owner=nina, name="Price in EUR", kind=FieldDefinition.NUMBER
    )
    names = set(
        FieldDefinition.objects.filter(owner=nina).values_list("name", flat=True)
    )
    assert names == {"Priority", "Price in EUR"}
