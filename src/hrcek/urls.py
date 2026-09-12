from django.contrib import admin
from django.urls import include, path

from hrcek.accounts import views as account_views
from hrcek.api import api

urlpatterns = [
    path("", account_views.landing, name="landing"),
    path("admin/", admin.site.urls),
    path("accounts/", include("hrcek.accounts.urls")),
    path("entries/", include("hrcek.entries.urls")),
    path("api/", api.urls),
]
