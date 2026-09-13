from __future__ import annotations

from typing import cast

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from hrcek.accounts.models import User
from hrcek.entries.forms import EntryForm, FieldDefinitionForm
from hrcek.entries.models import Entry, FieldDefinition, FieldValue, Tag
from hrcek.entries.services import save_entry


@login_required
def entry_list(request: HttpRequest) -> HttpResponse:
    owner = cast("User", request.user)
    entries = Entry.objects.filter(owner=owner).prefetch_related("tags")

    tag = request.GET.get("tag", "").strip()
    if tag:
        entries = entries.filter(tags__name__iexact=tag)

    paginator = Paginator(entries, settings.ENTRIES_PER_PAGE)
    # get_page, not page: it copes with a missing, non-numeric or
    # out-of-range number instead of raising.
    page = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "entries/list.html",
        {"page": page, "tag": tag, "tags": Tag.objects.filter(owner=owner)},
    )


@login_required
def entry_create(request: HttpRequest) -> HttpResponse:
    owner = cast("User", request.user)
    if request.method != "POST":
        return render(request, "entries/form.html", {"form": EntryForm()})

    form = EntryForm(request.POST)
    if not form.is_valid():
        return render(request, "entries/form.html", {"form": form})

    # A URL already held is an update, not a duplicate.
    save_entry(
        owner,
        url=form.cleaned_data["url"],
        title=form.cleaned_data["title"],
        notes=form.cleaned_data["notes"],
        tag_names=form.tag_names(),
    )
    messages.success(request, _("Saved."))
    return redirect("entries:list")


@login_required
def entry_edit(request: HttpRequest, pk: int) -> HttpResponse:
    owner = cast("User", request.user)
    entry = get_object_or_404(Entry, pk=pk, owner=owner)

    if request.method != "POST":
        return render(
            request,
            "entries/form.html",
            {"form": EntryForm(instance=entry), "entry": entry},
        )

    form = EntryForm(request.POST, instance=entry)
    if not form.is_valid():
        return render(request, "entries/form.html", {"form": form, "entry": entry})

    save_entry(
        owner,
        url=form.cleaned_data["url"],
        title=form.cleaned_data["title"],
        notes=form.cleaned_data["notes"],
        tag_names=form.tag_names(),
    )
    messages.success(request, _("Saved."))
    return redirect("entries:list")


@login_required
def entry_delete(request: HttpRequest, pk: int) -> HttpResponse:
    owner = cast("User", request.user)
    entry = get_object_or_404(Entry, pk=pk, owner=owner)

    if request.method != "POST":
        return render(request, "entries/confirm_delete.html", {"entry": entry})

    entry.delete()
    # Deleting the entry can leave tags with nothing on them.
    Tag.prune_orphans(owner)
    messages.success(request, _("Deleted."))
    return redirect("entries:list")


@login_required
def field_list(request: HttpRequest) -> HttpResponse:
    owner = cast("User", request.user)
    if request.method == "POST":
        form = FieldDefinitionForm(owner, request.POST)
        if form.is_valid():
            definition = form.save(commit=False)
            definition.owner = owner
            definition.save()
            messages.success(request, _("Field added."))
            return redirect("entries:fields")
    else:
        form = FieldDefinitionForm(owner)

    return render(
        request,
        "entries/fields.html",
        {"form": form, "fields": FieldDefinition.objects.filter(owner=owner)},
    )


@login_required
def field_edit(request: HttpRequest, pk: int) -> HttpResponse:
    owner = cast("User", request.user)
    definition = get_object_or_404(FieldDefinition, pk=pk, owner=owner)

    if request.method == "POST":
        form = FieldDefinitionForm(owner, request.POST, instance=definition)
        if form.is_valid():
            form.save()
            messages.success(request, _("Field renamed."))
            return redirect("entries:fields")
    else:
        form = FieldDefinitionForm(owner, instance=definition)

    return render(
        request,
        "entries/field_form.html",
        {"form": form, "definition": definition},
    )


@login_required
def field_delete(request: HttpRequest, pk: int) -> HttpResponse:
    owner = cast("User", request.user)
    definition = get_object_or_404(FieldDefinition, pk=pk, owner=owner)

    if request.method != "POST":
        return render(
            request,
            "entries/field_confirm_delete.html",
            {
                "definition": definition,
                # The count is what makes the consequence real to
                # somebody about to press the button.
                "value_count": FieldValue.objects.filter(definition=definition).count(),
            },
        )

    definition.delete()
    messages.success(request, _("Field deleted."))
    return redirect("entries:fields")
