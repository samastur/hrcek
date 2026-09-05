from io import StringIO

import pytest
from django.core.management import call_command


# makemigrations checks migration history against the database, so this
# needs database access even though it never touches a model.
@pytest.mark.django_db
def test_no_missing_migrations():
    out = StringIO()
    try:
        call_command("makemigrations", "--check", "--dry-run", stdout=out, verbosity=1)
    except SystemExit:
        # Not pytest.fail(): ty cannot see through the decorator pytest
        # wraps it in, and reports a false positive on the call.
        raise AssertionError(
            "Model changes are not reflected in migrations. Run:\n"
            "  uv run python manage.py makemigrations\n\n"
            f"{out.getvalue()}"
        ) from None
