import pytest
from django.core import mail
from django.core.management import call_command
from django.test import override_settings

from hrcek.accounts.emails import EMAIL_NAMES
from hrcek.accounts.emails.previews import PREVIEW_CONTEXTS
from hrcek.accounts.mail import (
    absolute_url,
    build_message,
    html_alternative,
    send_email,
)


def test_every_email_has_a_preview_context():
    assert sorted(PREVIEW_CONTEXTS) == sorted(EMAIL_NAMES)


@pytest.mark.parametrize("name", EMAIL_NAMES)
def test_every_email_renders_with_its_preview_context(name):
    message = build_message(name, "nina@example.com", PREVIEW_CONTEXTS[name])
    assert message.subject.strip()
    assert "\n" not in message.subject
    assert message.body.strip()
    html = html_alternative(message)
    assert message.alternatives[0][1] == "text/html"
    assert "<html" in html.lower()
    # A raw template tag in the output means the template did not render.
    assert "{{" not in html
    assert "{%" not in html


@pytest.mark.parametrize("name", EMAIL_NAMES)
def test_every_email_contains_its_link(name):
    context = PREVIEW_CONTEXTS[name]
    url = next(v for k, v in context.items() if k.endswith("_url"))
    message = build_message(name, "nina@example.com", context)
    assert url in message.body
    assert url in html_alternative(message)


def test_sending_puts_one_message_in_the_outbox():
    send_email("invitation", "nina@example.com", PREVIEW_CONTEXTS["invitation"])
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["nina@example.com"]


@override_settings(HRCEK_BASE_URL="https://hrcek.example.com")
def test_absolute_url_joins_without_doubling_slashes():
    assert absolute_url("/accounts/signup/") == (
        "https://hrcek.example.com/accounts/signup/"
    )


@override_settings(HRCEK_BASE_URL="https://hrcek.example.com/")
def test_absolute_url_tolerates_a_trailing_slash_in_the_base():
    assert absolute_url("/accounts/signup/") == (
        "https://hrcek.example.com/accounts/signup/"
    )


def test_the_preview_command_writes_every_email(tmp_path):
    call_command("preview_emails", "--output-dir", str(tmp_path))
    for name in EMAIL_NAMES:
        assert (tmp_path / f"{name}.html").is_file()
    index = (tmp_path / "index.html").read_text(encoding="utf-8")
    for name in EMAIL_NAMES:
        assert name in index
