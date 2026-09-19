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
        # The picker is only of use to a collection that follows a
        # label. These mark the two inputs so the page can reveal it
        # when one is chosen; the value is the kind that needs it, so
        # no script has to hardcode the constant.
        self.fields["kind"].widget.attrs["data-kind-select"] = ""
        self.fields["label"].widget.attrs["data-label-field"] = Collection.BY_LABEL
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
        if cleaned.get("kind") == Collection.MANUAL and cleaned.get("label"):
            # Not silently dropped: the picker is hidden for a manual
            # collection, so a label arriving here means the two halves
            # of the submission disagree, and saying so beats accepting
            # it and discarding one of them.
            self.add_error(
                "label",
                _("A collection chosen by hand does not follow a label."),
            )
        return cleaned
