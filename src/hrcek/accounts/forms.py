from __future__ import annotations

from django.contrib.auth.forms import BaseUserCreationForm
from django.contrib.auth.forms import UserChangeForm as BaseUserChangeForm

from hrcek.accounts.models import User


class UserCreationForm(BaseUserCreationForm):
    """Django's creation form, re-pointed at our user model."""

    class Meta(BaseUserCreationForm.Meta):
        model = User
        fields = ("email", "display_name")


class UserChangeForm(BaseUserChangeForm):
    class Meta(BaseUserChangeForm.Meta):
        model = User
        fields = "__all__"
