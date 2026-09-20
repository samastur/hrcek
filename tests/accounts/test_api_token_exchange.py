"""Trading credentials for a token, for clients that cannot hold a
session.

A browser extension is the case this exists for: Firefox attaches
`Origin: moz-extension://<uuid>` to every request it makes, the uuid
differs per install, and Django's CSRF machinery rejects the origin
before it looks at anything else. So an extension can sign in but can
do nothing unsafe with the session afterwards.

This endpoint takes no session at all. It is unauthenticated and it
mints a durable credential, which is why the throttling tests below
matter as much as the rest.
"""

from datetime import timedelta

import pytest
from django.core.cache import cache
from django.utils import timezone

from hrcek.accounts.models import ApiToken, User

pytestmark = pytest.mark.django_db

URL = "/api/auth/tokens/exchange"
PASSWORD = "a-long-enough-passphrase"
EXTENSION_ORIGIN = "moz-extension://26989e36-45d7-43d2-87c1-065a5dd84f16"


@pytest.fixture(autouse=True)
def _empty_cache():
    """Throttle counters live in the cache; one test must not spend
    another's allowance."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def nina():
    return User.objects.create_user(
        email="nina@example.com", password=PASSWORD, email_verified_at=timezone.now()
    )


def _exchange(client, **payload):
    body = {"name": "Hrček extension", "identifier": "nina@example.com"}
    body.update(payload)
    if "password" not in body:
        body["password"] = PASSWORD
    return client.post(URL, body, content_type="application/json")


def test_credentials_are_traded_for_a_token(client, nina):
    response = _exchange(client)
    assert response.status_code == 201

    body = response.json()
    assert body["name"] == "Hrček extension"
    assert body["token"].startswith(ApiToken.TOKEN_PREFIX)
    assert ApiToken.objects.filter(user=nina, name="Hrček extension").exists()


def test_the_token_it_returns_works(client, nina):
    raw = _exchange(client).json()["token"]
    response = client.get("/api/auth/me", headers={"authorization": f"Bearer {raw}"})
    assert response.status_code == 200
    assert response.json()["email"] == "nina@example.com"


def test_an_extensions_origin_is_no_obstacle(client, nina):
    """The whole point. A session-authenticated route rejects this
    origin before reading anything; this one never looks at a session."""
    client.handler.enforce_csrf_checks = True
    response = client.post(
        URL,
        {
            "name": "Hrček extension",
            "identifier": "nina@example.com",
            "password": PASSWORD,
        },
        content_type="application/json",
        headers={"origin": EXTENSION_ORIGIN},
    )
    assert response.status_code == 201


def test_a_display_name_works_as_the_identifier(client, nina):
    nina.display_name = "nina"
    nina.save()
    assert _exchange(client, identifier="nina").status_code == 201


def test_every_call_makes_a_new_token(client, nina):
    first = _exchange(client).json()["token"]
    second = _exchange(client).json()["token"]
    assert first != second
    assert ApiToken.objects.filter(user=nina).count() == 2


def test_only_the_hash_is_kept(client, nina):
    raw = _exchange(client).json()["token"]
    stored = ApiToken.objects.get(user=nina)
    assert stored.token_hash == ApiToken.hash_token(raw)


# --- refusals ----------------------------------------------------------


def test_a_wrong_password_is_refused_with_the_login_code(client, nina):
    response = _exchange(client, password="not-the-password")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "HRC-AUTH-0001"
    assert not ApiToken.objects.exists()


def test_an_unknown_identifier_answers_the_same_way(client):
    """Telling the two apart would turn this into a way to discover
    who has an account."""
    response = _exchange(client, identifier="nobody@example.com")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "HRC-AUTH-0001"


def test_an_unconfirmed_address_is_refused(client):
    User.objects.create_user(email="new@example.com", password=PASSWORD)
    response = _exchange(client, identifier="new@example.com")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "HRC-AUTH-0002"
    assert not ApiToken.objects.exists()


def test_a_disabled_account_is_refused(client, nina):
    nina.is_active = False
    nina.save()
    response = _exchange(client)
    assert response.status_code == 401
    assert not ApiToken.objects.exists()


def test_a_name_is_required(client, nina):
    response = client.post(
        URL,
        {"identifier": "nina@example.com", "password": PASSWORD},
        content_type="application/json",
    )
    assert response.status_code == 422
    assert not ApiToken.objects.exists()


@pytest.mark.parametrize("name", ["", "   "])
def test_a_blank_name_is_refused(client, nina, name):
    response = _exchange(client, name=name)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "HRC-CORE-0002"


def test_a_name_longer_than_the_column_is_refused(client, nina):
    assert _exchange(client, name="x" * 51).status_code == 422


def test_the_name_is_trimmed(client, nina):
    _exchange(client, name="  Hrček extension  ")
    assert ApiToken.objects.get(user=nina).name == "Hrček extension"


# --- expiry ------------------------------------------------------------


def test_an_expiry_can_be_given(client, nina):
    later = timezone.now() + timedelta(days=30)
    response = _exchange(client, expires_at=later.isoformat())
    assert response.status_code == 201

    stored = ApiToken.objects.get(user=nina)
    assert stored.expires_at is not None
    assert abs((stored.expires_at - later).total_seconds()) < 1


def test_without_an_expiry_the_token_does_not_expire(client, nina):
    _exchange(client)
    assert ApiToken.objects.get(user=nina).expires_at is None


def test_an_expiry_in_the_past_is_refused(client, nina):
    earlier = timezone.now() - timedelta(minutes=1)
    assert _exchange(client, expires_at=earlier.isoformat()).status_code == 422


# --- the properties this must not break --------------------------------


def test_a_token_still_cannot_mint_another_token(client, nina):
    """The session route's rule is untouched by this addition."""
    _existing, raw = ApiToken.issue(nina, name="ci")
    response = client.post(
        "/api/auth/tokens",
        {"name": "sneaky"},
        content_type="application/json",
        headers={"authorization": f"Bearer {raw}"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "HRC-AUTH-0006"


def test_the_session_route_still_refuses_a_stranger(client):
    response = client.post(
        "/api/auth/tokens", {"name": "x"}, content_type="application/json"
    )
    assert response.status_code == 401


def test_the_exchange_ignores_a_session_entirely(client, nina):
    """Signed in or not, the credentials in the body are what count.

    This is what keeps the route safe without a CSRF check: there is
    no path through it that a cookie alone can take.
    """
    client.force_login(nina)
    response = client.post(
        URL,
        {"name": "x", "identifier": "nina@example.com", "password": "wrong"},
        content_type="application/json",
    )
    assert response.status_code == 401, "a session must not stand in for a password"
    assert not ApiToken.objects.exists()


# --- throttling --------------------------------------------------------


def test_repeated_failures_are_throttled(client, nina):
    """An unauthenticated route that mints durable credentials is worth
    guessing at, so the guessing has to get expensive."""
    statuses = [_exchange(client, password="wrong").status_code for _ in range(12)]
    assert 429 in statuses, statuses
    assert not ApiToken.objects.exists()


def test_the_throttle_does_not_stop_ordinary_use(client, nina):
    assert _exchange(client).status_code == 201
    assert _exchange(client).status_code == 201


def test_throttling_leaves_the_rest_of_the_api_alone(client, nina):
    for _ in range(12):
        _exchange(client, password="wrong")
    assert client.get("/api/health").status_code == 200
