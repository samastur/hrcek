import json

import pytest
from django.utils import timezone

from hrcek.accounts.models import ApiToken, User
from hrcek.entries.models import Entry, FieldDefinition, FieldValue
from hrcek.entries.services import save_entry

pytestmark = pytest.mark.django_db

PASSWORD = "a-long-enough-passphrase"
URL = "https://example.com/watch"


def _person(email):
    return User.objects.create_user(
        email=email, password=PASSWORD, email_verified_at=timezone.now()
    )


@pytest.fixture
def nina():
    """An account with a number field beside the seeded Priority.

    Only Priority is seeded now, so a test wanting a number makes one.
    """
    person = _person("nina@example.com")
    FieldDefinition.objects.create(
        owner=person, name="Cost", kind=FieldDefinition.NUMBER
    )
    return person


@pytest.fixture
def auth(nina):
    _token, raw = ApiToken.issue(nina, name="script")
    return {"authorization": f"Bearer {raw}"}


def _post(client, headers, body, path="/api/entries/"):
    return client.post(
        path,
        data=json.dumps(body),
        content_type="application/json",
        headers=headers,
    )


def test_an_entry_can_be_created_with_fields(client, auth):
    response = _post(
        client, auth, {"url": URL, "fields": {"cost": "129.00", "priority": "high"}}
    )
    assert response.status_code == 201
    assert response.json()["fields"] == {"Cost": "129", "Priority": "high"}


def test_values_come_back_as_strings(client, auth):
    response = _post(client, auth, {"url": URL, "fields": {"cost": 129}})
    assert response.json()["fields"]["Cost"] == "129"


def test_a_number_may_be_sent_as_a_json_number(client, auth):
    response = _post(client, auth, {"url": URL, "fields": {"cost": 38.5}})
    assert response.status_code == 201
    assert response.json()["fields"]["Cost"] == "38.5"


def test_names_match_without_regard_to_case(client, auth):
    response = _post(client, auth, {"url": URL, "fields": {"COST": "12"}})
    assert response.json()["fields"] == {"Cost": "12"}


def test_an_entry_without_fields_has_an_empty_object(client, auth):
    assert _post(client, auth, {"url": URL}).json()["fields"] == {}


def test_omitting_fields_leaves_existing_values_alone(client, auth):
    """A client that predates custom fields must not destroy them."""
    _post(client, auth, {"url": URL, "fields": {"cost": "129"}})
    response = _post(client, auth, {"url": URL, "title": "A watch"})
    assert response.status_code == 200
    assert response.json()["fields"] == {"Cost": "129"}


def test_an_empty_fields_object_changes_nothing(client, auth):
    _post(client, auth, {"url": URL, "fields": {"cost": "129"}})
    response = _post(client, auth, {"url": URL, "fields": {}})
    assert response.json()["fields"] == {"Cost": "129"}


def test_a_field_the_mapping_does_not_name_keeps_its_value(client, auth):
    _post(client, auth, {"url": URL, "fields": {"cost": "129", "priority": "high"}})
    response = _post(client, auth, {"url": URL, "fields": {"priority": "low"}})
    assert response.json()["fields"] == {"Cost": "129", "Priority": "low"}


def test_an_empty_string_clears_one_value(client, auth):
    _post(client, auth, {"url": URL, "fields": {"cost": "129", "priority": "high"}})
    response = _post(client, auth, {"url": URL, "fields": {"cost": ""}})
    assert response.json()["fields"] == {"Priority": "high"}


def test_an_unknown_field_name_is_refused(client, auth):
    response = _post(client, auth, {"url": URL, "fields": {"colour": "red"}})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "HRC-FIELD-0001"
    assert error["details"]["field"] == "colour"
    assert not Entry.objects.exists()


def test_somebody_elses_field_is_unknown_to_you(client, auth):
    marko = _person("marko@example.com")
    FieldDefinition.objects.create(owner=marko, name="Seller")
    response = _post(client, auth, {"url": URL, "fields": {"seller": "Nobody"}})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "HRC-FIELD-0001"


def test_a_bad_number_is_ordinary_validation(client, auth):
    response = _post(client, auth, {"url": URL, "fields": {"cost": "cheap"}})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "HRC-CORE-0002"
    # Keyed by the field's name, so a client knows which input to blame.
    assert list(error["details"]["fields"]) == ["Cost"]


def test_a_value_outside_a_choice_is_refused(client, auth):
    response = _post(client, auth, {"url": URL, "fields": {"priority": "urgent"}})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "HRC-CORE-0002"
    assert "high, medium, low" in error["details"]["fields"]["Priority"][0]


def test_a_bad_url_is_still_reported_under_url(client, auth):
    """The shape did not change for the errors that already existed."""
    response = _post(client, auth, {"url": "not a url"})
    assert response.status_code == 422
    assert list(response.json()["error"]["details"]["fields"]) == ["url"]


def test_the_list_carries_fields(client, auth, nina):
    save_entry(nina, url=URL, fields={"cost": "129"})
    response = client.get("/api/entries/", headers=auth)
    assert response.json()["items"][0]["fields"] == {"Cost": "129"}


def test_a_batch_row_may_carry_fields(client, auth):
    response = _post(
        client,
        auth,
        [
            {"url": "https://example.com/1", "fields": {"cost": "10"}},
            {"url": "https://example.com/2", "fields": {"priority": "low"}},
        ],
        path="/api/entries/batch/",
    )
    assert response.status_code == 200
    assert [r["status"] for r in response.json()["results"]] == ["created", "created"]
    first = Entry.objects.get(url="https://example.com/1")
    assert FieldValue.objects.get(entry=first).value == "10"


def test_a_bad_field_fails_only_its_own_row(client, auth):
    response = _post(
        client,
        auth,
        [
            {"url": "https://example.com/1", "fields": {"cost": "10"}},
            {"url": "https://example.com/2", "fields": {"colour": "red"}},
            {"url": "https://example.com/3", "fields": {"cost": "30"}},
        ],
        path="/api/entries/batch/",
    )
    assert response.status_code == 207
    results = response.json()["results"]
    assert [r["status"] for r in results] == ["created", "error", "created"]
    assert results[1]["error"]["code"] == "HRC-FIELD-0001"
    assert Entry.objects.count() == 2


def test_a_bad_value_in_a_batch_row_leaves_its_siblings_alone(client, auth):
    response = _post(
        client,
        auth,
        [
            {"url": "https://example.com/1", "fields": {"cost": "cheap"}},
            {"url": "https://example.com/2", "fields": {"cost": "30"}},
        ],
        path="/api/entries/batch/",
    )
    assert response.status_code == 207
    results = response.json()["results"]
    assert results[0]["error"]["code"] == "HRC-CORE-0002"
    assert list(results[0]["error"]["details"]["fields"]) == ["Cost"]
    assert results[1]["status"] == "created"
