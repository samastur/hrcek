"""The addresses a collection is shared at.

Kept out of `urls.py` because these sit at the root — `/c/...` and
`/u/...` — rather than under `/collections/`, while still belonging to
the same URL namespace.
"""

from django.urls import path

from hrcek.collections import views

# Its own namespace: two includes cannot share one, and "shared"
# says what these addresses are for.
app_name = "shared"

urlpatterns = [
    path("c/<str:secret>/", views.unlisted_collection, name="unlisted"),
    path(
        "u/<str:namespace>/<slug:slug>/",
        views.public_collection,
        name="public",
    ),
]
