import pytest

from hrcek.accounts.models import User

pytestmark = pytest.mark.django_db

PASSWORD = "a-long-enough-passphrase"


@pytest.fixture
def staff():
    return User.objects.create_superuser(email="root@example.com", password=PASSWORD)


def test_a_confirmed_superuser_reaches_the_admin(client, staff):
    client.force_login(staff)
    assert client.get("/admin/").status_code == 200


def test_an_unconfirmed_staff_user_is_turned_away(client, staff):
    staff.email_verified_at = None
    staff.save()
    client.force_login(staff)
    response = client.get("/admin/")
    # The admin bounces unauthorised users to its own login page.
    assert response.status_code == 302
    assert "/admin/login/" in response["Location"]


def test_a_non_staff_user_is_turned_away(client):
    person = User.objects.create_user(email="nina@example.com", password=PASSWORD)
    client.force_login(person)
    assert client.get("/admin/").status_code == 302


def test_anonymous_visitors_are_turned_away(client):
    assert client.get("/admin/").status_code == 302


def test_the_user_list_is_registered(client, staff):
    client.force_login(staff)
    assert client.get("/admin/accounts/user/").status_code == 200


def test_a_user_can_be_created_from_the_admin(client, staff):
    client.force_login(staff)
    response = client.post(
        "/admin/accounts/user/add/",
        {
            "email": "new@example.com",
            "display_name": "Newcomer",
            "password1": PASSWORD,
            "password2": PASSWORD,
        },
    )
    assert response.status_code == 302
    assert User.objects.filter(email="new@example.com").exists()
