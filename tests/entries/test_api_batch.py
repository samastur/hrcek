import json

import pytest
from django.utils import timezone

from hrcek.accounts.models import ApiToken, User
from hrcek.entries.models import Entry

pytestmark = pytest.mark.django_db

PASSWORD = "a-long-enough-passphrase"


@pytest.fixture
def nina():
    return User.objects.create_user(
        email="nina@example.com", password=PASSWORD, email_verified_at=timezone.now()
    )


@pytest.fixture
def auth(nina):
    _token, raw = ApiToken.issue(nina, name="script")
    return {"authorization": f"Bearer {raw}"}


def _batch(client, headers, rows):
    return client.post(
        "/api/entries/batch/",
        data=json.dumps(rows),
        content_type="application/json",
        headers=headers,
    )


def test_a_clean_batch_answers_200(client, nina, auth):
    response = _batch(
        client,
        auth,
        [
            {"url": "https://example.com/1", "title": "One"},
            {"url": "https://example.com/2", "title": "Two"},
        ],
    )
    assert response.status_code == 200
    results = response.json()["results"]
    assert [r["status"] for r in results] == ["created", "created"]
    assert [r["index"] for r in results] == [0, 1]
    assert Entry.objects.filter(owner=nina).count() == 2


def test_a_repeated_batch_updates_rather_than_duplicating(client, nina, auth):
    rows = [{"url": "https://example.com/1", "title": "One"}]
    _batch(client, auth, rows)
    response = _batch(client, auth, rows)
    assert response.json()["results"][0]["status"] == "updated"
    assert Entry.objects.filter(owner=nina).count() == 1


def test_a_mixed_batch_answers_207(client, nina, auth):
    response = _batch(
        client,
        auth,
        [
            {"url": "https://example.com/1", "title": "Good"},
            {"url": "not a url", "title": "Bad"},
            {"url": "https://example.com/3", "title": "Also good"},
        ],
    )
    # A flat 200 would hide the failure from a client checking status.
    assert response.status_code == 207
    assert [r["status"] for r in response.json()["results"]] == [
        "created",
        "error",
        "created",
    ]


def test_the_good_rows_of_a_mixed_batch_really_are_saved(client, nina, auth):
    _batch(
        client,
        auth,
        [
            {"url": "https://example.com/1", "title": "Good"},
            {"url": "not a url", "title": "Bad"},
            {"url": "https://example.com/3", "title": "Also good"},
        ],
    )
    assert sorted(e.title for e in Entry.objects.filter(owner=nina)) == [
        "Also good",
        "Good",
    ]


def test_a_failing_row_reports_a_code_and_a_message(client, nina, auth):
    response = _batch(client, auth, [{"url": "not a url"}])
    error = response.json()["results"][0]["error"]
    assert error["code"] == "HRC-CORE-0002"
    assert error["message"]


def test_results_keep_the_order_they_were_sent_in(client, nina, auth):
    rows = [{"url": f"https://example.com/{n}"} for n in range(10)]
    rows[4]["url"] = "not a url"
    results = _batch(client, auth, rows).json()["results"]
    assert [r["index"] for r in results] == list(range(10))
    assert results[4]["status"] == "error"


def test_too_many_rows_is_refused_whole(client, nina, auth, settings):
    rows = [
        {"url": f"https://example.com/{n}"} for n in range(settings.HRCEK_MAX_BATCH + 1)
    ]
    response = _batch(client, auth, rows)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "HRC-ENTRY-0001"
    assert not Entry.objects.filter(owner=nina).exists()


def test_exactly_the_limit_is_accepted(client, nina, auth, settings):
    rows = [
        {"url": f"https://example.com/{n}"} for n in range(settings.HRCEK_MAX_BATCH)
    ]
    assert _batch(client, auth, rows).status_code == 200


def test_an_empty_batch_is_harmless(client, nina, auth):
    response = _batch(client, auth, [])
    assert response.status_code == 200
    assert response.json()["results"] == []


def test_batching_without_credentials_is_refused(client):
    assert _batch(client, {}, [{"url": "https://example.com/1"}]).status_code == 401
