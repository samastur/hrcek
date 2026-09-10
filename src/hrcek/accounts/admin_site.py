from __future__ import annotations

from django.contrib import admin
from django.contrib.admin.apps import AdminConfig
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _


class HrcekAdminSite(admin.AdminSite):
    site_title = _("Hrcek administration")
    site_header = _("Hrcek")
    index_title = _("Administration")

    def has_permission(self, request: HttpRequest) -> bool:
        """Staff only, and only with a confirmed email address.

        Email verification is kept out of the authentication backend so
        that failures stay distinguishable, which means every entry
        point applies it itself. This is that application for the admin.
        """
        user = request.user
        return bool(
            user.is_active
            and getattr(user, "is_staff", False)
            and getattr(user, "email_verified_at", None) is not None
        )


class HrcekAdminConfig(AdminConfig):
    """Replace the default admin site with ours.

    This lives here rather than in apps.py because Django scans that
    module for the app's own AppConfig, and every AppConfig subclass in
    it — including imported ones — counts as a candidate.
    """

    default_site = "hrcek.accounts.admin_site.HrcekAdminSite"
