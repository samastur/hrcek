import pytest
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from hrcek.accounts.models import User

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


def test_the_account_page_needs_a_session(client):
    response = client.get(reverse("accounts:account"))
    assert response.status_code == 302
    assert "/?next=" in response["Location"]


def test_it_shows_the_current_details(client, person):
    client.force_login(person)
    body = client.get(reverse("accounts:account")).content.decode()
    assert "nina@example.com" in body
    assert "Nina" in body


def test_the_display_name_can_be_changed(client, person):
    client.force_login(person)
    response = client.post(reverse("accounts:display_name"), {"display_name": "Nina S"})
    assert response.status_code == 302
    person.refresh_from_db()
    assert person.display_name == "Nina S"


def test_the_display_name_can_be_cleared(client, person):
    client.force_login(person)
    client.post(reverse("accounts:display_name"), {"display_name": ""})
    person.refresh_from_db()
    assert person.display_name is None


def test_a_name_another_person_holds_is_refused(client, person):
    User.objects.create_user(
        email="other@example.com", password=PASSWORD, display_name="Marko"
    )
    client.force_login(person)
    response = client.post(reverse("accounts:display_name"), {"display_name": "marko"})
    assert response.status_code == 200
    person.refresh_from_db()
    assert person.display_name == "Nina"


def test_keeping_your_own_name_is_not_a_collision(client, person):
    client.force_login(person)
    response = client.post(reverse("accounts:display_name"), {"display_name": "Nina"})
    assert response.status_code == 302


def test_an_at_sign_is_refused(client, person):
    client.force_login(person)
    response = client.post(
        reverse("accounts:display_name"), {"display_name": "nina@example.com"}
    )
    assert response.status_code == 200
    person.refresh_from_db()
    assert person.display_name == "Nina"


def test_signing_in_lands_on_the_account_page(client, person):
    """The destination, named rather than inferred from a setting.

    test_landing.py can only assert against LOGIN_REDIRECT_URL, because
    the account page does not exist at that layer. Here it does.
    """
    response = client.post("/", {"username": "nina@example.com", "password": PASSWORD})
    assert response.status_code == 302
    assert response["Location"] == reverse("accounts:account")


def test_a_signed_in_visitor_at_the_root_goes_to_their_account(client, person):
    client.force_login(person)
    response = client.get("/")
    assert response.status_code == 302
    assert response["Location"] == reverse("accounts:account")


def test_the_welcome_page_is_gone():
    with pytest.raises(NoReverseMatch):
        reverse("accounts:welcome")
