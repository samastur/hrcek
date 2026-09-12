import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from hrcek.accounts.models import User
from hrcek.accounts.tokens import make_email_change_token

pytestmark = pytest.mark.django_db

PASSWORD = "a-long-enough-passphrase"
NEW = "nina.new@example.com"


@pytest.fixture
def person():
    return User.objects.create_user(
        email="nina@example.com",
        password=PASSWORD,
        email_verified_at=timezone.now(),
    )


def _request(client, email=NEW, password=PASSWORD):
    return client.post(
        reverse("accounts:email_change"),
        {"new_email": email, "current_password": password},
    )


def test_requesting_stores_a_pending_address(client, person):
    client.force_login(person)
    assert _request(client).status_code == 302
    person.refresh_from_db()
    assert person.pending_email == NEW
    # The address people sign in with has not moved.
    assert person.email == "nina@example.com"


def test_the_confirmation_goes_to_the_new_address(client, person):
    client.force_login(person)
    _request(client)
    assert NEW in [m.to[0] for m in mail.outbox]


def test_a_notice_goes_to_the_old_address(client, person):
    # How the real owner finds out if somebody else is moving the account.
    client.force_login(person)
    _request(client)
    assert "nina@example.com" in [m.to[0] for m in mail.outbox]


def test_the_old_address_still_signs_in_while_pending(client, person):
    client.force_login(person)
    _request(client)
    client.logout()
    response = client.post("/", {"username": "nina@example.com", "password": PASSWORD})
    assert response.wsgi_request.user.is_authenticated


def test_a_wrong_current_password_is_refused(client, person):
    client.force_login(person)
    response = _request(client, password="wrong")
    assert response.status_code == 200
    person.refresh_from_db()
    assert person.pending_email is None
    assert mail.outbox == []


def test_an_address_in_use_is_refused(client, person):
    User.objects.create_user(email="taken@example.com", password=PASSWORD)
    client.force_login(person)
    response = _request(client, email="taken@example.com")
    # A form error the person can act on, so the form comes back at 200
    # carrying the message. The code itself surfaces on the confirm
    # route, where the failure is terminal and answers 409.
    assert response.status_code == 200
    assert "already in use" in response.content.decode()
    person.refresh_from_db()
    assert person.pending_email is None


def test_the_current_address_is_refused(client, person):
    client.force_login(person)
    response = _request(client, email="nina@example.com")
    assert response.status_code == 200
    person.refresh_from_db()
    assert person.pending_email is None


def test_confirming_moves_the_address(client, person):
    client.force_login(person)
    _request(client)
    person.refresh_from_db()
    token = make_email_change_token(person, NEW)
    response = client.get(reverse("accounts:email_change_confirm", args=[token]))
    assert response.status_code == 200
    person.refresh_from_db()
    assert person.email == NEW
    assert person.pending_email is None
    assert person.is_email_confirmed


def test_confirming_does_not_need_a_session(client, person):
    # The link arrives in the new inbox, quite possibly on another device.
    client.force_login(person)
    _request(client)
    person.refresh_from_db()
    token = make_email_change_token(person, NEW)
    client.logout()
    response = client.get(reverse("accounts:email_change_confirm", args=[token]))
    assert response.status_code == 200
    person.refresh_from_db()
    assert person.email == NEW


def test_a_tampered_token_is_refused(client, person):
    client.force_login(person)
    _request(client)
    person.refresh_from_db()
    token = make_email_change_token(person, NEW)
    response = client.get(
        reverse("accounts:email_change_confirm", args=[token[:-1] + "x"])
    )
    assert response.status_code == 400
    assert "HRC-ACCT-0005" in response.content.decode()
    person.refresh_from_db()
    assert person.email == "nina@example.com"


def test_a_superseded_link_is_refused(client, person):
    """Asking again replaces the pending address; the old link must die."""
    client.force_login(person)
    _request(client)
    person.refresh_from_db()
    stale = make_email_change_token(person, NEW)
    _request(client, email="nina.other@example.com")
    response = client.get(reverse("accounts:email_change_confirm", args=[stale]))
    assert response.status_code == 400
    person.refresh_from_db()
    assert person.email == "nina@example.com"


def test_an_expired_link_is_refused(client, person, settings):
    client.force_login(person)
    _request(client)
    person.refresh_from_db()
    token = make_email_change_token(person, NEW)
    settings.HRCEK_EMAIL_CONFIRMATION_EXPIRY_HOURS = 0
    response = client.get(reverse("accounts:email_change_confirm", args=[token]))
    assert response.status_code == 400


def test_an_address_taken_since_the_request_is_refused(client, person):
    client.force_login(person)
    _request(client)
    person.refresh_from_db()
    token = make_email_change_token(person, NEW)
    User.objects.create_user(email=NEW, password=PASSWORD)
    response = client.get(reverse("accounts:email_change_confirm", args=[token]))
    assert response.status_code == 409
    person.refresh_from_db()
    assert person.email == "nina@example.com"


def test_cancelling_clears_the_pending_address(client, person):
    client.force_login(person)
    _request(client)
    assert client.post(reverse("accounts:email_change_cancel")).status_code == 302
    person.refresh_from_db()
    assert person.pending_email is None


def test_the_hub_shows_a_pending_address(client, person):
    client.force_login(person)
    _request(client)
    assert NEW in client.get(reverse("accounts:account")).content.decode()
