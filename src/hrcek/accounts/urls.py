from django.urls import path

from hrcek.accounts import views

app_name = "accounts"

urlpatterns = [
    path("welcome/", views.welcome, name="welcome"),
    path(
        "invitation/<str:token>/",
        views.invitation_accept,
        name="invitation_accept",
    ),
]
