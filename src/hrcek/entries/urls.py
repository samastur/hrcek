from django.urls import path

from hrcek.entries import views

app_name = "entries"

urlpatterns = [
    path("", views.entry_list, name="list"),
    path("new/", views.entry_create, name="create"),
    path("<int:pk>/edit/", views.entry_edit, name="edit"),
    path("<int:pk>/delete/", views.entry_delete, name="delete"),
    path("fields/", views.field_list, name="fields"),
    path("fields/<int:pk>/edit/", views.field_edit, name="field_edit"),
    path("fields/<int:pk>/delete/", views.field_delete, name="field_delete"),
]
