"""What Sentry is allowed to carry off the machine.

`send_default_pii=False` covers cookies, bodies and user details. It
does not cover the query string, which the WSGI integration attaches
to every event — so anything a client puts in one would leave the
machine on the next error.
"""

from hrcek.core.telemetry import strip_query_strings


def _event(url: str, query: str = "") -> dict:
    request: dict[str, object] = {"url": url, "method": "GET"}
    if query:
        request["query_string"] = query
    return {"request": request}


def test_the_query_string_is_removed():
    event = strip_query_strings(_event("https://hrcek.example.com/x", "url=secret"))
    assert "query_string" not in event["request"]


def test_a_query_string_hidden_in_the_url_goes_too():
    event = strip_query_strings(
        _event("https://hrcek.example.com/x?url=https://private.example/page")
    )
    assert event["request"]["url"] == "https://hrcek.example.com/x"
    assert "private.example" not in str(event)


def test_the_rest_of_the_request_survives():
    event = strip_query_strings(_event("https://hrcek.example.com/x", "a=1"))
    assert event["request"]["method"] == "GET"
    assert event["request"]["url"] == "https://hrcek.example.com/x"


def test_an_event_without_a_request_is_left_alone():
    event = {"message": "something happened"}
    assert strip_query_strings(event) == event


def test_an_event_with_an_odd_request_shape_does_not_raise():
    """A hook that throws loses the error it was reporting."""
    assert strip_query_strings({"request": "not a mapping"}) is not None
    assert strip_query_strings({"request": {}}) is not None
    assert strip_query_strings({"request": {"url": None}}) is not None


def test_the_event_is_still_sent():
    """Scrubbing, not dropping: an error still has to reach Sentry."""
    assert strip_query_strings(_event("https://hrcek.example.com/x", "a=1")) is not None
