"""Pictures through the API: by address in JSON, by upload as multipart."""

import io

import pytest
from django.utils import timezone
from PIL import Image

from hrcek.accounts.models import User
from hrcek.entries import fetching
from hrcek.entries.models import Entry, EntryImage

pytestmark = pytest.mark.django_db


def _png(colour=(200, 80, 40)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (40, 30), colour).save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture(autouse=True)
def _media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


@pytest.fixture
def nina():
    return User.objects.create_user(
        email="nina@example.com",
        password="a-long-enough-passphrase",
        email_verified_at=timezone.now(),
    )


@pytest.fixture
def signed_in(client, nina):
    client.force_login(nina)
    return client


@pytest.fixture
def entry(nina):
    return Entry.objects.create(owner=nina, url="https://example.com/watch")


# --- reading -----------------------------------------------------------


def _read(client, entry):
    # There is no get-by-id endpoint; the lookup is how a client reads
    # one, and it takes the address in a body.
    return client.post(
        "/api/entries/lookup",
        {"url": entry.url},
        content_type="application/json",
    ).json()


def test_an_entry_without_a_picture_says_so(signed_in, entry):
    assert _read(signed_in, entry)["image"] is None


def test_an_entry_with_a_picture_describes_it(signed_in, entry):
    EntryImage.attach(entry, _png())
    body = _read(signed_in, entry)
    assert body["image"]["width"] == 40
    assert body["image"]["height"] == 30
    assert body["image"]["url"].endswith(f"/entries/{entry.pk}/image/")
    assert "original" not in body["image"], "the archived copy is not exposed"


# --- creating with an address ------------------------------------------


def test_an_entry_can_be_created_with_a_picture_address(signed_in, nina, monkeypatch):
    monkeypatch.setattr(fetching, "fetch", lambda address: _png())
    response = signed_in.post(
        "/api/entries/",
        {"url": "https://example.com/watch", "image_url": "https://cdn.test/a.png"},
        content_type="application/json",
    )
    assert response.status_code in (200, 201)

    entry = Entry.objects.get(owner=nina, url="https://example.com/watch")
    assert EntryImage.objects.get(entry=entry).source_url == "https://cdn.test/a.png"


def test_a_refused_address_comes_back_as_its_code(signed_in):
    response = signed_in.post(
        "/api/entries/",
        {"url": "https://example.com/watch", "image_url": "http://127.0.0.1/x.png"},
        content_type="application/json",
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "HRC-IMAGE-0005"
    assert not EntryImage.objects.exists()


def test_a_saved_entry_keeps_its_picture_when_the_address_is_omitted(signed_in, entry):
    EntryImage.attach(entry, _png())
    signed_in.post(
        "/api/entries/",
        {"url": "https://example.com/watch", "title": "Renamed"},
        content_type="application/json",
    )
    assert EntryImage.objects.filter(entry=entry).exists()


# --- uploading ---------------------------------------------------------


def test_a_picture_can_be_uploaded_to_an_entry(signed_in, entry):
    response = signed_in.post(
        f"/api/entries/{entry.pk}/image",
        {"file": io.BytesIO(_png())},
    )
    assert response.status_code == 200
    assert EntryImage.objects.get(entry=entry).original == _png()


def test_uploading_replaces_what_was_there(signed_in, entry):
    EntryImage.attach(entry, _png())
    signed_in.post(
        f"/api/entries/{entry.pk}/image",
        {"file": io.BytesIO(_png(colour=(1, 2, 3)))},
    )
    assert EntryImage.objects.get(entry=entry).original == _png(colour=(1, 2, 3))


def test_uploading_something_that_is_not_an_image_is_refused(signed_in, entry):
    response = signed_in.post(
        f"/api/entries/{entry.pk}/image",
        {"file": io.BytesIO(b"not an image")},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "HRC-IMAGE-0001"


def test_uploading_to_somebody_elses_entry_is_a_404(signed_in, nina):
    other = User.objects.create_user(
        email="marko@example.com",
        password="a-long-enough-passphrase",
        email_verified_at=timezone.now(),
    )
    theirs = Entry.objects.create(owner=other, url="https://example.com/theirs")
    response = signed_in.post(
        f"/api/entries/{theirs.pk}/image", {"file": io.BytesIO(_png())}
    )
    assert response.status_code == 404


# --- removing ----------------------------------------------------------


def test_a_picture_can_be_deleted(signed_in, entry):
    EntryImage.attach(entry, _png())
    response = signed_in.delete(f"/api/entries/{entry.pk}/image")
    assert response.status_code == 204
    assert not EntryImage.objects.filter(entry=entry).exists()


def test_deleting_when_there_is_none_is_a_404(signed_in, entry):
    assert signed_in.delete(f"/api/entries/{entry.pk}/image").status_code == 404


def test_the_endpoints_need_authentication(client, entry):
    assert client.post(f"/api/entries/{entry.pk}/image").status_code == 401
    assert client.delete(f"/api/entries/{entry.pk}/image").status_code == 401
