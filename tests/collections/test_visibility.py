import pytest
from django.utils import timezone

from hrcek.accounts.models import User
from hrcek.collections.models import Collection

pytestmark = pytest.mark.django_db


@pytest.fixture
def nina():
    return User.objects.create_user(
        email="nina@example.com",
        password="a-long-enough-passphrase",
        email_verified_at=timezone.now(),
        namespace="nina",
    )


def test_a_new_collection_is_private(nina):
    assert (
        Collection.objects.create(owner=nina, name="W").visibility == Collection.PRIVATE
    )


def test_every_collection_gets_a_secret_that_does_not_change(nina):
    collection = Collection.objects.create(owner=nina, name="W")
    assert len(collection.secret) >= 20
    original = collection.secret

    collection.visibility = Collection.UNLISTED
    collection.save()
    collection.visibility = Collection.PRIVATE
    collection.save()
    collection.refresh_from_db()
    assert collection.secret == original


def test_two_collections_do_not_share_a_secret(nina):
    first = Collection.objects.create(owner=nina, name="One")
    second = Collection.objects.create(owner=nina, name="Two")
    assert first.secret != second.secret


def test_a_public_collection_gets_a_slug_from_its_name(nina):
    collection = Collection.objects.create(
        owner=nina, name="Watches I want", visibility=Collection.PUBLIC
    )
    assert collection.slug == "watches-i-want"
    assert collection.public_url() == "/u/nina/watches-i-want/"


def test_a_private_collection_has_no_slug(nina):
    assert Collection.objects.create(owner=nina, name="Watches").slug == ""


def test_two_public_collections_cannot_share_a_slug(nina):
    Collection.objects.create(owner=nina, name="Watches", visibility=Collection.PUBLIC)
    second = Collection.objects.create(
        owner=nina, name="watches!", visibility=Collection.PUBLIC
    )
    assert second.slug == "watches-2"


def test_renaming_a_public_collection_moves_it(nina):
    collection = Collection.objects.create(
        owner=nina, name="Watches", visibility=Collection.PUBLIC
    )
    collection.name = "Clocks"
    collection.save()
    assert collection.slug == "clocks"


def test_a_name_with_nothing_sluggable_still_gets_an_address(nina):
    collection = Collection.objects.create(
        owner=nina, name="!!!", visibility=Collection.PUBLIC
    )
    assert collection.slug == "collection"


def test_nothing_is_shown_by_default(nina):
    collection = Collection.objects.create(owner=nina, name="W")
    assert not collection.show_notes
    assert not collection.show_tags
    assert not collection.show_images
    assert collection.visible_fields.count() == 0


def test_only_shared_collections_count_as_shared(nina):
    private = Collection.objects.create(owner=nina, name="One")
    unlisted = Collection.objects.create(
        owner=nina, name="Two", visibility=Collection.UNLISTED
    )
    public = Collection.objects.create(
        owner=nina, name="Three", visibility=Collection.PUBLIC
    )
    assert not private.is_shared()
    assert unlisted.is_shared()
    assert public.is_shared()
