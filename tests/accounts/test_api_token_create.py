"""Creating an API token through the API.

A token is a credential, so the rules about who may mint one, and what
comes back, matter more than the convenience of the endpoint.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from hrcek.accounts.models import ApiToken, User

pytestmark = pytest.mark.django_db

PASSWORD = "a-long-enough-passphrase"
URL = "/api/auth/tokens"


@pytest.fixture
def nina():
    return User.objects.create_user(
        email="nina@example.com", password=PASSWORD, email_verified_at=timezone.now()
    )


@pytest.fixture
def signed_in(client, nina):
    client.force_login(nina)
    return client


def _create(client, **payload):
    return client.post(URL, payload, content_type="application/json")


def test_a_signed_in_person_gets_a_token(signed_in, nina):
    response = _create(signed_in, name="laptop")
    assert response.status_code == 201

    body = response.json()
    assert body["name"] == "laptop"
    assert body["token"].startswith(ApiToken.TOKEN_PREFIX)
    assert ApiToken.objects.filter(user=nina, name="laptop").exists()


def test_the_token_it_returns_actually_works(client, signed_in):
    raw = _create(signed_in, name="laptop").json()["token"]
    signed_in.logout()

    response = client.get("/api/auth/me", headers={"authorization": f"Bearer {raw}"})
    assert response.status_code == 200
    assert response.json()["email"] == "nina@example.com"


def test_only_the_hash_is_kept(signed_in, nina):
    raw = _create(signed_in, name="laptop").json()["token"]
    stored = ApiToken.objects.get(user=nina)
    assert stored.token_hash == ApiToken.hash_token(raw)
    assert raw not in stored.token_hash


def test_every_call_makes_a_new_one(signed_in, nina):
    first = _create(signed_in, name="laptop").json()["token"]
    second = _create(signed_in, name="laptop").json()["token"]
    assert first != second
    assert ApiToken.objects.filter(user=nina).count() == 2


def test_a_name_is_required(signed_in, nina):
    assert _create(signed_in).status_code == 422
    assert not ApiToken.objects.filter(user=nina).exists()


@pytest.mark.parametrize("name", ["", "   ", "\t"])
def test_an_empty_name_is_refused(signed_in, nina, name):
    response = _create(signed_in, name=name)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "HRC-CORE-0002"
    assert not ApiToken.objects.filter(user=nina).exists()


def test_a_name_longer_than_the_column_is_refused(signed_in, nina):
    response = _create(signed_in, name="x" * 51)
    assert response.status_code == 422
    assert not ApiToken.objects.filter(user=nina).exists()


def test_the_name_is_trimmed(signed_in, nina):
    _create(signed_in, name="  laptop  ")
    assert ApiToken.objects.get(user=nina).name == "laptop"


def test_a_stranger_cannot_create_one(client):
    assert _create(client, name="laptop").status_code == 401
    assert not ApiToken.objects.exists()


def test_a_token_cannot_mint_another_token(client, nina):
    """Otherwise revoking a leaked token does not end the access.

    A stolen token that can make more tokens is a permanent foothold:
    the thief mints a fresh one, and revoking the original changes
    nothing.
    """
    _existing, raw = ApiToken.issue(nina, name="ci")
    response = client.post(
        URL,
        {"name": "sneaky"},
        content_type="application/json",
        headers={"authorization": f"Bearer {raw}"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "HRC-AUTH-0006"
    assert not ApiToken.objects.filter(user=nina, name="sneaky").exists()


def test_an_expiry_can_be_given(signed_in, nina):
    later = timezone.now() + timedelta(days=7)
    response = _create(signed_in, name="ci", expires_at=later.isoformat())
    assert response.status_code == 201
    assert response.json()["expires_at"] is not None

    stored = ApiToken.objects.get(user=nina)
    assert stored.expires_at is not None
    assert abs((stored.expires_at - later).total_seconds()) < 1


def test_an_expiry_in_the_past_is_refused(signed_in, nina):
    earlier = timezone.now() - timedelta(minutes=1)
    response = _create(signed_in, name="ci", expires_at=earlier.isoformat())
    assert response.status_code == 422
    assert not ApiToken.objects.filter(user=nina).exists()


def test_without_an_expiry_the_token_does_not_expire(signed_in, nina):
    _create(signed_in, name="laptop")
    assert ApiToken.objects.get(user=nina).expires_at is None


def test_one_person_cannot_make_a_token_for_another(signed_in, nina):
    other = User.objects.create_user(
        email="marko@example.com", password=PASSWORD, email_verified_at=timezone.now()
    )
    _create(signed_in, name="laptop")
    assert ApiToken.objects.get(name="laptop").user == nina
    assert not ApiToken.objects.filter(user=other).exists()
