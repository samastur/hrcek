"""The committed OpenAPI schema.

The schema is exported to a file and committed so that a client can be
generated without running Hrček, and a hook fails when the file and the
running API disagree. Same arrangement as the compiled translations and
the compiled email templates: the generated artefact is committed, and
drift is a build failure rather than something a client discovers.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings
from django.utils.functional import Promise
from django.utils.translation import gettext_lazy as _

SCHEMA_PATH = Path(settings.BASE_DIR) / "docs" / "api" / "openapi.json"


def render_schema() -> str:
    """The schema as it should appear on disk.

    Sorted keys and a trailing newline so the output is byte-stable: a
    freshness check is worthless if the rendering moves on its own.
    """
    # Imported here, not at module level: hrcek.api pulls in the routers,
    # which import models, and this module is loaded from settings-time
    # contexts.
    from hrcek.api import api  # noqa: PLC0415

    schema = api.get_openapi_schema()
    return json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def stale_reason() -> Promise | None:
    """Why the committed schema is out of date, or None if it is not.

    Lazy translatable strings, not plain text: the reason is
    interpolated into a translated sentence, and mixing the two would
    produce a half-translated message.
    """
    if not SCHEMA_PATH.is_file():
        return _("it has not been exported yet")
    if SCHEMA_PATH.read_text(encoding="utf-8") != render_schema():
        return _("the API has changed since it was exported")
    return None


def write_schema() -> bool:
    """Write the schema. Returns whether the file changed."""
    SCHEMA_PATH.parent.mkdir(parents=True, exist_ok=True)
    rendered = render_schema()
    if SCHEMA_PATH.is_file() and SCHEMA_PATH.read_text(encoding="utf-8") == rendered:
        return False
    SCHEMA_PATH.write_text(rendered, encoding="utf-8")
    return True
