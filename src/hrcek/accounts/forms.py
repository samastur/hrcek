from __future__ import annotations

from typing import Any

from django import forms
from django.contrib.auth.forms import BaseUserCreationForm, PasswordResetForm
from django.contrib.auth.forms import UserChangeForm as BaseUserChangeForm
from django.contrib.auth.password_validation import validate_password
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from hrcek.accounts.errors import DISPLAY_NAME_TAKEN
from hrcek.accounts.models import User
from hrcek.accounts.validators import validate_display_name


class UserCreationForm(BaseUserCreationForm):
    """Django's creation form, re-pointed at our user model."""

    class Meta(BaseUserCreationForm.Meta):
        model = User
        fields = ("email", "display_name")


class UserChangeForm(BaseUserChangeForm):
    class Meta(BaseUserChangeForm.Meta):
        model = User
        fields = "__all__"


class InvitationAcceptForm(forms.Form):
    """Choose a password, and optionally a display name."""

    display_name = forms.CharField(
        label=_("Display name"),
        max_length=50,
        required=False,
        validators=[validate_display_name],
        help_text=_("Optional. You can sign in with this instead of your email."),
    )
    password1 = forms.CharField(
        label=_("Password"), widget=forms.PasswordInput, strip=False
    )
    password2 = forms.CharField(
        label=_("Repeat password"), widget=forms.PasswordInput, strip=False
    )

    def clean_display_name(self) -> str | None:
        name = (self.cleaned_data.get("display_name") or "").strip()
        if not name:
            return None
        if User.objects.filter(display_name__iexact=name).exists():
            raise forms.ValidationError(
                str(DISPLAY_NAME_TAKEN.message), code=DISPLAY_NAME_TAKEN.code
            )
        return name

    def clean(self) -> dict[str, Any]:
        # Form.clean() is typed as possibly returning None; for a plain
        # Form it never does, and self.cleaned_data is the real store.
        super().clean()
        cleaned = self.cleaned_data
        first, second = cleaned.get("password1"), cleaned.get("password2")
        if first and second and first != second:
            self.add_error("password2", _("The two passwords do not match."))
        if first:
            validate_password(first)
        return cleaned


class SignupForm(InvitationAcceptForm):
    """Invitation acceptance, plus an email address that must be allowed."""

    email = forms.EmailField(label=_("Email address"), max_length=254)

    field_order = ("email", "display_name", "password1", "password2")

    def clean_email(self) -> str:
        # Normalisation only. Whether the address is allowed, and whether
        # it is already registered, are both decided by the view: the
        # first so the refusal can carry a 403 rather than a redisplayed
        # form, the second so the answer is identical either way.
        return self.cleaned_data["email"].strip().lower()


class HrcekPasswordResetForm(PasswordResetForm):
    """Django's reset flow, sending Hrcek's email instead of its own.

    Overriding send_mail keeps every message in one place and one style.
    Django's context supplies a uid and a token; we turn those into the
    absolute link the templates expect.
    """

    # The signature is Django's, not ours; it cannot be narrowed without
    # breaking the override.
    def send_mail(  # noqa: PLR0913, PLR0917
        self,
        subject_template_name: str,
        email_template_name: str,
        context: dict[str, Any],
        from_email: str | None,
        to_email: str,
        html_email_template_name: str | None = None,
    ) -> None:
        # Imported here to avoid a circular import through settings.
        from hrcek.accounts.mail import absolute_url, send_email  # noqa: PLC0415

        reset_url = absolute_url(
            reverse(
                "accounts:password_reset_confirm",
                kwargs={"uidb64": context["uid"], "token": context["token"]},
            )
        )
        send_email("password_reset", to_email, {"reset_url": reset_url})
