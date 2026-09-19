import pytest
from django.db import IntegrityError
from django.utils import timezone

from hrcek.accounts.models import User
from hrcek.collections.models import Collection, CollectionEntry
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


def _entry(owner, n):
    return Entry.objects.create(owner=owner, url=f"https://example.com/{n}")


def test_a_manual_collection_holds_what_is_put_in_it(nina):
    collection = Collection.objects.create(owner=nina, name="Watches")
    first, second = _entry(nina, 1), _entry(nina, 2)
    CollectionEntry.objects.create(collection=collection, entry=first)
    CollectionEntry.objects.create(collection=collection, entry=second)

    assert list(collection.entries()) == [second, first]  # newest first


def test_a_label_collection_follows_its_tag(nina):
    tag = Tag.objects.create(owner=nina, name="watches")
    collection = Collection.objects.create(
        owner=nina, name="Watches", kind=Collection.BY_LABEL, label=tag
    )
    tagged, untagged = _entry(nina, 1), _entry(nina, 2)
    tagged.tags.add(tag)

    assert list(collection.entries()) == [tagged]

    untagged.tags.add(tag)
    assert set(collection.entries()) == {tagged, untagged}

    tagged.tags.remove(tag)
    assert list(collection.entries()) == [untagged]


def test_a_label_collection_holds_only_its_owners_entries(nina):
    """Two people may use the same tag name; the rows are unrelated."""
    marko = _person("marko@example.com")
    mine = Tag.objects.create(owner=nina, name="watches")
    collection = Collection.objects.create(
        owner=nina, name="Watches", kind=Collection.BY_LABEL, label=mine
    )
    theirs = _entry(marko, 1)
    theirs.tags.add(Tag.objects.create(owner=marko, name="watches"))

    assert list(collection.entries()) == []


def test_the_same_entry_cannot_be_added_twice(nina):
    collection = Collection.objects.create(owner=nina, name="Watches")
    entry = _entry(nina, 1)
    CollectionEntry.objects.create(collection=collection, entry=entry)
    with pytest.raises(IntegrityError):
        CollectionEntry.objects.create(collection=collection, entry=entry)


def test_two_collections_of_one_person_cannot_share_a_name(nina):
    Collection.objects.create(owner=nina, name="Watches")
    with pytest.raises(IntegrityError):
        Collection.objects.create(owner=nina, name="watches")


def test_two_people_may_both_have_a_collection_called_watches(nina):
    marko = _person("marko@example.com")
    Collection.objects.create(owner=nina, name="Watches")
    Collection.objects.create(owner=marko, name="Watches")  # no error


def test_a_label_collection_must_name_a_label(nina):
    with pytest.raises(IntegrityError):
        Collection.objects.create(owner=nina, name="Watches", kind=Collection.BY_LABEL)


def test_a_manual_collection_may_not_name_a_label(nina):
    tag = Tag.objects.create(owner=nina, name="watches")
    with pytest.raises(IntegrityError):
        Collection.objects.create(
            owner=nina, name="Watches", kind=Collection.MANUAL, label=tag
        )


def test_deleting_an_entry_removes_it_from_collections(nina):
    collection = Collection.objects.create(owner=nina, name="Watches")
    entry = _entry(nina, 1)
    CollectionEntry.objects.create(collection=collection, entry=entry)
    entry.delete()
    assert collection.entries().count() == 0


def test_deleting_a_collection_leaves_its_entries_alone(nina):
    collection = Collection.objects.create(owner=nina, name="Watches")
    entry = _entry(nina, 1)
    CollectionEntry.objects.create(collection=collection, entry=entry)
    collection.delete()
    assert Entry.objects.filter(pk=entry.pk).exists()
