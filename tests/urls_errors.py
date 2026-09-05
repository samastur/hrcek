"""A throwaway API whose endpoints fail on purpose.

Mounted via override_settings(ROOT_URLCONF="tests.urls_errors") so the
exception handlers can be exercised through the full middleware stack
without adding fault-injection routes to the real API.
"""

from django.http import Http404
from django.urls import path
from ninja import NinjaAPI, Schema

from hrcek.api import register_exception_handlers
from hrcek.core.errors import NOT_FOUND, HrcekError

failing_api = NinjaAPI(title="Failing", version="test", urls_namespace="failing")
register_exception_handlers(failing_api)


class Payload(Schema):
    count: int


@failing_api.get("/known")
def raise_known(request):
    raise HrcekError(NOT_FOUND, {"field": "url"})


@failing_api.get("/django-404")
def raise_django_404(request):
    raise Http404


@failing_api.get("/boom")
def raise_unexpected(request):
    raise RuntimeError("database on fire, password is hunter2")


@failing_api.post("/validated")
def validated(request, payload: Payload):
    return {"count": payload.count}


urlpatterns = [path("api/", failing_api.urls)]
