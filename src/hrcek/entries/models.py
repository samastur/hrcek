from __future__ import annotations

from typing import ClassVar
from urllib.parse import urlsplit, urlunsplit

from django.conf import settings
from django.db import models
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _


class Tag(models.Model):
    """A label, belonging to one person.

    Nina's "watches" and Marko's "watches" are unrelated rows; neither
    can see the other's.
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tags",
        verbose_name=_("owner"),
    )
    name = models.CharField(_("name"), max_length=50)

    class Meta:
        verbose_name = _("tag")
        verbose_name_plural = _("tags")
        ordering = ("name",)
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                "owner", Lower("name"), name="unique_tag_per_owner_ci"
            )
        ]

    def __str__(self) -> str:
        return self.name

    @staticmethod
    def parse_names(raw: str) -> list[str]:
        """Split a comma-separated field, keeping the first casing seen."""
        seen: set[str] = set()
        names: list[str] = []
        for part in (raw or "").split(","):
            name = part.strip()
            if not name or name.lower() in seen:
                continue
            seen.add(name.lower())
            names.append(name)
        return names

    @classmethod
    def set_for(cls, entry: Entry, names: list[str]) -> None:
        tags = []
        for name in names:
            tag = cls.objects.filter(owner=entry.owner, name__iexact=name).first()
            if tag is None:
                tag = cls.objects.create(owner=entry.owner, name=name)
            tags.append(tag)
        entry.tags.set(tags)
        cls.prune_orphans(entry.owner)

    @classmethod
    def prune_orphans(cls, owner: object) -> None:
        """Remove this owner's tags that no entry uses any more.

        Otherwise every typo lives in the tag list forever. Written as a
        string lookup rather than through a reverse accessor, which ty
        cannot see.
        """
        cls.objects.filter(owner=owner, entries__isnull=True).delete()


class Entry(models.Model):
    """Something somebody found worth keeping."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="entries",
        verbose_name=_("owner"),
    )
    url = models.URLField(_("address"), max_length=2000)
    title = models.CharField(_("title"), max_length=300, blank=True)
    notes = models.TextField(_("notes"), blank=True)
    tags = models.ManyToManyField(
        Tag, related_name="entries", blank=True, verbose_name=_("tags")
    )
    created_at = models.DateTimeField(_("saved at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("changed at"), auto_now=True)

    class Meta:
        verbose_name = _("entry")
        verbose_name_plural = _("entries")
        # -pk as well as -created_at: entries saved in one batch can share
        # a timestamp, and without a tiebreaker pagination can repeat or
        # skip a row.
        ordering = ("-created_at", "-pk")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["owner", "url"], name="unique_entry_url_per_owner"
            )
        ]

    def __str__(self) -> str:
        return self.display_title

    @property
    def display_title(self) -> str:
        return self.title or self.url

    @staticmethod
    def normalise_url(value: str) -> str:
        """Trim, and lowercase the scheme and host. Nothing else.

        Fuller normalisation — trailing slashes, www., stripping utm_* —
        is a rabbit hole where every rule is wrong for some site, and its
        failure mode is silent: two different pages merge into one entry
        and one is lost. This way the failure mode is a visible duplicate
        the person can fix.
        """
        parts = urlsplit((value or "").strip())
        return urlunsplit(
            (
                parts.scheme.lower(),
                parts.netloc.lower(),
                parts.path,
                parts.query,
                parts.fragment,
            )
        )
