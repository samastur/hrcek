from html.parser import HTMLParser

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone

from hrcek.accounts.models import User
from hrcek.core.errors import HrcekError
from hrcek.entries.models import Entry, FieldDefinition, FieldValue
from hrcek.entries.services import save_entry

pytestmark = pytest.mark.django_db

PASSWORD = "a-long-enough-passphrase"


def _person(email):
    return User.objects.create_user(
        email=email, password=PASSWORD, email_verified_at=timezone.now()
    )


@pytest.fixture
def nina():
    """An account with a number field to put values in.

    Only Priority is seeded now, so a test that wants a number makes
    one rather than borrowing whatever the account happened to start
    with.
    """
    person = _person("nina@example.com")
    FieldDefinition.objects.create(
        owner=person, name="Cost", kind=FieldDefinition.NUMBER
    )
    return person


def _value(entry, name):
    return FieldValue.objects.filter(entry=entry, definition__name__iexact=name).first()


class _Pairs(HTMLParser):
    """Collect the dt/dd pairs of every description list on the page."""

    def __init__(self) -> None:
        super().__init__()
        self.stack: list[str] = []
        self.pairs: list[tuple[str, str]] = []
        self._term = ""

    def handle_starttag(self, tag, attrs):
        if tag in {"dl", "dt", "dd"}:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in self.stack:
            while self.stack and self.stack.pop() != tag:
                pass

    def handle_data(self, data):
        text = data.strip()
        if not text or "dl" not in self.stack:
            return
        if self.stack[-1] == "dt":
            self._term = text
        elif self.stack[-1] == "dd":
            self.pairs.append((self._term, text))


def _pairs(html: str) -> list[tuple[str, str]]:
    parser = _Pairs()
    parser.feed(html)
    return parser.pairs


def _post(url="https://example.com/1", **extra):
    data = {"url": url, "title": "", "notes": "", "tags": ""}
    data.update(extra)
    return data


def test_values_are_set_from_the_service(nina):
    entry, _ = save_entry(
        nina,
        url="https://example.com/1",
        fields={"cost": "129.00", "priority": "high"},
    )
    assert _value(entry, "cost").value == "129"
    assert _value(entry, "priority").value == "high"


def test_field_names_match_without_regard_to_case(nina):
    entry, _ = save_entry(nina, url="https://example.com/1", fields={"COST": "12"})
    assert _value(entry, "cost").value == "12"


def test_omitting_fields_leaves_existing_values_alone(nina):
    """The one place the API is not uniform, and the reason it exists.

    A client written before custom fields must not destroy them.
    """
    entry, _ = save_entry(nina, url="https://example.com/1", fields={"cost": "129"})
    save_entry(nina, url="https://example.com/1", title="Renamed")
    assert _value(entry, "cost").value == "129"


def test_an_empty_fields_object_changes_nothing(nina):
    entry, _ = save_entry(nina, url="https://example.com/1", fields={"cost": "129"})
    save_entry(nina, url="https://example.com/1", fields={})
    assert _value(entry, "cost").value == "129"


def test_a_field_left_out_of_a_given_mapping_keeps_its_value(nina):
    entry, _ = save_entry(
        nina, url="https://example.com/1", fields={"cost": "129", "priority": "high"}
    )
    save_entry(nina, url="https://example.com/1", fields={"priority": "low"})
    assert _value(entry, "cost").value == "129"
    assert _value(entry, "priority").value == "low"


def test_an_empty_string_clears_one_value(nina):
    entry, _ = save_entry(
        nina, url="https://example.com/1", fields={"cost": "129", "priority": "high"}
    )
    save_entry(nina, url="https://example.com/1", fields={"cost": ""})
    assert _value(entry, "cost") is None
    assert _value(entry, "priority").value == "high"


def test_a_value_can_be_changed(nina):
    entry, _ = save_entry(nina, url="https://example.com/1", fields={"cost": "129"})
    save_entry(nina, url="https://example.com/1", fields={"cost": "99"})
    assert _value(entry, "cost").value == "99"
    assert FieldValue.objects.filter(entry=entry).count() == 1


def test_a_number_field_refuses_text(nina):
    with pytest.raises(ValidationError):
        save_entry(nina, url="https://example.com/1", fields={"cost": "cheap"})


def test_a_choice_field_refuses_an_option_it_does_not_have(nina):
    with pytest.raises(ValidationError):
        save_entry(nina, url="https://example.com/1", fields={"priority": "urgent"})


def test_an_unknown_field_name_is_reported(nina):
    with pytest.raises(HrcekError) as caught:
        save_entry(nina, url="https://example.com/1", fields={"colour": "red"})
    assert caught.value.error_code.code == "HRC-FIELD-0001"


def test_somebody_elses_field_is_unknown_to_you(nina):
    marko = _person("marko@example.com")
    FieldDefinition.objects.create(owner=marko, name="Seller")
    with pytest.raises(HrcekError):
        save_entry(nina, url="https://example.com/1", fields={"seller": "Nobody"})


def test_nothing_is_written_when_a_later_value_is_bad(nina):
    """Validation runs over the whole mapping before anything is saved."""
    entry, _ = save_entry(nina, url="https://example.com/1", fields={"cost": "129"})
    with pytest.raises(ValidationError):
        save_entry(
            nina,
            url="https://example.com/1",
            fields={"cost": "99", "priority": "urgent"},
        )
    assert _value(entry, "cost").value == "129"


def test_a_number_may_be_given_as_a_json_number(nina):
    entry, _ = save_entry(nina, url="https://example.com/1", fields={"cost": 129.5})
    assert _value(entry, "cost").value == "129.5"


def test_the_entry_form_shows_an_input_per_field(client, nina):
    client.force_login(nina)
    form = client.get(reverse("entries:create")).context["form"]
    names = [n for n in form.fields if n.startswith("field_")]
    assert len(names) == 2


def test_a_choice_field_is_rendered_as_a_choice(client, nina):
    priority = FieldDefinition.objects.get(owner=nina, name="Priority")
    client.force_login(nina)
    form = client.get(reverse("entries:create")).context["form"]
    values = [value for value, _label in form.fields[f"field_{priority.pk}"].choices]
    assert values == ["", "high", "medium", "low"]


def test_the_entry_form_saves_values(client, nina):
    price = FieldDefinition.objects.get(owner=nina, name="Cost")
    priority = FieldDefinition.objects.get(owner=nina, name="Priority")
    client.force_login(nina)
    client.post(
        reverse("entries:create"),
        _post(**{f"field_{price.pk}": "129.00", f"field_{priority.pk}": "high"}),
    )
    entry = Entry.objects.get(owner=nina)
    assert _value(entry, "cost").value == "129"
    assert _value(entry, "priority").value == "high"


def test_the_entry_form_refuses_a_bad_number(client, nina):
    price = FieldDefinition.objects.get(owner=nina, name="Cost")
    client.force_login(nina)
    response = client.post(
        reverse("entries:create"), _post(**{f"field_{price.pk}": "cheap"})
    )
    assert response.status_code == 200
    assert not Entry.objects.filter(owner=nina).exists()


def test_the_edit_form_arrives_with_the_values_filled_in(client, nina):
    entry, _ = save_entry(nina, url="https://example.com/1", fields={"cost": "129"})
    price = FieldDefinition.objects.get(owner=nina, name="Cost")
    client.force_login(nina)
    form = client.get(reverse("entries:edit", args=[entry.pk])).context["form"]
    assert form.initial[f"field_{price.pk}"] == "129"


def test_emptying_an_input_on_the_form_clears_the_value(client, nina):
    entry, _ = save_entry(nina, url="https://example.com/1", fields={"cost": "129"})
    price = FieldDefinition.objects.get(owner=nina, name="Cost")
    client.force_login(nina)
    client.post(
        reverse("entries:edit", args=[entry.pk]),
        _post(**{f"field_{price.pk}": ""}),
    )
    assert _value(entry, "cost") is None


def test_the_form_offers_only_your_own_fields(client, nina):
    marko = _person("marko@example.com")
    theirs = FieldDefinition.objects.create(owner=marko, name="Seller")
    client.force_login(nina)
    form = client.get(reverse("entries:create")).context["form"]
    assert f"field_{theirs.pk}" not in form.fields


def test_the_list_shows_values(client, nina):
    save_entry(nina, url="https://example.com/1", fields={"cost": "129"})
    client.force_login(nina)
    body = client.get(reverse("entries:list")).content.decode()
    assert "129" in body
    assert "Cost" in body


def test_the_list_marks_values_up_as_name_and_value_pairs(client, nina):
    """A description list, not a paragraph with a colon in it."""
    save_entry(nina, url="https://example.com/1", fields={"cost": "129"})
    client.force_login(nina)
    pairs = _pairs(client.get(reverse("entries:list")).content.decode())
    assert pairs == [("Cost", "129")]
