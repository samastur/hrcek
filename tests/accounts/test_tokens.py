from datetime import timedelta

import pytest
from django.utils import timezone

from hrcek.accounts.models import ApiToken, User

pytestmark = pytest.mark.django_db

PASSWORD = "a-long-enough-passphrase"


@pytest.fixture
def person():
    return User.objects.create_user(email="nina@example.com", password=PASSWORD)


def test_issue_returns_a_prefixed_raw_token(person):
    token, raw = ApiToken.issue(person, name="laptop")
    assert raw.startswith(ApiToken.TOKEN_PREFIX)
    assert token.user == person
    assert token.name == "laptop"


def test_the_raw_token_is_never_stored(person):
    _token, raw = ApiToken.issue(person, name="laptop")
    assert not ApiToken.objects.filter(token_hash=raw).exists()
    assert ApiToken.objects.filter(token_hash=ApiToken.hash_token(raw)).exists()


def test_two_tokens_are_never_the_same(person):
    _first, raw_one = ApiToken.issue(person, name="one")
    _second, raw_two = ApiToken.issue(person, name="two")
    assert raw_one != raw_two


def test_a_fresh_token_is_usable(person):
    token, _raw = ApiToken.issue(person, name="laptop")
    assert token.is_usable is True


def test_a_revoked_token_is_not_usable(person):
    token, _raw = ApiToken.issue(person, name="laptop")
    token.revoked_at = timezone.now()
    assert token.is_usable is False


def test_an_expired_token_is_not_usable(person):
    token, _raw = ApiToken.issue(
        person, name="laptop", expires_at=timezone.now() - timedelta(seconds=1)
    )
    assert token.is_usable is False


def test_a_future_expiry_is_still_usable(person):
    token, _raw = ApiToken.issue(
        person, name="laptop", expires_at=timezone.now() + timedelta(days=1)
    )
    assert token.is_usable is True


def test_touch_records_first_use(person):
    token, _raw = ApiToken.issue(person, name="laptop")
    assert token.last_used_at is None
    token.touch()
    assert token.last_used_at is not None


def test_touch_does_not_write_again_within_a_minute(person):
    token, _raw = ApiToken.issue(person, name="laptop")
    token.touch()
    first = token.last_used_at
    token.touch()
    # A busy client must not turn every read into a SQLite write.
    assert token.last_used_at == first


def test_touch_writes_again_after_a_minute(person):
    token, _raw = ApiToken.issue(person, name="laptop")
    token.last_used_at = timezone.now() - timedelta(minutes=2)
    token.save()
    token.touch()
    assert token.last_used_at > timezone.now() - timedelta(seconds=5)


def test_the_admin_shows_a_new_token_once(client, person):
    staff = User.objects.create_superuser(email="root@example.com", password=PASSWORD)
    client.force_login(staff)
    response = client.post(
        "/admin/accounts/apitoken/add/",
        {"user": person.pk, "name": "laptop", "expires_at_0": "", "expires_at_1": ""},
        follow=True,
    )
    assert response.status_code == 200
    # The only moment the raw value is ever visible.
    assert ApiToken.TOKEN_PREFIX in response.content.decode()
    assert ApiToken.objects.filter(user=person, name="laptop").exists()
