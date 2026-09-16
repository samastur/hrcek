import json
from io import StringIO

import pytest
from django.core.management import CommandError, call_command

from hrcek.core.openapi import SCHEMA_PATH, render_schema, stale_reason

EXPECTED_PATHS = {
    "/api/health",
    "/api/auth/login",
    "/api/auth/logout",
    "/api/auth/me",
    "/api/entries/",
    "/api/entries/batch/",
    "/api/entries/by-url/",
    "/api/entries/{pk}/image",
}


def test_the_committed_schema_matches_the_running_api():
    assert SCHEMA_PATH.read_text(encoding="utf-8") == render_schema()


def test_nothing_is_stale():
    assert stale_reason() is None


def test_the_schema_covers_every_endpoint():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert set(schema["paths"]) == EXPECTED_PATHS


def test_rendering_is_deterministic():
    # A freshness check is worthless if the output moves on its own.
    assert render_schema() == render_schema()


def test_the_check_command_succeeds_when_current():
    out = StringIO()
    call_command("export_openapi", "--check", stdout=out)
    assert "up to date" in out.getvalue()


def test_the_check_command_fails_on_drift(tmp_path, monkeypatch):
    stale = tmp_path / "openapi.json"
    stale.write_text('{"openapi": "3.1.0"}\n', encoding="utf-8")
    monkeypatch.setattr("hrcek.core.openapi.SCHEMA_PATH", stale)
    with pytest.raises(CommandError, match="out of date"):
        call_command("export_openapi", "--check")


def test_a_missing_schema_is_reported_rather_than_crashing(tmp_path, monkeypatch):
    monkeypatch.setattr("hrcek.core.openapi.SCHEMA_PATH", tmp_path / "absent.json")
    assert stale_reason() is not None
