from unittest.mock import patch

import pytest
from django.contrib.auth import authenticate

from hrcek.accounts.models import User

pytestmark = pytest.mark.django_db

PASSWORD = "a-long-enough-passphrase"


@pytest.fixture
def person():
    return User.objects.create_user(
        email="nina@example.com", password=PASSWORD, display_name="Nina"
    )


def test_signs_in_with_an_email(person):
    assert authenticate(None, username="nina@example.com", password=PASSWORD) == person


def test_signs_in_with_a_display_name(person):
    assert authenticate(None, username="Nina", password=PASSWORD) == person


def test_identifiers_are_case_insensitive(person):
    assert authenticate(None, username="NINA@EXAMPLE.COM", password=PASSWORD) == person
    assert authenticate(None, username="nina", password=PASSWORD) == person


def test_rejects_a_wrong_password(person):
    assert authenticate(None, username="nina@example.com", password="wrong") is None


def test_rejects_an_unknown_identifier(person):
    assert authenticate(None, username="nobody@example.com", password=PASSWORD) is None


def test_rejects_an_inactive_user(person):
    person.is_active = False
    person.save()
    assert authenticate(None, username="nina@example.com", password=PASSWORD) is None


def test_an_unconfirmed_email_still_authenticates(person):
    # Verification is checked by the caller, not the backend, so that
    # "unconfirmed" and "wrong password" stay distinguishable.
    person.email_verified_at = None
    person.save()
    assert authenticate(None, username="nina@example.com", password=PASSWORD) == person


def test_a_missing_user_still_hashes_a_password():
    # Otherwise response time reveals which accounts exist.
    with patch.object(User, "set_password") as set_password:
        authenticate(None, username="nobody@example.com", password=PASSWORD)
    set_password.assert_called_once_with(PASSWORD)


def test_missing_credentials_are_rejected_without_a_query(person):
    assert authenticate(None, username="", password="") is None
    assert authenticate(None, username="nina@example.com", password="") is None
