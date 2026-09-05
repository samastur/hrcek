import re

import pytest
from django.utils.functional import Promise
from django.utils.translation import gettext_lazy as _

from hrcek.core import errors

CODE_RE = re.compile(r"^HRC-[A-Z]{3,6}-\d{4}$")


def test_registry_codes_are_unique():
    registry = errors.registry()
    assert len(registry) == len({entry.code for entry in registry.values()})


def test_every_registered_code_is_well_formed():
    bad = [code for code in errors.registry() if not CODE_RE.match(code)]
    assert bad == [], f"Malformed error codes: {bad}"


def test_every_registered_message_is_lazy():
    plain = [
        code
        for code, entry in errors.registry().items()
        if not isinstance(entry.message, Promise)
    ]
    assert plain == [], f"Untranslatable error messages: {plain}"


def test_every_registered_status_is_a_client_or_server_error():
    bad = [
        code
        for code, entry in errors.registry().items()
        if not 400 <= entry.http_status <= 599
    ]
    assert bad == [], f"Error codes with non-error status: {bad}"


def test_register_rejects_a_malformed_code():
    with pytest.raises(ValueError, match="Malformed"):
        errors.register("nope", 400, _("Message."))


def test_register_rejects_a_plain_string_message():
    with pytest.raises(TypeError, match="lazy"):
        # The wrong type is the point of this test.
        errors.register("HRC-TEST-9001", 400, "Not translatable.")  # ty: ignore[invalid-argument-type]


def test_register_rejects_a_duplicate_code():
    errors.register("HRC-TEST-9002", 400, _("First."))
    with pytest.raises(ValueError, match="Duplicate"):
        errors.register("HRC-TEST-9002", 400, _("Second."))


def test_registry_returns_a_copy():
    snapshot = errors.registry()
    snapshot.clear()
    assert errors.registry() != {}


def test_hrcek_error_carries_code_and_details():
    exc = errors.HrcekError(errors.NOT_FOUND, {"field": "url"})
    assert exc.error_code is errors.NOT_FOUND
    assert exc.details == {"field": "url"}
    assert str(exc) == "HRC-CORE-0003"


def test_hrcek_error_defaults_to_empty_details():
    assert errors.HrcekError(errors.INTERNAL_ERROR).details == {}
