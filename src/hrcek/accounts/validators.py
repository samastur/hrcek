import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_display_name(value: str) -> None:
    """Keep display names distinguishable from email addresses.

    Sign-in accepts either identifier, so a display name containing "@"
    would make the two impossible to tell apart.
    """
    if "@" in value:
        raise ValidationError(
            _('A display name may not contain "@".'),
            code="display_name_has_at",
        )
    if not value.strip():
        raise ValidationError(
            _("A display name may not be blank."),
            code="display_name_blank",
        )


def validate_domain(value: str) -> None:
    """A bare domain, not an address and not a hostname."""
    candidate = value.strip().lower()
    if "@" in candidate:
        raise ValidationError(
            _('Enter a domain only, without "@".'), code="domain_has_at"
        )
    if "." not in candidate or candidate.startswith(".") or candidate.endswith("."):
        raise ValidationError(
            _("Enter a valid domain, for example example.com."),
            code="domain_malformed",
        )


NAMESPACE_RE = re.compile(r"^[A-Za-z0-9_-]{1,50}$")


def validate_namespace(value: str) -> None:
    """A public name has to survive being part of an address.

    Letters, digits, hyphens and underscores only: no spaces to
    encode, no dots to be read as a file extension, nothing whose
    meaning changes between a browser's address bar and a link
    somebody copies out by hand.
    """
    if not NAMESPACE_RE.match(value or ""):
        raise ValidationError(
            _(
                "A public name may use only letters, digits, hyphens and "
                "underscores, and may be at most 50 characters long."
            ),
            code="namespace_unusable",
        )
