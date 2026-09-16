import pytest
from django.urls import reverse
from django.utils import timezone

from hrcek.accounts.models import User

pytestmark = pytest.mark.django_db

PASSWORD = "a-long-enough-passphrase"


@pytest.fixture
def person():
    return User.objects.create_user(
        email="nina@example.com", password=PASSWORD, email_verified_at=timezone.now()
    )


def test_nav_signs_out_with_a_post_form_not_a_link(client, person):
    client.force_login(person)
    response = client.get(reverse("entries:list"))
    logout_url = reverse("accounts:logout")
    assert f'action="{logout_url}"' in response.text
    assert f'href="{logout_url}"' not in response.text


def test_posting_the_nav_form_signs_out(client, person):
    client.force_login(person)
    response = client.post(reverse("accounts:logout"))
    assert response.status_code == 302
    response = client.get(reverse("entries:list"))
    assert response.status_code == 302  # anonymous again, sent to sign in
