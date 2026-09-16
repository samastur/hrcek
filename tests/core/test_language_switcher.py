import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_every_page_offers_the_languages(client):
    response = client.get(reverse("landing"))
    assert f'action="{reverse("set_language")}"' in response.text
    # Both languages are named; only the one not in use is a button.
    assert "English" in response.text
    assert "Slovenščina" in response.text
    assert 'value="sl"' in response.text
    assert 'value="en"' not in response.text


def test_choosing_a_language_sticks(client):
    response = client.post(
        reverse("set_language"), {"language": "sl", "next": "/"}, follow=True
    )
    assert "Prijava" in response.text
    # The choice survives later requests, without any header asking for it.
    assert "Prijava" in client.get(reverse("landing")).text


def test_browser_preference_still_wins_when_nothing_is_chosen(client):
    response = client.get(reverse("landing"), headers={"accept-language": "sl"})
    assert "Prijava" in response.text
    response = client.get(reverse("landing"), headers={"accept-language": "en"})
    assert "Sign in" in response.text
