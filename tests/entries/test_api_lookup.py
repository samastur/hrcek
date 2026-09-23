import pytest
from django.utils import timezone

from hrcek.accounts.models import ApiToken, User
from hrcek.entries.models import FieldDefinition
from hrcek.entries.services import save_entry

pytestmark = pytest.mark.django_db

PASSWORD = "a-long-enough-passphrase"
URL = "https://example.com/watch"
PATH = "/api/entries/lookup"


def _person(email):
    return User.objects.create_user(
        email=email, password=PASSWORD, email_verified_at=timezone.now()
    )


@pytest.fixture
def nina():
    """An account with a number field beside the seeded Priority.

    Only Priority is seeded now, so a test wanting a number makes one.
    """
    person = _person("nina@example.com")
    FieldDefinition.objects.create(
        owner=person, name="Cost", kind=FieldDefinition.NUMBER
    )
    return person


@pytest.fixture
def auth(nina):
    _token, raw = ApiToken.issue(nina, name="script")
    return {"authorization": f"Bearer {raw}"}


def test_it_answers_the_entry_held_at_that_address(client, auth, nina):
    entry, _ = save_entry(nina, url=URL, title="A watch")
    response = client.post(
        PATH, {"url": URL}, content_type="application/json", headers=auth
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == entry.pk
    assert body["title"] == "A watch"


def test_it_carries_the_fields(client, auth, nina):
    save_entry(nina, url=URL, fields={"cost": "129"})
    response = client.post(
        PATH, {"url": URL}, content_type="application/json", headers=auth
    )
    assert response.json()["fields"] == {"Cost": "129"}


def test_it_carries_the_tags(client, auth, nina):
    save_entry(nina, url=URL, tag_names=["watches"])
    assert client.post(
        PATH, {"url": URL}, content_type="application/json", headers=auth
    ).json()["tags"] == ["watches"]


def test_an_address_nobody_holds_is_a_404(client, auth):
    response = client.post(
        PATH,
        {"url": "https://example.com/nothing"},
        content_type="application/json",
        headers=auth,
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "HRC-CORE-0003"


def test_somebody_elses_address_is_a_404_not_a_403(client, auth):
    marko = _person("marko@example.com")
    save_entry(marko, url=URL)
    response = client.post(
        PATH, {"url": URL}, content_type="application/json", headers=auth
    )
    assert response.status_code == 404


def test_the_lookup_normalises_the_address(client, auth, nina):
    """The same rule the upsert uses, so the two agree on what matches."""
    save_entry(nina, url=URL)
    response = client.post(
        PATH,
        {"url": "  HTTPS://EXAMPLE.COM/watch  "},
        content_type="application/json",
        headers=auth,
    )
    assert response.status_code == 200


def test_the_path_is_not_read_as_an_entry_id(client, auth, nina):
    """Case is kept in the path, so /Watch is a different address."""
    save_entry(nina, url=URL)
    response = client.post(
        PATH,
        {"url": "https://example.com/Watch"},
        content_type="application/json",
        headers=auth,
    )
    assert response.status_code == 404


def test_a_missing_url_parameter_is_refused(client, auth):
    assert (
        client.post(PATH, {}, content_type="application/json", headers=auth).status_code
        == 422
    )


def test_it_needs_authentication(client, nina):
    save_entry(nina, url=URL)
    response = client.post(PATH, {"url": URL}, content_type="application/json")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "HRC-AUTH-0003"
