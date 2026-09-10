from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.translation import gettext as _

from hrcek.accounts.emails import EMAIL_NAMES
from hrcek.accounts.emails.previews import PREVIEW_CONTEXTS
from hrcek.accounts.mail import build_message, html_alternative

INDEX = """<!doctype html>
<meta charset="utf-8">
<title>Hrcek email previews</title>
<h1>Hrcek email previews</h1>
<ul>{items}</ul>
"""


class Command(BaseCommand):
    help = "Render every email with sample data so it can be looked at."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--output-dir",
            default=str(Path(settings.BASE_DIR) / "build" / "email-preview"),
            help="Where to write the rendered previews.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        out = Path(options["output_dir"])
        out.mkdir(parents=True, exist_ok=True)

        items = []
        for name in EMAIL_NAMES:
            message = build_message(name, "preview@example.com", PREVIEW_CONTEXTS[name])
            (out / f"{name}.html").write_text(
                html_alternative(message), encoding="utf-8"
            )
            (out / f"{name}.txt").write_text(str(message.body), encoding="utf-8")
            items.append(
                f'<li><a href="{name}.html">{html.escape(name)}</a> '
                f"&mdash; {html.escape(str(message.subject))} "
                f'(<a href="{name}.txt">text</a>)</li>'
            )

        (out / "index.html").write_text(
            INDEX.format(items="".join(items)), encoding="utf-8"
        )
        self.stdout.write(_("Previews written to %(path)s") % {"path": out})
        self.stdout.write(_("Open %(path)s") % {"path": out / "index.html"})
