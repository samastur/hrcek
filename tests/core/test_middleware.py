import pytest

from hrcek.core.request_id import REQUEST_ID_HEADER, is_acceptable

pytestmark = pytest.mark.django_db


def test_response_carries_a_request_id(client):
    response = client.get("/api/health")
    assert response.headers[REQUEST_ID_HEADER]


def test_a_valid_incoming_request_id_is_reused(client):
    response = client.get("/api/health", headers={"x-request-id": "abc-123_XYZ"})
    assert response.headers[REQUEST_ID_HEADER] == "abc-123_XYZ"


@pytest.mark.parametrize(
    "hostile",
    ["a" * 65, "has spaces", "semi;colon", ""],
)
def test_an_unacceptable_incoming_request_id_is_replaced(client, hostile):
    response = client.get("/api/health", headers={"x-request-id": hostile})
    assert response.headers[REQUEST_ID_HEADER] != hostile
    assert len(response.headers[REQUEST_ID_HEADER]) == 32


def test_the_request_id_is_tagged_on_sentry(client, monkeypatch):
    tags = {}
    monkeypatch.setattr("hrcek.core.middleware.set_tag", tags.__setitem__)
    response = client.get("/api/health")
    assert tags["request_id"] == response.headers[REQUEST_ID_HEADER]


@pytest.mark.parametrize(
    "value",
    ["abc", "a" * 64, "with.dots-and_underscores"],
)
def test_is_acceptable_accepts_sane_ids(value):
    assert is_acceptable(value) is True


@pytest.mark.parametrize(
    "value",
    ["", "a" * 65, "has spaces", "semi;colon", "inject\r\nX-Evil: 1", "a\nb"],
)
def test_is_acceptable_rejects_anything_header_unsafe(value):
    # Django's test client refuses CR/LF in headers outright, so these
    # cases can only be exercised against the predicate directly.
    assert is_acceptable(value) is False
