import pytest
from django.utils import translation

from hrcek.accounts import errors

pytestmark = pytest.mark.django_db

# One string from each area, so a whole area going untranslated is caught.
SAMPLES = (
    errors.INVALID_CREDENTIALS,
    errors.EMAIL_NOT_CONFIRMED,
    errors.SIGNUP_NOT_ALLOWED,
    errors.INVITATION_INVALID,
    errors.CONFIRMATION_INVALID,
    errors.DISPLAY_NAME_TAKEN,
)


@pytest.mark.parametrize("code", SAMPLES, ids=lambda c: c.code)
def test_every_account_error_is_translated_into_slovenian(code):
    with translation.override("en"):
        english = str(code.message)
    with translation.override("sl"):
        slovenian = str(code.message)
    assert slovenian != english, f"{code.code} has no Slovenian translation"
    assert slovenian.strip()


def test_the_signup_page_is_translated(client):
    english = client.get("/accounts/signup/", headers={"accept-language": "en"})
    slovenian = client.get("/accounts/signup/", headers={"accept-language": "sl"})
    assert b"Create an account" in english.content
    assert b"Create an account" not in slovenian.content
