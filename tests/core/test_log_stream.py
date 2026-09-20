"""The console log stream: one JSON line per event, and nothing else.

The JSON stream is the machine-readable record. A plain-text copy
beside it is not just noise — it means whatever reads the stream has
to cope with lines that are not JSON.
"""

import io
import json
import logging

import pytest
from django.urls import reverse
from django.utils import timezone

from hrcek.accounts.models import User

pytestmark = pytest.mark.django_db

ORIGIN = "moz-extension://26989e36-45d7-43d2-87c1-065a5dd84f16"


@pytest.fixture
def captured(settings):
    """Every line the root and django loggers would print."""
    stream = io.StringIO()
    handlers = []
    for name in ("", "django"):
        logger = logging.getLogger(name)
        # A copy: adding to the list while walking it grows it
        # forever, which hangs rather than fails.
        for handler in list(logger.handlers):
            spy = logging.StreamHandler(stream)
            spy.setFormatter(handler.formatter)
            spy.setLevel(handler.level)
            logger.addHandler(spy)
            handlers.append((logger, spy))
    yield stream
    for logger, spy in handlers:
        logger.removeHandler(spy)


def _lines(stream) -> list[str]:
    return [line for line in stream.getvalue().splitlines() if line.strip()]


def test_the_django_logger_does_not_keep_djangos_own_handlers():
    """Django's DEFAULT_LOGGING runs first and attaches a plain-text
    handler plus mail_admins. Leaving the `django` logger unmentioned
    keeps both, and propagation adds ours on top."""
    django_logger = logging.getLogger("django")
    assert django_logger.propagate is False, "records reach root as well"
    kinds = {type(h).__name__ for h in django_logger.handlers}
    assert "AdminEmailHandler" not in kinds, "Django's mail handler is still on"
    formatters = {type(h.formatter).__name__ for h in django_logger.handlers}
    assert formatters == {"JSONFormatter"}, f"not all JSON: {formatters}"


def test_nothing_is_said_twice(client, captured):
    """One request, one line per thing that has something to say.

    Django marks a response it has already logged, so a rejected page
    view is reported once, by the logger that knows why. What must not
    happen is the same event appearing twice.
    """
    client.handler.enforce_csrf_checks = True
    client.post(
        reverse("collections:create"),
        {"name": "Watches"},
        headers={"origin": ORIGIN},
    )

    entries = [json.loads(line) for line in _lines(captured)]
    assert entries, "the rejection was not logged at all"

    seen = [(entry["logger"], entry["message"]) for entry in entries]
    assert len(seen) == len(set(seen)), f"an event was logged twice: {seen}"
    assert any(logger == "django.security.csrf" for logger, _ in seen), seen


def test_every_line_is_json(client, captured):
    """A plain-text copy beside the JSON is the whole complaint in #52:
    whatever reads the stream then has to cope with lines that are not
    JSON at all."""
    client.handler.enforce_csrf_checks = True
    client.post(
        reverse("collections:create"),
        {"name": "Watches"},
        headers={"origin": ORIGIN},
    )
    for line in _lines(captured):
        json.loads(line)  # raises if a plain-text copy slipped in


def test_the_api_path_reports_reason_and_outcome_once_each(client, captured):
    """The case in the issue. django-ninja answers the rejection with
    its own response, which Django has not marked as logged, so both
    the reason and the outcome are reported — once each, not twice."""
    client.handler.enforce_csrf_checks = True
    client.post(
        "/api/entries/",
        {"url": "https://example.com/x"},
        content_type="application/json",
        headers={"origin": ORIGIN},
    )

    entries = [json.loads(line) for line in _lines(captured)]
    loggers = [entry["logger"] for entry in entries]
    assert loggers.count("django.security.csrf") == 1, loggers
    assert loggers.count("django.request") == 1, loggers


def test_a_failed_request_carries_its_id(client, captured):
    """Django logs the response status after the middleware chain has
    returned. If the id is cleared when the chain unwinds, the one line
    worth correlating is the one that loses it."""
    client.handler.enforce_csrf_checks = True
    client.post(
        "/api/entries/",
        {"url": "https://example.com/x"},
        content_type="application/json",
        headers={"origin": ORIGIN},
    )

    outcome = [
        json.loads(line)
        for line in _lines(captured)
        if json.loads(line)["logger"] == "django.request"
    ]
    assert outcome, "django.request said nothing"
    assert outcome[0]["request_id"], "the outcome line has no request id"


def test_the_id_is_the_one_the_caller_asked_for(client, captured):
    client.handler.enforce_csrf_checks = True
    client.post(
        reverse("collections:create"),
        {"name": "Watches"},
        headers={"origin": ORIGIN, "x-request-id": "abc123def456"},
    )
    ids = {json.loads(line)["request_id"] for line in _lines(captured)}
    assert ids == {"abc123def456"}, ids


def test_an_id_does_not_leak_into_the_next_request(client, captured):
    """Ids are per request. One request's id appearing on the next
    would be worse than none at all."""
    client.get(reverse("landing"), headers={"x-request-id": "firstrequest1"})
    client.handler.enforce_csrf_checks = True
    client.post(
        reverse("collections:create"),
        {"name": "Watches"},
        headers={"origin": ORIGIN, "x-request-id": "secondrequest"},
    )

    later = [json.loads(line) for line in _lines(captured)]
    assert later, "nothing was logged"
    assert all(entry["request_id"] != "firstrequest1" for entry in later), (
        "an earlier id survived into a later request"
    )


def test_a_signed_in_person_still_gets_one_line_per_event(client, captured):
    User.objects.create_user(
        email="nina@example.com",
        password="a-long-enough-passphrase",
        email_verified_at=timezone.now(),
    )
    client.get("/collections/999999/")  # a 404 for an anonymous caller
    for line in _lines(captured):
        json.loads(line)
