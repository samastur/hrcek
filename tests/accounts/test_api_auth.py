import json
from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from hrcek.accounts.models import ApiToken, User

pytestmark = pytest.mark.django_db

PASSWORD = "a-long-enough-passphrase"


@pytest.fixture
def person():
    return User.objects.create_user(
        email="nina@example.com",
        password=PASSWORD,
        display_name="Nina",
        email_verified_at=timezone.now(),
    )


def _login(client, identifier, password=PASSWORD):
    return client.post(
        "/api/auth/login",
        data=json.dumps({"identifier": identifier, "password": password}),
        content_type="application/json",
    )


def test_login_with_an_email_succeeds(client, person):
    response = _login(client, "nina@example.com")
    assert response.status_code == 200
    assert response.json() == {"email": "nina@example.com", "display_name": "Nina"}


def test_login_with_a_display_name_succeeds(client, person):
    assert _login(client, "Nina").status_code == 200


def test_login_with_a_wrong_password_is_401(client, person):
    response = _login(client, "nina@example.com", password="wrong")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "HRC-AUTH-0001"


def test_login_by_a_disabled_account_is_indistinguishable(client, person):
    person.is_active = False
    person.save()
    response = _login(client, "nina@example.com")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "HRC-AUTH-0001"


def test_login_with_an_unconfirmed_email_is_403(client, person):
    person.email_verified_at = None
    person.save()
    response = _login(client, "nina@example.com")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "HRC-AUTH-0002"


def test_me_requires_authentication(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "HRC-AUTH-0003"


def test_me_works_with_a_session(client, person):
    _login(client, "nina@example.com")
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == "nina@example.com"


def test_me_works_with_a_bearer_token(client, person):
    _token, raw = ApiToken.issue(person, name="script")
    response = client.get("/api/auth/me", headers={"authorization": f"Bearer {raw}"})
    assert response.status_code == 200
    assert response.json()["email"] == "nina@example.com"


def test_a_token_post_needs_no_csrf_token(person):
    """Regression test for the auth ordering.

    django-ninja aborts the auth chain on the first exception, and
    SessionAuth raises during its CSRF check before it looks at any
    cookie. If SessionAuth is placed before ApiTokenAuth, this request
    fails with a CSRF error even though it carries a valid token.

    It must use enforce_csrf_checks=True: the default test client sets
    _dont_enforce_csrf_checks, which makes ninja's check pass no matter
    what, so this test would happily pass with the ordering wrong.
    """
    csrf_client = Client(enforce_csrf_checks=True)
    _token, raw = ApiToken.issue(person, name="script")
    response = csrf_client.post(
        "/api/auth/logout", headers={"authorization": f"Bearer {raw}"}
    )
    assert response.status_code == 204


def test_a_session_post_without_a_csrf_token_is_403(person):
    csrf_client = Client(enforce_csrf_checks=True)
    csrf_client.force_login(person)
    response = csrf_client.post("/api/auth/logout")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "HRC-AUTH-0005"


def test_a_garbage_token_is_401_with_its_own_code(client, person):
    response = client.get(
        "/api/auth/me", headers={"authorization": "Bearer hrcek_nonsense"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "HRC-AUTH-0004"


def test_a_revoked_token_is_rejected(client, person):
    token, raw = ApiToken.issue(person, name="script")
    token.revoked_at = timezone.now()
    token.save()
    response = client.get("/api/auth/me", headers={"authorization": f"Bearer {raw}"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "HRC-AUTH-0004"


def test_an_expired_token_is_rejected(client, person):
    _token, raw = ApiToken.issue(
        person, name="script", expires_at=timezone.now() - timedelta(seconds=1)
    )
    response = client.get("/api/auth/me", headers={"authorization": f"Bearer {raw}"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "HRC-AUTH-0004"


def test_a_token_belonging_to_a_disabled_user_is_rejected(client, person):
    _token, raw = ApiToken.issue(person, name="script")
    person.is_active = False
    person.save()
    response = client.get("/api/auth/me", headers={"authorization": f"Bearer {raw}"})
    assert response.status_code == 401


def test_health_stays_public(client):
    assert client.get("/api/health").status_code == 200


def test_logout_ends_the_session(client, person):
    _login(client, "nina@example.com")
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401
