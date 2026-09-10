"""Building and sending the messages Hrcek sends.

Uses Django 6.1's mailers API. Never pass fail_silently or connection:
both are deprecated and would fail the suite.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


def absolute_url(path: str) -> str:
    """Build a full URL for a link in an email.

    Most of these messages are sent from an admin action or a management
    context, where there is no request to build a URL from.
    """
    return f"{settings.HRCEK_BASE_URL.rstrip('/')}/{path.lstrip('/')}"


def build_message(
    name: str, to: str, context: dict[str, Any]
) -> EmailMultiAlternatives:
    full_context = {"base_url": settings.HRCEK_BASE_URL, **context}
    # A subject spanning several lines would be a header injection.
    subject = " ".join(
        render_to_string(f"emails/{name}.subject.txt", full_context).split()
    )
    text = render_to_string(f"emails/{name}.txt", full_context)
    # <mj-preview> in _head.mjml renders this as the inbox snippet. Taking
    # it from the text body means it never has to be written, or
    # translated, a second time.
    preview = next((line.strip() for line in text.splitlines() if line.strip()), "")

    message = EmailMultiAlternatives(subject=subject, body=text, to=[to])
    message.attach_alternative(
        render_to_string(f"emails/{name}.html", {**full_context, "preview": preview}),
        "text/html",
    )
    return message


def html_alternative(message: EmailMultiAlternatives) -> str:
    """The HTML body of a message built by build_message().

    Django types an alternative's content as a union that includes
    bytes and Message, so reading it needs one narrowing in one place
    rather than a cast at every call site.

    Indexed rather than named access: at runtime this is Django 6.1's
    EmailAlternative named tuple, but django-stubs still describes it as
    a plain tuple. Indexing satisfies both.
    """
    return str(message.alternatives[0][0])


def send_email(name: str, to: str, context: dict[str, Any]) -> None:
    build_message(name, to, context).send()
