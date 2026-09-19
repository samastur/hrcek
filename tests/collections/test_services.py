import pytest
from django.utils import timezone

from hrcek.accounts.models import User
from hrcek.collections.models import Collection, CollectionEntry
from hrcek.collections.services import add_entry, remove_entry
from hrcek.core.errors import HrcekError
from hrcek.entries.models import Entry, Tag

pytestmark = pytest.mark.django_db


def _person(email):
    return User.objects.create_user(
        email=email,
        password="a-long-enough-passphrase",
        email_verified_at=timezone.now(),
    )


@pytest.fixture
def nina():
    return _person("nina@example.com")


def test_an_entry_joins_its_owners_collection(nina):
    collection = Collection.objects.create(owner=nina, name="Watches")
    entry = Entry.objects.create(owner=nina, url="https://example.com/1")
    add_entry(collection, entry)
    assert list(collection.entries()) == [entry]


def test_adding_twice_is_harmless(nina):
    collection = Collection.objects.create(owner=nina, name="Watches")
    entry = Entry.objects.create(owner=nina, url="https://example.com/1")
    add_entry(collection, entry)
    add_entry(collection, entry)
    assert CollectionEntry.objects.filter(collection=collection).count() == 1


def test_somebody_elses_entry_is_refused(nina):
    marko = _person("marko@example.com")
    collection = Collection.objects.create(owner=nina, name="Watches")
    theirs = Entry.objects.create(owner=marko, url="https://example.com/1")
    with pytest.raises(HrcekError) as raised:
        add_entry(collection, theirs)
    assert raised.value.error_code.code == "HRC-COLL-0001"
    assert CollectionEntry.objects.count() == 0


def test_a_label_collection_cannot_be_added_to_by_hand(nina):
    tag = Tag.objects.create(owner=nina, name="watches")
    collection = Collection.objects.create(
        owner=nina, name="Watches", kind=Collection.BY_LABEL, label=tag
    )
    entry = Entry.objects.create(owner=nina, url="https://example.com/1")
    with pytest.raises(HrcekError) as raised:
        add_entry(collection, entry)
    assert raised.value.error_code.code == "HRC-COLL-0002"


def test_removing_what_is_not_there_is_harmless(nina):
    collection = Collection.objects.create(owner=nina, name="Watches")
    entry = Entry.objects.create(owner=nina, url="https://example.com/1")
    remove_entry(collection, entry)  # no error


def test_removing_takes_it_out(nina):
    collection = Collection.objects.create(owner=nina, name="Watches")
    entry = Entry.objects.create(owner=nina, url="https://example.com/1")
    add_entry(collection, entry)
    remove_entry(collection, entry)
    assert collection.entries().count() == 0
