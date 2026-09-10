from django.contrib import admin
from django.urls import include, path

from hrcek.api import api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("hrcek.accounts.urls")),
    path("api/", api.urls),
]
