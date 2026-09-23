"""An address is the private part of an entry, so it must not travel
where request lines are written down.

Hrček's own log records the path and never the query string, but a
query string also reaches the web server's access log, any proxy in
front, and Sentry — none of which this project controls. So the
address is asked for in a body instead.
"""

import json

import pytest
from django.utils import timezone

from hrcek.accounts.models import User
from hrcek.entries.models import Entry

pytestmark = pytest.mark.django_db

LOOKUP = "/api/entries/lookup"
SECRET = "https://example.com/a-private-page"
PASSWORD = "a-long-enough-passphrase"


@pytest.fixture
def nina():
    return User.objects.create_user(
        email="nina@example.com", password=PASSWORD, email_verified_at=timezone.now()
    )


@pytest.fixture
def signed_in(client, nina):
    client.force_login(nina)
    return client


def _lookup(client, url=SECRET):
    return client.post(LOOKUP, {"url": url}, content_type="application/json")


def test_an_entry_can_be_looked_up_by_its_address(signed_in, nina):
    Entry.objects.create(owner=nina, url=SECRET, title="A page")
    body = _lookup(signed_in).json()
    assert body["url"] == SECRET
    assert body["title"] == "A page"


def test_the_address_is_normalised_the_way_saving_normalises_it(signed_in, nina):
    Entry.objects.create(owner=nina, url=SECRET)
    assert _lookup(signed_in, "  HTTPS://EXAMPLE.COM/a-private-page ").status_code == (
        200
    )


def test_an_address_you_do_not_hold_is_a_404(signed_in):
    response = _lookup(signed_in)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "HRC-CORE-0003"


def test_somebody_elses_address_is_a_404_not_a_403(signed_in):
    marko = User.objects.create_user(
        email="marko@example.com", password=PASSWORD, email_verified_at=timezone.now()
    )
    Entry.objects.create(owner=marko, url=SECRET)
    assert _lookup(signed_in).status_code == 404


def test_it_needs_authentication(client):
    assert _lookup(client).status_code == 401


def test_the_address_is_not_in_the_path(signed_in, nina):
    """The point of the whole change: nothing that writes down a
    request line can write down the address."""
    Entry.objects.create(owner=nina, url=SECRET)
    response = _lookup(signed_in)
    assert SECRET not in response.request["PATH_INFO"]
    assert SECRET not in response.request.get("QUERY_STRING", "")


def test_a_404_does_not_put_the_address_in_the_error_details(signed_in):
    """The details travel to clients and into logs that keep bodies."""
    body = _lookup(signed_in).json()
    assert SECRET not in json.dumps(body)


def test_the_old_query_string_route_is_gone(signed_in, nina):
    """It put the address in the query string, where the web server
    writes it into its access log."""
    Entry.objects.create(owner=nina, url=SECRET)
    assert signed_in.get("/api/entries/by-url/", {"url": SECRET}).status_code == 404
