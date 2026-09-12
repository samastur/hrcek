from __future__ import annotations

from typing import Any

from django import forms
from django.utils.translation import gettext_lazy as _

from hrcek.entries.models import Entry, Tag


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
