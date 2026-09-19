"""The public name: the part of a public collection's address that
names the person. Optional until somebody publishes something."""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.urls import reverse
from django.utils import timezone

from hrcek.accounts.models import User
from hrcek.accounts.validators import validate_namespace

pytestmark = pytest.mark.django_db


def _person(email, **extra):
    return User.objects.create_user(
        email=email,
        password="a-long-enough-passphrase",
        email_verified_at=timezone.now(),
        **extra,
    )


@pytest.mark.parametrize("value", ["nina", "nina-s", "nina_s", "n1na", "A-b_9"])
def test_a_usable_name_is_accepted(value):
    validate_namespace(value)  # no error


@pytest.mark.parametrize(
    "value",
    ["nina samastur", "nina/s", "nina@s", "nina.s", "niña", "", "  ", "a" * 51],
)
def test_an_unusable_name_is_refused(value):
    with pytest.raises(ValidationError):
        validate_namespace(value)


def test_two_people_cannot_share_one_ignoring_case():
    _person("nina@example.com", namespace="nina")
    with pytest.raises(IntegrityError):
        _person("marko@example.com", namespace="Nina")


def test_most_accounts_have_none():
    assert _person("nina@example.com").namespace is None


def test_it_can_be_set_from_the_account_page(client):
    nina = _person("nina@example.com")
    client.force_login(nina)
    client.post(reverse("accounts:public_name"), {"namespace": "nina"})
    nina.refresh_from_db()
    assert nina.namespace == "nina"


def test_a_taken_name_is_refused_on_the_form(client):
    _person("marko@example.com", namespace="marko")
    nina = _person("nina@example.com")
    client.force_login(nina)
    response = client.post(reverse("accounts:public_name"), {"namespace": "Marko"})
    assert response.status_code == 200
    nina.refresh_from_db()
    assert nina.namespace is None


def test_an_unusable_name_is_refused_on_the_form(client):
    nina = _person("nina@example.com")
    client.force_login(nina)
    response = client.post(
        reverse("accounts:public_name"), {"namespace": "nina samastur"}
    )
    assert response.status_code == 200
    nina.refresh_from_db()
    assert nina.namespace is None


def test_it_can_be_changed(client):
    nina = _person("nina@example.com", namespace="nnia")
    client.force_login(nina)
    client.post(reverse("accounts:public_name"), {"namespace": "nina"})
    nina.refresh_from_db()
    assert nina.namespace == "nina"


def test_the_page_says_what_it_is_for(client):
    nina = _person("nina@example.com")
    client.force_login(nina)
    page = client.get(reverse("accounts:account"))
    assert "public name" in page.text.lower()
