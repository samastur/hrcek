from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext as _

from hrcek.core.openapi import SCHEMA_PATH, stale_reason, write_schema


class Command(BaseCommand):
    help = "Export the OpenAPI schema that clients are generated from."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--check",
            action="store_true",
            help="Report a stale schema instead of rewriting it.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        if options["check"]:
            reason = stale_reason()
            if reason is not None:
                raise CommandError(
                    _(
                        "The OpenAPI schema is out of date: %(reason)s. Run: "
                        "uv run python manage.py export_openapi"
                    )
                    % {"reason": reason}
                )
            self.stdout.write(_("The OpenAPI schema is up to date."))
            return

        if write_schema():
            self.stdout.write(_("Wrote %(path)s") % {"path": SCHEMA_PATH})
        else:
            self.stdout.write(_("The OpenAPI schema is up to date."))
