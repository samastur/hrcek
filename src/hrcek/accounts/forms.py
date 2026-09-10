from __future__ import annotations

from typing import Any

from django import forms
from django.contrib.auth.forms import BaseUserCreationForm
from django.contrib.auth.forms import UserChangeForm as BaseUserChangeForm
from django.contrib.auth.password_validation import validate_password
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
