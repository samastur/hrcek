import json
import logging
import sys

from hrcek.core.logging import JSONFormatter
from hrcek.core.request_id import reset_request_id, set_request_id


def _record(level: int = logging.INFO, exc_info=None) -> logging.LogRecord:
    return logging.LogRecord(
        name="hrcek.test",
        level=level,
        pathname=__file__,
        lineno=10,
        msg="hello %s",
        args=("world",),
        exc_info=exc_info,
    )


def test_formatter_emits_valid_json_with_the_expected_fields():
    payload = json.loads(JSONFormatter().format(_record()))
    assert payload["level"] == "INFO"
    assert payload["logger"] == "hrcek.test"
    assert payload["message"] == "hello world"
    assert payload["timestamp"]


def test_formatter_includes_the_active_request_id():
    token = set_request_id("abc123")
    try:
        payload = json.loads(JSONFormatter().format(_record()))
    finally:
        reset_request_id(token)
    assert payload["request_id"] == "abc123"


def test_formatter_uses_an_empty_request_id_outside_a_request():
    payload = json.loads(JSONFormatter().format(_record()))
    assert payload["request_id"] == ""


def test_formatter_includes_the_traceback_when_there_is_one():
    try:
        raise ValueError("boom")
    except ValueError:
        record = _record(level=logging.ERROR, exc_info=sys.exc_info())
    payload = json.loads(JSONFormatter().format(record))
    assert "ValueError: boom" in payload["exception"]
