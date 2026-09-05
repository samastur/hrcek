import re
from pathlib import Path

from django.conf import settings

from hrcek.core import errors

CODE_RE = re.compile(r"HRC-[A-Z]{3,6}-\d{4}")
# Reserved by tests/core/test_errors.py; never shipped, never documented.
TEST_PREFIX = "HRC-TEST-"


def _reference() -> str:
    path = Path(settings.BASE_DIR) / "docs" / "dev" / "error-codes.md"
    return path.read_text(encoding="utf-8")


def _registered_codes_table() -> str:
    """Only the reference table counts.

    Prose elsewhere in the page uses illustrative codes that are not
    registered on purpose, so matching the whole file would be wrong.
    """
    text = _reference()
    heading = "## Registered codes"
    assert heading in text, f"{heading!r} section is missing"
    after = text.split(heading, 1)[1]
    return after.split("\n## ", 1)[0]


def test_every_registered_code_is_documented():
    table = _registered_codes_table()
    missing = sorted(
        code
        for code in errors.registry()
        if not code.startswith(TEST_PREFIX) and code not in table
    )
    assert missing == [], (
        f"Undocumented error codes: {missing}. "
        "Add them to the table in docs/dev/error-codes.md."
    )


def test_no_documented_code_has_been_removed():
    documented = set(CODE_RE.findall(_registered_codes_table()))
    stale = sorted(documented - set(errors.registry()))
    assert stale == [], (
        f"Documented codes that no longer exist: {stale}. "
        "Remove them from the table in docs/dev/error-codes.md."
    )
