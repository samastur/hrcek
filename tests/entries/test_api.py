import json

import pytest
from django.utils import timezone

from hrcek.accounts.models import ApiToken, User
from hrcek.entries.models import Entry
from hrcek.entries.services import save_entry

pytestmark = pytest.mark.django_db

PASSWORD = "a-long-enough-passphrase"


def _person(email):
    return User.objects.create_user(
        email=email, password=PASSWORD, email_verified_at=timezone.now()
    )


@pytest.fixture
def nina():
    return _person("nina@example.com")


@pytest.fixture
def auth(nina):
    _token, raw = ApiToken.issue(nina, name="script")
    return {"authorization": f"Bearer {raw}"}


def _post(client, headers, body):
    return client.post(
        "/api/entries/",
        data=json.dumps(body),
        content_type="application/json",
        headers=headers,
    )


def test_creating_an_entry(client, nina, auth):
    response = _post(
        client,
        auth,
        {
            "url": "https://example.com/watch",
            "title": "A watch",
            "notes": "38mm",
            "tags": ["watches", "diving"],
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["url"] == "https://example.com/watch"
    assert sorted(body["tags"]) == ["diving", "watches"]
    assert Entry.objects.filter(owner=nina).count() == 1


def test_only_a_url_is_required(client, nina, auth):
    response = _post(client, auth, {"url": "https://example.com/watch"})
    assert response.status_code == 201
    assert response.json()["title"] == ""


def test_posting_the_same_url_updates_it(client, nina, auth):
    _post(client, auth, {"url": "https://example.com/watch", "title": "First"})
    response = _post(
        client, auth, {"url": "https://example.com/watch", "title": "Second"}
    )
    assert response.status_code == 200
    assert Entry.objects.filter(owner=nina).count() == 1
    assert Entry.objects.get(owner=nina).title == "Second"


def test_a_bad_url_is_refused(client, nina, auth):
    response = _post(client, auth, {"url": "not a url"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "HRC-CORE-0002"
    assert not Entry.objects.filter(owner=nina).exists()


def test_creating_without_credentials_is_refused(client):
    response = _post(client, {}, {"url": "https://example.com/watch"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "HRC-AUTH-0003"


def test_listing_returns_your_entries_newest_first(client, nina, auth):
    save_entry(nina, url="https://example.com/1", title="One")
    save_entry(nina, url="https://example.com/2", title="Two")
    response = client.get("/api/entries/", headers=auth)
    assert response.status_code == 200
    assert [i["title"] for i in response.json()["items"]] == ["Two", "One"]


def test_listing_shows_nobody_elses(client, nina, auth):
    marko = _person("marko@example.com")
    save_entry(marko, url="https://example.com/theirs", title="Theirs")
    save_entry(nina, url="https://example.com/mine", title="Mine")
    items = client.get("/api/entries/", headers=auth).json()["items"]
    assert [i["title"] for i in items] == ["Mine"]


def test_listing_without_credentials_is_refused(client):
    assert client.get("/api/entries/").status_code == 401
