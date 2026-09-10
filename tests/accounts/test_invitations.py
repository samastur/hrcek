from datetime import timedelta

import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from hrcek.accounts.models import Invitation, User

pytestmark = pytest.mark.django_db

PASSWORD = "a-long-enough-passphrase"


@pytest.fixture
def admin_user():
    return User.objects.create_superuser(email="root@example.com", password=PASSWORD)


def test_issuing_returns_a_raw_token_that_is_not_stored(admin_user):
    invitation, raw = Invitation.issue("nina@example.com", admin_user)
    assert raw
    assert invitation.token_hash != raw
    assert not Invitation.objects.filter(token_hash=raw).exists()


def test_issuing_sends_the_invitation_email(admin_user):
    _invitation, raw = Invitation.issue("nina@example.com", admin_user)
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["nina@example.com"]
    # The raw token exists in exactly one place: the link.
    assert raw in mail.outbox[0].body


def test_only_one_pending_invitation_per_address(admin_user):
    Invitation.issue("nina@example.com", admin_user)
    Invitation.issue("nina@example.com", admin_user)
    assert Invitation.objects.filter(email="nina@example.com").count() == 1


def test_find_pending_matches_a_good_token(admin_user):
    invitation, raw = Invitation.issue("nina@example.com", admin_user)
    assert Invitation.find_pending(raw) == invitation


def test_find_pending_rejects_a_forged_token(admin_user):
    Invitation.issue("nina@example.com", admin_user)
    assert Invitation.find_pending("not-a-real-token") is None


def test_find_pending_rejects_an_expired_token(admin_user):
    invitation, raw = Invitation.issue("nina@example.com", admin_user)
    invitation.expires_at = timezone.now() - timedelta(seconds=1)
    invitation.save()
    assert Invitation.find_pending(raw) is None


def test_find_pending_rejects_a_revoked_token(admin_user):
    invitation, raw = Invitation.issue("nina@example.com", admin_user)
    invitation.revoked_at = timezone.now()
    invitation.save()
    assert Invitation.find_pending(raw) is None


def test_accepting_creates_a_confirmed_user(client, admin_user):
    _invitation, raw = Invitation.issue("nina@example.com", admin_user)
    response = client.post(
        reverse("accounts:invitation_accept", args=[raw]),
        {"password1": PASSWORD, "password2": PASSWORD, "display_name": "Nina"},
    )
    assert response.status_code == 302
    user = User.objects.get(email="nina@example.com")
    assert user.check_password(PASSWORD)
    assert user.display_name == "Nina"
    # The link itself proved control of the inbox.
    assert user.is_email_confirmed is True


def test_the_display_name_is_optional(client, admin_user):
    _invitation, raw = Invitation.issue("nina@example.com", admin_user)
    client.post(
        reverse("accounts:invitation_accept", args=[raw]),
        {"password1": PASSWORD, "password2": PASSWORD, "display_name": ""},
    )
    assert User.objects.get(email="nina@example.com").display_name is None


def test_a_token_cannot_be_used_twice(client, admin_user):
    _invitation, raw = Invitation.issue("nina@example.com", admin_user)
    url = reverse("accounts:invitation_accept", args=[raw])
    client.post(url, {"password1": PASSWORD, "password2": PASSWORD})
    response = client.get(url)
    assert response.status_code == 400
    assert "HRC-ACCT-0002" in response.content.decode()


def test_a_bad_token_shows_the_error_code(client, admin_user):
    response = client.get(reverse("accounts:invitation_accept", args=["rubbish"]))
    assert response.status_code == 400
    assert "HRC-ACCT-0002" in response.content.decode()


def test_a_taken_display_name_is_refused(client, admin_user):
    User.objects.create_user(
        email="other@example.com", password=PASSWORD, display_name="Nina"
    )
    _invitation, raw = Invitation.issue("nina@example.com", admin_user)
    response = client.post(
        reverse("accounts:invitation_accept", args=[raw]),
        {"password1": PASSWORD, "password2": PASSWORD, "display_name": "nina"},
    )
    assert response.status_code == 200
    assert not User.objects.filter(email="nina@example.com").exists()


def test_a_weak_password_is_refused(client, admin_user):
    _invitation, raw = Invitation.issue("nina@example.com", admin_user)
    response = client.post(
        reverse("accounts:invitation_accept", args=[raw]),
        {"password1": "abc", "password2": "abc"},
    )
    assert response.status_code == 200
    assert not User.objects.filter(email="nina@example.com").exists()


def test_creating_an_invitation_in_the_admin_sends_it(client, admin_user):
    client.force_login(admin_user)
    response = client.post(
        "/admin/accounts/invitation/add/", {"email": "nina@example.com"}, follow=True
    )
    assert response.status_code == 200
    assert Invitation.objects.filter(email="nina@example.com").exists()
    assert len(mail.outbox) == 1
