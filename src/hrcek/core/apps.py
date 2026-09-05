from django.apps import AppConfig
from django.utils.module_loading import autodiscover_modules
from django.utils.translation import gettext_lazy as _


class CoreConfig(AppConfig):
    name = "hrcek.core"
    verbose_name = _("Core")

    def ready(self) -> None:
        # Import every app's ``errors`` module so all codes are
        # registered — and any duplicate raises — at startup rather
        # than on the first request that happens to need one.
        autodiscover_modules("errors")
