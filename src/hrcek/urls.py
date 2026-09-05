from django.urls import path

from hrcek.api import api

urlpatterns = [path("api/", api.urls)]
