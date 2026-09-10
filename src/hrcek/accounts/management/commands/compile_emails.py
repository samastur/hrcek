from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext as _

from hrcek.accounts.emails.compiler import stale_templates, write_all


class Command(BaseCommand):
    help = "Compile MJML email sources into Django HTML templates."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--check",
            action="store_true",
            help="Report stale templates instead of writing them.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        if options["check"]:
            stale = stale_templates()
            if stale:
                raise CommandError(
                    _(
                        "Email templates are out of date: %(names)s. Run: "
                        "uv run python manage.py compile_emails"
                    )
                    % {"names": ", ".join(stale)}
                )
            self.stdout.write(_("Email templates are up to date."))
            return

        changed = write_all()
        if changed:
            self.stdout.write(_("Compiled: %(names)s") % {"names": ", ".join(changed)})
        else:
            self.stdout.write(_("Email templates are up to date."))
