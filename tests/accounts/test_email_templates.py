from io import StringIO

import pytest
from django.core.management import call_command

from hrcek.accounts.emails import EMAIL_NAMES
from hrcek.accounts.emails.compiler import (
    PARTIALS,
    compile_mjml,
    compiled_path,
    expected_html,
    source_path,
    stale_templates,
    subject_path,
    text_path,
)

SIMPLE = """
<mjml><mj-body><mj-section><mj-column>
<mj-text>{{ greeting }}</mj-text>
</mj-column></mj-section></mj-body></mjml>
"""


def test_compilation_produces_html():
    html = compile_mjml(SIMPLE)
    assert "<html" in html.lower()


def test_django_template_syntax_survives_compilation():
    # The whole precompile approach depends on this.
    assert "{{ greeting }}" in compile_mjml(SIMPLE)


@pytest.mark.parametrize("name", EMAIL_NAMES)
def test_every_email_has_all_three_parts(name):
    assert source_path(name).is_file()
    # Text and subject are hand-written and live where Django's template
    # loader can find them.
    assert text_path(name).is_file()
    assert subject_path(name).is_file()


@pytest.mark.parametrize("name", EMAIL_NAMES)
def test_the_committed_html_matches_its_mjml_source(name):
    assert compiled_path(name).read_text(encoding="utf-8") == expected_html(name)


def test_nothing_is_stale():
    assert stale_templates() == []


def test_the_check_command_succeeds_when_everything_is_current():
    out = StringIO()
    call_command("compile_emails", "--check", stdout=out)
    assert "up to date" in out.getvalue()


@pytest.mark.parametrize("partial", PARTIALS)
def test_every_shared_partial_exists(partial):
    assert (source_path("x").parent / partial).is_file()


@pytest.mark.parametrize("name", EMAIL_NAMES)
def test_every_email_pulls_in_the_shared_layout(name):
    source = source_path(name).read_text(encoding="utf-8")
    for partial in PARTIALS:
        assert partial in source, f"{name} does not include {partial}"


@pytest.mark.parametrize("name", EMAIL_NAMES)
def test_the_shared_footer_reaches_the_compiled_output(name):
    # Proves mj-include actually resolved rather than being ignored.
    assert "someone used your address" in compiled_path(name).read_text(
        encoding="utf-8"
    )


@pytest.mark.parametrize("name", EMAIL_NAMES)
def test_messages_carry_no_styling_of_their_own(name):
    """A message template says what it says, not how it looks.

    Fonts, colours and sizes belong in _head.mjml as mj-attributes and
    mj-class definitions. Without this the templates drift back into
    repeating inline styling, which is how they stop being readable and
    stop justifying a compile step at all.
    """
    source = source_path(name).read_text(encoding="utf-8")
    for attribute in ("font-size=", "color=", "font-weight=", "padding="):
        assert attribute not in source, (
            f"{name} sets {attribute} inline; move it into _head.mjml"
        )
