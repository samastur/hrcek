import re
from typing import cast

import pytest
from django.core import mail
from django.core.mail import EmailMultiAlternatives
from django.urls import reverse

from hrcek.accounts.models import User

pytestmark = pytest.mark.django_db

PASSWORD = "a-long-enough-passphrase"
NEW_PASSWORD = "an-entirely-different-passphrase"


@pytest.fixture
def person():
    return User.objects.create_user(email="nina@example.com", password=PASSWORD)


def _reset_link() -> str:
    match = re.search(r"/accounts/password/reset/\S+", str(mail.outbox[0].body))
    assert match is not None
    return match.group(0)


def test_requesting_a_reset_sends_our_email(client, person):
    response = client.post(
        reverse("accounts:password_reset"), {"email": "nina@example.com"}
    )
    assert response.status_code == 302
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["nina@example.com"]
    sent = cast("EmailMultiAlternatives", mail.outbox[0])
    assert sent.alternatives[0][1] == "text/html"


def test_requesting_a_reset_for_a_stranger_reveals_nothing(client, person):
    known = client.post(
        reverse("accounts:password_reset"), {"email": "nina@example.com"}
    )
    unknown = client.post(
        reverse("accounts:password_reset"), {"email": "nobody@example.com"}
    )
    assert known.status_code == unknown.status_code
    assert known["Location"] == unknown["Location"]
    assert len(mail.outbox) == 1


def test_the_whole_reset_round_trip_works(client, person):
    client.post(reverse("accounts:password_reset"), {"email": "nina@example.com"})
    link = _reset_link()

    # Django's confirm view redirects to a session-backed URL first.
    response = client.get(link, follow=True)
    assert response.status_code == 200
    target = response.redirect_chain[-1][0] if response.redirect_chain else link

    response = client.post(
        target,
        {"new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD},
        follow=True,
    )
    assert response.status_code == 200

    person.refresh_from_db()
    assert person.check_password(NEW_PASSWORD)


def test_a_used_link_stops_working(client, person):
    client.post(reverse("accounts:password_reset"), {"email": "nina@example.com"})
    link = _reset_link()
    response = client.get(link, follow=True)
    target = response.redirect_chain[-1][0] if response.redirect_chain else link
    client.post(
        target,
        {"new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD},
        follow=True,
    )

    # The token is single-use: Django invalidates it once the hash changes.
    again = client.get(link, follow=True)
    assert "invalid" in again.content.decode().lower()


def test_a_weak_new_password_is_refused(client, person):
    client.post(reverse("accounts:password_reset"), {"email": "nina@example.com"})
    link = _reset_link()
    response = client.get(link, follow=True)
    target = response.redirect_chain[-1][0] if response.redirect_chain else link
    client.post(target, {"new_password1": "abc", "new_password2": "abc"}, follow=True)

    person.refresh_from_db()
    assert person.check_password(PASSWORD)


def test_the_login_page_renders(client):
    assert client.get(reverse("landing")).status_code == 200
