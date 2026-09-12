from django.urls import path

from hrcek.entries import views

app_name = "entries"

urlpatterns = [
    path("", views.entry_list, name="list"),
    path("new/", views.entry_create, name="create"),
    path("<int:pk>/edit/", views.entry_edit, name="edit"),
    path("<int:pk>/delete/", views.entry_delete, name="delete"),
]
