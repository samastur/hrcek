"""The API guide has to keep up with the API.

Documentation rots silently; a test is the only thing that notices. The
committed OpenAPI schema is the source of truth here, and a hook already
keeps that in step with the running code.
"""

import json
from pathlib import Path

import pytest
from django.conf import settings

from hrcek.core.openapi import SCHEMA_PATH

GUIDE = Path(settings.BASE_DIR) / "docs" / "dev" / "api.md"


def _operations() -> list[str]:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return [
        f"{method.upper()} {path}"
        for path, operations in schema["paths"].items()
        for method in operations
    ]


@pytest.mark.parametrize("operation", _operations(), ids=lambda o: o)
def test_every_endpoint_is_documented(operation):
    assert operation in GUIDE.read_text(encoding="utf-8"), (
        f"{operation} is not mentioned in docs/dev/api.md. "
        "Add it, or the guide is lying to whoever reads it."
    )


def test_the_guide_explains_the_error_envelope():
    text = GUIDE.read_text(encoding="utf-8")
    # The one thing a client author must get right.
    assert '"code"' in text or "`code`" in text
    assert "error-codes.md" in text


def test_the_guide_points_at_the_committed_schema():
    text = GUIDE.read_text(encoding="utf-8")
    assert "openapi.json" in text
