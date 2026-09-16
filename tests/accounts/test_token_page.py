import re

import pytest
from django.urls import reverse
from django.utils import timezone

from hrcek.accounts.models import ApiToken, User

pytestmark = pytest.mark.django_db

PASSWORD = "a-long-enough-passphrase"


def _make(email):
    return User.objects.create_user(
        email=email, password=PASSWORD, email_verified_at=timezone.now()
    )


@pytest.fixture
def person():
    return _make("nina@example.com")


@pytest.fixture
def other():
    return _make("marko@example.com")


def _raw_from(body: str) -> str:
    """Pull the one-time token out of the page.

    Matched by its character set rather than by splitting on whitespace:
    the value is followed immediately by markup.
    """
    match = re.search(rf"{ApiToken.TOKEN_PREFIX}[A-Za-z0-9_-]+", body)
    assert match is not None, "no token found in the page"
    return match.group(0)


def test_the_page_lists_your_tokens(client, person):
    ApiToken.issue(person, name="laptop")
    client.force_login(person)
    assert "laptop" in client.get(reverse("accounts:clients")).content.decode()


def test_the_account_page_links_to_the_clients_page(client, person):
    client.force_login(person)
    body = client.get(reverse("accounts:account")).content.decode()
    assert f'href="{reverse("accounts:clients")}"' in body


def test_the_clients_page_needs_a_session(client):
    assert client.get(reverse("accounts:clients")).status_code == 302


def test_it_does_not_list_anybody_elses(client, person, other):
    ApiToken.issue(other, name="not-yours")
    client.force_login(person)
    body = client.get(reverse("accounts:clients")).content.decode()
    assert "not-yours" not in body


def test_creating_shows_the_raw_token_once(client, person):
    client.force_login(person)
    response = client.post(
        reverse("accounts:token_create"), {"name": "laptop"}, follow=True
    )
    assert ApiToken.TOKEN_PREFIX in response.content.decode()
    # Second look: the raw value is gone for good.
    later = client.get(reverse("accounts:clients")).content.decode()
    assert ApiToken.TOKEN_PREFIX not in later


def test_creating_stores_only_the_hash(client, person):
    client.force_login(person)
    response = client.post(
        reverse("accounts:token_create"), {"name": "laptop"}, follow=True
    )
    raw = _raw_from(response.content.decode())
    assert not ApiToken.objects.filter(token_hash=raw).exists()
    assert ApiToken.objects.filter(token_hash=ApiToken.hash_token(raw)).exists()


def test_the_new_token_actually_authenticates(client, person):
    client.force_login(person)
    response = client.post(
        reverse("accounts:token_create"), {"name": "laptop"}, follow=True
    )
    raw = _raw_from(response.content.decode())
    client.logout()
    api = client.get("/api/auth/me", headers={"authorization": f"Bearer {raw}"})
    assert api.status_code == 200
    assert api.json()["email"] == "nina@example.com"


def test_a_token_can_be_deleted(client, person):
    token, _raw = ApiToken.issue(person, name="laptop")
    client.force_login(person)
    assert (
        client.post(reverse("accounts:token_delete", args=[token.pk])).status_code
        == 302
    )
    assert not ApiToken.objects.filter(pk=token.pk).exists()


def test_deleting_somebody_elses_token_is_a_404(client, person, other):
    token, _raw = ApiToken.issue(other, name="not-yours")
    client.force_login(person)
    response = client.post(reverse("accounts:token_delete", args=[token.pk]))
    # 404 rather than 403: a 403 would confirm the id exists.
    assert response.status_code == 404
    assert ApiToken.objects.filter(pk=token.pk).exists()


def test_creating_needs_a_session(client):
    assert (
        client.post(reverse("accounts:token_create"), {"name": "laptop"}).status_code
        == 302
    )


def test_a_nameless_token_is_refused(client, person):
    client.force_login(person)
    response = client.post(reverse("accounts:token_create"), {"name": ""})
    assert response.status_code == 200
    assert not ApiToken.objects.filter(user=person).exists()
