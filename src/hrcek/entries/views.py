from __future__ import annotations

from typing import cast

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from hrcek.accounts.models import User
from hrcek.entries.models import Entry, Tag


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
