from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from hrcek.accounts import views
from hrcek.accounts.forms import HrcekPasswordResetForm

app_name = "accounts"

urlpatterns = [
    path("me/", views.account, name="account"),
    path("me/display-name/", views.display_name, name="display_name"),
    path("signup/", views.signup, name="signup"),
    path("confirm/<str:token>/", views.confirm, name="confirm"),
    path(
        "invitation/<str:token>/",
        views.invitation_accept,
        name="invitation_accept",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path(
        "password/reset/",
        auth_views.PasswordResetView.as_view(
            form_class=HrcekPasswordResetForm,
            template_name="accounts/password_reset.html",
            success_url=reverse_lazy("accounts:password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "password/reset/sent/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="accounts/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "password/reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html",
            success_url=reverse_lazy("accounts:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "password/reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
]
