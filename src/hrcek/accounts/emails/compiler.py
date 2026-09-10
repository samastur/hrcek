"""Compile MJML sources into committed Django HTML templates.

Both the source and its output are committed, and a hook fails when they
diverge, so a broken template is a build failure rather than a surprise
at send time. Production never runs this: mjml-python is a development
dependency.
"""

from __future__ import annotations

from pathlib import Path

import mjml

from hrcek.accounts.emails import EMAIL_NAMES

EMAILS_DIR = Path(__file__).resolve().parent
# Shared fragments pulled in with <mj-include>; not messages themselves.
PARTIALS = ("_head.mjml", "_header.mjml", "_footer.mjml")
TEMPLATES_DIR = EMAILS_DIR.parent / "templates" / "emails"

# The MJML parser requires <mjml> to be the root element, so the
# {% load %} tag cannot live in the source and is emitted here instead.
BANNER = (
    "{{# Generated from {name}.mjml by manage.py compile_emails. #}}\n{{% load i18n %}}"
)


def source_path(name: str) -> Path:
    return EMAILS_DIR / f"{name}.mjml"


def compiled_path(name: str) -> Path:
    return TEMPLATES_DIR / f"{name}.html"


def text_path(name: str) -> Path:
    return TEMPLATES_DIR / f"{name}.txt"


def subject_path(name: str) -> Path:
    return TEMPLATES_DIR / f"{name}.subject.txt"


def _load_include(path: str) -> str:
    """Resolve <mj-include path="..."> against the emails directory."""
    return (EMAILS_DIR / path).read_text(encoding="utf-8")


def compile_mjml(source: str) -> str:
    """Render MJML to HTML, leaving Django template tags untouched."""
    return mjml.mjml2html(source, include_loader=_load_include)


def expected_html(name: str) -> str:
    source = source_path(name).read_text(encoding="utf-8")
    # Normalise the trailing newline so the end-of-file-fixer hook and
    # this function agree on what the file should contain.
    body = compile_mjml(source).rstrip("\n")
    return f"{BANNER.format(name=name)}{body}\n"


def stale_templates() -> list[str]:
    """Names whose committed HTML no longer matches their source."""
    stale = []
    for name in EMAIL_NAMES:
        target = compiled_path(name)
        if not target.is_file() or target.read_text(encoding="utf-8") != expected_html(
            name
        ):
            stale.append(name)
    return stale


def write_all() -> list[str]:
    """Write every template, returning the names that actually changed."""
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    changed = stale_templates()
    for name in changed:
        compiled_path(name).write_text(expected_html(name), encoding="utf-8")
    return changed
