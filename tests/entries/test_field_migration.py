"""The data migration that seeds accounts predating custom fields.

It runs once, against rows nobody can make any more, so the only way to
know it works is to call it.
"""

import importlib

import pytest
from django.apps import apps as live_apps
from django.utils import timezone

from hrcek.accounts.models import User
from hrcek.entries.models import Entry, FieldDefinition, FieldValue

pytestmark = pytest.mark.django_db

migration = importlib.import_module("hrcek.entries.migrations.0003_seed_default_fields")


def _person(email="nina@example.com"):
    return User.objects.create_user(
        email=email,
        password="a-long-enough-passphrase",
        email_verified_at=timezone.now(),
    )


@pytest.fixture
def nina():
    """An account with no fields, as one predating this phase would be."""
    person = _person()
    FieldDefinition.objects.filter(owner=person).delete()
    return person


def test_it_gives_an_account_the_starting_two(nina):
    migration.seed(live_apps, None)
    assert sorted(
        FieldDefinition.objects.filter(owner=nina).values_list("name", "kind")
    ) == [("Price", "number"), ("Priority", "choice")]


def test_priority_arrives_with_its_options(nina):
    migration.seed(live_apps, None)
    priority = FieldDefinition.objects.get(owner=nina, name="Priority")
    assert priority.options == ["high", "medium", "low"]


def test_every_account_gets_them(nina):
    marko = _person("marko@example.com")
    FieldDefinition.objects.filter(owner=marko).delete()
    migration.seed(live_apps, None)
    assert FieldDefinition.objects.filter(owner=marko).count() == 2


def test_running_it_twice_does_not_duplicate(nina):
    migration.seed(live_apps, None)
    migration.seed(live_apps, None)
    assert FieldDefinition.objects.filter(owner=nina).count() == 2


def test_it_leaves_a_field_somebody_already_has_alone(nina):
    """Including one spelled differently: the lookup ignores case."""
    mine = FieldDefinition.objects.create(
        owner=nina, name="price", kind=FieldDefinition.TEXT
    )
    migration.seed(live_apps, None)
    mine.refresh_from_db()
    assert mine.kind == FieldDefinition.TEXT
    assert FieldDefinition.objects.filter(owner=nina, name__iexact="price").count() == 1


def test_going_back_removes_what_it_added(nina):
    migration.seed(live_apps, None)
    migration.unseed(live_apps, None)
    assert not FieldDefinition.objects.filter(owner=nina).exists()


def test_going_back_keeps_a_field_holding_values(nina):
    migration.seed(live_apps, None)
    entry = Entry.objects.create(owner=nina, url="https://example.com/1")
    price = FieldDefinition.objects.get(owner=nina, name="Price")
    FieldValue.objects.create(entry=entry, definition=price, value_number=1)

    migration.unseed(live_apps, None)

    assert FieldDefinition.objects.filter(owner=nina, name="Price").exists()
    assert not FieldDefinition.objects.filter(owner=nina, name="Priority").exists()
