from django.urls import path

from hrcek.entries import views

app_name = "entries"

urlpatterns = [
    path("", views.entry_list, name="list"),
    # Replaced with real views in the next branch; the list template
    # references both names, and an unresolvable name is a 500.
    path("new/", views.entry_list, name="create"),
    path("<int:pk>/edit/", views.entry_list, name="edit"),
]
