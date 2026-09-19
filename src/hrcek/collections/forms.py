from __future__ import annotations

from typing import Any, ClassVar

from django import forms
from django.utils.translation import gettext_lazy as _

from hrcek.accounts.models import User
from hrcek.collections.models import Collection
from hrcek.entries.models import Tag


class CollectionForm(forms.ModelForm):
    class Meta:
        model = Collection
        fields = ("name", "description", "kind", "label")
        help_texts: ClassVar[dict[str, Any]] = {
            "description": _(
                "Optional. Anyone who can see this collection sees its description too."
            ),
            "kind": _(
                "Choose entries by hand, or let the collection hold "
                "everything carrying one label. This cannot be changed "
                "afterwards."
            ),
            "label": _("Only needed for a collection that follows a label."),
        }

    def __init__(self, owner: User, *args: Any, **kwargs: Any) -> None:
        self.owner = owner
        super().__init__(*args, **kwargs)
        # Only this person's labels, so somebody else's tag cannot be
        # named by submitting its id.
        self.fields["label"].queryset = Tag.objects.filter(  # ty: ignore[unresolved-attribute]
            owner=owner
        )
        self.fields["label"].required = False
        if self.instance.pk:
            # Fixed once the collection exists: switching would either
            # discard what was chosen by hand or swallow a label's
            # entries whole. Deleting and making another is honest.
            del self.fields["kind"]
            del self.fields["label"]

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        if "kind" not in self.fields:
            return cleaned
        if cleaned.get("kind") == Collection.BY_LABEL and not cleaned.get("label"):
            self.add_error("label", _("Choose the label this collection follows."))
        if cleaned.get("kind") == Collection.MANUAL:
            cleaned["label"] = None
        return cleaned
