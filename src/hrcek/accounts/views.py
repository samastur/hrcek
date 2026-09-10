from __future__ import annotations

from django.contrib.auth import login
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _

from hrcek.accounts.errors import INVITATION_INVALID
from hrcek.accounts.forms import InvitationAcceptForm
from hrcek.accounts.models import Invitation, User
from hrcek.core.errors import ErrorCode


def _error_page(request: HttpRequest, code: ErrorCode, hint: str = "") -> HttpResponse:
    """Render a failure with the same code and status the API would use."""
    return render(
        request,
        "accounts/message.html",
        {"code": code.code, "message": str(code.message), "hint": hint},
        status=code.http_status,
    )


def welcome(request: HttpRequest) -> HttpResponse:
    """Where the flows land.

    Hrcek has no application UI yet, and a redirect to "/" would 404.
    """
    return render(request, "accounts/welcome.html")


def invitation_accept(request: HttpRequest, token: str) -> HttpResponse:
    invitation = Invitation.find_pending(token)
    if invitation is None:
        return _error_page(
            request,
            INVITATION_INVALID,
            _("Ask whoever invited you to send a new invitation."),
        )

    if request.method == "POST":
        form = InvitationAcceptForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                email=invitation.email,
                password=form.cleaned_data["password1"],
                display_name=form.cleaned_data["display_name"],
                # The link proved control of the inbox; a second
                # confirmation round would be theatre.
                email_verified_at=timezone.now(),
            )
            invitation.accepted_at = timezone.now()
            invitation.save(update_fields=["accepted_at"])
            login(request, user)
            return redirect("accounts:welcome")
    else:
        form = InvitationAcceptForm()

    return render(
        request,
        "accounts/invitation_accept.html",
        {"form": form, "email": invitation.email},
    )
