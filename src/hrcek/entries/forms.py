from __future__ import annotations

from typing import Any

from django import forms
from django.utils.translation import gettext_lazy as _

from hrcek.accounts.models import User
from hrcek.entries.models import Entry, FieldDefinition, Tag


class EntryForm(forms.ModelForm):
    tags = forms.CharField(
        label=_("Tags"),
        required=False,
        help_text=_("Separated by commas."),
    )

    class Meta:
        model = Entry
        fields = ("url", "title", "notes")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial["tags"] = ", ".join(t.name for t in self.instance.tags.all())

    def clean_url(self) -> str:
        return Entry.normalise_url(self.cleaned_data["url"])

    def tag_names(self) -> list[str]:
        return Tag.parse_names(self.cleaned_data.get("tags", ""))


class FieldDefinitionForm(forms.ModelForm):
    class Meta:
        model = FieldDefinition
        fields = ("name", "kind")

    def __init__(self, owner: User, *args: Any, **kwargs: Any) -> None:
        self.owner = owner
        super().__init__(*args, **kwargs)
        # Only the creatable kinds are offered. A choice field needs
        # options, and there is no interface for editing those.
        self.fields["kind"].choices = [  # ty: ignore[unresolved-attribute]
            (value, label)
            for value, label in FieldDefinition.KINDS
            if value in FieldDefinition.CREATABLE_KINDS
        ]
        if self.instance.pk:
            # An existing value cannot always be reread as another type,
            # so the kind is fixed once the field exists. Silent data
            # loss would be worse than a missing feature.
            del self.fields["kind"]

    def clean_name(self) -> str:
        name = self.cleaned_data["name"].strip()
        clash = FieldDefinition.objects.filter(
            owner=self.owner, name__iexact=name
        ).exclude(pk=self.instance.pk)
        if clash.exists():
            raise forms.ValidationError(
                _("You already have a field with that name."), code="duplicate"
            )
        return name
