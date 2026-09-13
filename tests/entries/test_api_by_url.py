import pytest
from django.utils import timezone

from hrcek.accounts.models import ApiToken, User
from hrcek.entries.services import save_entry

pytestmark = pytest.mark.django_db

PASSWORD = "a-long-enough-passphrase"
URL = "https://example.com/watch"
PATH = "/api/entries/by-url/"


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


def test_it_answers_the_entry_held_at_that_address(client, auth, nina):
    entry, _ = save_entry(nina, url=URL, title="A watch")
    response = client.get(PATH, {"url": URL}, headers=auth)
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == entry.pk
    assert body["title"] == "A watch"


def test_it_carries_the_fields(client, auth, nina):
    save_entry(nina, url=URL, fields={"price": "129"})
    response = client.get(PATH, {"url": URL}, headers=auth)
    assert response.json()["fields"] == {"Price": "129"}


def test_it_carries_the_tags(client, auth, nina):
    save_entry(nina, url=URL, tag_names=["watches"])
    assert client.get(PATH, {"url": URL}, headers=auth).json()["tags"] == ["watches"]


def test_an_address_nobody_holds_is_a_404(client, auth):
    response = client.get(PATH, {"url": "https://example.com/nothing"}, headers=auth)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "HRC-CORE-0003"


def test_somebody_elses_address_is_a_404_not_a_403(client, auth):
    marko = _person("marko@example.com")
    save_entry(marko, url=URL)
    response = client.get(PATH, {"url": URL}, headers=auth)
    assert response.status_code == 404


def test_the_lookup_normalises_the_address(client, auth, nina):
    """The same rule the upsert uses, so the two agree on what matches."""
    save_entry(nina, url=URL)
    response = client.get(PATH, {"url": "  HTTPS://EXAMPLE.COM/watch  "}, headers=auth)
    assert response.status_code == 200


def test_the_path_is_not_read_as_an_entry_id(client, auth, nina):
    """Case is kept in the path, so /Watch is a different address."""
    save_entry(nina, url=URL)
    response = client.get(PATH, {"url": "https://example.com/Watch"}, headers=auth)
    assert response.status_code == 404


def test_a_missing_url_parameter_is_refused(client, auth):
    assert client.get(PATH, headers=auth).status_code == 422


def test_it_needs_authentication(client, nina):
    save_entry(nina, url=URL)
    response = client.get(PATH, {"url": URL})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "HRC-AUTH-0003"
