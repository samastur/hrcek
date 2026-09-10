from __future__ import annotations

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from hrcek.accounts.forms import UserChangeForm, UserCreationForm
from hrcek.accounts.models import (
    AllowedDomain,
    AllowedEmail,
    ApiToken,
    Invitation,
    User,
)


class UserAdmin(BaseUserAdmin):
    add_form = UserCreationForm
    form = UserChangeForm
    model = User

    list_display = (
        "email",
        "display_name",
        "is_active",
        "is_staff",
        "email_verified_at",
    )
    list_filter = ("is_active", "is_staff", "is_superuser")
    search_fields = ("email", "display_name")
    ordering = ("email",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Profile"), {"fields": ("display_name",)}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            _("Important dates"),
            {"fields": ("last_login", "date_joined", "email_verified_at")},
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "display_name", "password1", "password2"),
            },
        ),
    )


admin.site.register(User, UserAdmin)


class ApiTokenAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "user",
        "created_at",
        "last_used_at",
        "expires_at",
        "revoked_at",
    )
    readonly_fields = ("created_at", "last_used_at")

    def get_fields(self, request, obj=None):
        if obj is None:
            return ("user", "name", "expires_at")
        return (
            "user",
            "name",
            "expires_at",
            "revoked_at",
            "created_at",
            "last_used_at",
        )

    def save_model(self, request, obj, form, change):
        if change:
            super().save_model(request, obj, form, change)
            return
        raw = ApiToken.new_raw_token()
        obj.token_hash = ApiToken.hash_token(raw)
        super().save_model(request, obj, form, change)
        # The only moment this value will ever be visible.
        self.message_user(
            request,
            _("API token created. Copy it now, it will not be shown again: %(token)s")
            % {"token": raw},
            level=messages.WARNING,
        )


admin.site.register(ApiToken, ApiTokenAdmin)


class AllowedEmailAdmin(admin.ModelAdmin):
    list_display = ("email", "note", "created_at")
    search_fields = ("email", "note")


class AllowedDomainAdmin(admin.ModelAdmin):
    list_display = ("domain", "note", "created_at")
    search_fields = ("domain", "note")


admin.site.register(AllowedEmail, AllowedEmailAdmin)
admin.site.register(AllowedDomain, AllowedDomainAdmin)


class InvitationAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "invited_by",
        "created_at",
        "expires_at",
        "accepted_at",
        "revoked_at",
    )
    search_fields = ("email",)
    actions = ("resend", "revoke")

    def get_fields(self, request, obj=None):
        if obj is None:
            return ("email",)
        return (
            "email",
            "invited_by",
            "created_at",
            "expires_at",
            "accepted_at",
            "revoked_at",
        )

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return ()
        return (
            "email",
            "invited_by",
            "created_at",
            "expires_at",
            "accepted_at",
            "revoked_at",
        )

    def save_model(self, request, obj, form, change):
        if change:
            super().save_model(request, obj, form, change)
            return
        # Creating an invitation is the act of sending it. Saving obj
        # directly would leave a row with no token.
        Invitation.issue(obj.email, request.user)
        self.message_user(
            request, _("Invitation sent to %(email)s.") % {"email": obj.email}
        )

    @admin.action(description=_("Resend the selected invitations"))
    def resend(self, request, queryset):
        for invitation in queryset:
            Invitation.issue(invitation.email, request.user)
        self.message_user(request, _("Invitations resent."))

    @admin.action(description=_("Revoke the selected invitations"))
    def revoke(self, request, queryset):
        queryset.filter(accepted_at__isnull=True).update(revoked_at=timezone.now())
        self.message_user(request, _("Invitations revoked."))


admin.site.register(Invitation, InvitationAdmin)
