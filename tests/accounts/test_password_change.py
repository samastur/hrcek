import pytest
from django.urls import reverse
from django.utils import timezone

from hrcek.accounts.models import User

pytestmark = pytest.mark.django_db

PASSWORD = "a-long-enough-passphrase"
NEW_PASSWORD = "an-entirely-different-passphrase"


@pytest.fixture
def person():
    return User.objects.create_user(
        email="nina@example.com",
        password=PASSWORD,
        email_verified_at=timezone.now(),
    )


def _change(client, old=PASSWORD, new=NEW_PASSWORD):
    return client.post(
        reverse("accounts:password_change"),
        {"old_password": old, "new_password1": new, "new_password2": new},
    )


def test_the_page_needs_a_session(client):
    assert client.get(reverse("accounts:password_change")).status_code == 302


def test_the_password_can_be_changed(client, person):
    client.force_login(person)
    assert _change(client).status_code == 302
    person.refresh_from_db()
    assert person.check_password(NEW_PASSWORD)


def test_the_session_survives_the_change(client, person):
    client.force_login(person)
    _change(client)
    # Django rotates the session hash; without update_session_auth_hash
    # this would sign the person out of their own password change.
    assert client.get(reverse("accounts:account")).status_code == 200


def test_a_wrong_old_password_is_refused(client, person):
    client.force_login(person)
    response = _change(client, old="wrong")
    assert response.status_code == 200
    person.refresh_from_db()
    assert person.check_password(PASSWORD)


def test_a_weak_new_password_is_refused(client, person):
    client.force_login(person)
    _change(client, new="abc")
    person.refresh_from_db()
    assert person.check_password(PASSWORD)


def test_the_account_page_links_to_it(client, person):
    client.force_login(person)
    body = client.get(reverse("accounts:account")).content.decode()
    assert reverse("accounts:password_change") in body
