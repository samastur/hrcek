import pytest
from django.urls import reverse
from django.utils import timezone

from hrcek.accounts.models import User
from hrcek.entries.models import Entry, FieldDefinition, FieldValue
from tests.entries.helpers import _structure

pytestmark = pytest.mark.django_db

PASSWORD = "a-long-enough-passphrase"


def _person(email):
    return User.objects.create_user(
        email=email, password=PASSWORD, email_verified_at=timezone.now()
    )


@pytest.fixture
def nina():
    return _person("nina@example.com")


def test_the_page_needs_a_session(client):
    assert client.get(reverse("entries:fields")).status_code == 302


def test_it_lists_your_fields(client, nina):
    client.force_login(nina)
    body = client.get(reverse("entries:fields")).content.decode()
    assert "Price" in body
    assert "Priority" in body


def test_it_lists_nobody_elses(client, nina):
    marko = _person("marko@example.com")
    FieldDefinition.objects.create(owner=marko, name="Secret")
    client.force_login(nina)
    assert "Secret" not in client.get(reverse("entries:fields")).content.decode()


def test_the_fields_are_marked_up_as_a_list(client, nina):
    client.force_login(nina)
    parsed = _structure(client.get(reverse("entries:fields")))
    rename_links = [a for a in parsed.anchors if "/edit/" in a[0]]
    assert len(rename_links) == 2, "no rename links rendered"
    for href, ancestors in rename_links:
        assert "li" in ancestors, f"{href} is not inside a list item"
        assert "ul" in ancestors, f"{href} is not inside a list"


def test_a_field_can_be_added(client, nina):
    client.force_login(nina)
    response = client.post(
        reverse("entries:fields"), {"name": "Seller", "kind": "text"}
    )
    assert response.status_code == 302
    assert FieldDefinition.objects.filter(owner=nina, name="Seller").exists()


def test_a_new_field_belongs_to_the_person_who_added_it(client, nina):
    _person("marko@example.com")
    client.force_login(nina)
    client.post(reverse("entries:fields"), {"name": "Seller", "kind": "text"})
    assert FieldDefinition.objects.get(name="Seller").owner == nina


def test_a_duplicate_name_is_refused_in_any_casing(client, nina):
    client.force_login(nina)
    response = client.post(
        reverse("entries:fields"), {"name": "price", "kind": "number"}
    )
    assert response.status_code == 200
    assert FieldDefinition.objects.filter(owner=nina).count() == 2


def test_choice_cannot_be_created_through_the_form(client, nina):
    # It exists in the model for the seeded priority, and nowhere else.
    client.force_login(nina)
    response = client.post(
        reverse("entries:fields"), {"name": "Mood", "kind": "choice"}
    )
    assert response.status_code == 200
    assert not FieldDefinition.objects.filter(owner=nina, name="Mood").exists()


def test_a_field_can_be_renamed(client, nina):
    priority = FieldDefinition.objects.get(owner=nina, name="Priority")
    client.force_login(nina)
    response = client.post(
        reverse("entries:field_edit", args=[priority.pk]), {"name": "Urgency"}
    )
    assert response.status_code == 302
    priority.refresh_from_db()
    assert priority.name == "Urgency"
    # Renaming must not change what it holds.
    assert priority.kind == FieldDefinition.CHOICE
    assert priority.options == ["high", "medium", "low"]


def test_a_rename_may_keep_the_same_name(client, nina):
    price = FieldDefinition.objects.get(owner=nina, name="Price")
    client.force_login(nina)
    assert (
        client.post(
            reverse("entries:field_edit", args=[price.pk]), {"name": "Price"}
        ).status_code
        == 302
    )


def test_a_rename_onto_another_field_is_refused(client, nina):
    price = FieldDefinition.objects.get(owner=nina, name="Price")
    client.force_login(nina)
    response = client.post(
        reverse("entries:field_edit", args=[price.pk]), {"name": "priority"}
    )
    assert response.status_code == 200
    price.refresh_from_db()
    assert price.name == "Price"


def test_editing_somebody_elses_field_is_a_404(client, nina):
    marko = _person("marko@example.com")
    theirs = FieldDefinition.objects.get(owner=marko, name="Price")
    client.force_login(nina)
    assert (
        client.get(reverse("entries:field_edit", args=[theirs.pk])).status_code == 404
    )


def test_deleting_somebody_elses_field_is_a_404(client, nina):
    marko = _person("marko@example.com")
    theirs = FieldDefinition.objects.get(owner=marko, name="Price")
    client.force_login(nina)
    assert (
        client.post(reverse("entries:field_delete", args=[theirs.pk])).status_code
        == 404
    )


def test_deleting_asks_first_and_says_how_many_entries(client, nina):
    price = FieldDefinition.objects.get(owner=nina, name="Price")
    entry = Entry.objects.create(owner=nina, url="https://example.com/1")
    FieldValue.objects.create(entry=entry, definition=price, value_number=1)
    client.force_login(nina)
    response = client.get(reverse("entries:field_delete", args=[price.pk]))
    assert response.status_code == 200
    assert response.context["value_count"] == 1
    assert FieldDefinition.objects.filter(pk=price.pk).exists()


def test_deleting_removes_the_field_and_its_values(client, nina):
    price = FieldDefinition.objects.get(owner=nina, name="Price")
    entry = Entry.objects.create(owner=nina, url="https://example.com/1")
    FieldValue.objects.create(entry=entry, definition=price, value_number=1)
    client.force_login(nina)
    assert (
        client.post(reverse("entries:field_delete", args=[price.pk])).status_code == 302
    )
    assert not FieldDefinition.objects.filter(pk=price.pk).exists()
    assert FieldValue.objects.count() == 0


def test_the_entry_list_links_to_the_fields_page(client, nina):
    client.force_login(nina)
    body = client.get(reverse("entries:list")).content.decode()
    assert reverse("entries:fields") in body
