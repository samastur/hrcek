"""The stored image: one per entry, owned through it, cached on disk."""

import io

import pytest
from django.utils import timezone
from PIL import Image

from hrcek.accounts.models import User
from hrcek.entries import imaging
from hrcek.entries.models import Entry, EntryImage

pytestmark = pytest.mark.django_db


def _png(colour=(200, 80, 40)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (40, 30), colour).save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def nina():
    return User.objects.create_user(
        email="nina@example.com",
        password="a-long-enough-passphrase",
        email_verified_at=timezone.now(),
    )


@pytest.fixture
def entry(nina):
    return Entry.objects.create(owner=nina, url="https://example.com/watch")


def test_attaching_stores_both_copies(entry):
    image = EntryImage.attach(entry, _png())
    assert image.original == _png()
    assert image.display != image.original
    assert (image.width, image.height) == (40, 30)
    assert image.byte_size == len(_png())


def test_an_entry_has_at_most_one_image(entry):
    first = EntryImage.attach(entry, _png())
    second = EntryImage.attach(entry, _png(colour=(1, 2, 3)))
    assert EntryImage.objects.filter(entry=entry).count() == 1
    assert second.pk == first.pk
    assert second.checksum != first.checksum


def test_where_it_came_from_is_remembered(entry):
    uploaded = EntryImage.attach(entry, _png())
    assert uploaded.source_url == ""

    fetched = EntryImage.attach(entry, _png(), source_url="https://example.com/a.png")
    assert fetched.source_url == "https://example.com/a.png"


def test_deleting_the_entry_takes_the_image_with_it(entry):
    EntryImage.attach(entry, _png())
    entry.delete()
    assert not EntryImage.objects.exists()


def test_the_display_copy_is_cached_on_disk(entry, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    image = EntryImage.attach(entry, _png())
    cached = image.cached_path("avif")
    assert cached.exists()
    assert cached.read_bytes() == image.display


def test_a_deleted_cache_file_is_rebuilt_from_the_database(entry, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    image = EntryImage.attach(entry, _png())
    image.cached_path("avif").unlink()

    assert image.rendition("avif") == image.display
    assert image.cached_path("avif").exists()


def test_an_older_browser_gets_a_webp_rendition(entry, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    image = EntryImage.attach(entry, _png())

    with Image.open(io.BytesIO(image.rendition("webp"))) as opened:
        assert opened.format == "WEBP"
    assert image.cached_path("webp").exists()


def test_the_cache_path_is_content_addressed(entry, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    image = EntryImage.attach(entry, _png())
    assert image.checksum == imaging.checksum(_png())
    assert image.checksum[:2] in image.cached_path("avif").parts
    assert image.cached_path("avif").name.startswith(image.checksum)
