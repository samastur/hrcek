import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_pages_link_the_compiled_stylesheet(client):
    response = client.get(reverse("landing"))
    assert response.status_code == 200
    assert 'href="/static/css/hrcek.css"' in response.text


def test_pages_declare_both_color_schemes(client):
    response = client.get(reverse("landing"))
    assert '<meta name="color-scheme" content="light dark">' in response.text


def test_landing_page_shows_the_mascot_above_the_title(client):
    response = client.get(reverse("landing"))
    assert 'src="/static/img/hrcek.png"' in response.text
    assert response.text.index('src="/static/img/hrcek.png"') < response.text.index(
        "<h1"
    )


def test_pages_link_the_favicon(client):
    response = client.get(reverse("landing"))
    assert 'rel="icon" href="/static/img/favicon-32.png"' in response.text
    assert 'rel="apple-touch-icon" href="/static/img/apple-touch-icon.png"' in (
        response.text
    )
