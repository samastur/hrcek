from __future__ import annotations

from typing import cast

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from hrcek.accounts.models import User
from hrcek.collections.forms import CollectionForm
from hrcek.collections.models import Collection
from hrcek.collections.services import add_entry, remove_entry
from hrcek.core.errors import HrcekError
from hrcek.entries.models import Entry


@login_required
def collection_list(request: HttpRequest) -> HttpResponse:
    owner = cast("User", request.user)
    return render(
        request,
        "collections/list.html",
        {"collections": Collection.objects.filter(owner=owner)},
    )


@login_required
def collection_create(request: HttpRequest) -> HttpResponse:
    owner = cast("User", request.user)
    if request.method != "POST":
        return render(request, "collections/form.html", {"form": CollectionForm(owner)})

    form = CollectionForm(owner, request.POST)
    if not form.is_valid():
        return render(request, "collections/form.html", {"form": form})

    collection = form.save(commit=False)
    collection.owner = owner
    collection.save()
    messages.success(request, _("Collection made."))
    return redirect("collections:detail", pk=collection.pk)


@login_required
def collection_detail(request: HttpRequest, pk: int) -> HttpResponse:
    owner = cast("User", request.user)
    collection = get_object_or_404(Collection, pk=pk, owner=owner)
    # Only what is not already in it, and only where membership is
    # chosen by hand at all.
    candidates = (
        Entry.objects.filter(owner=owner).exclude(
            collection_memberships__collection=collection
        )
        if collection.kind == Collection.MANUAL
        else Entry.objects.none()
    )
    return render(
        request,
        "collections/detail.html",
        {
            "collection": collection,
            "entries": collection.entries().prefetch_related("tags"),
            "candidates": candidates,
        },
    )


@login_required
def collection_edit(request: HttpRequest, pk: int) -> HttpResponse:
    owner = cast("User", request.user)
    collection = get_object_or_404(Collection, pk=pk, owner=owner)
    if request.method != "POST":
        return render(
            request,
            "collections/form.html",
            {
                "form": CollectionForm(owner, instance=collection),
                "collection": collection,
            },
        )

    form = CollectionForm(owner, request.POST, instance=collection)
    if not form.is_valid():
        return render(
            request,
            "collections/form.html",
            {"form": form, "collection": collection},
        )
    form.save()
    messages.success(request, _("Saved."))
    return redirect("collections:detail", pk=collection.pk)


@login_required
def collection_delete(request: HttpRequest, pk: int) -> HttpResponse:
    owner = cast("User", request.user)
    collection = get_object_or_404(Collection, pk=pk, owner=owner)
    if request.method != "POST":
        return render(
            request, "collections/confirm_delete.html", {"collection": collection}
        )
    collection.delete()
    messages.success(request, _("Collection deleted. Its entries are untouched."))
    return redirect("collections:list")


@require_http_methods(["POST"])
@login_required
def collection_add_entry(request: HttpRequest, pk: int) -> HttpResponse:
    owner = cast("User", request.user)
    collection = get_object_or_404(Collection, pk=pk, owner=owner)
    # Scoped to the owner, so somebody else's id is simply not found.
    entry = get_object_or_404(Entry, pk=request.POST.get("entry"), owner=owner)
    try:
        add_entry(collection, entry)
    except HrcekError:
        # The only reachable cause is a label collection, whose page
        # offers no such form; treat it as a wrong turn, not a crash.
        messages.error(request, _("That entry cannot be added here."))
    return redirect("collections:detail", pk=collection.pk)


@require_http_methods(["POST"])
@login_required
def collection_remove_entry(
    request: HttpRequest, pk: int, entry_pk: int
) -> HttpResponse:
    owner = cast("User", request.user)
    collection = get_object_or_404(Collection, pk=pk, owner=owner)
    entry = get_object_or_404(Entry, pk=entry_pk, owner=owner)
    remove_entry(collection, entry)
    return redirect("collections:detail", pk=collection.pk)


def _shared_context(collection: Collection) -> dict[str, object]:
    """What both shared pages need.

    `visible_fields` is a set of ids rather than objects, because the
    template asks the question once per field per entry.
    """
    return {
        "collection": collection,
        "entries": collection.entries().prefetch_related(
            "tags", "field_values__definition"
        ),
        "visible_field_ids": set(
            collection.visible_fields.values_list("pk", flat=True)
        ),
    }


def unlisted_collection(request: HttpRequest, secret: str) -> HttpResponse:
    """A collection shared by link.

    The secret is the whole of the access control, so a wrong one is a
    404 like any other unknown address — and a collection that has
    stopped being unlisted stops answering here at once.
    """
    collection = get_object_or_404(
        Collection, secret=secret, visibility=Collection.UNLISTED
    )
    response = render(request, "collections/shared.html", _shared_context(collection))
    # A search engine that learned the link would end the point of it.
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


def public_collection(request: HttpRequest, namespace: str, slug: str) -> HttpResponse:
    """A collection anybody may read, at an address anybody may guess."""
    collection = get_object_or_404(
        Collection,
        owner__namespace__iexact=namespace,
        slug=slug,
        visibility=Collection.PUBLIC,
    )
    return render(request, "collections/shared.html", _shared_context(collection))
