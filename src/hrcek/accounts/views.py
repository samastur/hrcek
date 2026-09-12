from __future__ import annotations

from typing import Any

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from hrcek.accounts.allowlist import is_signup_allowed
from hrcek.accounts.errors import (
    CONFIRMATION_INVALID,
    INVITATION_INVALID,
    SIGNUP_NOT_ALLOWED,
)
from hrcek.accounts.forms import (
    ConfirmedUserAuthenticationForm,
    DisplayNameForm,
    InvitationAcceptForm,
    SignupForm,
)
from hrcek.accounts.mail import absolute_url, send_email
from hrcek.accounts.models import Invitation, User
from hrcek.accounts.tokens import make_confirmation_token, read_confirmation_token
from hrcek.core.errors import ErrorCode


def _error_page(request: HttpRequest, code: ErrorCode, hint: str = "") -> HttpResponse:
    """Render a failure with the same code and status the API would use."""
    return render(
        request,
        "accounts/message.html",
        {"code": code.code, "message": str(code.message), "hint": hint},
        status=code.http_status,
    )


@login_required
def account(request: HttpRequest) -> HttpResponse:
    return render_account(request)


def render_account(request: HttpRequest, **overrides: Any) -> HttpResponse:
    """Render the hub, letting one caller substitute a bound form.

    Each form on the page posts to its own URL. When one fails
    validation its view re-renders this page with its own form bound, so
    the person sees a single page while each view keeps one
    responsibility.
    """
    context: dict[str, Any] = {
        "display_name_form": DisplayNameForm(instance=request.user),
    }
    context.update(overrides)
    return render(request, "accounts/account.html", context)


@require_http_methods(["POST"])
@login_required
def display_name(request: HttpRequest) -> HttpResponse:
    form = DisplayNameForm(request.POST, instance=request.user)
    if not form.is_valid():
        return render_account(request, display_name_form=form)
    form.save()
    messages.success(request, _("Your display name has been updated."))
    return redirect("accounts:account")


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
            return redirect("accounts:account")
    else:
        form = InvitationAcceptForm()

    return render(
        request,
        "accounts/invitation_accept.html",
        {"form": form, "email": invitation.email},
    )


def signup(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return render(request, "accounts/signup.html", {"form": SignupForm()})

    form = SignupForm(request.POST)
    if not form.is_valid():
        return render(request, "accounts/signup.html", {"form": form})

    email = form.cleaned_data["email"]
    if not is_signup_allowed(email):
        # A refusal the visitor cannot remedy, so it gets its own page
        # and a truthful status rather than a redisplayed form.
        return _error_page(request, SIGNUP_NOT_ALLOWED)

    existing = User.objects.filter(email__iexact=email).first()
    if existing is not None:
        # Same page, different email. Anything else would turn this form
        # into a way to discover who has an account.
        send_email(
            "signup_existing_account",
            email,
            {"reset_url": absolute_url(reverse("accounts:password_reset"))},
        )
    else:
        user = User.objects.create_user(
            email=email,
            password=form.cleaned_data["password1"],
            display_name=form.cleaned_data["display_name"],
        )
        send_email(
            "email_confirmation",
            email,
            {
                "confirm_url": absolute_url(
                    reverse("accounts:confirm", args=[make_confirmation_token(user)])
                ),
                "expires_hours": settings.HRCEK_EMAIL_CONFIRMATION_EXPIRY_HOURS,
            },
        )

    # No context: the page must not vary with what we just discovered.
    return render(request, "accounts/signup_done.html")


def confirm(request: HttpRequest, token: str) -> HttpResponse:
    user = read_confirmation_token(token)
    if user is None:
        return _error_page(
            request,
            CONFIRMATION_INVALID,
            _("Sign up again to get a fresh link."),
        )
    if not user.is_email_confirmed:
        user.email_verified_at = timezone.now()
        user.save(update_fields=["email_verified_at"])
    login(request, user)
    return redirect("accounts:account")


# The landing page is the login page. redirect_authenticated_user sends
# anyone already signed in to LOGIN_REDIRECT_URL instead.
landing = LoginView.as_view(
    template_name="accounts/landing.html",
    authentication_form=ConfirmedUserAuthenticationForm,
    redirect_authenticated_user=True,
)
