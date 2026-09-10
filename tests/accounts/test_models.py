import pytest
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

from hrcek.accounts.models import User

pytestmark = pytest.mark.django_db

PASSWORD = "a-long-enough-passphrase"


def test_create_user_needs_only_an_email_and_a_password():
    user = User.objects.create_user(email="Nina@Example.com", password=PASSWORD)
    assert user.email == "nina@example.com"
    assert user.display_name is None
    assert user.check_password(PASSWORD)
    assert user.email_verified_at is None
    assert user.is_email_confirmed is False
    assert user.is_active is True
    assert user.is_staff is False


def test_email_uniqueness_is_enforced_case_insensitively():
    User.objects.create_user(email="nina@example.com", password=PASSWORD)
    with pytest.raises(IntegrityError):
        # bulk_create skips save(), so this exercises the database
        # constraint rather than our own normalisation.
        User.objects.bulk_create([User(email="NINA@example.com")])


def test_display_name_uniqueness_is_enforced_case_insensitively():
    User.objects.create_user(
        email="a@example.com", password=PASSWORD, display_name="Marko"
    )
    with pytest.raises(IntegrityError):
        User.objects.bulk_create([User(email="b@example.com", display_name="marko")])


def test_any_number_of_users_may_have_no_display_name():
    User.objects.create_user(email="a@example.com", password=PASSWORD)
    User.objects.create_user(email="b@example.com", password=PASSWORD)
    assert User.objects.filter(display_name__isnull=True).count() == 2


def test_a_blank_display_name_is_stored_as_null():
    user = User.objects.create_user(
        email="a@example.com", password=PASSWORD, display_name="   "
    )
    assert user.display_name is None


def test_a_display_name_may_not_contain_an_at_sign():
    user = User(email="a@example.com", display_name="nina@example.com")
    with pytest.raises(ValidationError) as excinfo:
        user.full_clean()
    assert "display_name" in excinfo.value.error_dict


def test_str_prefers_the_display_name():
    assert str(User(email="a@example.com")) == "a@example.com"
    assert str(User(email="a@example.com", display_name="Nina")) == "Nina"


def test_create_superuser_is_staff_and_already_confirmed():
    user = User.objects.create_superuser(email="root@example.com", password=PASSWORD)
    assert user.is_staff is True
    assert user.is_superuser is True
    # Without this they could not reach the admin, which requires a
    # confirmed address.
    assert user.email_verified_at is not None


def test_create_user_rejects_a_missing_email():
    with pytest.raises(ValueError, match="email address is required"):
        User.objects.create_user(email="", password=PASSWORD)
