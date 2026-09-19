from __future__ import annotations

from typing import Any, ClassVar

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _

from hrcek.entries.models import Entry


class Collection(models.Model):
    """A named set of somebody's entries.

    Membership is decided one way or the other and never both: either
    the owner picks the entries, or the collection names a label and
    holds whatever carries it. The kind is fixed at creation, because
    changing it would either discard hand-picked membership or swallow
    a label's entries whole — both are surprises worth refusing.
    """

    MANUAL = "manual"
    BY_LABEL = "label"
    KINDS: ClassVar[list[tuple[str, Any]]] = [
        (MANUAL, _("chosen by hand")),
        (BY_LABEL, _("everything with a label")),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="collections",
        verbose_name=_("owner"),
    )
    name = models.CharField(_("name"), max_length=100)
    description = models.TextField(_("description"), blank=True)
    kind = models.CharField(_("kind"), max_length=10, choices=KINDS, default=MANUAL)
    label = models.ForeignKey(
        "entries.Tag",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="collections",
        verbose_name=_("label"),
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("changed at"), auto_now=True)

    class Meta:
        verbose_name = _("collection")
        verbose_name_plural = _("collections")
        ordering = ("name",)
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                "owner", Lower("name"), name="unique_collection_per_owner_ci"
            ),
            # A label collection names exactly one label; a manual one
            # names none. The database refuses the other two shapes,
            # because a collection in either of them has no meaning.
            models.CheckConstraint(
                condition=(
                    Q(kind="label", label__isnull=False)
                    | Q(kind="manual", label__isnull=True)
                ),
                name="label_set_exactly_when_kind_is_label",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def entries(self) -> models.QuerySet[Entry]:
        """This collection's entries, newest first.

        The two kinds order by different clocks: a manual collection by
        when the entry was put into it, a label collection by when the
        entry was saved, because there is no moment of adding. One
        method, so pages, feeds and tests cannot drift apart.
        """
        if self.kind == self.BY_LABEL:
            return (
                Entry.objects.filter(owner=self.owner, tags=self.label)
                .order_by("-created_at", "-pk")
                .distinct()
            )
        return Entry.objects.filter(collection_memberships__collection=self).order_by(
            "-collection_memberships__added_at",
            "-collection_memberships__pk",
        )


class CollectionEntry(models.Model):
    """One entry's place in one manual collection.

    `added_at` is what orders a manual collection, which is why this is
    a model of its own rather than a plain many-to-many.
    """

    collection = models.ForeignKey(
        Collection,
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name=_("collection"),
    )
    entry = models.ForeignKey(
        "entries.Entry",
        on_delete=models.CASCADE,
        related_name="collection_memberships",
        verbose_name=_("entry"),
    )
    added_at = models.DateTimeField(_("added at"), auto_now_add=True)

    class Meta:
        verbose_name = _("collection entry")
        verbose_name_plural = _("collection entries")
        ordering = ("-added_at", "-pk")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["collection", "entry"], name="unique_entry_per_collection"
            )
        ]

    def __str__(self) -> str:
        return f"{self.entry} in {self.collection}"
